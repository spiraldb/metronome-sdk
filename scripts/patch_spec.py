#!/usr/bin/env python3
"""Patch the raw Metronome OpenAPI spec so progenitor/typify can generate it.

Metronome's published spec lists case-insensitive enums by enumerating every
casing of each value (e.g. ["count","Count","COUNT", ...]). typify can't turn
three casings into one unique Rust variant name, so it panics. Stainless's
official SDKs use a private overlay that collapses these; we don't have it.

Fix: any enum whose values collide when lower-cased is downgraded to a plain
`string`. This round-trips losslessly regardless of which casing the API
returns (important for billing correctness). Every non-colliding enum keeps
its strong typing.

Usage: patch_spec.py <input.json> <output.json>
"""
import json
import sys


def case_insensitive_collision(values):
    strs = [v for v in values if isinstance(v, str)]
    if len(strs) != len(values):
        return False  # non-string enum (e.g. ints) — leave it alone
    folded = [v.lower() for v in strs]
    return len(set(folded)) < len(folded)


def patch(node, stats):
    if isinstance(node, dict):
        enum = node.get("enum")
        if isinstance(enum, list) and enum and all(isinstance(v, str) for v in enum):
            # Some enums are mis-typed as object/array though their values are
            # strings (e.g. billable_status: {type:object, enum:[...strings]}).
            # typify reads each enum value against the declared type and errors.
            # Anchor the type to what the values actually are.
            if node.get("type") != "string":
                node["type"] = "string"
                stats["retyped"] += 1
            if case_insensitive_collision(enum):
                del node["enum"]
                node.pop("default", None)  # default may not survive the downgrade
                stats["downgraded"] += 1
        # `format` is only meaningful on scalars. The spec attaches scalar
        # formats (e.g. uuid) to array/object nodes — really meant for the
        # items — which trips typify. Strip it from non-scalar nodes.
        if "format" in node and node.get("type") in ("array", "object"):
            del node["format"]
            stats["stripped_format"] += 1
        for v in node.values():
            patch(v, stats)
    elif isinstance(node, list):
        for v in node:
            patch(v, stats)


def main():
    if len(sys.argv) != 3:
        sys.exit(f"usage: {sys.argv[0]} <input.json> <output.json>")
    src, dst = sys.argv[1], sys.argv[2]
    spec = json.load(open(src))
    stats = {"downgraded": 0, "retyped": 0, "stripped_format": 0}
    patch(spec, stats)
    json.dump(spec, open(dst, "w"), indent=2)
    print(
        f"patched {src} -> {dst}: "
        f"downgraded {stats['downgraded']} case-insensitive enums to string, "
        f"retyped {stats['retyped']} mis-typed string enums, "
        f"stripped format from {stats['stripped_format']} non-scalar nodes"
    )


if __name__ == "__main__":
    main()
