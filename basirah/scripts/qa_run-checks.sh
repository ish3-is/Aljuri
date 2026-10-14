#!/usr/bin/env bash
set -euo pipefail
cd "/d/MDR/Aljuri-Greadute-Project/basirah"
echo "=== tsc ==="
npx tsc -p tsconfig.app.json --noEmit
echo "tsc exit=$?"
echo "=== lint ==="
npm run lint
echo "lint exit=$?"
echo "=== build ==="
npm run build
echo "build exit=$?"
