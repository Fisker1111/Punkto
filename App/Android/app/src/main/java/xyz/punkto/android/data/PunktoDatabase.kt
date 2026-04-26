package xyz.punkto.android.data

import android.content.Context
import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase

@Database(
    entities = [Atom::class],
    version = 1,
    exportSchema = false
)
abstract class PunktoDatabase : RoomDatabase() {

    abstract fun atomDao(): AtomDao

    companion object {
        private const val DATABASE_NAME = "punkto.db"

        @Volatile
        private var INSTANCE: PunktoDatabase? = null

        fun getInstance(context: Context): PunktoDatabase {
            return INSTANCE ?: synchronized(this) {
                INSTANCE ?: buildDatabase(context).also { INSTANCE = it }
            }
        }

        private fun buildDatabase(context: Context): PunktoDatabase {
            return Room.databaseBuilder(
                context.applicationContext,
                PunktoDatabase::class.java,
                DATABASE_NAME
            )
                .fallbackToDestructiveMigration()
                .build()
        }
    }
}
