<div align="center">
  <img src="assets/logo/CV forge logo.png" alt="CV Forge Logo" width="120" />
  <h1>CV Forge</h1>
  <p><strong>A browser-based LaTeX CV builder with server-side PDF compilation.</strong></p>
  <p>
    <a href="https://cv-forge-lvog.onrender.com" target="_blank">
      <img src="https://img.shields.io/badge/Live%20Demo-%F0%9F%9A%80-46E3B7?style=for-the-badge" />
    </a>
  </p>
  <p>
    <img src="https://img.shields.io/badge/Python-3.8+-blue?logo=python&logoColor=white" />
    <img src="https://img.shields.io/badge/Vue.js-3-42b883?logo=vue.js&logoColor=white" />
    <img src="https://img.shields.io/badge/LaTeX-Online-008080?logo=latex&logoColor=white" />
    <img src="https://img.shields.io/badge/Deployed%20on-Render-46E3B7?logo=render&logoColor=white" />
    <img src="https://img.shields.io/badge/License-MIT-yellow" />
  </p>
</div>

---

## 📋 Overview

**CV Forge** is a lightweight, self-hosted CV builder that lets you craft a professional LaTeX-typeset CV directly in your browser — no LaTeX installation required. You fill out a structured form, the app renders a LaTeX document in real time, and a local Python proxy server compiles it to PDF via [latexonline.cc](https://latexonline.cc) and streams it back for instant preview and download.

### ✨ Key Features

- **Live Form → LaTeX rendering** — every keystroke updates the LaTeX source in real time using Vue 3
- **One-click PDF compilation** — proxied through a local Python server to bypass browser CORS restrictions
- **In-browser PDF preview** — compiled PDF is rendered inline via an `<iframe>`
- **Download PDF** — save the finished CV with a single click
- **AI Text Suggestions** — ✨ AI Suggest buttons powered by Gemini generate professional summaries, experience highlights, and project descriptions
- **6 CV sections** — Personal, Experience, Education, Projects, Certifications, References
- **Conditional section rendering** — sections with no content are automatically omitted from the compiled PDF
- **No third-party dependencies** — the Python server uses the standard library only (`http.server`, `urllib`)
- **Fully customisable LaTeX template** — edit the embedded template in `index.html` to change the CV layout
- **Clean slate on load** — all form fields start blank; placeholder text guides the user

---

## 🖼️ Tech Stack

| Layer | Technology |
|---|---|
| Frontend framework | [Vue 3](https://vuejs.org/) (CDN, no build step) |
| Styling | Vanilla CSS with CSS custom properties |
| LaTeX compilation | [latexonline.cc](https://latexonline.cc) REST API |
| Proxy server | Python 3 `http.server` (stdlib only) |
| Fonts | Inter (bundled in `assets/fonts/`) |

---

## 📁 Project Structure

```
CV-Forge/
├── index.html          # Main app — Vue 3 form, live LaTeX preview, PDF viewer
├── app.js              # Vue 3 application logic — data model, template renderer, compile & download
├── styles.css          # All UI styles (CSS custom properties, responsive grid)
├── server.py           # Local proxy server — serves static files + /api/compile endpoint
├── render.yaml         # Render.com deployment configuration
├── template.tex        # Standalone LaTeX template (used as fallback if inline template is removed)
├── requirements.txt    # No pip dependencies (stdlib only)
├── schema.json         # CV data schema reference
├── assets/logo/CV forge logo.png   # Application logo
├── assets/
│   ├── fonts/          # Inter font family (18pt, 24pt, 28pt — all weights)
│   └── styles/
│       └── cv.sty      # Custom LaTeX style package (inlined by server at compile time)
└── swiftlatex/         # Legacy SwiftLaTeX WASM files (kept for reference, not used)
```

---

## 🚀 Getting Started

### Prerequisites

- **Python 3.8+** — no pip packages needed
- A modern web browser (Chrome, Firefox, Edge)
- An internet connection (for the latexonline.cc compiler API)

### 1. Clone the Repository

```bash
git clone https://github.com/notavishek/CV-Forge.git
cd CV-Forge
```

### 2. Start the Local Server

```bash
python server.py
```

You should see:

```
CVforge server running at http://localhost:3000
Press Ctrl+C to stop.
```

### 3. Open in Browser

Navigate to **[http://localhost:3000](http://localhost:3000)**

> ⚠️ **Do not open `index.html` directly as a `file://` URL.** The compile API will not work without the proxy server. Always use `http://localhost:3000`.

---

## 🌐 Live Demo

CV Forge is already deployed and available at:

🔗 **[https://cv-forge-lvog.onrender.com](https://www.cvforge.pro.bd/)**

> ⚠️ Hosted on Render's free tier — the app may take ~30–50 seconds to load after a period of inactivity (cold start).

---

## 📝 How It Works

### 1. Form → LaTeX

The Vue 3 app watches all form fields reactively. On every change, `renderTemplate()` in `app.js` performs a `{{placeholder}}` substitution on the LaTeX template, producing a complete `.tex` source string visible in the **LaTeX Preview** panel.

### 2. Compile

When you click **Compile PDF**, the app sends a `POST /api/compile` request with the rendered `.tex` source as JSON to the local Python server.

### 3. Proxy → latexonline.cc

`server.py` receives the request, URL-encodes the LaTeX source, and forwards it to:

```
https://latexonline.cc/compile?text=<encoded_tex>
```

The `cv.sty` package is inlined directly into the `.tex` source before it is sent, so the remote compiler can resolve all custom commands without needing access to local files.

### 4. PDF Response

If compilation succeeds, latexonline.cc returns a PDF binary. The proxy streams it back to the browser as `application/pdf`. The Vue app creates an object URL and loads it into the iframe for preview. The **Download PDF** button triggers a local file save.

---

## ✏️ Customising the CV Template

The LaTeX template lives in two places:

| Location | When used |
|---|---|
| `<script id="latex-template">` inside `index.html` | **Primary** — loaded first on startup |
| `template.tex` | Fallback if the inline script block is removed |

### Available Template Variables

| Variable | Description |
|---|---|
| `{{personal.name}}` | Full name |
| `{{personal.title}}` | Professional title / headline |
| `{{personal.email}}` | Email address |
| `{{personal.phone}}` | Phone number |
| `{{personal.location}}` | City, Country |
| `{{personal.website}}` | Portfolio / personal website URL |
| `{{personal.linkedin}}` | LinkedIn profile URL |
| `{{personal.github}}` | GitHub profile URL |
| `{{contact_line}}` | Auto-built contact line (email · phone · location · links) |
| `{{summary_section}}` | Professional summary — **omitted if empty** |
| `{{experience_section}}` | Full experience section — **omitted if no entries** |
| `{{education_section}}` | Full education section — **omitted if no entries** |
| `{{projects_section}}` | Full projects section — **omitted if no entries** |
| `{{skills_section}}` | Core skills — **omitted if no skills added** |
| `{{certificates_section}}` | Certifications — **omitted if no entries** |
| `{{references_section}}` | References — **omitted if no entries** |

### Custom LaTeX Commands (from `cv.sty`)

| Command | Usage |
|---|---|
| `\cvheader{name}{title}{contact}` | Renders the name/title/contact block at the top |
| `\cvsection{title}` | Section heading with accent rule |
| `\cvsubheading{role}{org}{location}{dates}` | Experience or education entry heading |
| `\cvproject{name}{description}{meta}` | Project entry |
| `\cvskillline{label}{items}` | Skill group row |

---

## ⚙️ Configuration

### Changing the Port

Set the `PORT` environment variable before running the server:

```bash
# Windows (PowerShell)
$env:PORT = 8080; python server.py

# Linux / macOS
PORT=8080 python server.py
```

### Using a Different LaTeX Compiler

Edit the `LATEX_API` constant at the top of `server.py`:

```python
LATEX_API = "https://latexonline.cc/compile"
```

Replace it with any compatible REST API that accepts `?text=<latex_source>` and returns a PDF.

---

## 🔒 LaTeX Special Character Escaping

All user input is automatically escaped before being inserted into the LaTeX document. The following characters are safely handled:

| Character | Escaped as |
|---|---|
| `\` | `\textbackslash{}` |
| `{` `}` | `\{` `\}` |
| `#` | `\#` |
| `$` | `\$` |
| `%` | `\%` |
| `&` | `\&` |
| `_` | `\_` |
| `~` | `\textasciitilde{}` |
| `^` | `\textasciicircum{}` |

---

## 🛠️ Development Notes

- **No build step** — the frontend is plain HTML + JS + CSS loaded directly by the browser
- **Vue 3** is loaded from the unpkg CDN; no `npm install` needed
- **Hard refresh** (`Ctrl+Shift+R`) may be needed after editing `app.js` if the browser has cached an older version
- The `swiftlatex/` directory contains the legacy WASM-based in-browser compiler; it is not used in the current architecture but kept for reference

---

## 🐛 Troubleshooting

| Problem | Solution |
|---|---|
| "Compilation timed out. Is server.py running?" | Make sure `python server.py` is running and you're on `http://localhost:3000` |
| PDF compiles but looks wrong | Check the **Compiler Log** panel for LaTeX errors |
| Form shows old data after a code change | Hard refresh with `Ctrl+Shift+R` |
| Port 3000 already in use | Set `$env:PORT=3001; python server.py` |
| `latexonline.cc` is unreachable | Check your internet connection; the API is a free external service |

---

## 📄 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgements

- [latexonline.cc](https://latexonline.cc) — free LaTeX compilation API
- [LaTeX Project](https://www.latex-project.org/) — document typesetting system

---

<div align="center">
  <sub>Built by <a href="https://github.com/notavishek">notavishek</a></sub>
</div>
