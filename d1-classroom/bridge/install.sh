#!/bin/sh
set -eu
DEPLOY_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
if [ -n "${D1_PYTHON:-}" ]; then
    exec "$D1_PYTHON" "$DEPLOY_DIR/install.py" "$@"
fi
for D1_CANDIDATE in python3.10 python3; do
    if command -v "$D1_CANDIDATE" >/dev/null 2>&1 && "$D1_CANDIDATE" -c 'import sys; sys.exit(sys.version_info[:2] != (3, 10))' 2>/dev/null; then
        exec "$D1_CANDIDATE" "$DEPLOY_DIR/install.py" "$@"
    fi
done
echo 'CPython 3.10 is required by the bundled vendor SDK. No files were installed.' >&2
exit 1
