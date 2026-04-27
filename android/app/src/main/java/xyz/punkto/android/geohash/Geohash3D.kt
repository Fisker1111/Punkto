package xyz.punkto.android.geohash

/**
 * Geohash3D — Kotlin port of the Punkto 3D geohash algorithm.
 *
 * Encodes (lat, lon, alt) into a 12-character Base32 string by interleaving
 * 20 bits each of latitude, longitude and altitude (60 bits total → 12 × 5-bit chars).
 *
 * Bit interleave order per bit position: lat bit, lon bit, alt bit
 *
 * Ranges:
 *   Latitude  : -90.0  .. +90.0  degrees
 *   Longitude : -180.0 .. +180.0 degrees
 *   Altitude  : -500.0 .. +8500.0 metres
 */
object Geohash3D {

    private const val BASE32 = "0123456789bcdefghjkmnpqrstuvwxyz"
    private const val BITS = 20

    private const val LAT_MIN = -90.0
    private const val LAT_MAX = 90.0
    private const val LON_MIN = -180.0
    private const val LON_MAX = 180.0
    private const val ALT_MIN = -500.0
    private const val ALT_MAX = 8500.0

    /**
     * Encode (lat, lon, alt) → 12-char Base32 geohash string.
     */
    fun encode(lat: Double, lon: Double, alt: Double): String {
        // Clamp inputs to valid ranges
        val clampedLat = lat.coerceIn(LAT_MIN, LAT_MAX)
        val clampedLon = lon.coerceIn(LON_MIN, LON_MAX)
        val clampedAlt = alt.coerceIn(ALT_MIN, ALT_MAX)

        // Normalise each dimension to [0, 1) then scale to BITS integer range
        val maxVal = (1L shl BITS) - 1L  // 2^20 - 1 = 1_048_575

        val latInt = ((clampedLat - LAT_MIN) / (LAT_MAX - LAT_MIN) * (maxVal + 1)).toLong()
            .coerceIn(0L, maxVal)
        val lonInt = ((clampedLon - LON_MIN) / (LON_MAX - LON_MIN) * (maxVal + 1)).toLong()
            .coerceIn(0L, maxVal)
        val altInt = ((clampedAlt - ALT_MIN) / (ALT_MAX - ALT_MIN) * (maxVal + 1)).toLong()
            .coerceIn(0L, maxVal)

        // Interleave 20 bits each: lat(bit19..0), lon(bit19..0), alt(bit19..0)
        // Per bit position i (from MSB=19 to LSB=0): output bit order = lat[i], lon[i], alt[i]
        // Total 60 bits packed into a Long (bits 59..0)
        var combined = 0L
        for (i in (BITS - 1) downTo 0) {
            val latBit = (latInt shr i) and 1L
            val lonBit = (lonInt shr i) and 1L
            val altBit = (altInt shr i) and 1L

            val shift = i * 3  // each 'slot' occupies 3 bits in combined
            combined = combined or (latBit shl (shift + 2))
            combined = combined or (lonBit shl (shift + 1))
            combined = combined or (altBit shl shift)
        }

        // Extract 12 × 5-bit groups from the 60-bit combined value (MSB first)
        val sb = StringBuilder(12)
        for (c in 11 downTo 0) {
            val index = ((combined shr (c * 5)) and 0x1F).toInt()
            sb.append(BASE32[index])
        }
        return sb.toString()
    }

    /**
     * Decode a 12-char geohash → Triple(lat, lon, alt) as centre-point values.
     */
    fun decode(hash: String): Triple<Double, Double, Double> {
        require(hash.length == 12) { "Geohash3D hash must be exactly 12 characters, got ${hash.length}" }

        // Reconstruct 60-bit combined value from 12 × 5-bit chars
        var combined = 0L
        for (ch in hash) {
            val idx = BASE32.indexOf(ch)
            require(idx >= 0) { "Invalid geohash character: '$ch'" }
            combined = (combined shl 5) or idx.toLong()
        }

        // De-interleave: extract lat, lon, alt 20-bit integers
        var latInt = 0L
        var lonInt = 0L
        var altInt = 0L
        for (i in 0 until BITS) {
            val shift = i * 3
            altInt = altInt or (((combined shr shift) and 1L) shl i)
            lonInt = lonInt or (((combined shr (shift + 1)) and 1L) shl i)
            latInt = latInt or (((combined shr (shift + 2)) and 1L) shl i)
        }

        val maxVal = (1L shl BITS).toDouble()  // 2^20 = 1_048_576.0

        // Convert integers back to coordinate ranges (centre-point of the bucket)
        val lat = (latInt.toDouble() + 0.5) / maxVal * (LAT_MAX - LAT_MIN) + LAT_MIN
        val lon = (lonInt.toDouble() + 0.5) / maxVal * (LON_MAX - LON_MIN) + LON_MIN
        val alt = (altInt.toDouble() + 0.5) / maxVal * (ALT_MAX - ALT_MIN) + ALT_MIN

        return Triple(lat, lon, alt)
    }

    /**
     * Build a full Punkto address from coordinates.
     * Format: p:<12-char-hash>
     */
    fun toPunkto(lat: Double, lon: Double, alt: Double): String {
        return "p:${encode(lat, lon, alt)}"
    }

    /**
     * Extract lat/lon/alt from a Punkto address string.
     * Accepts both "p:<hash>" and "p:<hash>-<suffix>" forms.
     */
    fun fromPunkto(punkto: String): Triple<Double, Double, Double> {
        val spatial = punkto
            .removePrefix("p:")
            .split("-")
            .first()
        return decode(spatial)
    }
}
