#!/bin/bash
# Supervisor program: Vast PyWorker (runs on every boot, after the wrapper is healthy).
for i in $(seq 1 180); do curl -sf localhost:18000/health >/dev/null && break; sleep 2; done
curl -fsSL https://raw.githubusercontent.com/vast-ai/pyworker/main/start_server.sh | bash
