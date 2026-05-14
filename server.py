"""
CVforge local server.
- Serves static files from this directory on port 3000.
- Proxies POST /api/compile → latexonline.cc GET ?text=, bypassing browser CORS.

Run:  python server.py
Open: http://localhost:3000
"""
import http.server
import urllib.request
import urllib.parse
import json
import os
import re

PORT = int(os.environ.get("PORT", 3000))
LATEX_API = "https://latexonline.cc/compile"


def inline_sty(tex: str, sty: str) -> str:
    """Replace \\usepackage{cv} with the sty content, stripped of package-only directives."""
    # Remove \ProvidesPackage line (only valid inside .sty files, not inline)
    clean = re.sub(r"\\ProvidesPackage\{[^}]*\}[^\n]*\n?", "", sty)
    # Replace \RequirePackage with \usepackage so it works in document preamble
    clean = clean.replace(r"\RequirePackage", r"\usepackage")
    # Normalise line endings
    clean = clean.replace("\r\n", "\n").replace("\r", "\n")
    return tex.replace(r"\usepackage{cv}", f"% cv.sty inlined\n{clean.strip()}")


class Handler(http.server.SimpleHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def do_POST(self):
        if self.path == "/api/compile":
            self._handle_compile()
        else:
            self.send_error(404)

    def _handle_compile(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)

        try:
            data = json.loads(body)
            tex = data.get("tex", "")
        except Exception:
            self.send_error(400, "Bad JSON")
            return

        encoded = urllib.parse.urlencode({"text": tex})
        url = f"{LATEX_API}?{encoded}"

        print(f"  -> Sending to latexonline.cc ({len(tex)} chars)")

        try:
            req = urllib.request.Request(url, headers={"User-Agent": "CVforge/1.0"})
            with urllib.request.urlopen(req, timeout=60) as resp:
                pdf = resp.read()

            print(f"  OK Got PDF ({len(pdf)} bytes)")
            self.send_response(200)
            self._cors()
            self.send_header("Content-Type", "application/pdf")
            self.send_header("Content-Length", str(len(pdf)))
            self.end_headers()
            self.wfile.write(pdf)

        except urllib.error.HTTPError as e:
            msg = e.read().decode("utf-8", errors="replace")
            print(f"  ERR latexonline error {e.code}:\n{msg[:500]}")
            self.send_response(e.code)
            self._cors()
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            body_out = msg.encode()
            self.send_header("Content-Length", str(len(body_out)))
            self.end_headers()
            self.wfile.write(body_out)

        except Exception as e:
            print(f"  ERR Proxy error: {e}")
            self.send_response(502)
            self._cors()
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            msg = str(e).encode()
            self.send_header("Content-Length", str(len(msg)))
            self.end_headers()
            self.wfile.write(msg)

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def log_message(self, fmt, *args):
        print(f"  {self.address_string()} - {fmt % args}")


os.chdir(os.path.dirname(os.path.abspath(__file__)))
print(f"CVforge server running at http://localhost:{PORT}")
print("Press Ctrl+C to stop.\n")
with http.server.HTTPServer(("0.0.0.0", PORT), Handler) as httpd:
    httpd.serve_forever()
