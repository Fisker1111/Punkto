package xyz.punkto.android.ui

import android.Manifest
import android.annotation.SuppressLint
import android.content.Context
import android.content.pm.PackageManager
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.util.Log
import android.view.HapticFeedbackConstants
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Button
import android.widget.RadioGroup
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
import androidx.core.content.ContextCompat
import androidx.fragment.app.Fragment
import androidx.fragment.app.activityViewModels
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.lifecycleScope
import androidx.lifecycle.repeatOnLifecycle
import com.google.android.gms.location.FusedLocationProviderClient
import com.google.android.gms.location.LocationCallback
import com.google.android.gms.location.LocationRequest
import com.google.android.gms.location.LocationResult
import com.google.android.gms.location.LocationServices
import com.google.android.gms.location.Priority
import com.google.android.material.textfield.TextInputEditText
import xyz.punkto.android.R
import xyz.punkto.android.data.Atom
import xyz.punkto.android.databinding.FragmentMapBinding
import xyz.punkto.android.geohash.Geohash3D
import kotlinx.coroutines.launch
import org.maplibre.android.camera.CameraPosition
import org.maplibre.android.camera.CameraUpdateFactory
import org.maplibre.android.geometry.LatLng
import org.maplibre.android.location.LocationComponentActivationOptions
import org.maplibre.android.location.modes.CameraMode
import org.maplibre.android.location.modes.RenderMode
import org.maplibre.android.maps.MapLibreMap
import org.maplibre.android.maps.MapView
import org.maplibre.android.maps.OnMapReadyCallback
import org.maplibre.android.maps.Style
import org.maplibre.android.style.expressions.Expression.get
import org.maplibre.android.style.expressions.Expression.has
import org.maplibre.android.style.expressions.Expression.literal
import org.maplibre.android.style.expressions.Expression.not
import org.maplibre.android.style.expressions.Expression.step
import org.maplibre.android.style.expressions.Expression.stop
import org.maplibre.android.style.layers.CircleLayer
import org.maplibre.android.style.layers.PropertyFactory
import org.maplibre.android.style.layers.SymbolLayer
import org.maplibre.android.style.sources.GeoJsonOptions
import org.maplibre.android.style.sources.GeoJsonSource
import org.maplibre.geojson.Feature
import org.maplibre.geojson.FeatureCollection
import org.maplibre.geojson.Point
import kotlin.math.abs

class MapFragment : Fragment(), OnMapReadyCallback {

    private var _binding: FragmentMapBinding? = null
    private val binding get() = _binding!!

    private val viewModel: AtomViewModel by activityViewModels()

    private lateinit var mapView: MapView
    private var mapLibreMap: MapLibreMap? = null
    private var mapStyle: Style? = null

    private lateinit var fusedLocationClient: FusedLocationProviderClient
    private var locationCallback: LocationCallback? = null
    private var highAccuracy: Boolean = true

    private var is3D = false
    private val atomSourceId = "punkto-atoms-source"
    private val atomLayerId  = "punkto-atoms-layer"
    private var atomFeatureMap = mutableMapOf<String, Atom>()

    // -------------------------------------------------------------------------
    // Battery optimisation — adaptive location accuracy
    // -------------------------------------------------------------------------

    private var lastInteractionMs: Long = System.currentTimeMillis()
    private val idleHandler = Handler(Looper.getMainLooper())
    private val idleRunnable = Runnable {
        if (highAccuracy) setHighAccuracy(false)
    }

    private fun setHighAccuracy(enabled: Boolean) {
        highAccuracy = enabled
        stopLocationUpdates()
        startLocationUpdatesIfPermitted()
    }

    private fun resetIdleTimer() {
        lastInteractionMs = System.currentTimeMillis()
        idleHandler.removeCallbacks(idleRunnable)
        if (!highAccuracy) setHighAccuracy(true)
        idleHandler.postDelayed(idleRunnable, IDLE_TIMEOUT_MS)
    }

    // -------------------------------------------------------------------------
    // Offline banner
    // -------------------------------------------------------------------------

