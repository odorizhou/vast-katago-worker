#!/bin/bash
# Supervisor program: KataGo HTTP wrapper (runs on every boot).
export APPIMAGE_EXTRACT_AND_RUN=1
D=/workspace/katago
export KATAGO_EXECUTABLE=$D/katago KATAGO_CONFIG=$D/analysis.cfg KATAGO_MODEL=$D/model.bin.gz PORT=18000
mkdir -p /var/log/portal
: > /var/log/portal/katago.log     # per-run log: PyWorker matches KATAGO_HTTP_READY in it
python3 /workspace/kw/katago_http_wrapper.py 2>&1 | tee -a /var/log/portal/katago.log
