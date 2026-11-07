#!/bin/bash
# Run by vastai/base-image via PROVISIONING_SCRIPT. Fetches KataGo, starts the wrapper, then Vast's PyWorker.
set -u
rm -rf /workspace/kw
git clone --depth 1 https://github.com/odorizhou/vast-katago-worker /workspace/kw
bash /workspace/kw/provision.sh
nohup bash -c 'curl -fsSL https://raw.githubusercontent.com/vast-ai/pyworker/main/start_server.sh | bash' > /workspace/start_server.out 2>&1 &