    private var networkCallback: android.net.ConnectivityManager.NetworkCallback? = null
    private var offlineSnackbar: com.google.android.material.snackbar.Snackbar? = null

    private fun registerNetworkCallback() {
        val cm = requireContext().getSystemService(Context.CONNECTIVITY_SERVICE)
            as android.net.ConnectivityManager
        val request = android.net.NetworkRequest.Builder()
            .addCapability(android.net.NetworkCapabilities.NET_CAPABILITY_INTERNET).build()
        val cb = object : android.net.ConnectivityManager.NetworkCallback() {
            override fun onAvailable(network: android.net.Network) {
                requireActivity().runOnUiThread { showOfflineBanner(false) }
            }
            override fun onLost(network: android.net.Network) {
                requireActivity().runOnUiThread { showOfflineBanner(true) }
            }
        }
        cm.registerNetworkCallback(request, cb)
        networkCallback = cb
    }

    private fun unregisterNetworkCallback() {
        networkCallback?.let {
            val cm = requireContext().getSystemService(Context.CONNECTIVITY_SERVICE)
                as android.net.ConnectivityManager
            cm.unregisterNetworkCallback(it)
        }
        networkCallback = null
    }

    private fun showOfflineBanner(offline: Boolean) {
        if (offline) {
            offlineSnackbar = com.google.android.material.snackbar.Snackbar.make(
                binding.root, "No internet connection",
                com.google.android.material.snackbar.Snackbar.LENGTH_INDEFINITE
            )
            offlineSnackbar?.show()
        } else {
            offlineSnackbar?.dismiss()
            offlineSnackbar = null
        }
    }

    // -------------------------------------------------------------------------
    // SharedPreferences — remember last author
    // -------------------------------------------------------------------------

    private val prefs by lazy {
        requireContext().getSharedPreferences("punkto_prefs", Context.MODE_PRIVATE)
    }

    // -------------------------------------------------------------------------
    // Fragment lifecycle
    // -------------------------------------------------------------------------

    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View {
        _binding = FragmentMapBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        mapView = binding.mapView
        mapView.onCreate(savedInstanceState)
        mapView.getMapAsync(this)

        fusedLocationClient = LocationServices.getFusedLocationProviderClient(requireActivity())

        binding.fabDropAtom.setOnClickListener  { onFabDropAtom() }
        binding.btnToggle3d.setOnClickListener  { onToggle3D() }
        binding.fabMyLocation.setOnClickListener { onMyLocation() }
        binding.btnCompass.setOnClickListener   { onResetBearing() }

        viewLifecycleOwner.lifecycleScope.launch {
            viewLifecycleOwner.repeatOnLifecycle(Lifecycle.State.STARTED) {
                launch { viewModel.atoms.collect           { atoms  -> renderAtoms(atoms) } }
                launch { viewModel.postResult.collect      { result -> handlePostResult(result) } }
                launch { viewModel.currentLocation.collect { loc    ->
                    if (loc != null) updateAltitudeHud(loc.altitude)
                }}
                launch { viewModel.isSyncing.collect { syncing ->
                    binding.syncIndicator.visibility = if (syncing) View.VISIBLE else View.GONE
                }}
            }
        }
    }

    // -------------------------------------------------------------------------
    // MapLibre callbacks
    // -------------------------------------------------------------------------

    override fun onMapReady(map: MapLibreMap) {
        mapLibreMap = map
        map.setStyle(MAP_STYLE_URL) { style ->
            mapStyle = style
            setupAtomLayer(style)
            startLocationUpdatesIfPermitted()
            enableLocationComponent(map, style)
            viewModel.currentLocation.value?.let { loc ->
                map.moveCamera(CameraUpdateFactory.newLatLngZoom(
                    LatLng(loc.latitude, loc.longitude), 15.0))
            }
            renderAtoms(viewModel.atoms.value)
        }
        map.addOnMapClickListener { latLng ->
            resetIdleTimer()
            handleMapTap(latLng)
            true
        }
        map.addOnCameraIdleListener { updateCrosshairLabel() }
        map.addOnCameraMoveListener { updateCrosshairLabel() }
    }

