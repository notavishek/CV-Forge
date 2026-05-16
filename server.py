"""
CVforge local server.
- Serves static files from this directory on port 3000.
- Proxies POST /api/compile  → latexonline.cc, bypassing browser CORS.
- Proxies POST /api/suggest  → Groq (Llama 3.3) for CV text suggestions.

Run:  python server.py
Open: http://localhost:3000

Requires GROQ_API_KEY env var for AI suggestions.
"""
import http.server
import urllib.request
import urllib.parse
import json
import os
import re

PORT = int(os.environ.get("PORT", 3000))
LATEX_API = "https://latexonline.cc/compile"
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"


def build_prompt(field: str, context: dict) -> str:
    """Build a Groq/Llama prompt for the given CV field."""
    if field == "summary":
        return (
            "You are a professional CV writer. Write a compelling 2-3 sentence "
            "professional summary for a CV. "
            f"Name: {context.get('name', 'the candidate')}. "
            f"Title: {context.get('title', 'professional')}. "
            "Make it concise, impactful, and written in first-person-free style. "
            "Return ONLY the summary text — no preamble, no quotes."
        )
    if field == "highlight":
        return (
            "You are a professional CV writer. Suggest ONE strong, action-verb-led, "
            "quantified bullet point for a CV experience section. "
            f"Role: {context.get('role', '')}. "
            f"Company: {context.get('company', '')}. "
            "Return ONLY the bullet text (no dash or bullet symbol), no preamble."
        )
    if field == "description":
        tech = ", ".join(context.get("tech", []))
        return (
            "You are a professional CV writer. Write a single-sentence project "
            "description for a CV. "
            f"Project name: {context.get('name', '')}. "
            f"Technologies: {tech}. "
            "Return ONLY the description text, no preamble."
        )
    return "Please provide a helpful professional suggestion."


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
        elif self.path == "/api/suggest":
            self._handle_suggest()
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

    def _handle_suggest(self):
        if not GROQ_API_KEY:
            self._json_error(503, "GROQ_API_KEY is not configured on the server.")
            return

        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        try:
            data = json.loads(body)
            field = data.get("field", "")
            context = data.get("context", {})
        except Exception:
            self.send_error(400, "Bad JSON")
            return

        prompt = build_prompt(field, context)
        payload = json.dumps({
            "model": GROQ_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 300,
            "temperature": 0.7
        }).encode()

        print(f"  -> Groq suggest: field={field}")
        try:
            req = urllib.request.Request(
                GROQ_URL, data=payload,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "User-Agent": "CVforge/1.0"
                }
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read())
            suggestion = result["choices"][0]["message"]["content"].strip()
            print(f"  OK Groq responded ({len(suggestion)} chars)")
            self._json_response({"suggestion": suggestion})
        except urllib.error.HTTPError as e:
            msg = e.read().decode("utf-8", errors="replace")
            print(f"  ERR Groq error {e.code}: {msg[:500]}")
            self._json_error(e.code, f"AI API error: {msg[:500]}")
        except Exception as e:
            print(f"  ERR Suggest proxy error: {e}")
            self._json_error(502, f"Suggestion failed: {e}")

    def _json_response(self, obj):
        body = json.dumps(obj).encode()
        self.send_response(200)
        self._cors()
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _json_error(self, code, message):
        body = json.dumps({"error": message}).encode()
        self.send_response(code)
        self._cors()
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

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
