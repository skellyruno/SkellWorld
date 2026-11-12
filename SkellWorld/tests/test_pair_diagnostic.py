"""SW1 integration fixture is isolated and does not claim FL Studio coverage."""
import sys
from pathlib import Path
import unittest
TOOLS = str(Path(__file__).resolve().parents[2] / "tools")
if TOOLS not in sys.path: sys.path.insert(0, TOOLS)
from skellworld_pair_diagnostic import run_pair_diagnostic

class WorldPairDiagnosticTests(unittest.TestCase):
    def test_simulated_key_to_tune_complete_tuning_and_leave(self):
        result = run_pair_diagnostic()
        self.assertEqual(result["key_to_tune"], "pass")
        self.assertEqual(result["disconnect_cleanup"], "pass")
        self.assertEqual(result["actual_vst3_host_test"], "NOT RUN")

if __name__ == "__main__":
    unittest.main()
