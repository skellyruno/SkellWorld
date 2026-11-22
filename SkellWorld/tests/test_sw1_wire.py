"""Regression coverage for the informational SW1 localhost wire parser.

Run from repository root (also exercised in Windows + Ubuntu CI):
    python -m unittest discover -s SkellWorld/tests -p 'test_sw1_wire.py'
"""
import importlib.util
import re
from pathlib import Path
import unittest
from unittest import mock

MODULE_PATH = Path(__file__).resolve().parents[2] / "tools" / "skellworld_hub.py"
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

    def test_maximum_valid_fields_roundtrip(self):
        # Individual field caps (47/47/95) are stricter than MAX_WIRE (256).
        instance, topic, value = "i" * 47, "t" * 47, "v" * 95
        wire = hub.encode("EVENT", instance, topic, value)
        self.assertEqual(len(wire), 202)
        self.assertLess(len(wire), hub.MAX_WIRE)
        self.assertEqual(hub.decode(wire), ["EVENT", instance, topic, value])
        self.assertIsNone(hub.decode(wire[:-1] + b"v\n"))

    def test_boundary_length_is_exclusive(self):
        # A normal frame cannot reach 255 bytes: VALUE caps at 95 chars.
        # Widen only the VALUE regex locally to isolate the 256-byte wire
        # safety guard; leave production field validation unchanged.
        prefix = b"SW1|EVENT|k|t|"
        longest = prefix + b"x" * (hub.MAX_WIRE - len(prefix) - 2) + b"\n"
        self.assertEqual(len(longest), hub.MAX_WIRE - 1)
        with mock.patch.object(hub, "VALUE", re.compile(r"^[\x20-\x7e]{1,255}$")):
            self.assertEqual(hub.decode(longest), ["EVENT", "k", "t", "x" * 240])
            exactly_limit = longest[:-1] + b"x\n"
            self.assertEqual(len(exactly_limit), hub.MAX_WIRE)
            self.assertIsNone(hub.decode(exactly_limit))
        with self.assertRaisesRegex(ValueError, "oversized wire frame"):
            hub.encode("EVENT", "k", "t", "x" * hub.MAX_WIRE)

if __name__ == "__main__":
    unittest.main()
