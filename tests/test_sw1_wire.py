"""Regression coverage for the informational SW1 localhost wire parser.

Run from repository root:
    python -m unittest discover -s tests -p 'test_sw1_wire.py'
"""
import importlib.util
from pathlib import Path
import unittest

MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "skellworld_hub.py"
spec = importlib.util.spec_from_file_location("skellworld_hub_under_test", MODULE_PATH)
hub = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hub)


class SW1WireTests(unittest.TestCase):
    def test_valid_informational_event_roundtrip(self):
        wire = hub.encode("EVENT", "key.1", "musical.key", "0.1")
        self.assertEqual(hub.decode(wire), ["EVENT", "key.1", "musical.key", "0.1"])

    def test_rejects_malformed_and_non_ascii_frames(self):
        valid = hub.encode("EVENT", "key.1", "musical.key", "0.1")
        bad = [
            valid[:-1],  # no terminator
            valid.replace(b"SW1|", b"SW2|", 1),
            valid.replace(b"EVENT", b"COMMAND", 1),
            valid.replace(b"key.1", b"bad id", 1),
            valid.replace(b"0.1", b"0|1", 1),
            valid.replace(b"0.1", b"0\\1", 1),
            valid.replace(b"0.1", b"\xff", 1),
            b"SW1|EVENT|key.1|musical.key|" + b"x" * 250 + b"\n",
        ]
        for frame in bad:
            with self.subTest(frame=repr(frame[:64])):
                self.assertIsNone(hub.decode(frame))

    def test_boundary_length_is_exclusive(self):
        # The protocol caps complete frames at strictly less than MAX_WIRE.
        prefix = b"SW1|EVENT|k|t|"
        longest = prefix + b"x" * (hub.MAX_WIRE - len(prefix) - 2) + b"\n"
        self.assertEqual(len(longest), hub.MAX_WIRE - 1)
        self.assertIsNotNone(hub.decode(longest))
        self.assertIsNone(hub.decode(longest[:-1] + b"x\n"))


if __name__ == "__main__":
    unittest.main()
