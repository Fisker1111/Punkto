package xyz.punkto.android.data

import android.content.Context
import android.content.SharedPreferences
import android.util.Log
import xyz.punkto.android.BuildConfig
import xyz.punkto.android.network.AtomPostBody
import xyz.punkto.android.network.AtomPostResponse
import xyz.punkto.android.network.FeedAtom
import xyz.punkto.android.network.RetrofitClient
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.security.MessageDigest

/**
 * NodeRepository — manages synchronisation with one or more Punkto nodes.
 *
 * Responsibilities:
 *  - Discover peer nodes via GET /info
 *  - Sync the atom feed per node using a per-node byte-offset cursor
 *  - Deduplicate atoms by SHA-256 of canonical JSON (excluding "sig" field)
 *  - Persist new atoms to Room
 *  - POST new atoms to the primary node
 */
class NodeRepository(
    context: Context,
    private val atomDao: AtomDao
) {
    private val appContext = context.applicationContext
    private val prefs: SharedPreferences =
        appContext.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)

    // -------------------------------------------------------------------------
    // Public API
    // -------------------------------------------------------------------------

    /**
     * Sync all known nodes (starting from the bootstrapped set, then peers discovered
     * via /info). Returns the total number of new atoms persisted.
     */
    suspend fun syncAll(): Int = withContext(Dispatchers.IO) {
        val nodes = collectNodes()
        Log.d(TAG, "syncAll: nodes=$nodes")
        var total = 0
        for (nodeUrl in nodes) {
            try {
                total += syncNode(nodeUrl)
            } catch (e: Exception) {
                Log.w(TAG, "syncNode failed for $nodeUrl: ${e.message}")
            }
        }
        total
    }

    /**
     * POST a new atom to the primary node and persist it locally.
     * Returns the server-assigned atom_id on success.
     */
    suspend fun postAtom(
        punkto: String,
        t: Long,
        f: String?,
        x: String?
    ): Result<AtomPostResponse> = withContext(Dispatchers.IO) {
        try {
            val body = AtomPostBody(punkto = punkto, t = t, f = f, x = x)
            val api = RetrofitClient.buildApi(BuildConfig.DEFAULT_NODE_URL)
            val response = api.postAtom(body)

            // Build local canonical map (excluding sig) for dedup
            val canonicalMap = buildCanonicalMap(punkto, t, f, x)
            val atomId = computeAtomId(canonicalMap)

            // Persist locally (ignore if already present)
            val atom = Atom(
                punkto = punkto,
                t = t,
                f = f,
                x = x,
                atomId = atomId,
                nodeUrl = BuildConfig.DEFAULT_NODE_URL
            )
            atomDao.insert(atom)

            Result.success(response)
        } catch (e: Exception) {
            Log.e(TAG, "postAtom failed: ${e.message}", e)
            Result.failure(e)
        }
    }

    // -------------------------------------------------------------------------
    // Private helpers
    // -------------------------------------------------------------------------

    /**
     * Collect the set of nodes to sync: bootstrap defaults + any peers
     * discovered from the primary node's /info response.
     */
    private suspend fun collectNodes(): Set<String> {
        val nodes = mutableSetOf(
            BuildConfig.DEFAULT_NODE_URL,
            BuildConfig.NODE_URL_APP1,
            BuildConfig.NODE_URL_APP2
        )
        // Discover additional peers from primary node /info
        try {
            val api = RetrofitClient.buildApi(BuildConfig.DEFAULT_NODE_URL)
            val info = api.getInfo()
            info.peers?.forEach { peer ->
                val normalised = peer.trimEnd('/')
                if (normalised.startsWith("http")) {
                    nodes.add(normalised)
                }
            }
        } catch (e: Exception) {
            Log.w(TAG, "collectNodes: /info failed: ${e.message}")
        }
        return nodes
    }

    /**
     * Sync a single node: fetch feed since stored cursor, persist new atoms,
     * update cursor. Returns count of newly inserted atoms.
     */
    private suspend fun syncNode(nodeUrl: String): Int {
        val cursorKey = "cursor_$nodeUrl"
        val cursor = prefs.getLong(cursorKey, 0L)
        Log.d(TAG, "syncNode: $nodeUrl cursor=$cursor")

        val api = RetrofitClient.buildApi(nodeUrl)
        val feedResponse = api.getFeed(since = cursor)

        val feedAtoms = feedResponse.atoms ?: emptyList()
        val newCursor = feedResponse.cursor ?: cursor

        if (feedAtoms.isEmpty()) {
            // Still update cursor in case the node advanced
            if (newCursor > cursor) {
                prefs.edit().putLong(cursorKey, newCursor).apply()
            }
            return 0
        }

        val toInsert = feedAtoms.mapNotNull { fa -> feedAtomToEntity(fa, nodeUrl) }
        val inserted = atomDao.insertAll(toInsert)
        val newCount = inserted.count { it != -1L }

        // Persist updated cursor
        prefs.edit().putLong(cursorKey, newCursor).apply()
        Log.d(TAG, "syncNode: $nodeUrl inserted=$newCount/${feedAtoms.size} newCursor=$newCursor")
        return newCount
    }

    /**
     * Convert a FeedAtom (wire format) to a Room [Atom] entity.
     * Computes atom_id as SHA-256 of canonical JSON (sorted keys, no whitespace,
     * excludes "sig" field per spec v0.3).
     *
     * Returns null if the atom is malformed (missing required fields).
     */
    private fun feedAtomToEntity(fa: FeedAtom, nodeUrl: String): Atom? {
        val punkto = fa.punkto ?: return null
        val t = fa.t ?: return null

        val canonicalMap = buildCanonicalMap(punkto, t, fa.f, fa.x)
        val atomId = fa.atomId ?: computeAtomId(canonicalMap)

        return Atom(
            punkto = punkto,
            t = t,
            f = fa.f,
            x = fa.x,
            atomId = atomId,
            nodeUrl = nodeUrl
        )
    }

    /**
     * Build the canonical map of atom fields (excluding "sig").
     * Only includes non-null fields to match server canonical form.
     */
    private fun buildCanonicalMap(
        punkto: String,
        t: Long,
        f: String?,
        x: String?
    ): Map<String, Any> {
        val map = mutableMapOf<String, Any>(
            "punkto" to punkto,
            "t" to t
        )
        if (!f.isNullOrEmpty()) map["f"] = f
        if (!x.isNullOrEmpty()) map["x"] = x
        return map
    }

    /**
     * Compute atom_id: SHA-256 of canonical JSON.
     * Canonical JSON: keys sorted lexicographically, no whitespace, UTF-8.
     * The "sig" field is excluded per spec v0.3.
     */
    fun computeAtomId(atom: Map<String, Any>): String {
        val sorted = atom.toSortedMap()
        // Build JSON manually to avoid library whitespace / ordering surprises
        val json = buildString {
            append('{')
            sorted.entries.forEachIndexed { idx, (k, v) ->
                if (idx > 0) append(',')
                append('"').append(k).append('"').append(':')
                when (v) {
                    is String -> append('"').append(v.replace("\\", "\\\\").replace("\"", "\\\"")).append('"')
                    is Long   -> append(v)
                    is Int    -> append(v)
                    is Boolean -> append(v)
                    else      -> append('"').append(v.toString()).append('"')
                }
            }
            append('}')
        }
        return sha256hex(json.toByteArray(Charsets.UTF_8))
    }

    private fun sha256hex(bytes: ByteArray): String {
        val digest = MessageDigest.getInstance("SHA-256")
        return digest.digest(bytes).joinToString("") { "%02x".format(it) }
    }

    companion object {
        private const val TAG = "NodeRepository"
        private const val PREFS_NAME = "punkto_sync"

        // Singleton instance
        @Volatile
        private var INSTANCE: NodeRepository? = null

        fun getInstance(context: Context, atomDao: AtomDao): NodeRepository {
            return INSTANCE ?: synchronized(this) {
                INSTANCE ?: NodeRepository(context, atomDao).also { INSTANCE = it }
            }
        }
    }
}
