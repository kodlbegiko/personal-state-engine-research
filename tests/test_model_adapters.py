from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

from personal_state_engine.model_adapters import (
    ModelAdapterError,
    ModelRequest,
    ModelResponse,
    ReplayAdapter,
    RunManifest,
    SubprocessJSONAdapter,
)


class ModelAdapterTests(unittest.TestCase):
    def manifest(self, **overrides):
        data = {
            "model_provider": "test",
            "model_id": "model",
            "model_version": "1",
            "temperature": 0.0,
            "seed": 7,
            "token_budget": 256,
            "timeout_seconds": 2.0,
            "tool_policy": "none",
        }
        data.update(overrides)
        return RunManifest(**data)

    def request(self, **overrides):
        data = {
            "request_id": "r1",
            "system_prompt": "test",
            "messages": ({"role": "user", "content": "hello"},),
            "manifest": self.manifest(),
        }
        data.update(overrides)
        return ModelRequest(**data)

    def test_manifest_requires_all_fields(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.json"
            path.write_text("{}")
            with self.assertRaises(ModelAdapterError):
                RunManifest.from_json(path)

    def test_replay_adapter_is_deterministic(self):
        response = ModelResponse("r1", "ok", {"input_tokens": 1}, 2.0, {})
        adapter = ReplayAdapter({"r1": response})
        self.assertEqual(adapter.complete(self.request()), response)

    def test_replay_missing_response_fails(self):
        with self.assertRaises(ModelAdapterError):
            ReplayAdapter({}).complete(self.request())

    def test_subprocess_adapter_round_trip(self):
        script = (
            "import json,sys; p=json.load(sys.stdin); "
            "print(json.dumps({'request_id':p['request_id'],'text':'ok','usage':{'output_tokens':1},'latency_ms':1}))"
        )
        adapter = SubprocessJSONAdapter([sys.executable, "-c", script])
        response = adapter.complete(self.request())
        self.assertEqual(response.text, "ok")
        self.assertEqual(response.request_id, "r1")

    def test_subprocess_malformed_output_fails(self):
        adapter = SubprocessJSONAdapter([sys.executable, "-c", "print('not-json')"])
        with self.assertRaises(ModelAdapterError):
            adapter.complete(self.request())


if __name__ == "__main__":
    unittest.main()
