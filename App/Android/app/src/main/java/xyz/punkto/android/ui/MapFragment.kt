package xyz.punkto.android.ui

import android.Manifest
import android.annotation.SuppressLint
import android.content.pm.PackageManager
import android.os.Bundle
import android.os.Looper
import android.util.Log
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.EditText
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
import xyz.punkto.android.R
import xyz.punkto.android.data.Atom
import xyz.punkto.android.databinding.FragmentMapBinding
import xyz.punkto.android.geohash.Geohash3D
import kotlinx.coroutines.launch
import org.maplibre.android.camera.CameraPosition
import org.maplibre.android.camera.CameraUpdateFactory
import org.maplibre.android.geometry.LatLng
import org.maplibre.android.maps.MapLibreMap
import org.maplibre.android.maps.MapView
import org.maplibre.android.maps.OnMapReadyCallback
import org.maplibre.android.maps.Style
import org.maplibre.android.style.layers.CircleLayer
import org.maplibre.android.style.layers.PropertyFactory
import org.maplibre.android.style.sources.GeoJsonSource
import org.maplibre.geojson.Feature
import org.maplibre.geojson.FeatureCollection
import org.maplibre.geojson.Point

class MapFragment : Fragment(), OnMapReadyCallback {

    private var _binding: FragmentMapBinding? = null
    private val binding get() = _binding!!

    private val viewModel: AtomViewModel by activityViewModels()

    private lateinit var mapView: MapView
    private var mapLibreMap: MapLibreMap? = null
    private var mapStyle: Style? = null

    // Location
    private lateinit var fusedLocationClient: FusedLocationProviderClient
    private var locationCallback: LocationCallback? = null

    // Map state
    private var is3D = false
    private val atomSourceId = "punkto-atoms-source"
    private val atomLayerId = "punkto-atoms-layer"
    private val atomLayerTappableId = "punkto-atoms-tappable"

    // Keep a handle for tapping: atomId → Atom
    private var atomFeatureMap = mutableMapOf<String, Atom>()

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

        binding.fabDropAtom.setOnClickListener { onFabDropAtom() }
        binding.btnToggle3d.setOnClickListener { onToggle3D() }

