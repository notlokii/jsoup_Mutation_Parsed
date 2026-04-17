#!/bin/bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

"$ROOT_DIR/scripts/run_pit.sh"

python3 "$ROOT_DIR/scripts/parse_mutations.py" \
  --mutations "$ROOT_DIR/Test/target/pit-reports/mutations.xml" \
  --output "$ROOT_DIR/reports"

python3 "$ROOT_DIR/scripts/apply_mutations.py" \
  --mutations "$ROOT_DIR/Test/target/pit-reports/mutations.xml" \
  --project "$ROOT_DIR/Test" \
  --output "$ROOT_DIR/mutants"

