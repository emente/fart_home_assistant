#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

RESOURCE_URL = "/local/fart-ha-card.js"


def ensure_lovelace_resource(configuration_path: Path) -> tuple[bool, str]:
    """Ensure configuration.yaml contains the FART Lovelace resource.

    Returns (changed, message)
    """
    if not configuration_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {configuration_path}")

    original = configuration_path.read_text(encoding="utf-8")
    if RESOURCE_URL in original:
        return False, "The FART card resource is already configured."

    lines = original.splitlines(keepends=True)
    lovelace_index = next(
        (index for index, line in enumerate(lines) if line.strip() == "lovelace:"),
        None,
    )

    if lovelace_index is None:
        if original and not original.endswith("\n"):
            original += "\n"
        block = (
            "\n"
            "lovelace:\n"
            "  resources:\n"
            f"    - url: {RESOURCE_URL}\n"
            "      type: module\n"
        )
        configuration_path.write_text(original + block, encoding="utf-8")
        return True, "Added a new lovelace resources block to the configuration file."

    resources_index = next(
        (
            index
            for index in range(lovelace_index + 1, len(lines))
            if lines[index].strip() == "resources:"
        ),
        None,
    )

    if resources_index is None:
        insert_at = lovelace_index + 1
        lines[insert_at:insert_at] = [
            "  resources:\n",
            f"    - url: {RESOURCE_URL}\n",
            "      type: module\n",
        ]
    else:
        insert_at = resources_index + 1
        lines[insert_at:insert_at] = [
            f"    - url: {RESOURCE_URL}\n",
            "      type: module\n",
        ]

    configuration_path.write_text("".join(lines), encoding="utf-8")
    return True, "Added the FART card resource to the existing lovelace configuration."


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Add the FART Lovelace resource to Home Assistant configuration.yaml if it is missing."
    )
    parser.add_argument(
        "configuration",
        nargs="?",
        default="configuration.yaml",
        help="Path to configuration.yaml (default: configuration.yaml)",
    )
    args = parser.parse_args()

    try:
        changed, message = ensure_lovelace_resource(Path(args.configuration))
    except Exception as err:
        print(f"Error: {err}", file=sys.stderr)
        return 1

    print(message)
    return 0


if __name__ == "__main__":
    import sys

    raise SystemExit(main())
