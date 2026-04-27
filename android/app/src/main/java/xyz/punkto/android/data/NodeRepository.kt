package xyz.punkto.android.data

import android.content.Context
import android.content.SharedPreferences
import android.util.Log
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
 * Implements protocol-native client-side load balancing per punkto.sync.md §5b:
 *  - Maintains a seed list of known nodes with in-memory health tracking
 *  - Round-robin POST over healthy nodes with automatic failure/recovery handling
 *  - Discovers additional peers via GET /info from all known nodes
 *  - Syncs the atom feed from ALL known nodes regardless of health
 *  - Deduplicates atoms by SHA-256 of canonical JSON (excluding "sig" field)
 *  - Persists new atoms to Room
 */
class NodeRepository(
    context: Context,
    private val atomDao: AtomDao
) {
    private val appContext = context.applicationContext
    private val prefs: SharedPreferences =
        appContext.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)

    // -------------------------------------------------------------------------
    // Health model
    // -------------------------------------------------------------------------

    enum class NodeHealth { OK, FAILING, UNAVAILABLE, RECOVERING }

    data class NodeState(
        val url: String,
        var health: NodeHealth = NodeHealth.OK,
        var failures: Int = 0,
        var unavailableSince: Long = 0L
    )

    // In-memory node registry — resets on process restart
    private val nodeStates: MutableMap<String, NodeState> = LinkedHashMap()

    // Round-robin write pointer
    @Volatile private var writeIndex: Int = 0

    init {
        // Seed the registry with hardcoded defaults
        SEED_NODES.forEach { url ->
            nodeStates.getOrPut(url) { NodeState(url) }
        }
    }

    // -------------------------------------------------------------------------
    // Public API
    // -------------------------------------------------------------------------

    /**
     * Discover peers by querying GET /info on every known seed node.
     * Any new peer URLs found in the peers[] array are added to nodeStates.
     */
    suspend fun discoverPeers() = withContext(Dispatchers.IO) {
        val seeds = nodeStates.keys.toList()
        for (seedUrl in seeds) {
            try {
                val api = RetrofitClient.buildApi(seedUrl)
                val info = api.getInfo()
                info.peers?.forEach { peer ->
                    val normalised = peer.trimEnd('/')
                    if (normalised.startsWith("http")) {
                        nodeStates.getOrPut(normalised) { NodeState(normalised) }
                    }
                }
                Log.d(TAG, "discoverPeers: $seedUrl ok, peers=${info.peers}")
            } catch (e: Exception) {
                Log.w(TAG, "discoverPeers: /info failed for $seedUrl: ${e.message}")
            }
        }
    }

    /**
     * POST a new atom using round-robin over healthy nodes.
     *
     * Candidate list = nodes where health != UNAVAILABLE,
     * except RECOVERING nodes are included only if 60 s has elapsed since unavailableSince.
     *
     * On success: mark node OK, return result.
     * On failure: increment failures; mark FAILING at 2+, UNAVAILABLE at 5+.
     * If all candidates fail: return failure.
     */
    suspend fun postAtom(
        punkto: String,
        t: Long,
        f: String?,
        x: String?
    ): Result<AtomPostResponse> = withContext(Dispatchers.IO) {
        val body = AtomPostBody(punkto = punkto, t = t, f = f, x = x)
        val candidates = getWriteCandidates()

        if (candidates.isEmpty()) {
            Log.e(TAG, "postAtom: no healthy nodes available")
            return@withContext Result.failure(Exception("No healthy nodes available"))
        }

        val startIndex = writeIndex % candidates.size

        for (i in candidates.indices) {
            val state = candidates[(startIndex + i) % candidates.size]
            try {
                val api = RetrofitClient.buildApi(state.url)
                val response = api.postAtom(body)

                // Success — mark node healthy, advance write pointer
                markSuccess(state)
                writeIndex = (startIndex + i + 1) % candidates.size
                Log.d(TAG, "postAtom: success via ${state.url}")

                // Persist locally
                val canonicalMap = buildCanonicalMap(punkto, t, f, x)
                val atomId = computeAtomId(canonicalMap)
                val atom = Atom(
                    punkto = punkto,
                    t = t,
                    f = f,
                    x = x,
                    atomId = atomId,
                    nodeUrl = state.url
                )
                atomDao.insert(atom)

                return@withContext Result.success(response)
            } catch (e: Exception) {
                Log.w(TAG, "postAtom: failed via ${state.url}: ${e.message}")
                markFailure(state)
            }
        }

        Log.e(TAG, "postAtom: all candidates failed")
        Result.failure(Exception("All nodes failed"))
    }

    /**
     * Sync feed from ALL known nodes regardless of health.
     * Returns total number of new atoms persisted.
     */
    suspend fun syncAll(): Int = withContext(Dispatchers.IO) {
        val nodes = nodeStates.keys.toList()
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

    /** Returns count of nodes currently considered healthy (OK or FAILING). */
    fun getHealthyNodeCount(): Int =
        nodeStates.values.count { it.health == NodeHealth.OK || it.health == NodeHealth.FAILING }

    /** Returns a snapshot of all tracked node states for UI/debug. */
    fun getAllNodes(): List<NodeState> = nodeStates.values.toList()

    // -------------------------------------------------------------------------
    // Private — health management
    // -------------------------------------------------------------------------

    /**
     * Build the candidate list for writes:
     * - OK and FAILING nodes always included
     * - RECOVERING nodes included if 60 s elapsed since unavailableSince
     * - UNAVAILABLE nodes promoted to RECOVERING if 60 s elapsed, then included
     * - Pure UNAVAILABLE (< 60 s) excluded
     */
    private fun getWriteCandidates(): List<NodeState> {
        val now = System.currentTimeMillis()
        return nodeStates.values.filter { state ->
            when (state.health) {
                NodeHealth.OK, NodeHealth.FAILING -> true
                NodeHealth.RECOVERING -> true
                NodeHealth.UNAVAILABLE -> {
                    if (now - state.unavailableSince > RECOVERY_MS) {
                        state.health = NodeHealth.RECOVERING
                        true
                    } else false
                }
            }
        }
    }

    private fun markSuccess(state: NodeState) {
        state.health = NodeHealth.OK
        state.failures = 0
        state.unavailableSince = 0L
    }

    private fun markFailure(state: NodeState) {
        state.failures++
        when {
            state.failures >= UNAVAILABLE_THRESHOLD -> {
                state.health = NodeHealth.UNAVAILABLE
                state.unavailableSince = System.currentTimeMillis()
            }
            state.failures >= FAILING_THRESHOLD -> state.health = NodeHealth.FAILING
        }
    }

    // -------------------------------------------------------------------------
    // Private — sync
    // -------------------------------------------------------------------------

    private suspend fun syncNode(nodeUrl: String): Int {
        val cursorKey = "cursor_$nodeUrl"
        val cursor = prefs.getLong(cursorKey, 0L)
        Log.d(TAG, "syncNode: $nodeUrl cursor=$cursor")

        val api = RetrofitClient.buildApi(nodeUrl)
        val feedResponse = api.getFeed(since = cursor)

        val feedAtoms = feedResponse.atoms ?: emptyList()
        val newCursor = feedResponse.cursor ?: cursor

        if (feedAtoms.isEmpty()) {
            if (newCursor > cursor) {
                prefs.edit().putLong(cursorKey, newCursor).apply()
            }
            return 0
        }

        val toInsert = feedAtoms.mapNotNull { fa -> feedAtomToEntity(fa, nodeUrl) }
        val inserted = atomDao.insertAll(toInsert)
        val newCount = inserted.count { it != -1L }

        prefs.edit().putLong(cursorKey, newCursor).apply()
        Log.d(TAG, "syncNode: $nodeUrl inserted=$newCount/${feedAtoms.size} newCursor=$newCursor")
        return newCount
    }

    // -------------------------------------------------------------------------
    // Private — atom helpers
    // -------------------------------------------------------------------------

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

    private fun buildCanonicalMap(
        punkto: String,
        t: Long,
        f: String?,
        x: String?
    ): Map<String, Any> {
        val map = mutableMapOf<String, Any>("punkto" to punkto, "t" to t)
        if (!f.isNullOrEmpty()) map["f"] = f
        if (!x.isNullOrEmpty()) map["x"] = x
        return map
    }

    fun computeAtomId(atom: Map<String, Any>): String {
        val sorted = atom.toSortedMap()
        val json = buildString {
            append('{')
            sorted.entries.forEachIndexed { idx, (k, v) ->
                if (idx > 0) append(',')
                append('"').append(k).append('"').append(':')
                when (v) {
                    is String  -> append('"').append(v.replace("\\", "\\\\").replace("\"", "\\\"")).append('"')
                    is Long    -> append(v)
                    is Int     -> append(v)
                    is Boolean -> append(v)
                    else       -> append('"').append(v.toString()).append('"')
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

    // -------------------------------------------------------------------------
    // Companion
    // -------------------------------------------------------------------------

    companion object {
        private const val TAG = "NodeRepository"
        private const val PREFS_NAME = "punkto_sync"
        private const val FAILING_THRESHOLD = 2
        private const val UNAVAILABLE_THRESHOLD = 5
        private const val RECOVERY_MS = 60_000L

        /** Hardcoded seed nodes — overridable at runtime via discoverPeers(). */
        private val SEED_NODES = listOf(
            "https://app1.punkto.xyz",
            "https://app2.punkto.xyz"
        )

        @Volatile
        private var INSTANCE: NodeRepository? = null

        fun getInstance(context: Context, atomDao: AtomDao): NodeRepository {
            return INSTANCE ?: synchronized(this) {
                INSTANCE ?: NodeRepository(context, atomDao).also { INSTANCE = it }
            }
        }
    }
}
