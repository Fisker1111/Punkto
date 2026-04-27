package xyz.punkto.android.ui

import android.app.Application
import android.location.Location
import android.util.Log
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import androidx.work.Constraints
import androidx.work.NetworkType
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.WorkManager
import xyz.punkto.android.BuildConfig
import xyz.punkto.android.data.Atom
import xyz.punkto.android.data.NodeRepository
import xyz.punkto.android.data.PunktoDatabase
import xyz.punkto.android.geohash.Geohash3D
import xyz.punkto.android.network.SyncWorker
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

class AtomViewModel(application: Application) : AndroidViewModel(application) {

    private val db = PunktoDatabase.getInstance(application)
    private val atomDao = db.atomDao()
    private val repository = NodeRepository.getInstance(application, atomDao)

    // -------------------------------------------------------------------------
    // Public state
    // -------------------------------------------------------------------------

    /** All atoms from the local Room DB, ordered newest-first. */
    val atoms: StateFlow<List<Atom>> = atomDao.getAll()
        .stateIn(
            scope = viewModelScope,
            started = SharingStarted.WhileSubscribed(5_000),
            initialValue = emptyList()
        )

    /** Most-recent GPS fix received from FusedLocationProviderClient. */
    private val _currentLocation = MutableStateFlow<Location?>(null)
    val currentLocation: StateFlow<Location?> = _currentLocation.asStateFlow()

    /** Per-operation busy/error state for the UI. */
    private val _postResult = MutableStateFlow<PostResult>(PostResult.Idle)
    val postResult: StateFlow<PostResult> = _postResult.asStateFlow()

    /** Sync activity indicator for the UI sync dot. */
    private val _isSyncing = MutableStateFlow(false)
    val isSyncing: StateFlow<Boolean> = _isSyncing.asStateFlow()

    // -------------------------------------------------------------------------
    // Pagination state (B2)
    // -------------------------------------------------------------------------

    private var currentCursor: Int = 0

    // -------------------------------------------------------------------------
    // Public actions
    // -------------------------------------------------------------------------

    /**
     * Update the current GPS location — called by MapFragment on each fix.
     */
    fun updateLocation(location: Location) {
        _currentLocation.value = location
    }

    /**
     * Encode coordinates to a Punkto address and POST a new atom.
     *
     * @param nodeUrl  Target node (defaults to BuildConfig.DEFAULT_NODE_URL)
     * @param lat      Latitude degrees
     * @param lon      Longitude degrees
     * @param alt      Altitude metres
     * @param author   Author / "from" field (optional, empty string → null)
     * @param text     Text payload (optional, empty string → null)
     */
    fun postAtom(
        nodeUrl: String = BuildConfig.DEFAULT_NODE_URL,
        lat: Double,
        lon: Double,
        alt: Double,
        author: String,
        text: String
    ) {
        _postResult.value = PostResult.Loading
        viewModelScope.launch {
            try {
                val hash = Geohash3D.encode(lat, lon, alt)
                val punkto = "p:$hash"
                val t = System.currentTimeMillis()
                val f = author.trim().ifEmpty { null }
                val x = text.trim().ifEmpty { null }

                val result = repository.postAtom(punkto = punkto, t = t, f = f, x = x)
                result.fold(
                    onSuccess = { response ->
                        Log.i(TAG, "postAtom success: atomId=${response.atomId}")
                        _postResult.value = PostResult.Success(response.atomId ?: "")
                    },
                    onFailure = { err ->
                        Log.e(TAG, "postAtom failure: ${err.message}", err)
                        _postResult.value = PostResult.Error(err.message ?: "Unknown error")
                    }
                )
            } catch (e: Exception) {
                Log.e(TAG, "postAtom exception: ${e.message}", e)
                _postResult.value = PostResult.Error(e.message ?: "Unknown error")
            }
        }
    }

    /**
     * Enqueue a one-off WorkManager sync, e.g. when returning to foreground.
     * Sets isSyncing true for the duration of the direct coroutine path.
     */
    fun triggerSync() {
        _isSyncing.value = true
        val constraints = Constraints.Builder()
            .setRequiredNetworkType(NetworkType.CONNECTED)
            .build()
        val request = OneTimeWorkRequestBuilder<SyncWorker>()
            .setConstraints(constraints)
            .addTag(SyncWorker.TAG)
            .build()
        WorkManager.getInstance(getApplication()).enqueue(request)
        Log.d(TAG, "triggerSync: one-time sync enqueued")
        // Reset cursor so next loadMore starts fresh
        currentCursor = 0
        _isSyncing.value = false
    }

    /**
     * Load the next page of atoms from the feed using the current cursor.
     * Appends results to local Room DB via repository.
     */
    fun loadMore() {
        viewModelScope.launch {
            _isSyncing.value = true
            try {
                val page = repository.fetchFeed(cursor = currentCursor)
                if (page.nextCursor != null) {
                    currentCursor = page.nextCursor
                }
                Log.d(TAG, "loadMore: got ${page.atoms.size} atoms, hasMore=${page.hasMore}, nextCursor=${page.nextCursor}")
            } catch (e: Exception) {
                Log.e(TAG, "loadMore exception: ${e.message}", e)
            } finally {
                _isSyncing.value = false
            }
        }
    }

    /** Reset the post result state back to idle (call after dialog dismiss). */
    fun clearPostResult() {
        _postResult.value = PostResult.Idle
    }

    // -------------------------------------------------------------------------
    // Sealed result type
    // -------------------------------------------------------------------------

    sealed class PostResult {
        object Idle : PostResult()
        object Loading : PostResult()
        data class Success(val atomId: String) : PostResult()
        data class Error(val message: String) : PostResult()
    }

    companion object {
        private const val TAG = "AtomViewModel"
    }
}
