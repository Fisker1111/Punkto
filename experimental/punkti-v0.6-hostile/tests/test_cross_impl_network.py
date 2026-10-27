"""The same ten scenarios in both initiator directions: twenty test methods."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from hostile.harness import Runner, report
from hostile.cases_network import SCENARIOS

ROWS = []
SETS = {}


def tearDownModule():
    report('cross_impl_network', ROWS)


class CrossImplementation(unittest.TestCase):
    pass


def make_test(scenario, direction):
    def test(self):
        with Runner(scenario.__name__, direction) as runner:
            try:
                row = scenario(runner)
                other = SETS.get(scenario.__name__)
                if other is not None:
                    self.assertEqual(row['addresses'], other)
                SETS[scenario.__name__] = row['addresses']
                self.assertTrue(row['admitted_set_equality'])
                self.assertEqual(row['candidate_sizes'], [0] * len(row['store_sizes']))
            except Exception as exc:
                ROWS.append(dict(scenario=scenario.__name__, initiator=direction, status='FAIL',
                                 error=repr(exc), proxies=[dict(stats=p.stats(), exchanges=list(p.exchanges))
                                                          for p in runner.proxies]))
                raise
            ROWS.append(row)
    return test


for scenario in SCENARIOS:
    for direction in ('ref', 'nb'):
        setattr(CrossImplementation, f'test_{scenario.__name__}_{direction}', make_test(scenario, direction))

if __name__ == '__main__':
    unittest.main()