    private fun setupAtomLayer(style: Style) {
        // Cluster-enabled GeoJSON source
        val source = GeoJsonSource(
            atomSourceId,
            FeatureCollection.fromFeatures(emptyList()),
            GeoJsonOptions()
                .withCluster(true)
                .withClusterMaxZoom(14)
                .withClusterRadius(50)
        )
        style.addSource(source)

        // Cluster circle layer
        val clusterLayer = CircleLayer("clusters", atomSourceId).apply {
            setFilter(has("point_count"))
            setProperties(
                PropertyFactory.circleRadius(
                    step(get("point_count"), literal(16f),
                        stop(literal(10), literal(22f)), stop(literal(50), literal(30f)))
                ),
                PropertyFactory.circleColor(
                    step(get("point_count"), literal("#00CCDD"),
                        stop(literal(10), literal("#2E86FF")), stop(literal(50), literal("#9B59B6")))
                ),
                PropertyFactory.circleOpacity(0.85f),
                PropertyFactory.circleStrokeWidth(2f),
                PropertyFactory.circleStrokeColor("#FFFFFF")
            )
        }
        style.addLayer(clusterLayer)

        // Cluster count label
        val countLayer = SymbolLayer("cluster-count", atomSourceId).apply {
            setFilter(has("point_count"))
            setProperties(
                PropertyFactory.textField("{point_count}"),
                PropertyFactory.textSize(12f),
                PropertyFactory.textColor("#FFFFFF"),
                PropertyFactory.textIgnorePlacement(true),
                PropertyFactory.textAllowOverlap(true)
            )
        }
        style.addLayer(countLayer)

        // Individual atom layer (unclustered) with altitude colour coding
        val circleLayer = CircleLayer(atomLayerId, atomSourceId).apply {
            setFilter(not(has("point_count")))
            setProperties(
                PropertyFactory.circleRadius(7f),
                PropertyFactory.circleColor(
                    step(
                        get("altitude"),
                        literal("#00CCDD"),   // ground: 0–3.5 m
                        stop(literal(3.5),  literal("#2E86FF")), // floor 1–3
                        stop(literal(14.0), literal("#9B59B6"))  // floor 4+
                    )
                ),
                PropertyFactory.circleOpacity(0.85f),
                PropertyFactory.circleStrokeWidth(1.5f),
                PropertyFactory.circleStrokeColor("#FFFFFF")
            )
        }
        style.addLayer(circleLayer)
    }

    // -------------------------------------------------------------------------
    // Location component (blue dot)
    // -------------------------------------------------------------------------

    @SuppressLint("MissingPermission")
    private fun enableLocationComponent(map: MapLibreMap, style: Style) {
        try {
            val locationComponent = map.locationComponent
            val hasPermission = ContextCompat.checkSelfPermission(
                requireContext(), Manifest.permission.ACCESS_FINE_LOCATION
            ) == PackageManager.PERMISSION_GRANTED
            if (!hasPermission) return
            locationComponent.activateLocationComponent(
                LocationComponentActivationOptions.builder(requireContext(), style).build()
            )
            locationComponent.isLocationComponentEnabled = true
            locationComponent.cameraMode = CameraMode.NONE
            locationComponent.renderMode = RenderMode.COMPASS
        } catch (e: Exception) {
            Log.w(TAG, "LocationComponent unavailable: ${e.message}")
        }
    }

    // -------------------------------------------------------------------------
    // Atom rendering
    // -------------------------------------------------------------------------

