package xyz.punkto.android.network

import com.google.gson.annotations.SerializedName
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Query

// ---------------------------------------------------------------------------
// API interface
// ---------------------------------------------------------------------------

interface PunktoApiService {

    /**
     * GET /info
     * Returns node metadata and known peers.
     */
    @GET("info")
    suspend fun getInfo(): NodeInfo

    /**
     * GET /feed?since=<byte_offset>
     * Returns atoms after the given byte cursor.
     */
    @GET("feed")
    suspend fun getFeed(
        @Query("since") since: Long = 0L
    ): FeedResponse

    /**
     * POST /atom
     * Publishes a new atom to the node.
     */
    @POST("atom")
    suspend fun postAtom(
        @Body body: AtomPostBody
    ): AtomPostResponse
}

// ---------------------------------------------------------------------------
// Wire-format data classes
// ---------------------------------------------------------------------------

/**
 * Response from GET /info
 * { "node": "...", "version": "...", "capabilities": [...], "peers": [...] }
 */
data class NodeInfo(
    @SerializedName("node")         val node: String? = null,
    @SerializedName("version")      val version: String? = null,
    @SerializedName("capabilities") val capabilities: List<String>? = null,
    @SerializedName("peers")        val peers: List<String>? = null
)

/**
 * Response from GET /feed
 * { "cursor": <long>, "atoms": [ {punkto, t, f?, x?, atom_id?}, ... ] }
 */
data class FeedResponse(
    @SerializedName("cursor") val cursor: Long? = null,
    @SerializedName("atoms")  val atoms: List<FeedAtom>? = null
)

/**
 * A single atom as returned in the feed.
 */
data class FeedAtom(
    @SerializedName("punkto")   val punkto: String? = null,
    @SerializedName("t")        val t: Long? = null,
    @SerializedName("f")        val f: String? = null,
    @SerializedName("x")        val x: String? = null,
    @SerializedName("atom_id")  val atomId: String? = null
)

/**
 * Body for POST /atom
 * { "punkto": "p:<hash>", "t": <unix_ms>, "f": "<author>", "x": "<text>" }
 * Null fields are omitted from serialization.
 */
data class AtomPostBody(
    @SerializedName("punkto") val punkto: String,
    @SerializedName("t")      val t: Long,
    @SerializedName("f")      val f: String? = null,
    @SerializedName("x")      val x: String? = null
)

/**
 * Response from POST /atom
 * { "status": "ok", "atom_id": "<sha256>", "cursor": <long>, "punkto": "p:<hash>" }
 */
data class AtomPostResponse(
    @SerializedName("status")   val status: String? = null,
    @SerializedName("atom_id")  val atomId: String? = null,
    @SerializedName("cursor")   val cursor: Long? = null,
    @SerializedName("punkto")   val punkto: String? = null
)
