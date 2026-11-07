#!/bin/bash
# Runs on the Vast worker before start_server.sh. Fetches KataGo + model, starts the HTTP wrapper.
# Defaults: official KataGo v1.18.2 CUDA 12.8 release (an AppImage -> needs extract-and-run, no FUSE in containers)
# and the public kata1-tf3-b11c768 network. Override with KATAGO_BIN_URL / KATAGO_MODEL_URL.
set -euo pipefail
KATAGO_BIN_URL=${KATAGO_BIN_URL:-https://github.com/lightvector/KataGo/releases/download/v1.18.2/katago-v1.18.2-cuda12.8-cudnn9.8.0-linux-x64.zip}
KATAGO_MODEL_URL=${KATAGO_MODEL_URL:-https://media.katagotraining.org/uploaded/networks/models/kata1/kata1-tf3-b11c768-s12382M-d6533M.bin.gz}
export APPIMAGE_EXTRACT_AND_RUN=1
D=/workspace/katago; mkdir -p "$D" /var/log/portal
HDR=(); [ -n "${DL_AUTH_HEADER:-}" ] && HDR=(-H "$DL_AUTH_HEADER")
[ -x "$D/katago" ] || { curl -fL "${HDR[@]}" "$KATAGO_BIN_URL" -o "$D/katago.zip"; python3 -c "import zipfile,sys;zipfile.ZipFile(sys.argv[1]).extract('katago',sys.argv[2])" "$D/katago.zip" "$D"; chmod +x "$D/katago"; }
[ -s "$D/model.bin.gz" ]  || curl -fL "${HDR[@]}" "$KATAGO_MODEL_URL" -o "$D/model.bin.gz"
cat > "$D/analysis.cfg" <<CFG
reportAnalysisWinratesAs = BLACK
maxVisits = 500
numAnalysisThreads = 2
numSearchThreadsPerAnalysisThread = 16
nnMaxBatchSize = 64
nnCacheSizePowerOfTwo = 22
nnMutexPoolSizePowerOfTwo = 16
CFG
export KATAGO_EXECUTABLE="$D/katago" KATAGO_CONFIG="$D/analysis.cfg" KATAGO_MODEL="$D/model.bin.gz" PORT=18000
: > /var/log/portal/katago.log   # per-run log (PyWorker matches on it)
nohup python3 "$(dirname "$0")/katago_http_wrapper.py" >> /var/log/portal/katago.log 2>&1 &
