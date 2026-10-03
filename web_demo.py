"""Local web demo for the Rejection Memory Guard.

Paste a candidate idea and see BLOCK / WARN / RECONSIDER / ALLOW from the real guard.

Run:  RMG_OFFLINE=1 .venv/bin/python web_demo.py [--port 8765]
Uses its own throwaway demo ledger (never the real ~/.rmg ledger).
"""
import argparse
import json
import os
import shutil
import socket
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, List, Optional

os.environ.setdefault("RMG_OFFLINE", "1")  # deterministic, no LLM calls

from rmg import api  # noqa: E402
from rmg.inject import compaction_block  # noqa: E402
from rmg.ledger import Ledger  # noqa: E402

DEFAULT_TASK = "improve the Solana trading strategy using top wallets"

SESSION_1 = [
    {"role": "assistant",
     "content": "I suggest we copy the trades of the most profitable wallets on-chain."},
    {"role": "user",
     "content": "We already tried that, it didn't work — the edge decays before we can execute. "
                "Don't suggest that again. Only reconsider if our execution latency drops below 100ms."},
]

EXAMPLES = [
    {"label": "Reworded copy-wallets (BLOCK)",
     "candidate": "How about we mirror the positions of top-performing whale addresses?",
     "conditions": "", "expect": "BLOCK"},
    {"label": "WebSocket with REST fallback (WARN)",
     "candidate": "Use WebSockets with REST polling only as a fallback on disconnect",
     "conditions": "", "expect": "WARN"},
    {"label": "Latency now <100ms (RECONSIDER)",
     "candidate": "Let's copy the top wallets' trades again",
     "conditions": "our execution latency now drops below 100ms", "expect": "RECONSIDER"},
]

SEVERITY = {"BLOCK": 3, "RECONSIDER": 2, "WARN": 1, "ALLOW": 0}


class DemoState:
    """Holds the demo ledger in its own temp dir; thread-safe via a lock."""

    def __init__(self, data_dir: Optional[str] = None):
        self.lock = threading.RLock()
        self.own_dir = data_dir is None
        self.data_dir = data_dir or tempfile.mkdtemp(prefix="rmg-web-demo-")
        os.makedirs(self.data_dir, exist_ok=True)
        self.db_path = os.path.join(self.data_dir, "demo.db")
        self.ledger: Optional[Ledger] = None
        self.reset()

    def reset(self) -> None:
        with self.lock:
            if self.ledger is not None:
                self.ledger.close()
            if os.path.exists(self.db_path):
                os.remove(self.db_path)
            self.ledger = Ledger(self.db_path)
            api.ingest(SESSION_1, ledger=self.ledger)
            api.reject("poll the API every second", "rate limits", ledger=self.ledger)

    def rejections(self) -> List[Dict[str, Any]]:
        with self.lock:
            return [{
                "id": r.id, "idea": r.canonical_idea, "reason": r.rejection_reason,
                "reconsider_if": r.reconsider_if, "status": r.status.value,
                "times_reproposed": r.times_reproposed, "rejected_at": r.rejected_at[:10],
            } for r in self.ledger.active()]

    def injection(self, task: str = DEFAULT_TASK) -> str:
        with self.lock:
            return compaction_block(self.ledger, task or DEFAULT_TASK)

    def check(self, candidate: str, conditions: str = "") -> Dict[str, Any]:
        reqs = [c.strip() for c in (conditions or "").splitlines() if c.strip()]
        context = {"requirements": reqs} if reqs else None
        with self.lock:
            results = api.check(candidate, context=context, ledger=self.ledger)
            for r in results:
                m = r.get("matched_rejection")
                if m:
                    rec = self.ledger.get(m["id"])
                    if rec:
                        m["reconsider_if"] = rec.reconsider_if
        if not results:
            results = [{"candidate": candidate, "decision": "ALLOW", "matched_rejection": None,
                        "similarity": 0.0, "reason": "No proposal found in the text",
                        "conditions_changed": False}]
        primary = max(results, key=lambda r: (SEVERITY.get(r["decision"], 0), r["similarity"]))
        return {"decision": primary["decision"], "primary": primary, "results": results,
                "context": context}

    def add_rejection(self, idea: str, reason: str, reconsider_if: str = "") -> Dict[str, Any]:
        with self.lock:
            rec = api.reject(idea, reason, reconsider_if=reconsider_if, ledger=self.ledger)
            return {"id": rec.id, "idea": rec.canonical_idea}

    def close(self) -> None:
        with self.lock:
            if self.ledger is not None:
                self.ledger.close()
                self.ledger = None
            if self.own_dir:
                shutil.rmtree(self.data_dir, ignore_errors=True)


