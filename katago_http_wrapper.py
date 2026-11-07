#!/usr/bin/env python3
"""Stateless HTTP wrapper around KataGo's JSON analysis engine.

Each POST /analyze carries the full position (size, komi, rules, moves,
initialStones, analyzeTurns, maxVisits) -- exactly KataGo's native analysis
query -- so any worker can serve any request. No sessions.

Env: KATAGO_EXECUTABLE, KATAGO_CONFIG, KATAGO_MODEL, PORT (default 18000),
     MAX_VISITS_CAP (default 2000), MAX_TURNS_CAP (default 400)
Prints KATAGO_HTTP_READY once KataGo has loaded (for PyWorker on_load).
"""
import json, os, subprocess, sys, threading, itertools, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

KATAGO = os.environ["KATAGO_EXECUTABLE"]
CFG = os.environ["KATAGO_CONFIG"]
MODEL = os.environ["KATAGO_MODEL"]
PORT = int(os.environ.get("PORT", "18000"))
VISITS_CAP = int(os.environ.get("MAX_VISITS_CAP", "2000"))
TURNS_CAP = int(os.environ.get("MAX_TURNS_CAP", "400"))

proc = subprocess.Popen(
    [KATAGO, "analysis", "-config", CFG, "-model", MODEL],
    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    text=True, bufsize=1,
)
write_lock = threading.Lock()
pending = {}            # qid -> {"expect": n, "results": {}, "event": Event}
pending_lock = threading.Lock()
ready = threading.Event()
ids = itertools.count(1)


def _stderr_reader():
    for line in proc.stderr:
        sys.stderr.write(line)
        sys.stderr.flush()
        if "Started, ready to begin handling requests" in line:
            ready.set()
            print("KATAGO_HTTP_READY", flush=True)


def _stdout_reader():
    for line in proc.stdout:
        try:
            r = json.loads(line)
        except ValueError:
            continue
        with pending_lock:
            p = pending.get(r.get("id"))
        if not p:
            continue
        if "error" in r and "turnNumber" not in r:
            p["error"] = r["error"]
            p["event"].set()
            continue
        p["results"][r.get("turnNumber", 0)] = r
        if len(p["results"]) >= p["expect"]:
            p["event"].set()


threading.Thread(target=_stderr_reader, daemon=True).start()
threading.Thread(target=_stdout_reader, daemon=True).start()


def analyze(q):
    moves = q.get("moves")
    if not isinstance(moves, list):
        raise ValueError("moves (list) required")
    turns = q.get("analyzeTurns") or [len(moves)]
    if not isinstance(turns, list) or len(turns) > TURNS_CAP:
        raise ValueError("bad analyzeTurns")
    q = dict(q)
    q["analyzeTurns"] = turns
    q["maxVisits"] = max(1, min(int(q.get("maxVisits") or 30), VISITS_CAP))
    qid = f"q{next(ids)}"
    q["id"] = qid
    p = {"expect": len(turns), "results": {}, "event": threading.Event()}
    with pending_lock:
        pending[qid] = p
    try:
        with write_lock:
            proc.stdin.write(json.dumps(q) + "\n")
            proc.stdin.flush()
        timeout = min(170.0, 20.0 + q["maxVisits"] * 0.1 * len(turns))
        if not p["event"].wait(timeout):
            with write_lock:
                proc.stdin.write(json.dumps({"id": f"t{qid}", "action": "terminate", "terminateId": qid}) + "\n")
                proc.stdin.flush()
            raise TimeoutError("analysis timed out")
        if "error" in p:
            raise ValueError(p["error"])
        return [p["results"][t] for t in sorted(p["results"])]
    finally:
        with pending_lock:
            pending.pop(qid, None)


class H(BaseHTTPRequestHandler):
    def _send(self, code, obj):
        b = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def log_message(self, *a):
        pass

    def do_GET(self):
        if self.path == "/health":
            self._send(200 if ready.is_set() and proc.poll() is None else 503,
                       {"ready": ready.is_set(), "alive": proc.poll() is None})
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):
        if self.path != "/analyze":
            return self._send(404, {"error": "not found"})
        try:
            n = int(self.headers.get("Content-Length") or 0)
            if n > 2_000_000:
                return self._send(413, {"error": "too large"})
            q = json.loads(self.rfile.read(n))
            t0 = time.time()
            res = analyze(q)
            self._send(200, {"results": res, "elapsed": round(time.time() - t0, 3)})
        except TimeoutError as e:
            self._send(504, {"error": str(e)})
        except (ValueError, KeyError, TypeError) as e:
            self._send(400, {"error": str(e)})


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()