    private fun renderAtoms(atoms: List<Atom>) {
        val source = mapStyle?.getSourceAs<GeoJsonSource>(atomSourceId) ?: return
        atomFeatureMap.clear()
        val features = atoms.mapNotNull { atom ->
            try {
                val (lat, lon, alt) = Geohash3D.fromPunkto(atom.punkto)
                Feature.fromGeometry(Point.fromLngLat(lon, lat)).also { f ->
                    f.addStringProperty("atomId",   atom.atomId)
                    f.addStringProperty("punkto",   atom.punkto)
                    f.addNumberProperty("altitude", alt)
                    atomFeatureMap[atom.atomId] = atom
                }
            } catch (e: Exception) {
                Log.w(TAG, "skip ${atom.punkto}: ${e.message}")
                null
            }
        }
        source.setGeoJson(FeatureCollection.fromFeatures(features))

        // Atom count badge
        binding.chipAtomCount.visibility = if (atoms.isEmpty()) View.GONE else View.VISIBLE
        binding.chipAtomCount.text = "${atoms.size} atoms"

        // Empty state
        binding.tvEmptyState.visibility = if (atoms.isEmpty()) View.VISIBLE else View.GONE
    }

    // -------------------------------------------------------------------------
    // Map tap
    // -------------------------------------------------------------------------

    private fun handleMapTap(latLng: LatLng): Boolean {
        resetIdleTimer()
        val map   = mapLibreMap ?: return false
        val pt    = map.projection.toScreenLocation(latLng)
        val rect  = android.graphics.RectF(
            pt.x - TAP_SLOP_PX, pt.y - TAP_SLOP_PX,
            pt.x + TAP_SLOP_PX, pt.y + TAP_SLOP_PX)
        val feat  = map.queryRenderedFeatures(rect, atomLayerId).firstOrNull() ?: return false
        val atomId = feat.getStringProperty("atomId") ?: return false
        val atom  = atomFeatureMap[atomId] ?: return false
        AtomBottomSheetFragment.newInstance(atom)
            .show(childFragmentManager, AtomBottomSheetFragment.TAG)
        return true
    }

    // -------------------------------------------------------------------------
    // FAB — drop atom with floor picker
    // -------------------------------------------------------------------------

    private fun onFabDropAtom() {
        resetIdleTimer()
        // Use crosshair (map center) for lat/lon; GPS for altitude default
        val center = mapLibreMap?.cameraPosition?.target
        val gpsAlt = viewModel.currentLocation.value?.altitude ?: 0.0
        if (center == null) {
            Toast.makeText(requireContext(), getString(R.string.error_no_location), Toast.LENGTH_SHORT).show()
            return
        }
        showDropAtomDialog(center.latitude, center.longitude, gpsAlt)
    }

    // -------------------------------------------------------------------------
    // Crosshair label — updates as map moves
    // -------------------------------------------------------------------------

    private fun updateCrosshairLabel() {
        val center = mapLibreMap?.cameraPosition?.target ?: return
        val tv = binding.tvCrosshairLabel
        try {
            val spatial = Geohash3D.encode(center.latitude, center.longitude, 0.0, 12)
            tv.text = "p:$spatial"
            tv.visibility = View.VISIBLE
        } catch (e: Exception) {
            tv.visibility = View.GONE
        }
    }

