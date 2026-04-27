package xyz.punkto.android.ui

import android.content.Context
import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Toast
import com.google.android.material.bottomsheet.BottomSheetDialogFragment
import xyz.punkto.android.data.Atom
import xyz.punkto.android.databinding.FragmentAtomBottomSheetBinding
import xyz.punkto.android.geohash.Geohash3D
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

/**
 * AtomBottomSheetFragment — displays full details for a single Punkto atom.
 *
 * Create via [newInstance], passing the [Atom] entity.
 * The fragment shows the canonical Punkto address, decoded lat/lon/alt,
 * author, text payload, and a human-readable timestamp.
 * Copy and Share actions are available for the Punkto address.
 */
class AtomBottomSheetFragment : BottomSheetDialogFragment() {

    private var _binding: FragmentAtomBottomSheetBinding? = null
    private val binding get() = _binding!!

    private lateinit var atom: Atom

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        @Suppress("DEPRECATION")
        atom = requireArguments().getSerializable(ARG_ATOM) as Atom
    }

    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View {
        _binding = FragmentAtomBottomSheetBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)
        populateViews()
        wireActions()
    }

    private fun populateViews() {
        // Punkto canonical address
        binding.tvPunkto.text = atom.punkto

        // Decode lat/lon/alt from geohash
        try {
            val (lat, lon, alt) = Geohash3D.fromPunkto(atom.punkto)
            val floor = (alt / 3.5).toInt()
            val floorLabel = if (floor > 0) "  ·  Floor $floor" else ""
            binding.tvCoords.text = String.format(
                Locale.US, "%.6f°, %.6f°  ·  %.0f m%s", lat, lon, alt, floorLabel
            )
        } catch (e: Exception) {
            binding.tvCoords.text = atom.punkto
        }

        // Author
        binding.tvAuthor.text = atom.f?.takeIf { it.isNotBlank() } ?: "—"

        // Text payload
        binding.tvText.text = atom.x?.takeIf { it.isNotBlank() } ?: "—"

        // Timestamp
        binding.tvTime.text = formatTimestamp(atom.t)
    }

    private fun wireActions() {
        // C7 — Copy Punkto address to clipboard
        binding.btnCopyAddress.setOnClickListener {
            val clipboard = requireContext()
                .getSystemService(Context.CLIPBOARD_SERVICE) as android.content.ClipboardManager
            clipboard.setPrimaryClip(
                android.content.ClipData.newPlainText("Punkto", atom.punkto)
            )
            Toast.makeText(requireContext(), "Copied!", Toast.LENGTH_SHORT).show()
        }

        // C7 — Share Punkto address as URL
        binding.btnShare.setOnClickListener {
            val hash = atom.punkto.removePrefix("p:")
            val url = "https://punkto.xyz/p/$hash"
            val intent = android.content.Intent(android.content.Intent.ACTION_SEND).apply {
                type = "text/plain"
                putExtra(android.content.Intent.EXTRA_TEXT, url)
            }
            startActivity(android.content.Intent.createChooser(intent, "Share Punkto"))
        }
    }

    private fun formatTimestamp(unixMs: Long): String {
        return try {
            val sdf = SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.getDefault())
            sdf.format(Date(unixMs))
        } catch (e: Exception) {
            unixMs.toString()
        }
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }

    companion object {
        const val TAG = "AtomBottomSheet"
        private const val ARG_ATOM = "arg_atom"

        fun newInstance(atom: Atom): AtomBottomSheetFragment {
            return AtomBottomSheetFragment().apply {
                arguments = Bundle().apply {
                    putSerializable(ARG_ATOM, atom)
                }
            }
        }
    }
}
