#!/bin/bash
# Run by vastai/base-image via PROVISIONING_SCRIPT (first boot only). Registers supervisor programs so
# the wrapper and PyWorker start on EVERY boot, including restarts of a stopped (cold) worker.
set -eu
rm -rf /workspace/kw
git clone --depth 1 https://github.com/odorizhou/vast-katago-worker /workspace/kw
chmod +x /workspace/kw/*.sh
bash /workspace/kw/provision.sh

mk() {  # name script
cat > /etc/supervisor/conf.d/$1.conf <<CONF
[program:$1]
environment=PROC_NAME="%(program_name)s"
command=$2
autostart=true
autorestart=unexpected
exitcodes=0
startsecs=5
stopasgroup=true
killasgroup=true
stopsignal=TERM
stopwaitsecs=10
stdout_logfile=/dev/stdout
redirect_stderr=true
stdout_events_enabled=true
stdout_logfile_maxbytes=0
stdout_logfile_backups=0
CONF
}
mk katago-wrapper /workspace/kw/run_wrapper.sh
mk katago-pyworker /workspace/kw/run_pyworker.sh
supervisorctl reread && supervisorctl update
