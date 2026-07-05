from __future__ import annotations

import asyncio
import json
import sys

from runtime.health import validate_runtime
from runtime.run_config import RunMode, load_run_config


def _print_health(checks) -> None:
    print("Runtime health:")
    for item in checks:
        status = "ok" if item.available else "missing"
        required = "required" if item.required else "optional"
        print(f"- {item.name}: {status} ({required}) - {item.message}")


def main(argv=None) -> int:
    config = load_run_config(argv)
    checks = validate_runtime(config)
    print(json.dumps(config.to_dict(), ensure_ascii=False, indent=2))
    _print_health(checks)

    failed_required = [item for item in checks if item.required and not item.available]
    if config.dry_run_config:
        return 1 if config.mode == RunMode.FULL and failed_required else 0

    if failed_required:
        print("Cannot start because required runtime checks failed:", file=sys.stderr)
        for item in failed_required:
            print(f"- {item.name}: {item.message}", file=sys.stderr)
        return 1

    from runtime.runner import run_pipeline, run_stage

    try:
        if config.mode == RunMode.STAGE:
            manifest_or_artifact = asyncio.run(run_stage(config, config.stage))
            print(f"Stage artifact: {manifest_or_artifact.path}")
        else:
            manifest = asyncio.run(run_pipeline(config))
            print(f"Manifest: {config.output_dir / config.session_id / 'manifest.json'}")
            print(f"Stages: {manifest.stages}")
    except Exception as exc:
        print(f"Runtime error: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

