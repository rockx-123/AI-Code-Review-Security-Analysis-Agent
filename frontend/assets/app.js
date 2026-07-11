(() => {
  "use strict";

  const API_BASE_URL = window.API_BASE_URL || "http://localhost:8000";

  const el = (id) => document.getElementById(id);
  const apiLabel = el("api-base-label");
  if (apiLabel) apiLabel.textContent = API_BASE_URL.replace(/^https?:\/\//, "");

  // ---------------------------------------------------------------------
  // Tabs: paste vs upload
  // ---------------------------------------------------------------------
  let mode = "paste";
  const tabButtons = document.querySelectorAll(".tab-btn");
  const viewPaste = el("view-paste");
  const viewUpload = el("view-upload");

  tabButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      mode = btn.dataset.mode;
      tabButtons.forEach((b) => {
        b.classList.toggle("is-active", b === btn);
        b.setAttribute("aria-selected", b === btn ? "true" : "false");
      });
      viewPaste.classList.toggle("is-hidden", mode !== "paste");
      viewUpload.classList.toggle("is-hidden", mode !== "upload");
    });
  });

  // ---------------------------------------------------------------------
  // Language switch
  // ---------------------------------------------------------------------
  let language = "python";
  const langButtons = document.querySelectorAll(".lang-btn");
  langButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      language = btn.dataset.lang;
      langButtons.forEach((b) => {
        b.classList.toggle("is-active", b === btn);
        b.setAttribute("aria-checked", b === btn ? "true" : "false");
      });
    });
  });

  // ---------------------------------------------------------------------
  // Paste editor: gutter line numbers + char count
  // ---------------------------------------------------------------------
  const codeInput = el("code-input");
  const codeGutter = el("code-gutter");
  const charCount = el("char-count");

  // Tracks how the last change to the editor happened. A real Ctrl+V / right-click
  // paste fires a "paste" event right after the keydown, so it correctly overrides
  // "typed" below. This reflects the most recent action, not a full edit history.
  let entryMethod = "typed";
  codeInput.addEventListener("paste", () => {
    entryMethod = "pasted";
  });
  codeInput.addEventListener("keydown", (e) => {
    if (!["Control", "Shift", "Alt", "Meta"].includes(e.key)) {
      entryMethod = "typed";
    }
  });

  function refreshGutter() {
    const lineCount = Math.max(1, codeInput.value.split("\n").length);
    codeGutter.textContent = Array.from({ length: lineCount }, (_, i) => i + 1).join("\n");
    charCount.textContent = `${codeInput.value.length} characters`;
  }
  codeInput.addEventListener("input", refreshGutter);
  codeInput.addEventListener("scroll", () => {
    codeGutter.scrollTop = codeInput.scrollTop;
  });
  refreshGutter();

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
    dropzone.addEventListener(evt, (e) => {
      e.preventDefault();
      dropzone.classList.add("is-dragover");
    })
  );
  ["dragleave", "drop"].forEach((evt) =>
    dropzone.addEventListener(evt, (e) => {
      e.preventDefault();
      dropzone.classList.remove("is-dragover");
    })
  );
  dropzone.addEventListener("drop", (e) => {
    const file = e.dataTransfer.files[0];
    if (file) setSelectedFile(file);
  });

  // ---------------------------------------------------------------------
  // Submit
  // ---------------------------------------------------------------------
  const submitBtn = el("submit-btn");
  const submitHint = el("submit-hint");
  const resultsPanel = el("results-panel");
  const resultsBadge = el("results-badge");
  const resultsMeta = el("results-meta");
  const resultsErrors = el("results-errors");

  function renderResults(submission) {
    resultsPanel.classList.remove("is-hidden");
    const valid = submission.validation.is_valid;

    resultsBadge.textContent = valid ? "Syntax valid" : "Syntax errors found";
    resultsBadge.className = "badge " + (valid ? "badge-ok" : "badge-err");

    resultsMeta.innerHTML = `
      <span>Language: <b>${submission.language}</b></span>
      <span>Source: <b>${submission.source}</b></span>
      ${submission.entry_method ? `<span>Entry: <b>${submission.entry_method}</b></span>` : ""}
      ${submission.filename ? `<span>File: <b>${submission.filename}</b></span>` : ""}
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
  }

  function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
  }

  async function submitPaste() {
    const code = codeInput.value;
    if (!code.trim()) throw new Error("Paste some code before submitting.");
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
  // Knowledge base status + search
  // ---------------------------------------------------------------------
  const kbDot = el("kb-dot");
  const kbStatusText = el("kb-status-text");
  const kbMeta = el("kb-meta");
  const kbQuery = el("kb-query");
  const kbSearchBtn = el("kb-search-btn");
  const kbResults = el("kb-results");

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
        body: JSON.stringify({ query, top_k: 4 }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || `Request failed (${res.status})`);
      }
      const data = await res.json();
      if (!data.results.length) {
        kbResults.innerHTML = `<div class="kb-empty">No matches found.</div>`;
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
        `;
        kbResults.appendChild(card);
      });
    } catch (err) {
      kbResults.innerHTML = `<div class="kb-empty">${escapeHtml(err.message)}</div>`;
    }
  }

  kbSearchBtn.addEventListener("click", runKbSearch);
  kbQuery.addEventListener("keydown", (e) => {
    if (e.key === "Enter") runKbSearch();
  });
})();
