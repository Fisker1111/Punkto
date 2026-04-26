package com.punkto.android.data

import androidx.room.Entity
import androidx.room.Index
import androidx.room.PrimaryKey
import java.io.Serializable

/**
 * Room entity representing a Punkto atom.
 *
 * Maps to the wire format:
 *   { "punkto": "p:<hash>", "t": <unix_ms>, "f": "<author>", "x": "<text>" }
 *
 * Additional local fields:
 *   - atomId   : content-addressed SHA-256 of canonical JSON (dedup key)
 *   - nodeUrl  : which node this atom was received from
 *
 * Implements [Serializable] so instances can be passed between fragments via Bundle.
 */
@Entity(
    tableName = "atoms",
    indices = [
        Index(value = ["atomId"], unique = true),
        Index(value = ["punkto"]),
        Index(value = ["t"])
    ]
)
data class Atom(
    @PrimaryKey(autoGenerate = true)
    val id: Long = 0,

    /** Canonical Punkto address, e.g. "p:u07qsuustfsh" or "p:u07qsuustfsh-9xk3" */
    val punkto: String,

    /** Unix timestamp in milliseconds (13 digits) */
    val t: Long,

    /** Author / from field (optional) */
    val f: String? = null,

    /** Text payload (optional) */
    val x: String? = null,

    /**
     * Content-addressed identifier: SHA-256 hex of canonical JSON
     * (sorted keys, no whitespace, excludes "sig" field).
     * Used for cross-node deduplication.
     */
    val atomId: String,

    /** The node URL this atom was synced from */
    val nodeUrl: String
) : Serializable