PAGE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>Rejection Memory Guard — demo</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
:root{--bg:#0f1115;--panel:#171a21;--line:#262b36;--fg:#e6e8ee;--mut:#8b93a7;--acc:#7aa2ff;
--block:#e5484d;--warn:#f5a524;--recon:#3b82f6;--allow:#30a46c}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);
font:14px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}
header{padding:18px 28px;border-bottom:1px solid var(--line)}h1{margin:0;font-size:18px}
header p{margin:4px 0 0;color:var(--mut)}
.wrap{display:grid;grid-template-columns:minmax(0,1fr) 400px;gap:20px;padding:20px 28px}
@media(max-width:1000px){.wrap{grid-template-columns:1fr}}
.card{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:16px;margin-bottom:16px}
h2{font-size:13px;text-transform:uppercase;letter-spacing:.06em;color:var(--mut);margin:0 0 10px}
label{display:block;color:var(--mut);font-size:12px;margin:10px 0 4px}
textarea,input{width:100%;background:#0c0e12;color:var(--fg);border:1px solid var(--line);
border-radius:8px;padding:9px 10px;font:inherit;resize:vertical}
textarea:focus,input:focus{outline:none;border-color:var(--acc)}
button{background:#232838;color:var(--fg);border:1px solid var(--line);border-radius:8px;
padding:8px 12px;font:inherit;cursor:pointer}button:hover{border-color:var(--acc)}
button.primary{background:var(--acc);color:#0b0d12;border-color:var(--acc);font-weight:600}
button.danger:hover{border-color:var(--block);color:var(--block)}
.row{display:flex;gap:8px;flex-wrap:wrap;margin-top:10px;align-items:center}
.badge{display:inline-block;font-size:34px;font-weight:800;letter-spacing:.05em;padding:10px 26px;
border-radius:12px;color:#fff}
.BLOCK{background:var(--block)}.WARN{background:var(--warn);color:#1a1200}
.RECONSIDER{background:var(--recon)}.ALLOW{background:var(--allow)}
.sim{color:var(--mut);margin-left:14px;font-size:15px}.reason{font-size:15px;margin:14px 0}
.kv{display:grid;grid-template-columns:120px 1fr;gap:4px 10px;margin-top:8px}.kv div:nth-child(odd){color:var(--mut)}
pre{background:#0c0e12;border:1px solid var(--line);border-radius:8px;padding:10px;
white-space:pre-wrap;word-break:break-word;font:12px/1.45 ui-monospace,Menlo,monospace;margin:8px 0 0}
details summary{cursor:pointer;color:var(--mut);margin-top:12px}
.rej{border-top:1px solid var(--line);padding:9px 0}.rej:first-child{border-top:none}
.rej b{display:block}.rej small{color:var(--mut);display:block}.empty{color:var(--mut)}
.mini{font-size:12px;color:var(--mut)}.pill{font-size:11px;padding:1px 7px;border-radius:99px;margin-left:6px}
</style></head><body>
<header><h1>Rejection Memory Guard — live demo</h1>
<p>Demo ledger seeded with the session-1 conversation from <code>demo.py</code> (offline, deterministic). Your real ledger is never touched.</p></header>
<div class="wrap"><main>
 <div class="card"><h2>Candidate idea</h2>
  <div class="row" id="examples" style="margin-top:0"></div>
  <label for="cand">Idea the agent wants to propose</label>
  <textarea id="cand" rows="4" placeholder="e.g. How about we mirror the positions of top-performing whale addresses?"></textarea>
  <label for="cond">Conditions / context now true (optional, one per line — enables RECONSIDER)</label>
  <textarea id="cond" rows="2" placeholder="e.g. our execution latency now drops below 100ms"></textarea>
  <div class="row"><button class="primary" id="checkBtn">Check</button><span class="mini">⌘/Ctrl + Enter</span></div>
 </div>
 <div class="card" id="resultCard" style="display:none"><h2>Guard decision</h2><div id="result"></div></div>
</main><aside>
 <div class="card"><h2>Active rejections in demo ledger</h2><div id="rejs"></div>
  <div class="row"><button class="danger" id="resetBtn">Reset demo ledger</button></div></div>
 <div class="card"><h2>Injection block</h2>
  <label for="task">Task (relevance filter)</label><input id="task">
  <pre id="inj"></pre></div>
 <div class="card"><h2>Add rejection</h2>
  <label>Idea</label><input id="aIdea" placeholder="e.g. Use a single global mutex for the order book">
  <label>Reason</label><input id="aReason" placeholder="e.g. contention killed throughput">
  <label>Reconsider if (optional)</label><input id="aRecon" placeholder="e.g. we move to a single-threaded engine">
  <div class="row"><button id="addBtn">Add to demo ledger</button><span class="mini" id="addMsg"></span></div></div>
</aside></div>
<script>
const $=id=>document.getElementById(id);
const esc=s=>String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const EXAMPLES=__EXAMPLES__;const DEFAULT_TASK=__TASK__;
async function j(url,body){const r=await fetch(url,body===undefined?{}:{method:"POST",
 headers:{"Content-Type":"application/json"},body:JSON.stringify(body)});return r.json();}
async function refresh(){const s=await j("/api/state?task="+encodeURIComponent($("task").value));
 $("rejs").innerHTML=s.rejections.length?s.rejections.map(r=>`<div class="rej"><b>${esc(r.idea)}</b>
 <small>Reason: ${esc(r.reason)}</small>${r.reconsider_if?`<small>Reconsider if: ${esc(r.reconsider_if)}</small>`:""}
 <small>${esc(r.id)} · ${esc(r.rejected_at)} · reproposed ${r.times_reproposed}×</small></div>`).join(""):'<div class="empty">No active rejections.</div>';
 $("inj").textContent=s.injection;}
function renderOne(r){const m=r.matched_rejection;return `<div><span class="badge ${r.decision}">${r.decision}</span>
 <span class="sim">similarity ${Number(r.similarity).toFixed(3)}</span></div>
 <div class="reason">${esc(r.reason)}</div>
 <div class="kv"><div>Candidate</div><div>${esc(r.candidate)}</div>
 ${m?`<div>Matched idea</div><div>${esc(m.canonical_idea)}</div><div>Reason</div><div>${esc(m.rejection_reason)}</div>
 <div>Reconsider if</div><div>${esc(m.reconsider_if||"—")}</div><div>Record id</div><div>${esc(m.id)}</div>`:`<div>Matched</div><div>none</div>`}
 <div>Conditions changed</div><div>${r.conditions_changed?"yes":"no"}</div></div>`;}
async function check(){const cand=$("cand").value.trim();if(!cand)return;
 const res=await j("/api/check",{candidate:cand,conditions:$("cond").value});
 if(res.error){$("result").innerHTML=`<div class="reason">${esc(res.error)}</div>`;$("resultCard").style.display="";return;}
 let h=renderOne(res.primary);const others=res.results.filter(x=>x!==res.primary&&JSON.stringify(x)!==JSON.stringify(res.primary));
 if(res.results.length>1)h+=`<details><summary>${res.results.length} proposals detected — all results</summary>${res.results.map(x=>`<div class="card" style="margin-top:10px">${renderOne(x)}</div>`).join("")}</details>`;
 h+=`<details><summary>Raw JSON</summary><pre>${esc(JSON.stringify(res,null,2))}</pre></details>`;
 $("result").innerHTML=h;$("resultCard").style.display="";refresh();}
EXAMPLES.forEach(e=>{const b=document.createElement("button");b.textContent=e.label;
 b.onclick=()=>{$("cand").value=e.candidate;$("cond").value=e.conditions;check();};$("examples").appendChild(b);});
$("checkBtn").onclick=check;
document.addEventListener("keydown",e=>{if((e.metaKey||e.ctrlKey)&&e.key==="Enter")check();});
$("resetBtn").onclick=async()=>{await j("/api/reset",{});$("resultCard").style.display="none";refresh();};
$("addBtn").onclick=async()=>{const r=await j("/api/reject",{idea:$("aIdea").value,reason:$("aReason").value,reconsider_if:$("aRecon").value});
 $("addMsg").textContent=r.error?r.error:"Added "+r.id;if(!r.error){$("aIdea").value=$("aReason").value=$("aRecon").value="";}refresh();};
let t;$("task").value=DEFAULT_TASK;$("task").oninput=()=>{clearTimeout(t);t=setTimeout(refresh,250);};
refresh();
</script></body></html>"""


def render_page() -> str:
    return (PAGE.replace("__EXAMPLES__", json.dumps(EXAMPLES).replace("</", "<\\/"))
                .replace("__TASK__", json.dumps(DEFAULT_TASK)))


def make_handler(state: DemoState):
    from urllib.parse import parse_qs, urlparse

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            print("%s - %s" % (self.address_string(), fmt % args), flush=True)

        def _send(self, body: bytes, ctype: str, status: int = 200):
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _json(self, data: Any, status: int = 200):
            self._send(json.dumps(data, indent=2).encode("utf-8"), "application/json", status)

        def _body(self) -> Dict[str, Any]:
            n = int(self.headers.get("Content-Length") or 0)
            if not n:
                return {}
            data = json.loads(self.rfile.read(n).decode("utf-8") or "{}")
            return data if isinstance(data, dict) else {}

        def do_GET(self):
            u = urlparse(self.path)
            if u.path == "/":
                self._send(render_page().encode("utf-8"), "text/html; charset=utf-8")
            elif u.path == "/api/state":
                task = (parse_qs(u.query).get("task") or [DEFAULT_TASK])[0]
                self._json({"rejections": state.rejections(), "injection": state.injection(task),
                            "examples": EXAMPLES})
            elif u.path == "/healthz":
                self._json({"ok": True})
            else:
                self._json({"error": "not found"}, 404)

        def do_POST(self):
            try:
                body = self._body()
            except (ValueError, UnicodeDecodeError):
                return self._json({"error": "invalid JSON body"}, 400)
            p = urlparse(self.path).path
            try:
                if p == "/api/check":
                    cand = str(body.get("candidate", "")).strip()
                    if not cand:
                        return self._json({"error": "candidate is required"}, 400)
                    self._json(state.check(cand, str(body.get("conditions", ""))))
                elif p == "/api/reject":
                    idea = str(body.get("idea", "")).strip()
                    reason = str(body.get("reason", "")).strip()
                    if not idea or not reason:
                        return self._json({"error": "idea and reason are required"}, 400)
                    self._json(state.add_rejection(idea, reason, str(body.get("reconsider_if", "")).strip()))
                elif p == "/api/reset":
                    state.reset()
                    self._json({"ok": True, "rejections": state.rejections()})
                else:
                    self._json({"error": "not found"}, 404)
            except Exception as e:  # keep the demo server alive
                self._json({"error": f"{type(e).__name__}: {e}"}, 500)

    return Handler


def _free_port(host: str, preferred: int) -> int:
    for port in [preferred] + list(range(preferred + 1, preferred + 50)):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind((host, port))
                return port
            except OSError:
                continue
    raise RuntimeError("no free port found")


def main(argv=None):
    ap = argparse.ArgumentParser(description="RMG local web demo")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=int(os.environ.get("RMG_DEMO_PORT", "8765")))
    ap.add_argument("--data-dir", default=os.environ.get("RMG_DEMO_DIR"),
                    help="demo ledger dir (default: fresh temp dir, removed on exit)")
    args = ap.parse_args(argv)
    state = DemoState(args.data_dir)
    port = _free_port(args.host, args.port)
    server = ThreadingHTTPServer((args.host, port), make_handler(state))
    print(f"RMG web demo on http://{args.host}:{port}  (ledger: {state.db_path}, "
          f"RMG_OFFLINE={os.environ.get('RMG_OFFLINE')}, pid {os.getpid()})", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        state.close()


if __name__ == "__main__":
    main()
