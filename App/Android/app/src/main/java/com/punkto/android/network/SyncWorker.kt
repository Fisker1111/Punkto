package com.punkto.android.network

import android.content.Context
import android.util.Log
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import com.punkto.android.data.NodeRepository
import com.punkto.android.data.PunktoDatabase

/**
 * SyncWorker — WorkManager CoroutineWorker that drives background synchronisation.
 *
 * Scheduled as a PeriodicWorkRequest (15 min minimum interval) in [PunktoApp].
 * Also enqueued as a one-off OneTimeWorkRequest whenever the app resumes in
 * [MainActivity.onResume] to ensure fresh data on every foreground transition.
 *
 * The worker delegates to [NodeRepository.syncAll] which handles per-node
 * cursor management, peer discovery, and Room persistence.
 */
class SyncWorker(
    appContext: Context,
    workerParams: WorkerParameters
) : CoroutineWorker(appContext, workerParams) {

    override suspend fun doWork(): Result {
        Log.d(TAG, "doWork: starting sync")
        return try {
            val db = PunktoDatabase.getInstance(applicationContext)
            val repo = NodeRepository.getInstance(applicationContext, db.atomDao())
            val newAtoms = repo.syncAll()
            Log.d(TAG, "doWork: sync complete, $newAtoms new atoms")
            Result.success()
        } catch (e: Exception) {
            Log.e(TAG, "doWork: sync failed: ${e.message}", e)
            // Retry on failure (WorkManager will back off automatically)
            Result.retry()
        }
    }

    companion object {
        const val TAG = "SyncWorker"
        const val WORK_NAME = "punkto_periodic_sync"
    }
}
