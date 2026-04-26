# Punkto Android

Native Kotlin Android app — work in progress.

## Tech Stack

- Kotlin
- MapLibre Android SDK (map + 3D)
- Retrofit / OkHttp (node API client)
- Room (local atom store)
- Coroutines + ViewModel

## Architecture

- Connects to configurable Punkto node URL
- Reads /feed and stores atoms locally in Room
- Posts atoms via /atom endpoint
- Renders atom positions on MapLibre map
