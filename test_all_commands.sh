#!/bin/bash
# Portable command smoke test for the current PolyTerm checkout.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON="${POLYTERM_PYTHON:-$ROOT_DIR/.venv/bin/python}"

if [ ! -x "$PYTHON" ]; then
    PYTHON="$(command -v python3)"
fi

cd "$ROOT_DIR"

echo "PolyTerm command smoke suite"
echo "============================"
echo "Python: $PYTHON"
echo ""

"$PYTHON" - <<'PY'
import subprocess
import sys

from polyterm.cli.lazy_group import LAZY_COMMANDS

base = [sys.executable, "-m", "polyterm"]
failures = []

command_names = set(LAZY_COMMANDS)
command_names.add("update")

for command in sorted(command_names):
    result = subprocess.run(
        base + [command, "--help"],
        text=True,
        capture_output=True,
        timeout=15,
    )
    if result.returncode != 0:
        failures.append((command, result.stderr or result.stdout))

if failures:
    for command, output in failures:
        print(f"[FAIL] {command} --help")
        print(output)
    raise SystemExit(1)

print(f"[OK] {len(command_names)} registered commands expose help")
PY

"$PYTHON" -m polyterm --version
"$PYTHON" -m polyterm config --get api.gamma_base_url
"$PYTHON" -m polyterm fees --amount 100 --price 0.65 --format json >/tmp/polyterm-fees-smoke.json
"$PYTHON" -m polyterm search "bitcoin" --limit 2 --format json >/tmp/polyterm-search-smoke.json

rm -f /tmp/polyterm-fees-smoke.json /tmp/polyterm-search-smoke.json

echo ""
echo "All command smoke checks passed."
