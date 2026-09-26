#!/bin/sh
# LOG_LEVEL: debug | info | warning | error | critical
# warning and stricter skip the per-request access line.
level="${LOG_LEVEL:-warning}"
case "$level" in
  debug|info)
    exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --log-level "$level"
    ;;
  *)
    exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --log-level "$level" --no-access-log
    ;;
esac
