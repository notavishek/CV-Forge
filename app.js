const DEFAULT_CV = {
  personal: {
    name: "",
    title: "",
    email: "",
    phone: "",
    location: "",
    website: "",
    linkedin: "",
    github: "",
    summary: ""
  },
  education: [],
  experience: [],
  skills: {
    languages: [],
    frameworks: [],
    tools: []
  },
  projects: []
};

const COMPILE_TIMEOUT_MS = 60000;
const COMPILE_PROXY = "/api/compile";

const LATEX_SPECIALS = /[\\{}#$%&_~^]/g;

function escapeLatex(value) {
  if (value == null) return "";
  return String(value).replace(LATEX_SPECIALS, (ch) => {
    switch (ch) {
      case "\\":
        return "\\textbackslash{}";
      case "{":
        return "\\{";
      case "}":
        return "\\}";
      case "#":
        return "\\#";
      case "$":
        return "\\$";
      case "%":
        return "\\%";
      case "&":
        return "\\&";
      case "_":
        return "\\_";
      case "~":
        return "\\textasciitilde{}";
      case "^":
        return "\\textasciicircum{}";
      default:
        return ch;
    }
  });
}

function escapeLatexMultiline(value) {
  return escapeLatex(value).replace(/\r?\n/g, "\\\\");
}

function bulletList(items) {
  if (!items || items.length === 0) return "";
  const rows = items.map((i) => `\\item ${escapeLatex(i)}`).join("\n");
  return `\\begin{itemize}\n${rows}\n\\end{itemize}`;
}

function buildContactLine(personal) {
  const left = [personal.email, personal.phone, personal.location]
    .filter(Boolean)
    .map(escapeLatex);
  const right = [
    personal.website
      ? `\\href{${escapeLatex(personal.website)}}{${escapeLatex(personal.website)}}`
      : "",
    personal.linkedin
      ? `\\href{${escapeLatex(personal.linkedin)}}{${escapeLatex(personal.linkedin)}}`
      : "",
    personal.github
      ? `\\href{${escapeLatex(personal.github)}}{${escapeLatex(personal.github)}}`
      : ""
  ].filter(Boolean);

  const line1 = left.join(" \\quad ");
  const line2 = right.join(" \\quad ");
  return [line1, line2].filter(Boolean).join(" \\\\ ");
}

function buildExperienceBlock(experience) {
  return (experience || [])
    .map((e) => {
      const heading = `\\cvsubheading{${escapeLatex(e.role)}}{${escapeLatex(
        e.company
      )}}{${escapeLatex(e.location)}}{${escapeLatex(e.start)}--${escapeLatex(
        e.end
      )}}`;
      const bullets = bulletList(e.highlights);
      return `${heading}\n${bullets}`.trim();
    })
    .filter(Boolean)
    .join("\n\n");
}

function buildEducationBlock(education) {
  return (education || [])
    .map((e) => {
      const heading = `\\cvsubheading{${escapeLatex(e.degree)}}{${escapeLatex(
        e.school
      )}}{${escapeLatex(e.location)}}{${escapeLatex(e.start)}--${escapeLatex(
        e.end
      )}}`;
      const details = bulletList(e.details);
      return `${heading}\n${details}`.trim();
    })
    .filter(Boolean)
    .join("\n\n");
}

function buildProjectsBlock(projects) {
  return (projects || [])
    .map((p) => {
      const tech = (p.tech || []).map(escapeLatex).join(", ");
      const link = p.link
        ? `\\href{${escapeLatex(p.link)}}{${escapeLatex(p.link)}}`
        : "";
      const meta = [tech, link].filter(Boolean).join(" \\quad ");
      return `\\cvproject{${escapeLatex(p.name)}}{${escapeLatex(
        p.description
      )}}{${meta}}`;
    })
    .filter(Boolean)
    .join("\n\n");
}

function renderTemplate(template, cv) {
  const view = {
    personal: {
      name: escapeLatex(cv.personal.name),
      title: escapeLatex(cv.personal.title),
      email: escapeLatex(cv.personal.email),
      phone: escapeLatex(cv.personal.phone),
      location: escapeLatex(cv.personal.location),
      website: escapeLatex(cv.personal.website),
      linkedin: escapeLatex(cv.personal.linkedin),
      github: escapeLatex(cv.personal.github),
      summary: escapeLatexMultiline(cv.personal.summary)
    },
    skills: {
      languages: (cv.skills.languages || []).map(escapeLatex).join(", "),
      frameworks: (cv.skills.frameworks || []).map(escapeLatex).join(", "),
      tools: (cv.skills.tools || []).map(escapeLatex).join(", ")
    },
    contact_line: buildContactLine(cv.personal),
    experience_block: buildExperienceBlock(cv.experience),
    education_block: buildEducationBlock(cv.education),
    projects_block: buildProjectsBlock(cv.projects)
  };

  return template.replace(/\{\{([a-zA-Z0-9_.]+)\}\}/g, (_, key) => {
    const parts = key.trim().split(".");
    let current = view;
    for (const part of parts) {
      current = current?.[part];
    }
    return current ?? "";
  });
}

async function loadText(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Failed to load ${url}`);
  return res.text();
}

function getInlineTemplate() {
  const node = document.getElementById("latex-template");
  if (!node) return "";
  return node.textContent.trim();
}

function withTimeout(promise, ms, message) {
  let timeoutId;
  const timeout = new Promise((_, reject) => {
    timeoutId = setTimeout(() => reject(new Error(message)), ms);
  });
  return Promise.race([promise, timeout]).finally(() => clearTimeout(timeoutId));
}

async function loadStyleFile(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Failed to load ${url}`);
  return res.text();
}

