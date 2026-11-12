"""Check fictional language assets without importing or mutating the SW1 bus."""
from __future__ import annotations
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CULTURE = ROOT / "culture" / "skellenese"


class SkelleneseCultureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dictionary = json.loads((CULTURE / "dictionary.json").read_text("utf-8"))
        cls.cipher = json.loads((CULTURE / "skellcipher.json").read_text("utf-8"))

    def test_dictionary_has_distinct_brand_identity(self):
        self.assertEqual(self.dictionary["schema"], "skellworld/skellenese-dictionary/1")
        self.assertEqual(self.dictionary["language"], "Skellenese")
        self.assertNotIn("SkellLang", self.dictionary["language"])
        self.assertEqual(self.dictionary["status"], "draft")

    def test_proposals_require_approval_and_attribution(self):
        seen = set()
        self.assertLessEqual(len(self.dictionary["entries"]), 100)
        for item in self.dictionary["entries"]:
            with self.subTest(item=item):
                self.assertRegex(item["id"], r"^[a-z][a-z0-9_]{0,31}$")
                self.assertNotIn(item["id"], seen)
                seen.add(item["id"])
                self.assertEqual(item["status"], "proposal")
                for key in ("term", "meaning", "pronunciation", "example", "origin", "credit"):
                    self.assertIsInstance(item[key], str)
                    self.assertTrue(item[key].strip())
                    self.assertLessEqual(len(item[key]), 240)
                    self.assertFalse(any(ord(ch) < 32 for ch in item[key]))

    def test_cipher_is_not_falsely_shipped_as_encryption(self):
        self.assertEqual(self.cipher["name"], "SkellCipher")
        self.assertEqual(self.cipher["status"], "design-not-approved")
        self.assertIn("not-encryption", self.cipher["security"])
        self.assertEqual(self.cipher["glyphs"], {})
        self.assertIn("plaintext", self.cipher["accessibility"])


if __name__ == "__main__":
    unittest.main()
