package com.punkto.android.network

import android.util.Log
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.util.concurrent.TimeUnit

/**
 * RetrofitClient — builds and caches [PunktoApiService] instances per node URL.
 *
 * Uses a simple in-memory cache keyed on base URL so we avoid creating
 * redundant Retrofit instances for nodes we sync repeatedly.
 */
object RetrofitClient {

    private const val TAG = "RetrofitClient"
    private const val CONNECT_TIMEOUT_S = 15L
    private const val READ_TIMEOUT_S = 30L
    private const val WRITE_TIMEOUT_S = 30L

    /** Cache: normalised base URL → PunktoApiService */
    private val cache = mutableMapOf<String, PunktoApiService>()

    private val okHttpClient: OkHttpClient by lazy {
        val logging = HttpLoggingInterceptor { message ->
            Log.d(TAG, message)
        }.apply {
            level = HttpLoggingInterceptor.Level.BASIC
        }

        OkHttpClient.Builder()
            .connectTimeout(CONNECT_TIMEOUT_S, TimeUnit.SECONDS)
            .readTimeout(READ_TIMEOUT_S, TimeUnit.SECONDS)
            .writeTimeout(WRITE_TIMEOUT_S, TimeUnit.SECONDS)
            .addInterceptor(logging)
            .build()
    }

    /**
     * Return a [PunktoApiService] for the given [baseUrl].
     * URLs are normalised to always end with a trailing slash.
     */
    fun buildApi(baseUrl: String): PunktoApiService {
        val normalised = baseUrl.trimEnd('/') + '/'
        return cache.getOrPut(normalised) {
            Log.d(TAG, "Building Retrofit client for $normalised")
            Retrofit.Builder()
                .baseUrl(normalised)
                .client(okHttpClient)
                .addConverterFactory(GsonConverterFactory.create())
                .build()
                .create(PunktoApiService::class.java)
        }
    }

    /** Evict all cached clients (useful for testing). */
    fun clearCache() {
        cache.clear()
    }
}
