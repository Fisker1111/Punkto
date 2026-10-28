"""Ten real HTTP scenarios; failures retain diagnostics and print module summary."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from hostile.harness import Runner, report
from hostile.cases_network import SCENARIOS

ROWS = []


def tearDownModule():
    report('network', ROWS)


class NetworkHostile(unittest.TestCase):
    pass


def make_test(scenario):
    def test(self):
        repeats = 3 if scenario.__name__ == 'partition_rejoin' else 1
        outcomes = []
        for repetition in range(repeats):
            with Runner(scenario.__name__) as runner:
                try:
                    row = scenario(runner)
                    outcome = {key: row[key] for key in ('status', 'addresses', 'store_sizes')}
                    outcomes.append(outcome)
                    self.assertEqual(outcomes[0], outcome)
                    self.assertTrue(row['admitted_set_equality'])
                    self.assertEqual(row['candidate_sizes'], [0] * len(row['store_sizes']))
                except Exception as exc:
                    ROWS.append(dict(scenario=scenario.__name__, initiator='ref', status='FAIL',
                                     error=repr(exc), proxies=[dict(stats=p.stats(), exchanges=list(p.exchanges))
                                                              for p in runner.proxies]))
                    raise
                row['notes']['determinism_repetition'] = repetition + 1
                ROWS.append(row)
        if repeats == 3:
            ROWS[-1]['notes']['determinism'] = dict(repetitions=3, identical=True, outcomes=outcomes)
    return test


for scenario in SCENARIOS:
    setattr(NetworkHostile, 'test_' + scenario.__name__, make_test(scenario))

if __name__ == '__main__':
    unittest.main()