async function compileViaLatexOnline(texSource) {
  const res = await withTimeout(
    fetch(COMPILE_PROXY, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ tex: texSource })
    }),
    COMPILE_TIMEOUT_MS,
    "Compilation timed out. Is server.py running?"
  );

  const contentType = res.headers.get("content-type") || "";

  if (!res.ok) {
    const errText = await res.text();
    return { pdfBytes: null, log: errText, status: res.status };
  }

  if (contentType.includes("application/pdf")) {
    const buf = await res.arrayBuffer();
    return { pdfBytes: new Uint8Array(buf), log: "Compilation succeeded.", status: 0 };
  }

  const text = await res.text();
  return { pdfBytes: null, log: text, status: -1 };
}

const { createApp } = Vue;

createApp({
  data() {
    return {
      templateTex: "",
      cv: structuredClone(DEFAULT_CV),
      latex: "",
      logs: "",
      isCompiling: false,
      pdfBytes: null,
      pdfUrl: "",
      skillDrafts: {
        languages: "",
        frameworks: "",
        tools: ""
      }
    };
  },
  async mounted() {
    this.templateTex = getInlineTemplate();
    if (!this.templateTex) {
      try {
        this.templateTex = await loadText("template.tex");
      } catch (err) {
        this.logs = `ERROR: ${err.message || err}`;
      }
    }

    if (this.templateTex) {
      this.latex = renderTemplate(this.templateTex, this.cv);
    }
  },
  watch: {
    cv: {
      deep: true,
      handler() {
        if (this.templateTex) {
          this.latex = renderTemplate(this.templateTex, this.cv);
        }
      }
    }
  },
  methods: {
    appendLog(line) {
      this.logs = `${this.logs}${line}\n`.slice(-8000);
    },
    addExperience() {
      this.cv.experience.push({
        company: "",
        role: "",
        location: "",
        start: "",
        end: "",
        highlights: [],
        newHighlight: ""
      });
    },
    removeExperience(index) {
      this.cv.experience.splice(index, 1);
    },
    addHighlight(index) {
      const exp = this.cv.experience[index];
      if (!exp.newHighlight) return;
      exp.highlights.push(exp.newHighlight);
      exp.newHighlight = "";
    },
    removeHighlight(expIndex, highlightIndex) {
      this.cv.experience[expIndex].highlights.splice(highlightIndex, 1);
    },
    addEducation() {
      this.cv.education.push({
        school: "",
        degree: "",
        location: "",
        start: "",
        end: "",
        details: [],
        newDetail: ""
      });
    },
    removeEducation(index) {
      this.cv.education.splice(index, 1);
    },
    addEducationDetail(index) {
      const edu = this.cv.education[index];
      if (!edu.newDetail) return;
      edu.details.push(edu.newDetail);
      edu.newDetail = "";
    },
    removeEducationDetail(eduIndex, detailIndex) {
      this.cv.education[eduIndex].details.splice(detailIndex, 1);
    },
    addProject() {
      this.cv.projects.push({
        name: "",
        description: "",
        tech: [],
        link: "",
        newTech: ""
      });
    },
    removeProject(index) {
      this.cv.projects.splice(index, 1);
    },
    addProjectTech(index) {
      const proj = this.cv.projects[index];
      if (!proj.newTech) return;
      proj.tech.push(proj.newTech);
      proj.newTech = "";
    },
    removeProjectTech(projectIndex, techIndex) {
      this.cv.projects[projectIndex].tech.splice(techIndex, 1);
    },
    addSkill(group) {
      const value = this.skillDrafts[group];
      if (!value) return;
      this.cv.skills[group].push(value);
      this.skillDrafts[group] = "";
    },
    removeSkill(group, index) {
      this.cv.skills[group].splice(index, 1);
    },
    async compilePdf() {
      if (!this.templateTex) return;
      this.isCompiling = true;
      this.logs = "Preparing compilation...\n";

      try {
        const texSource = renderTemplate(this.templateTex, this.cv);
        this.appendLog("Sending to LaTeX Online compiler...");
        const result = await compileViaLatexOnline(texSource);

        if (result.log) this.appendLog(result.log);

        if (!result.pdfBytes) {
          const statusNote =
            result.status !== undefined ? ` (status ${result.status})` : "";
          throw new Error(`LaTeX compilation failed${statusNote}. See log above.`);
        }

        this.pdfBytes = result.pdfBytes;
        if (this.pdfUrl) URL.revokeObjectURL(this.pdfUrl);
        this.pdfUrl = URL.createObjectURL(
          new Blob([this.pdfBytes], { type: "application/pdf" })
        );
        this.appendLog("Done.");
      } catch (err) {
        this.appendLog(`ERROR: ${err.message || err}`);
      } finally {
        this.isCompiling = false;
      }
    },
    downloadPdf() {
      if (!this.pdfBytes) return;
      const blob = new Blob([this.pdfBytes], { type: "application/pdf" });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = "cv.pdf";
      anchor.click();
      URL.revokeObjectURL(url);
    }
  }
}).mount("#app");
