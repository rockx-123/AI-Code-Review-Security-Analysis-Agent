(() => {
  "use strict";

  // In GitHub Codespaces, the frontend and backend are served on different forwarded
  // subdomains that only differ by port number (e.g. ...-5173.app.github.dev vs
  // ...-8000.app.github.dev). Detect that pattern automatically so nobody has to hand-edit
  // a URL every time a Codespace restarts. Falls back to plain localhost for local dev, or
  // to an explicit window.API_BASE_URL override if one is set before this script runs.
  function detectApiBaseUrl() {
    if (window.API_BASE_URL) return window.API_BASE_URL;
    const { hostname, protocol } = window.location;
    const codespacesMatch = hostname.match(/^(.*)-\d+\.app\.github\.dev$/);
    if (codespacesMatch) {
      return `${protocol}//${codespacesMatch[1]}-8000.app.github.dev`;
    }
    return `${protocol}//${hostname.split(":")[0]}:8000`;
  }

  const API_BASE_URL = detectApiBaseUrl();

  const el = (id) => document.getElementById(id);
  const apiLabel = el("api-base-label");
  if (apiLabel) apiLabel.textContent = API_BASE_URL.replace(/^https?:\/\//, "");

  function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
  }

  // ---------------------------------------------------------------------
  // Sample snippets — quick "try it" chips
  // ---------------------------------------------------------------------
  const SAMPLES = {
    "python-clean": {
      language: "python",
      code:
        "class Item:\n" +
        "    def __init__(self, name, price):\n" +
        "        self.name = name\n" +
        "        self.price = price\n\n" +
        "def calculate_total(cart):\n" +
        "    total = 0\n" +
        "    for item in cart:\n" +
        "        total += item.price\n" +
        "    return total\n\n" +
        "cart = [Item(\"Notebook\", 9.5), Item(\"Pen\", 2.25), Item(\"Backpack\", 32.0)]\n" +
        "print(f\"Total: {calculate_total(cart):.2f}\")\n",
    },
    "java-clean": {
      language: "java",
      code:
        "public class Calculator {\n" +
        "    public static int add(int a, int b) {\n" +
        "        return a + b;\n" +
        "    }\n\n" +
        "    public static void main(String[] args) {\n" +
        "        System.out.println(add(4, 7));\n" +
        "    }\n" +
        "}\n",
    },
    "python-broken": {
      language: "python",
      code:
        "def calculate_total(cart)\n" +
        "    total = 0\n" +
        "    for item in cart:\n" +
        "        total += item.price\n" +
        "    return total\n",
    },
  };

  document.querySelectorAll(".sample-chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      const sample = SAMPLES[chip.dataset.sample];
      if (!sample) return;
      setMode("paste");
      setLanguage(sample.language);
      codeInput.value = sample.code;
      refreshGutter();
      codeInput.focus();
    });
  });

  // ---------------------------------------------------------------------
  // Tabs: paste vs upload
  // ---------------------------------------------------------------------
  let mode = "paste";
  const tabButtons = document.querySelectorAll(".tab-btn");
  const viewPaste = el("view-paste");
  const viewUpload = el("view-upload");
  const sampleRow = el("sample-row");

  function setMode(newMode) {
    mode = newMode;
    tabButtons.forEach((b) => {
      const active = b.dataset.mode === mode;
      b.classList.toggle("is-active", active);
      b.setAttribute("aria-selected", active ? "true" : "false");
    });
    viewPaste.classList.toggle("is-hidden", mode !== "paste");
    viewUpload.classList.toggle("is-hidden", mode !== "upload");
    sampleRow.classList.toggle("is-hidden", mode !== "paste");
  }
  tabButtons.forEach((btn) => btn.addEventListener("click", () => setMode(btn.dataset.mode)));

  // ---------------------------------------------------------------------
  // Language switch
  // ---------------------------------------------------------------------
  let language = "python";
  const langButtons = document.querySelectorAll(".lang-btn");
  function setLanguage(lang) {
    language = lang;
    langButtons.forEach((b) => {
      const active = b.dataset.lang === lang;
      b.classList.toggle("is-active", active);
      b.setAttribute("aria-checked", active ? "true" : "false");
    });
  }
  langButtons.forEach((btn) => btn.addEventListener("click", () => setLanguage(btn.dataset.lang)));

  // ---------------------------------------------------------------------
  // Paste editor: gutter line numbers, char count, entry-method tracking, copy
  // ---------------------------------------------------------------------
  const codeInput = el("code-input");
  const codeGutter = el("code-gutter");
  const charCount = el("char-count");
  const copyCodeBtn = el("copy-code-btn");

  // Inline SVGs (not icon-font glyphs) for the copy/check toggle — some icon-font webfont
  // builds lag behind and are missing newer glyphs, which showed up as blank buttons. An
  // inline SVG has no external-loading dependency at all, so it can't silently fail this way.
  const SVG_COPY = '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="8" y="8" width="12" height="12" rx="2"/><path d="M16 8V6a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h2"/></svg>';
  const SVG_CHECK = '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M20 6 9 17l-5-5"/></svg>';

  function refreshGutter() {
    const lineCount = Math.max(1, codeInput.value.split("\n").length);
    codeGutter.textContent = Array.from({ length: lineCount }, (_, i) => i + 1).join("\n");
    charCount.textContent = `${codeInput.value.length} characters`;
  }
  codeInput.addEventListener("input", refreshGutter);
  codeInput.addEventListener("scroll", () => { codeGutter.scrollTop = codeInput.scrollTop; });
  refreshGutter();

  // Tracks how the last change to the editor happened, for the "Entry" field shown in results.
  let entryMethod = "typed";
  codeInput.addEventListener("paste", () => { entryMethod = "pasted"; });
  codeInput.addEventListener("keydown", (e) => {
    if (!["Control", "Shift", "Alt", "Meta"].includes(e.key)) entryMethod = "typed";
  });

  copyCodeBtn.addEventListener("click", async () => {
    if (!codeInput.value.trim()) return;
    try {
      await navigator.clipboard.writeText(codeInput.value);
      copyCodeBtn.classList.add("is-copied");
      copyCodeBtn.innerHTML = SVG_CHECK;
      setTimeout(() => {
        copyCodeBtn.classList.remove("is-copied");
        copyCodeBtn.innerHTML = SVG_COPY;
      }, 1400);
    } catch { /* clipboard permissions denied — silently ignore */ }
  });

  // ---------------------------------------------------------------------
  // Upload dropzone
  // ---------------------------------------------------------------------
  const dropzone = el("dropzone");
  const fileInput = el("file-input");
  const uploadChip = el("upload-chip");
  const uploadFilename = el("upload-filename");
  const uploadClear = el("upload-clear");
  let selectedFile = null;

  function setSelectedFile(file) {
    selectedFile = file;
    if (file) {
      uploadFilename.textContent = `${file.name}  ·  ${(file.size / 1024).toFixed(1)} KB`;
      uploadChip.classList.remove("is-hidden");
      dropzone.classList.add("is-hidden");
    } else {
      uploadChip.classList.add("is-hidden");
      dropzone.classList.remove("is-hidden");
      fileInput.value = "";
    }
  }

  fileInput.addEventListener("change", () => setSelectedFile(fileInput.files[0] || null));
  uploadClear.addEventListener("click", () => setSelectedFile(null));

  ["dragover", "dragenter"].forEach((evt) =>
    dropzone.addEventListener(evt, (e) => { e.preventDefault(); dropzone.classList.add("is-dragover"); })
  );
  ["dragleave", "drop"].forEach((evt) =>
    dropzone.addEventListener(evt, (e) => { e.preventDefault(); dropzone.classList.remove("is-dragover"); })
  );
  dropzone.addEventListener("drop", (e) => {
    const file = e.dataTransfer.files[0];
    if (file) setSelectedFile(file);
  });

  // ---------------------------------------------------------------------
  // Celebration burst — small dependency-free confetti puff on success
  // ---------------------------------------------------------------------
  function celebrate(anchorEl) {
    const colors = ["#ff4d8d", "#7c4dff", "#3da8f5", "#ffb020", "#14c38e"];
    for (let i = 0; i < 14; i++) {
      const dot = document.createElement("span");
      dot.className = "celebrate-dot";
      const angle = Math.random() * Math.PI * 2;
      const distance = 40 + Math.random() * 50;
      dot.style.setProperty("--dx", `${Math.cos(angle) * distance}px`);
      dot.style.setProperty("--dy", `${Math.sin(angle) * distance}px`);
      dot.style.background = colors[i % colors.length];
      dot.style.animationDelay = `${Math.random() * 0.08}s`;
      anchorEl.appendChild(dot);
      dot.addEventListener("animationend", () => dot.remove());
    }
  }

  // ---------------------------------------------------------------------
  // Submit
  // ---------------------------------------------------------------------
  const submitBtn = el("submit-btn");
  const panelActions = el("panel-actions");
  const submitHint = el("submit-hint");
  const resultsPanel = el("results-panel");
  const resultsBadge = el("results-badge");
  const resultsMeta = el("results-meta");
  const resultsErrors = el("results-errors");
  const runRow = el("run-row");
  const runBtn = el("run-btn");
  const outputPanel = el("output-panel");
  const outputMeta = el("output-meta");
  const outputBody = el("output-body");

  let currentSubmission = null;

  function renderResults(submission) {
    currentSubmission = submission;
    resultsPanel.classList.remove("is-hidden");
    outputPanel.classList.add("is-hidden");
    outputBody.textContent = "";
    const valid = submission.validation.is_valid;

    resultsBadge.textContent = valid ? "Syntax valid" : "Syntax errors found";
    resultsBadge.className = "badge " + (valid ? "badge-ok" : "badge-err");

    resultsMeta.innerHTML = `
      <span>Language: <b>${submission.language}</b></span>
      <span>Source: <b>${submission.source}</b></span>
      ${submission.entry_method ? `<span>Entry: <b>${submission.entry_method}</b></span>` : ""}
      ${submission.filename ? `<span>File: <b>${escapeHtml(submission.filename)}</b></span>` : ""}
      <span>Size: <b>${submission.size_bytes} bytes</b></span>
    `;

    resultsErrors.innerHTML = "";
    submission.validation.errors.forEach((e) => {
      const row = document.createElement("div");
      const isNote = submission.validation.is_valid;
      row.className = "error-row" + (isNote ? " is-note" : "");
      const loc = e.line ? `L${e.line}${e.column ? `:${e.column}` : ""}` : "note";
      row.innerHTML = `<span class="error-loc">${loc}</span><span>${escapeHtml(e.message)}</span>`;
      resultsErrors.appendChild(row);
    });

    runRow.classList.toggle("is-hidden", !valid);
    if (valid) celebrate(panelActions);
  }

  runBtn.addEventListener("click", async () => {
    if (!currentSubmission) return;
    runBtn.disabled = true;
    const originalLabel = runBtn.innerHTML;
    runBtn.innerHTML = '<i class="ti ti-loader-2" aria-hidden="true"></i> Running…';
    outputPanel.classList.remove("is-hidden");
    outputBody.textContent = "";
    outputMeta.textContent = "";

    try {
      const res = await fetch(`${API_BASE_URL}/api/execution/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ language: currentSubmission.language, code: currentSubmission.code }),
      });

      if (res.status === 403) {
        const body = await res.json().catch(() => ({}));
        outputBody.textContent = body.detail || "Code execution is disabled on this server.";
        outputMeta.textContent = "disabled";
        return;
      }
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        outputBody.textContent = body.detail || `Request failed (${res.status})`;
        return;
      }

      const result = await res.json();

      if (!result.ran) {
        const parts = [result.error, result.stderr].filter(Boolean);
        outputBody.textContent = parts.length ? parts.join("\n\n") : "Execution did not run.";
        outputMeta.textContent = "not run";
        return;
      }

      let text = result.stdout || "";
      if (result.stderr) {
        text += (text ? "\n" : "") + result.stderr;
      }
      outputBody.textContent = text || "(no output)";
      outputMeta.textContent =
        (result.timed_out ? "timed out · " : "") +
        `exit code ${result.exit_code ?? "—"} · ${result.duration_ms}ms` +
        (result.truncated ? " · truncated" : "");
    } catch (err) {
      outputBody.textContent = `Couldn't reach the backend: ${err.message}`;
    } finally {
      runBtn.disabled = false;
      runBtn.innerHTML = originalLabel;
    }
  });

  async function submitPaste() {
    const code = codeInput.value;
    if (!code.trim()) throw new Error("Paste or type some code before submitting.");
    const res = await fetch(`${API_BASE_URL}/api/submissions/paste`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ language, code, entry_method: entryMethod }),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body.detail || `Request failed (${res.status})`);
    }
    return res.json();
  }

  async function submitUpload() {
    if (!selectedFile) throw new Error("Choose a .py or .java file first.");
    const form = new FormData();
    form.append("file", selectedFile);
    const res = await fetch(`${API_BASE_URL}/api/submissions/upload`, { method: "POST", body: form });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body.detail || `Request failed (${res.status})`);
    }
    return res.json();
  }

  submitBtn.addEventListener("click", async () => {
    submitBtn.disabled = true;
    submitHint.textContent = "Validating…";
    try {
      const submission = mode === "paste" ? await submitPaste() : await submitUpload();
      renderResults(submission);
      submitHint.textContent = "Done. Analysis, remediation, and summary agents arrive in later milestones.";
      loadHistory();
    } catch (err) {
      resultsPanel.classList.remove("is-hidden");
      resultsBadge.textContent = "Request failed";
      resultsBadge.className = "badge badge-err";
      resultsMeta.innerHTML = "";
      resultsErrors.innerHTML = `<div class="error-row"><span>${escapeHtml(err.message)}</span></div>`;
      submitHint.textContent = "Something went wrong — see details above.";
    } finally {
      submitBtn.disabled = false;
    }
  });

  // ---------------------------------------------------------------------
  // Recent activity (history) panel
  // ---------------------------------------------------------------------
  const historyList = el("history-list");

  function relativeTime(iso) {
    const diffMs = Date.now() - new Date(iso).getTime();
    const mins = Math.round(diffMs / 60000);
    if (mins < 1) return "just now";
    if (mins < 60) return `${mins}m ago`;
    const hrs = Math.round(mins / 60);
    if (hrs < 24) return `${hrs}h ago`;
    return `${Math.round(hrs / 24)}d ago`;
  }

  async function loadHistory() {
    try {
      const res = await fetch(`${API_BASE_URL}/api/submissions?limit=8`);
      if (!res.ok) throw new Error();
      const items = await res.json();
      if (!items.length) {
        historyList.innerHTML = `<div class="history-empty">Your submissions this session will show up here.</div>`;
        return;
      }
      historyList.innerHTML = "";
      items.forEach((item) => {
        const row = document.createElement("button");
        row.type = "button";
        row.className = "history-item";
        row.innerHTML = `
          <span class="history-lang-icon lang-${item.language}">${item.language === "python" ? "PY" : "JV"}</span>
          <span class="history-text">
            <span class="history-snippet">${escapeHtml(item.snippet || item.filename || "(empty)")}</span>
            <span class="history-time">${relativeTime(item.created_at)} · ${item.source}</span>
          </span>
          <i class="ti ${item.is_valid ? "ti-circle-check" : "ti-circle-x"} history-valid-dot"
             style="color:${item.is_valid ? "var(--mint)" : "var(--coral)"}" aria-hidden="true"></i>
        `;
        row.addEventListener("click", () => loadSubmissionIntoEditor(item.id));
        historyList.appendChild(row);
      });
    } catch {
      historyList.innerHTML = `<div class="history-empty">Couldn't load history — is the backend running?</div>`;
    }
  }

  async function loadSubmissionIntoEditor(id) {
    try {
      const res = await fetch(`${API_BASE_URL}/api/submissions/${id}`);
      if (!res.ok) throw new Error();
      const submission = await res.json();
      setMode("paste");
      setLanguage(submission.language);
      codeInput.value = submission.code;
      refreshGutter();
      renderResults(submission);
      codeInput.scrollIntoView({ behavior: "smooth", block: "center" });
    } catch {
      /* best-effort — silently ignore if the submission can't be fetched */
    }
  }

  loadHistory();

  // ---------------------------------------------------------------------
  // Knowledge base status, category filter + search
  // ---------------------------------------------------------------------
  const kbDot = el("kb-dot");
  const kbStatusText = el("kb-status-text");
  const kbMeta = el("kb-meta");
  const kbQuery = el("kb-query");
  const kbSearchBtn = el("kb-search-btn");
  const kbResults = el("kb-results");
  const kbChips = document.querySelectorAll(".kb-chip");
  let activeCategory = "";

  kbChips.forEach((chip) => {
    chip.addEventListener("click", () => {
      kbChips.forEach((c) => c.classList.remove("is-active"));
      chip.classList.add("is-active");
      activeCategory = chip.dataset.category || "";
      if (kbQuery.value.trim()) runKbSearch();
    });
  });

  async function loadKbStatus() {
    try {
      const res = await fetch(`${API_BASE_URL}/api/knowledge-base/status`);
      if (!res.ok) throw new Error();
      const data = await res.json();
      kbDot.className = "dot dot-ok";
      kbStatusText.textContent = `Knowledge base ready`;
      kbMeta.textContent = `${data.document_count} documents · ${data.chunk_count} chunks · ${data.categories.join(", ")}`;
    } catch {
      kbDot.className = "dot dot-err";
      kbStatusText.textContent = "Knowledge base unreachable";
      kbMeta.textContent = "Start the backend and run: python -m app.rag.ingest";
    }
  }
  loadKbStatus();

  async function runKbSearch() {
    const query = kbQuery.value.trim();
    if (!query) return;
    kbResults.innerHTML = `<div class="kb-empty">Searching…</div>`;
    try {
      const res = await fetch(`${API_BASE_URL}/api/knowledge-base/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, top_k: 4, category: activeCategory || null }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || `Request failed (${res.status})`);
      }
      const data = await res.json();
      if (!data.results.length) {
        kbResults.innerHTML = `<div class="kb-empty">No matches found${activeCategory ? " in this category" : ""}.</div>`;
        return;
      }
      kbResults.innerHTML = "";
      data.results.forEach((r) => {
        const card = document.createElement("div");
        card.className = "kb-result-card";
        card.innerHTML = `
          <div class="kb-result-head">
            <span class="kb-result-title">${escapeHtml(r.title)}${r.heading ? ` <span class="kb-result-heading">— ${escapeHtml(r.heading)}</span>` : ""}</span>
            <span class="kb-result-score">match ${(r.score * 100).toFixed(0)}%</span>
          </div>
          <div class="kb-result-text">${escapeHtml(r.text.slice(0, 320))}${r.text.length > 320 ? "…" : ""}</div>
          <button class="kb-copy-btn" type="button" aria-label="Copy excerpt">${SVG_COPY}</button>
        `;
        card.querySelector(".kb-copy-btn").addEventListener("click", async (ev) => {
          try {
            await navigator.clipboard.writeText(r.text);
            const btn = ev.currentTarget;
            btn.innerHTML = SVG_CHECK;
            setTimeout(() => { btn.innerHTML = SVG_COPY; }, 1200);
          } catch { /* clipboard permissions denied — silently ignore */ }
        });
        kbResults.appendChild(card);
      });
    } catch (err) {
      kbResults.innerHTML = `<div class="kb-empty">${escapeHtml(err.message)}</div>`;
    }
  }

  kbSearchBtn.addEventListener("click", runKbSearch);
  kbQuery.addEventListener("keydown", (e) => { if (e.key === "Enter") runKbSearch(); });
})();