    private fun showDropAtomDialog(lat: Double, lon: Double, gpsAlt: Double) {
        resetIdleTimer()
        val dv = LayoutInflater.from(requireContext()).inflate(R.layout.dialog_drop_atom, null)

        val etAuthor    = dv.findViewById<TextInputEditText>(R.id.et_author)
        val etText      = dv.findViewById<TextInputEditText>(R.id.et_text)
        val rgAltMode   = dv.findViewById<RadioGroup>(R.id.rg_alt_mode)
        val rowFloor    = dv.findViewById<View>(R.id.row_floor_picker)
        val tvFloor     = dv.findViewById<TextView>(R.id.tv_floor_label)
        val btnDown     = dv.findViewById<Button>(R.id.btn_floor_down)
        val btnUp       = dv.findViewById<Button>(R.id.btn_floor_up)
        val tvGpsAlt    = dv.findViewById<TextView>(R.id.tv_gps_alt_display)

        // Restore last used author
        etAuthor.setText(prefs.getString("last_author", ""))

        tvGpsAlt.text = String.format("GPS: %.1f m", gpsAlt)
        var floor = altToFloor(gpsAlt)

        fun refreshLabel() {
            val alt = floorToAlt(floor)
            tvFloor.text = when {
                floor == 0 -> "Ground floor  ·  0 m"
                floor > 0  -> "Floor $floor  ·  ${String.format("%.1f", alt)} m"
                else       -> "Basement ${-floor}  ·  ${String.format("%.1f", alt)} m"
            }
        }
        refreshLabel()

        btnDown.setOnClickListener { if (floor > -5)   { floor--; refreshLabel() } }
        btnUp.setOnClickListener   { if (floor < 200)  { floor++; refreshLabel() } }

        rgAltMode.setOnCheckedChangeListener { _, id ->
            when (id) {
                R.id.rb_gps_alt -> { rowFloor.visibility = View.GONE;    tvGpsAlt.visibility = View.VISIBLE }
                R.id.rb_floor   -> { rowFloor.visibility = View.VISIBLE; tvGpsAlt.visibility = View.GONE    }
            }
        }

        AlertDialog.Builder(requireContext())
            .setTitle(R.string.dialog_drop_atom_title)
            .setView(dv)
            .setPositiveButton(R.string.action_drop) { _, _ ->
                val author = etAuthor.text.toString().trim()
                // Save last used author
                prefs.edit().putString("last_author", author).apply()
                val finalAlt = if (rgAltMode.checkedRadioButtonId == R.id.rb_floor)
                    floorToAlt(floor) else gpsAlt
                viewModel.postAtom(
                    lat    = lat, lon  = lon,  alt    = finalAlt,
                    author = author,
                    text   = etText.text.toString().trim()
                )
            }
            .setNegativeButton(android.R.string.cancel, null)
            .show()
    }

    // -------------------------------------------------------------------------
    // 3D toggle
    // -------------------------------------------------------------------------

    private fun onToggle3D() {
        val map = mapLibreMap ?: return
        is3D = !is3D
        map.animateCamera(CameraUpdateFactory.newCameraPosition(
            CameraPosition.Builder().tilt(if (is3D) 60.0 else 0.0).build()), 600)
        binding.btnToggle3d.text = getString(if (is3D) R.string.btn_2d else R.string.btn_3d)
    }

    // -------------------------------------------------------------------------
    // My Location
    // -------------------------------------------------------------------------

    private fun onMyLocation() {
        resetIdleTimer()
        val loc = viewModel.currentLocation.value
        if (loc == null) {
            Toast.makeText(requireContext(), getString(R.string.error_no_location), Toast.LENGTH_SHORT).show()
            return
        }
        mapLibreMap?.animateCamera(
            CameraUpdateFactory.newLatLngZoom(LatLng(loc.latitude, loc.longitude), 17.0), 600)
    }

    // -------------------------------------------------------------------------
    // Compass — reset bearing to north
    // -------------------------------------------------------------------------

    private fun onResetBearing() {
        val map = mapLibreMap ?: return
        val cur = map.cameraPosition
        map.animateCamera(CameraUpdateFactory.newCameraPosition(
            CameraPosition.Builder()
                .bearing(0.0).tilt(cur.tilt).zoom(cur.zoom).target(cur.target)
                .build()), 400)
    }

    // -------------------------------------------------------------------------
    // Altitude HUD
    // -------------------------------------------------------------------------

    private fun updateAltitudeHud(alt: Double) {
        val tv = binding.tvAltitudeHud
        tv.visibility = View.VISIBLE
        val floor = altToFloor(alt)
        tv.text = if (abs(alt) >= 2.0)
            getString(R.string.hud_alt, alt, floor)
        else
            getString(R.string.hud_alt_low, alt)
    }

    // -------------------------------------------------------------------------
    // Floor / altitude helpers
    // -------------------------------------------------------------------------

    private fun altToFloor(alt: Double): Int = (alt / FLOOR_HEIGHT_M).toInt()
    private fun floorToAlt(floor: Int): Double = floor * FLOOR_HEIGHT_M

    // -------------------------------------------------------------------------
    // Location
    // -------------------------------------------------------------------------

