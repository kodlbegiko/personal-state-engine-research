from __future__ import annotations

import json
import math
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

    def manifest_file(self, data):
        directory = tempfile.TemporaryDirectory()
        path = Path(directory.name) / "manifest.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        return directory, path

    def valid_manifest_data(self):
        return {
            "model_provider": "test",
            "model_id": "model",
            "model_version": "1",
            "temperature": 0.0,
            "seed": 7,
            "token_budget": 256,
            "timeout_seconds": 2.0,
            "tool_policy": "none",
        }

    def test_manifest_requires_all_fields(self):
        directory, path = self.manifest_file({})
        self.addCleanup(directory.cleanup)
        with self.assertRaises(ModelAdapterError):
            RunManifest.from_json(path)

    def test_manifest_rejects_blank_and_placeholder_identifiers(self):
        for field, value in (
            ("model_provider", " "),
            ("model_id", "REPLACE_ME"),
            ("model_version", "PIN_EXACT_VERSION"),
            ("tool_policy", "<tool-policy>"),
        ):
            with self.subTest(field=field, value=value):
                data = self.valid_manifest_data()
                data[field] = value
                directory, path = self.manifest_file(data)
                try:
                    with self.assertRaises(ModelAdapterError):
                        RunManifest.from_json(path)
                finally:
                    directory.cleanup()

    def test_manifest_rejects_invalid_types_and_non_finite_values(self):
        invalid = (
            ("seed", True),
            ("seed", "7"),
            ("token_budget", 2.5),
            ("token_budget", True),
            ("timeout_seconds", float("inf")),
            ("temperature", math.nan),
        )
        for field, value in invalid:
            with self.subTest(field=field, value=value):
                data = self.valid_manifest_data()
                data[field] = value
                directory, path = self.manifest_file(data)
                try:
                    with self.assertRaises(ModelAdapterError):
                        RunManifest.from_json(path)
                finally:
                    directory.cleanup()

    def test_manifest_rejects_unexpected_fields(self):
        data = self.valid_manifest_data()
        data["model_alias"] = "latest"
        directory, path = self.manifest_file(data)
        self.addCleanup(directory.cleanup)
        with self.assertRaises(ModelAdapterError):
            RunManifest.from_json(path)

    def test_committed_template_fails_until_pinned(self):
        with self.assertRaises(ModelAdapterError):
            RunManifest.from_json("experiments/configs/model-run-template.json")

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

    def test_subprocess_mismatched_request_id_fails(self):
        script = (
            "import json,sys; json.load(sys.stdin); "
            "print(json.dumps({'request_id':'stale-request','text':'ok','usage':{},'latency_ms':1}))"
        )
        adapter = SubprocessJSONAdapter([sys.executable, "-c", script])
        with self.assertRaisesRegex(ModelAdapterError, "request_id mismatch"):
            adapter.complete(self.request())

    def test_subprocess_rejects_negative_usage(self):
        script = (
            "import json,sys; p=json.load(sys.stdin); "
            "print(json.dumps({'request_id':p['request_id'],'text':'ok','usage':{'output_tokens':-1},'latency_ms':1}))"
        )
        adapter = SubprocessJSONAdapter([sys.executable, "-c", script])
        with self.assertRaises(ModelAdapterError):
            adapter.complete(self.request())

    def test_subprocess_rejects_negative_latency(self):
        script = (
            "import json,sys; p=json.load(sys.stdin); "
            "print(json.dumps({'request_id':p['request_id'],'text':'ok','usage':{},'latency_ms':-1}))"
        )
        adapter = SubprocessJSONAdapter([sys.executable, "-c", script])
        with self.assertRaises(ModelAdapterError):
            adapter.complete(self.request())

    def test_subprocess_malformed_output_fails(self):
        adapter = SubprocessJSONAdapter([sys.executable, "-c", "print('not-json')"])
        with self.assertRaises(ModelAdapterError):
            adapter.complete(self.request())


if __name__ == "__main__":
    unittest.main()