        // Observe ViewModel
        viewLifecycleOwner.lifecycleScope.launch {
            viewLifecycleOwner.repeatOnLifecycle(Lifecycle.State.STARTED) {
                launch {
                    viewModel.atoms.collect { atoms -> renderAtoms(atoms) }
                }
                launch {
                    viewModel.postResult.collect { result -> handlePostResult(result) }
                }
            }
        }
    }

    // -------------------------------------------------------------------------
    // MapLibre callbacks
    // -------------------------------------------------------------------------

    override fun onMapReady(mapboxMap: MapLibreMap) {
        mapLibreMap = mapboxMap

        mapboxMap.setStyle(MAP_STYLE_URL) { style ->
            mapStyle = style
            setupAtomLayer(style)
            startLocationUpdatesIfPermitted()

            // Move camera to last known location if available
            viewModel.currentLocation.value?.let { loc ->
                mapboxMap.moveCamera(
                    CameraUpdateFactory.newLatLngZoom(LatLng(loc.latitude, loc.longitude), 15.0)
                )
            }

            // Render any already-loaded atoms
            renderAtoms(viewModel.atoms.value)
        }

        // Tap listener for atom markers
        mapboxMap.addOnMapClickListener { latLng ->
            handleMapTap(latLng)
            true
        }
    }

    private fun setupAtomLayer(style: Style) {
        // Source
        val source = GeoJsonSource(atomSourceId, FeatureCollection.fromFeatures(emptyList()))
        style.addSource(source)

        // Layer — teal circles
        val circleLayer = CircleLayer(atomLayerId, atomSourceId).apply {
            setProperties(
                PropertyFactory.circleRadius(7f),
                PropertyFactory.circleColor("#00CCDD"),
                PropertyFactory.circleOpacity(0.85f),
                PropertyFactory.circleStrokeWidth(1.5f),
                PropertyFactory.circleStrokeColor("#FFFFFF")
            )
        }
        style.addLayer(circleLayer)
    }

    // -------------------------------------------------------------------------
    // Atom rendering
    // -------------------------------------------------------------------------

    private fun renderAtoms(atoms: List<Atom>) {
        val style = mapStyle ?: return
        val source = style.getSourceAs<GeoJsonSource>(atomSourceId) ?: return

        atomFeatureMap.clear()
        val features = atoms.mapNotNull { atom ->
            try {
                val (lat, lon, _) = Geohash3D.fromPunkto(atom.punkto)
                val feature = Feature.fromGeometry(
                    Point.fromLngLat(lon, lat)
                ).also { f ->
                    // Embed atomId as a feature property for tap lookup
                    f.addStringProperty("atomId", atom.atomId)
                    f.addStringProperty("punkto", atom.punkto)
                }
                atomFeatureMap[atom.atomId] = atom
                feature
            } catch (e: Exception) {
                Log.w(TAG, "renderAtoms: skipping malformed atom ${atom.punkto}: ${e.message}")
                null
            }
        }
        source.setGeoJson(FeatureCollection.fromFeatures(features))
    }

    // -------------------------------------------------------------------------
    // Map tap
    // -------------------------------------------------------------------------

    private fun handleMapTap(latLng: LatLng): Boolean {
        val map = mapLibreMap ?: return false
        val point = map.projection.toScreenLocation(latLng)
        val rect = android.graphics.RectF(
            point.x - TAP_SLOP_PX, point.y - TAP_SLOP_PX,
            point.x + TAP_SLOP_PX, point.y + TAP_SLOP_PX
        )
        val features = map.queryRenderedFeatures(rect, atomLayerId)
        if (features.isEmpty()) return false

        val atomId = features.first().getStringProperty("atomId") ?: return false
        val atom = atomFeatureMap[atomId] ?: return false

        AtomBottomSheetFragment.newInstance(atom)
            .show(childFragmentManager, AtomBottomSheetFragment.TAG)
        return true
    }

    // -------------------------------------------------------------------------
    // FAB — drop atom
    // -------------------------------------------------------------------------

    private fun onFabDropAtom() {
        val location = viewModel.currentLocation.value
        if (location == null) {
            Toast.makeText(requireContext(), getString(R.string.error_no_location), Toast.LENGTH_SHORT).show()
            return
        }
        showDropAtomDialog(location.latitude, location.longitude, location.altitude)
    }

    private fun showDropAtomDialog(lat: Double, lon: Double, alt: Double) {
        val dialogView = LayoutInflater.from(requireContext())
            .inflate(R.layout.dialog_drop_atom, null)
        val etAuthor = dialogView.findViewById<EditText>(R.id.et_author)
        val etText   = dialogView.findViewById<EditText>(R.id.et_text)

        AlertDialog.Builder(requireContext())
            .setTitle(R.string.dialog_drop_atom_title)
            .setView(dialogView)
            .setPositiveButton(R.string.action_drop) { _, _ ->
                val author = etAuthor.text.toString().trim()
                val text   = etText.text.toString().trim()
                viewModel.postAtom(
                    lat = lat, lon = lon, alt = alt,
                    author = author, text = text
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
        val pitch = if (is3D) 60.0 else 0.0
        val camera = CameraPosition.Builder()
            .tilt(pitch)
            .build()
        map.animateCamera(CameraUpdateFactory.newCameraPosition(camera), 600)
        binding.btnToggle3d.text = if (is3D) getString(R.string.btn_2d) else getString(R.string.btn_3d)
    }

    // -------------------------------------------------------------------------
    // Location
    // -------------------------------------------------------------------------

    fun onLocationPermissionGranted() {
        startLocationUpdatesIfPermitted()
    }

    @SuppressLint("MissingPermission")
    private fun startLocationUpdatesIfPermitted() {
        val fineGranted = ContextCompat.checkSelfPermission(
            requireContext(), Manifest.permission.ACCESS_FINE_LOCATION
        ) == PackageManager.PERMISSION_GRANTED
        val coarseGranted = ContextCompat.checkSelfPermission(
            requireContext(), Manifest.permission.ACCESS_COARSE_LOCATION
        ) == PackageManager.PERMISSION_GRANTED

        if (!fineGranted && !coarseGranted) return

        val request = LocationRequest.Builder(
            Priority.PRIORITY_HIGH_ACCURACY,
            LOCATION_INTERVAL_MS
        ).setMinUpdateIntervalMillis(LOCATION_FASTEST_MS).build()

        val callback = object : LocationCallback() {
            override fun onLocationResult(result: LocationResult) {
                result.lastLocation?.let { loc ->
                    viewModel.updateLocation(loc)
                }
            }
        }
        locationCallback = callback
        fusedLocationClient.requestLocationUpdates(request, callback, Looper.getMainLooper())
    }

    private fun stopLocationUpdates() {
        locationCallback?.let { fusedLocationClient.removeLocationUpdates(it) }
        locationCallback = null
    }

    // -------------------------------------------------------------------------
    // Post result handling
    // -------------------------------------------------------------------------

    private fun handlePostResult(result: AtomViewModel.PostResult) {
        when (result) {
            is AtomViewModel.PostResult.Success -> {
                Toast.makeText(
                    requireContext(),
                    getString(R.string.atom_posted_ok, result.atomId.take(12)),
                    Toast.LENGTH_SHORT
                ).show()
                viewModel.clearPostResult()
            }
            is AtomViewModel.PostResult.Error -> {
                Toast.makeText(
                    requireContext(),
                    getString(R.string.atom_post_error, result.message),
                    Toast.LENGTH_LONG
                ).show()
                viewModel.clearPostResult()
            }
            else -> { /* Idle / Loading — no UI action */ }
        }
    }

    // -------------------------------------------------------------------------
    // MapLibre lifecycle delegation
    // -------------------------------------------------------------------------

    override fun onStart() {
        super.onStart()
        mapView.onStart()
    }

    override fun onResume() {
        super.onResume()
        mapView.onResume()
        startLocationUpdatesIfPermitted()
    }

    override fun onPause() {
        super.onPause()
        mapView.onPause()
        stopLocationUpdates()
    }

    override fun onStop() {
        super.onStop()
        mapView.onStop()
    }

    override fun onDestroyView() {
        super.onDestroyView()
        mapView.onDestroy()
        _binding = null
    }

    override fun onSaveInstanceState(outState: Bundle) {
        super.onSaveInstanceState(outState)
        mapView.onSaveInstanceState(outState)
    }

    override fun onLowMemory() {
        super.onLowMemory()
        mapView.onLowMemory()
    }

    // -------------------------------------------------------------------------
    // Companion
    // -------------------------------------------------------------------------

    companion object {
        private const val TAG = "MapFragment"
        private const val MAP_STYLE_URL = "https://tiles.openfreemap.org/styles/liberty"
        private const val LOCATION_INTERVAL_MS = 5_000L
        private const val LOCATION_FASTEST_MS  = 2_000L
        private const val TAP_SLOP_PX = 32f

        fun newInstance() = MapFragment()
    }
}
