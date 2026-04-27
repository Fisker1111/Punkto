package xyz.punkto.android.data

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import kotlinx.coroutines.flow.Flow

@Dao
interface AtomDao {

    /**
     * Insert atoms, ignoring duplicates by atomId (unique index).
     * Returns list of inserted row IDs (-1 for ignored duplicates).
     */
    @Insert(onConflict = OnConflictStrategy.IGNORE)
    suspend fun insertAll(atoms: List<Atom>): List<Long>

    /**
     * Insert a single atom, ignoring if duplicate atomId exists.
     */
    @Insert(onConflict = OnConflictStrategy.IGNORE)
    suspend fun insert(atom: Atom): Long

    /**
     * Observe all atoms ordered by timestamp descending (newest first).
     */
    @Query("SELECT * FROM atoms ORDER BY t DESC")
    fun getAll(): Flow<List<Atom>>

    /**
     * Get the most recent atoms up to [limit], ordered newest-first.
     */
    @Query("SELECT * FROM atoms ORDER BY t DESC LIMIT :limit")
    fun getRecent(limit: Int = 100): Flow<List<Atom>>

    /**
     * Get atoms for a specific Punkto address, ordered newest-first.
     */
    @Query("SELECT * FROM atoms WHERE punkto = :punkto ORDER BY t DESC")
    fun getByPunkto(punkto: String): Flow<List<Atom>>

    /**
     * Get atoms within a bounding box (approximate, 2D only).
     * Note: bounding-box filtering is done in-memory after decode for now.
     */
    @Query("SELECT * FROM atoms ORDER BY t DESC LIMIT 500")
    suspend fun getAllSnapshot(): List<Atom>

    /**
     * Check if an atom with this content hash already exists.
     */
    @Query("SELECT COUNT(*) FROM atoms WHERE atomId = :atomId")
    suspend fun countByAtomId(atomId: String): Int

    /**
     * Delete all atoms from the local cache.
     */
    @Query("DELETE FROM atoms")
    suspend fun deleteAll()

    /**
     * Total number of stored atoms.
     */
    @Query("SELECT COUNT(*) FROM atoms")
    suspend fun count(): Int
}
