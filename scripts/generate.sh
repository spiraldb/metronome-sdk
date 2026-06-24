#!/usr/bin/env bash
# Regenerate src/lib.rs from the Metronome OpenAPI spec.
#
#   ./scripts/generate.sh            # generate from the vendored spec
#   ./scripts/generate.sh --refresh  # re-download the spec first, then generate
#
# Requires: cargo-progenitor  (cargo install cargo-progenitor --version 0.14.0)
set -euo pipefail

cd "$(dirname "$0")/.."

SPEC_URL="https://api.metronome.com/v1/docs/openapi"
RAW_SPEC="spec/metronome-openapi.json"
PATCHED_SPEC="$(mktemp -t metronome-spec).json"
trap 'rm -f "$PATCHED_SPEC"' EXIT

if [[ "${1:-}" == "--refresh" ]]; then
  echo "==> downloading spec from $SPEC_URL"
  curl -sSfL -o "$RAW_SPEC" "$SPEC_URL"
fi

echo "==> patching spec (work around case-insensitive / mis-typed enums)"
python3 scripts/patch_spec.py "$RAW_SPEC" "$PATCHED_SPEC"

echo "==> generating client"
GEN_DIR="$(mktemp -d -t metronome-gen)"
trap 'rm -rf "$PATCHED_SPEC" "$GEN_DIR"' EXIT
cargo progenitor -i "$PATCHED_SPEC" -o "$GEN_DIR" -n metronome-sdk -v 0.1.0 >/dev/null

cp "$GEN_DIR/src/lib.rs" src/lib.rs
echo "==> wrote src/lib.rs ($(wc -l < src/lib.rs | tr -d ' ') lines)"
echo "==> cargo check"
cargo check
echo "done."
