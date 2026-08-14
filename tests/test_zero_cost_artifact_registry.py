from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "results/zero-cost-algorithm/artifact-registry.json"


class ZeroCostArtifactRegistryTests(unittest.TestCase):
    def test_registry_is_fail_closed(self):
        registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        self.assertEqual(registry["schema_version"], "zero-cost-algorithm-artifact-registry-v1")
        self.assertEqual(registry["artifact_count"], len(registry["artifacts"]))
        self.assertFalse(registry["sealed_final_accessed"])
        self.assertEqual(registry["paid_api_cost_usd"], 0.0)
        for artifact in registry["artifacts"]:
            path = ROOT / artifact["path"]
            self.assertTrue(path.is_file(), artifact["path"])
            self.assertEqual(path.stat().st_size, artifact["bytes"], artifact["path"])
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), artifact["sha256"], artifact["path"])

    def test_registry_contains_no_sealed_final_path(self):
        registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        for artifact in registry["artifacts"]:
            normalized = artifact["path"].casefold().replace("_", "-")
            self.assertNotIn("sealed-final", normalized)


if __name__ == "__main__":
    unittest.main()
