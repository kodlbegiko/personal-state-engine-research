#!/usr/bin/env python3
import argparse

from personal_state_engine.model_adapters import RunManifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest")
    args = parser.parse_args()
    manifest = RunManifest.from_json(args.manifest)
    print(f"valid manifest: {manifest.model_provider}/{manifest.model_id}@{manifest.model_version}")