    fun onLocationPermissionGranted() = startLocationUpdatesIfPermitted()

    @SuppressLint("MissingPermission")
    private fun startLocationUpdatesIfPermitted() {
        val ok = ContextCompat.checkSelfPermission(requireContext(),
            Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED ||
            ContextCompat.checkSelfPermission(requireContext(),
            Manifest.permission.ACCESS_COARSE_LOCATION) == PackageManager.PERMISSION_GRANTED
        if (!ok) return

        val (priority, interval) = if (highAccuracy)
            Priority.PRIORITY_HIGH_ACCURACY to LOCATION_INTERVAL_MS
        else
            Priority.PRIORITY_BALANCED_POWER_ACCURACY to LOCATION_INTERVAL_LOW_MS

        val req = LocationRequest.Builder(priority, interval)
            .setMinUpdateIntervalMillis(LOCATION_FASTEST_MS).build()
        val cb = object : LocationCallback() {
            override fun onLocationResult(r: LocationResult) {
                r.lastLocation?.let { viewModel.updateLocation(it) }
            }
        }
        locationCallback = cb
        fusedLocationClient.requestLocationUpdates(req, cb, Looper.getMainLooper())
    }

    private fun stopLocationUpdates() {
        locationCallback?.let { fusedLocationClient.removeLocationUpdates(it) }
        locationCallback = null
    }

    // -------------------------------------------------------------------------
    // Post result
    // -------------------------------------------------------------------------

    private fun handlePostResult(result: AtomViewModel.PostResult) {
        when (result) {
            is AtomViewModel.PostResult.Success -> {
                Toast.makeText(requireContext(),
                    getString(R.string.atom_posted_ok, result.atomId.take(12)), Toast.LENGTH_SHORT).show()
                // Haptic confirmation
                binding.fabDropAtom.performHapticFeedback(
                    HapticFeedbackConstants.CONFIRM,
                    HapticFeedbackConstants.FLAG_IGNORE_GLOBAL_SETTING
                )
                viewModel.clearPostResult()
            }
            is AtomViewModel.PostResult.Error -> {
                Toast.makeText(requireContext(),
                    getString(R.string.atom_post_error, result.message), Toast.LENGTH_LONG).show()
                viewModel.clearPostResult()
            }
            else -> {}
        }
    }

    // -------------------------------------------------------------------------
    // MapLibre lifecycle delegation
    // -------------------------------------------------------------------------

    override fun onStart()  { super.onStart();  mapView.onStart() }
    override fun onResume() {
        super.onResume()
        mapView.onResume()
        startLocationUpdatesIfPermitted()
        registerNetworkCallback()
        resetIdleTimer()
    }
    override fun onPause()  {
        super.onPause()
        mapView.onPause()
        stopLocationUpdates()
        idleHandler.removeCallbacks(idleRunnable)
        unregisterNetworkCallback()
    }
    override fun onStop()         { super.onStop();     mapView.onStop() }
    override fun onDestroyView()  { super.onDestroyView(); mapView.onDestroy(); _binding = null }
    override fun onSaveInstanceState(out: Bundle) { super.onSaveInstanceState(out); mapView.onSaveInstanceState(out) }
    override fun onLowMemory()    { super.onLowMemory(); mapView.onLowMemory() }

    // -------------------------------------------------------------------------
    // Companion
    // -------------------------------------------------------------------------

    companion object {
        private const val TAG                    = "MapFragment"
        private const val MAP_STYLE_URL          = "https://tiles.openfreemap.org/styles/liberty"
        private const val LOCATION_INTERVAL_MS   = 5_000L
        private const val LOCATION_INTERVAL_LOW_MS = 15_000L
        private const val LOCATION_FASTEST_MS    = 2_000L
        private const val TAP_SLOP_PX            = 32f
        private const val FLOOR_HEIGHT_M         = 3.5  // typical floor-to-floor height in metres
        private const val IDLE_TIMEOUT_MS        = 30_000L

        fun newInstance() = MapFragment()
    }
}
