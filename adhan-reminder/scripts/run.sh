#!/bin/sh
# Finds a working Python 3.9+ (python3 on macOS/Linux; python or py on Windows)
# and runs adhan.py with the same arguments. Exits quietly if none is found,
# so a missing Python never breaks Claude Code.
dir=$(dirname "$0")
for py in python3 python py; do
  if command -v "$py" >/dev/null 2>&1 \
     && "$py" -c "import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)" >/dev/null 2>&1; then
    exec "$py" "$dir/adhan.py" "$@"
  fi
done
exit 0
