import json
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
class CatalogTests(unittest.TestCase):
    def test_catalog_integrity(self):
        d=json.loads((ROOT/"SkellWorld"/"catalog.json").read_text())
        self.assertEqual(d["schema"],"skellworld-catalog/1")
        self.assertGreaterEqual(len(d["plugins"]),20)
        names=[p["repository"] for p in d["plugins"]]
        self.assertEqual(len(names),len(set(names)))
        self.assertTrue(all(name.startswith("skellyruno/skell") for name in names))
        self.assertEqual(len([p for p in d["plugins"] if p["integration"]=="world-demo"]),1)
        self.assertEqual({p["product_id"] for p in d["plugins"] if p["integration"]=="world-enabled"},
                         {"skell.key","skell.tune","skell.silence"})
        codes=[p["vst3_code"].lower() for p in d["plugins"] if p.get("vst3_code")]
        self.assertEqual(len(codes),len(set(codes)))
        self.assertGreaterEqual(len(codes),22)
        self.assertTrue(all(p["integration"] in {"planned","shared-core-only","world-demo","world-enabled"} for p in d["plugins"]))
    def test_demo_identity(self):
        d=json.loads((ROOT/"skellworld.json").read_text())
        self.assertEqual(d["schema"],"skellworld-plugin/1")
        self.assertEqual(d["product_id"],"skellcore.quickstart")
        self.assertEqual(d["connection"],"explicit-opt-in-loopback")
if __name__=="__main__":unittest.main()
