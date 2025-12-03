#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-50001}"
LOG_DIR="${LOG_DIR:-${ROOT_DIR}/logs}"
mkdir -p "${LOG_DIR}"
LOG_FILE="${LOG_DIR}/data_server_${PORT}.log"

echo "Starting data MCP server on ${HOST}:${PORT}, logs -> ${LOG_FILE}"
python mcp_servers/data/server.py --host "${HOST}" --port "${PORT}" 2>&1 | tee -a "${LOG_FILE}"
