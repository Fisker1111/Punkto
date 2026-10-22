"""Fast guards for the scale measurement (convergence and accounting, not timings)."""
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / 'src'))

from hostile import measure_scale as scale  # noqa: E402


class ScaleEnvelope(unittest.TestCase):
    def _cell(self, overlap):
        pool = scale.build(300)
        return scale.cell(pool, pool[:int(300 * overlap)], overlap, 300)

    def test_identical_sets_converge_with_zero_useful_bytes(self):
        row = self._cell(1.0)
        self.assertTrue(row['converged_sets'])
        self.assertEqual(row['a_final'], 300)
        self.assertEqual(row['b_final'], 300)
        self.assertEqual(row['useful_bytes'], 0)
        self.assertIsNone(row['overhead_ratio'])
        # Nothing was needed, yet a full mutual sweep still moved a whole set.
        self.assertGreaterEqual(row['wire_bytes'], 300 * 80)
        self.assertGreaterEqual(row['steady_state']['wire_bytes'], 0)

    def test_disjoint_sets_converge_and_accounting_closes(self):
        row = self._cell(0.0)
        self.assertTrue(row['converged_sets'])
        self.assertEqual(row['records_needed'], 300)
        self.assertEqual(row['useful_bytes'], 300 * 384)
        self.assertGreater(row['overhead_ratio'], 3)
        self.assertEqual(
            row['wire_bytes'],
            row['request_bytes'] + row['response_bytes'])
        self.assertEqual(row['log_sizes'], [300, 300])
        self.assertEqual(row['candidate_sizes'], [0, 0])

    def test_half_overlap_and_fresh_subscriber(self):
        row = self._cell(0.5)
        self.assertTrue(row['converged_sets'])
        self.assertEqual(row['records_needed'], 150)
        self.assertEqual(row['useful_bytes'], 150 * 384)
        self.assertGreater(row['fresh_subscriber']['records'], 0)
        self.assertGreaterEqual(row['fresh_subscriber']['wire_bytes'], 300 * 200)


if __name__ == '__main__':
    unittest.main()
