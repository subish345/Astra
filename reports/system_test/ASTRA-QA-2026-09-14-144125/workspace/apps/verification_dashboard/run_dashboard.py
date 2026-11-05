"""Standalone Runner for ASTRA-EA Formal V&V Dashboard (Phase 16).

Serves the V&V Mission Assurance Dashboard locally at http://localhost:8090.
"""

import http.server
import socketserver
import webbrowser
from pathlib import Path
import sys

PORT = 8090
DIRECTORY = Path(__file__).parent.resolve()


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DIRECTORY), **kwargs)


def run_dashboard(open_browser: bool = False) -> None:
    print("=" * 60)
    print(" ASTRA-EA FORMAL V&V MISSION ASSURANCE DASHBOARD")
    print("=" * 60)
    print(f" Serving dashboard from: {DIRECTORY}")
    print(f" Access URL: http://localhost:{PORT}/index.html")
    print("=" * 60)

    if open_browser:
        try:
            webbrowser.open(f"http://localhost:{PORT}/index.html")
        except Exception:
            pass

    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        try:
            print(f"[READY] Listening on port {PORT}... (Press Ctrl+C to stop)")
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n[STOP] Dashboard server stopped.")


if __name__ == "__main__":
    open_b = "--open" in sys.argv
    run_dashboard(open_browser=open_b)
