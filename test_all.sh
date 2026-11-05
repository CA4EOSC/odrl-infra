#!/usr/bin/env bash
set -e

# Determine project root (directory containing this script)
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

echo "=================================================="
echo " Running ODRL Infra Test Suite"
echo "=================================================="

# 1. Run Python pytest suite
echo ""
echo "-> Running Python Backend & Vocabulary Tests..."
export PYTHONPATH="$DIR"
pytest "$DIR/tests" -v

# 2. Run Frontend Build / Verification
if [ -d "$DIR/frontend" ]; then
    echo ""
    echo "-> Running Frontend Build..."
    (cd "$DIR/frontend" && npm run build)
fi

echo ""
echo "=================================================="
echo " All tests completed successfully!"
echo "=================================================="
