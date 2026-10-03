import html
import json
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Optional, List, Dict, Any
from urllib.parse import urlparse, parse_qs

from rmg.models import Record
from rmg.ledger import Ledger
from rmg.similarity import similarity


def render_index(ledger: Ledger) -> str:
    records = ledger.all()
    rows = []
    for r in records:
        idea = html.escape(r.canonical_idea)
        date = r.rejected_at[:10]
        reason = html.escape(r.rejection_reason)
        status = html.escape(r.status.value)
        times = r.times_reproposed
        rows.append(f"""
            <tr>
                <td><a href="/record/{r.id}">{idea}</a></td>
                <td>{date}</td>
                <td>{reason}</td>
                <td>{status}</td>
                <td>{times}</td>
            </tr>
        """)
    
    table_body = "\n".join(rows)
    return f"""
    <html>
    <head><title>RMG Ledger</title></head>
    <body>
        <h1>Rejection Ledger</h1>
        <table border="1">
            <thead>
                <tr>
                    <th>Idea</th>
                    <th>Date</th>
                    <th>Reason</th>
                    <th>Status</th>
                    <th>Reproposed</th>
                </tr>
            </thead>
            <tbody>
                {table_body}
            </tbody>
        </table>
    </body>
    </html>
    """


def render_record(ledger: Ledger, id: str) -> Optional[str]:
    record = ledger.get(id)
    if not record:
        return None

    # Find related rejections
    related = []
    all_records = ledger.all()
    scores = []
    for other in all_records:
        if other.id == record.id:
            continue
        score = similarity(record.match_text(), other.match_text())
        scores.append((score, other))
    
    scores.sort(key=lambda x: x[0], reverse=True)
    related = [r for s, r in scores[:3]]

    related_html = ""
    if related:
        items = []
        for r in related:
            items.append(f'<li><a href="/record/{r.id}">{html.escape(r.canonical_idea)}</a></li>')
        related_html = f"<ul>{''.join(items)}</ul>"
    else:
        related_html = "<p>No related rejections found.</p>"

    # Fingerprint
    fp = record.fingerprint
    fp_html = f"""
        <p><strong>Objective:</strong> {html.escape(fp.objective)}</p>
        <p><strong>Mechanism:</strong> {html.escape(fp.mechanism)}</p>
        <p><strong>Why Failed:</strong> {html.escape(fp.why_failed)}</p>
        <p><strong>Constraint Violated:</strong> {html.escape(fp.constraint_violated)}</p>
        <p><strong>Conditions to Reconsider:</strong> {html.escape(fp.conditions_to_reconsider)}</p>
        <p><strong>Replacement:</strong> {html.escape(fp.replacement)}</p>
    """

    # Status History
    history_items = []
    for sc in record.status_history:
        history_items.append(f"""
            <li>
                <strong>{html.escape(sc.status.value)}</strong> 
                at {html.escape(sc.at)} 
                ({html.escape(sc.reason)})
            </li>
        """)
    history_html = f"<ul>{''.join(history_items)}</ul>"

    return f"""
    <html>
    <head><title>{html.escape(record.canonical_idea)}</title></head>
    <body>
        <h1>{html.escape(record.canonical_idea)}</h1>
        
        <h2>Details</h2>
        <p><strong>Original Discussion:</strong> {html.escape(record.original_discussion)}</p>
        <p><strong>Reason:</strong> {html.escape(record.rejection_reason)}</p>
        <p><strong>Evidence:</strong> {html.escape(record.evidence)}</p>
        
        <h2>Fingerprint</h2>
        {fp_html}
        
        <h2>Related Rejections</h2>
        {related_html}
        
        <h2>Status</h2>
        <p>Current: {html.escape(record.status.value)}</p>
        <h3>History</h3>
        {history_html}
        
        <h2>Reconsideration</h2>
        <p><strong>Reconsider If:</strong> {html.escape(record.reconsider_if)}</p>
        <p><strong>Times Reproposed:</strong> {record.times_reproposed}</p>
        <p><strong>Last Reproposal:</strong> {html.escape(record.last_reproposal)}</p>
        
        <p><a href="/">Back to Index</a></p>
    </body>
    </html>
    """


def make_handler(ledger: Ledger):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            pass

        def _send_html(self, content: str, status: int = 200):
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(content.encode("utf-8"))

        def _send_json(self, data: Any, status: int = 200):
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(data).encode("utf-8"))

        def do_GET(self):
            parsed = urlparse(self.path)
            path = parsed.path

            if path == "/":
                self._send_html(render_index(ledger))
            elif path.startswith("/record/"):
                record_id = path[len("/record/"):]
                content = render_record(ledger, record_id)
                if content is None:
                    self._send_html("<h1>404 Not Found</h1>", 404)
                else:
                    self._send_html(content)
            elif path == "/api/records":
                records = ledger.all()
                data = [r.to_dict() for r in records]
                self._send_json(data)
            elif path.startswith("/api/records/"):
                record_id = path[len("/api/records/"):]
                record = ledger.get(record_id)
                if record is None:
                    self._send_json({"error": "Not found"}, 404)
                else:
                    self._send_json(record.to_dict())
            else:
                self._send_html("<h1>404 Not Found</h1>", 404)

    return Handler


def serve(ledger: Ledger, host: str = "127.0.0.1", port: int = 8765):
    server = ThreadingHTTPServer((host, port), make_handler(ledger))
    print(f"Serving on http://{host}:{port}")
    server.serve_forever()
