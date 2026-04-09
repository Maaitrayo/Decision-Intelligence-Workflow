const runButton = document.getElementById("run-button");
const sidebar = document.getElementById("sidebar");
const sidebarToggle = document.getElementById("sidebar-toggle");
const sessionCount = document.getElementById("session-count");
const runHistory = document.getElementById("run-history");
const workspaceTitle = document.getElementById("workspace-title");
const workspaceSubtitle = document.getElementById("workspace-subtitle");
const statusPill = document.getElementById("status-pill");
const summaryLayout = document.getElementById("summary-layout");
const summaryOutput = document.getElementById("summary-output");
const summaryMetrics = document.getElementById("summary-metrics");
const metricSignals = document.getElementById("metric-signals");
const metricUncertainties = document.getElementById("metric-uncertainties");
const metricTrace = document.getElementById("metric-trace");
const metricTokens = document.getElementById("metric-tokens");
const signalsOutput = document.getElementById("signals-output");
const uncertaintiesOutput = document.getElementById("uncertainties-output");
const ignoredOutput = document.getElementById("ignored-output");
const traceOutput = document.getElementById("trace-output");
const chatOutput = document.getElementById("chat-output");
const chatForm = document.getElementById("chat-form");
const chatInput = document.getElementById("chat-input");
const chatSubmit = document.getElementById("chat-submit");

const RUN_ENDPOINT = "/api/runs";
const QUERY_ENDPOINT = "/api/query";
const PROGRESS_ENDPOINT = "/api/progress";

let selectedRun = null;
let currentSessionId = null;
let progressTimer = null;

async function runAnalysis() {
  setStatus("Running");
  setWorkspace("Running fresh analysis", "The pipeline is collecting sources and producing a new result.");
  runButton.disabled = true;
  startProgressPolling();

  try {
    const response = await fetch(RUN_ENDPOINT, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ eval: false }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Run request failed (${response.status}): ${errorText}`);
    }

    const payload = await response.json();
    currentSessionId = null;
    renderRun(payload);
    setStatus("Run Complete");
    await loadRunHistory(payload.run_id);
  } catch (error) {
    setStatus("Run Failed");
    renderErrorState(error instanceof Error ? error.message : String(error));
  } finally {
    stopProgressPolling();
    runButton.disabled = false;
  }
}

async function loadRunHistory(preferredRunId = null) {
  try {
    const response = await fetch(RUN_ENDPOINT);
    if (!response.ok) {
      throw new Error(`Could not load run history (${response.status})`);
    }

    const runs = await response.json();
    renderRunHistory(runs, preferredRunId);
  } catch (error) {
    sessionCount.textContent = "0";
    runHistory.innerHTML = `<p class="empty-state">${escapeHtml(
      error instanceof Error ? error.message : String(error)
    )}</p>`;
  }
}

function renderRunHistory(runs, preferredRunId) {
  const runList = Array.isArray(runs) ? runs : [];
  sessionCount.textContent = String(runList.length);

  if (runList.length === 0) {
    runHistory.innerHTML = '<p class="empty-state">No saved runs yet.</p>';
    return;
  }

  runHistory.innerHTML = runList
    .map((run) => {
      const active = selectedRun && selectedRun.run_id === run.run_id;
      return `
        <article class="run-card ${active ? "active" : ""}">
          <h3>${escapeHtml(shortId(run.run_id))}</h3>
          <p>${escapeHtml(run.executive_summary || "No summary available.")}</p>
          <button type="button" data-run-id="${escapeHtml(run.run_id)}">Open Session</button>
        </article>
      `;
    })
    .join("");

  runHistory.querySelectorAll("[data-run-id]").forEach((button) => {
    button.addEventListener("click", () => {
      void loadRun(button.getAttribute("data-run-id"));
    });
  });

  if (preferredRunId) {
    void loadRun(preferredRunId);
  }
}

async function loadRun(runId) {
  if (!runId) {
    return;
  }

  setStatus("Loading Session");
  setWorkspace("Loading saved analysis", "Fetching the selected run from storage.");

  try {
    const response = await fetch(`${RUN_ENDPOINT}/${encodeURIComponent(runId)}`);
    if (!response.ok) {
      throw new Error(`Could not load run (${response.status})`);
    }

    const payload = await response.json();
    currentSessionId = null;
    renderRun(payload);
    setStatus("Session Loaded");
    await loadRunHistory();
  } catch (error) {
    setStatus("Load Failed");
    renderErrorState(error instanceof Error ? error.message : String(error));
  }
}

async function pollProgress() {
  try {
    const response = await fetch(PROGRESS_ENDPOINT);
    if (!response.ok) {
      return;
    }

    const state = await response.json();
    if (state?.message) {
      setStatus(state.message);
    }
    if (state?.running) {
      workspaceSubtitle.textContent = `Current stage: ${state.stage || "unknown"}`;
    }
  } catch (_error) {
    // Best-effort polling only.
  }
}

function renderRun(run) {
  selectedRun = run;
  const signalCount = run.key_signals?.length || 0;
  const uncertaintyCount = run.uncertainties?.length || 0;
  const traceCount = run.trace?.length || 0;
  const totalTokens = run.token_usage?.total_tokens || 0;

  setWorkspace(
    run.run_id ? `Analysis ${shortId(run.run_id)}` : "Analysis loaded",
    `${signalCount} signals, ${uncertaintyCount} uncertainties, ${traceCount} trace entries`
  );

  summaryOutput.textContent = run.executive_summary || "No executive summary available.";
  metricSignals.textContent = String(signalCount);
  metricUncertainties.textContent = String(uncertaintyCount);
  metricTrace.textContent = String(traceCount);
  metricTokens.textContent = String(totalTokens);
  toggleSummaryMetrics(signalCount, uncertaintyCount, traceCount, totalTokens);

  renderSignals(run.key_signals || []);
  renderUncertainties(run.uncertainties || []);
  renderIgnored(run.ignored_signals || []);
  renderTrace(run.trace || []);
  renderChat([]);
}

function renderSignals(signals) {
  if (!signals.length) {
    signalsOutput.innerHTML = '<p class="empty-state">No signals to show.</p>';
    return;
  }

  signalsOutput.innerHTML = signals
    .map(
      (signal) => `
        <article class="item-card">
          <span class="item-meta">${escapeHtml(signal.source)} · ${escapeHtml(signal.confidence || "n/a")}</span>
          <h3>${escapeHtml(signal.title)}</h3>
          <p>${escapeHtml(signal.summary || "No summary available.")}</p>
        </article>
      `
    )
    .join("");
}

function renderUncertainties(items) {
  if (!items.length) {
    uncertaintiesOutput.innerHTML = '<p class="empty-state">No uncertainties surfaced yet.</p>';
    return;
  }

  uncertaintiesOutput.innerHTML = items
    .map(
      (item) => `
        <article class="item-card">
          <span class="item-meta">${escapeHtml(item.signal_a)} vs ${escapeHtml(item.signal_b)}</span>
          <p>${escapeHtml(item.description || "No detail available.")}</p>
        </article>
      `
    )
    .join("");
}

function renderIgnored(items) {
  if (!items.length) {
    ignoredOutput.innerHTML = '<p class="empty-state">No ignored items yet.</p>';
    return;
  }

  ignoredOutput.innerHTML = items
    .slice(0, 12)
    .map(
      (item) => `
        <article class="item-card">
          <span class="item-meta">${escapeHtml(item.source)} · ${escapeHtml(item.reason || "ignored")}</span>
          <h3>${escapeHtml(item.title)}</h3>
        </article>
      `
    )
    .join("");
}

function renderTrace(entries) {
  if (!entries.length) {
    traceOutput.innerHTML = '<p class="empty-state">No trace entries yet.</p>';
    return;
  }

  traceOutput.innerHTML = entries
    .map(
      (entry) => `
        <article class="trace-card">
          <span class="trace-meta">${escapeHtml(entry.stage)}</span>
          <h3>${escapeHtml(entry.decision || "No decision note")}</h3>
          <div class="trace-metrics">
            <div class="trace-metric">
              <span class="trace-metric-label">Duration</span>
              <span class="trace-metric-value">${escapeHtml(String(entry.duration_ms || 0))} ms</span>
            </div>
            <div class="trace-metric">
              <span class="trace-metric-label">Tokens</span>
              <span class="trace-metric-value">${escapeHtml(String(entry.tokens_used || 0))}</span>
            </div>
            <div class="trace-metric">
              <span class="trace-metric-label">Inputs</span>
              <span class="trace-metric-value">${escapeHtml(entry.inputs_summary || "n/a")}</span>
            </div>
            <div class="trace-metric">
              <span class="trace-metric-label">Outputs</span>
              <span class="trace-metric-value">${escapeHtml(entry.outputs_summary || "n/a")}</span>
            </div>
          </div>
        </article>
      `
    )
    .join("");
}

function renderChat(messages) {
  if (!messages.length) {
    chatOutput.innerHTML = '<p class="empty-state">Open a run to start a grounded follow-up chat.</p>';
    return;
  }

  chatOutput.innerHTML = messages
    .map(
      (message) => `
        <article class="chat-bubble ${escapeHtml(message.role || "assistant")}">
          <span class="item-meta">${escapeHtml((message.role || "assistant").toUpperCase())}</span>
          <p>${escapeHtml(message.content || "")}</p>
        </article>
      `
    )
    .join("");
}

async function submitChat(event) {
  event.preventDefault();

  const question = chatInput.value.trim();
  if (!question || !selectedRun?.run_id) {
    return;
  }

  chatSubmit.disabled = true;
  setStatus("Querying");

  const optimisticMessages = [...collectRenderedMessages(), { role: "user", content: question }];
  renderChat(optimisticMessages);
  chatInput.value = "";

  try {
    const response = await fetch(QUERY_ENDPOINT, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        run_id: selectedRun.run_id,
        session_id: currentSessionId,
        question,
      }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Query failed (${response.status}): ${errorText}`);
    }

    const payload = await response.json();
    currentSessionId = payload.session_id || currentSessionId;
    renderChat([...optimisticMessages, { role: "assistant", content: payload.answer || "No answer returned." }]);
    setStatus("Session Loaded");
  } catch (error) {
    renderChat([
      ...optimisticMessages,
      { role: "assistant", content: error instanceof Error ? error.message : String(error) },
    ]);
    setStatus("Query Failed");
  } finally {
    chatSubmit.disabled = false;
  }
}

function collectRenderedMessages() {
  return Array.from(chatOutput.querySelectorAll(".chat-bubble")).map((node) => ({
    role: node.classList.contains("user") ? "user" : "assistant",
    content: node.querySelector("p")?.textContent || "",
  }));
}

function setStatus(label) {
  statusPill.textContent = label;
}

function setWorkspace(title, subtitle) {
  workspaceTitle.textContent = title;
  workspaceSubtitle.textContent = subtitle;
}

function renderErrorState(message) {
  summaryOutput.textContent = message;
  metricSignals.textContent = "0";
  metricUncertainties.textContent = "0";
  metricTrace.textContent = "0";
  metricTokens.textContent = "0";
  toggleSummaryMetrics(0, 0, 0, 0);
  signalsOutput.innerHTML = '<p class="empty-state">No signals to show.</p>';
  uncertaintiesOutput.innerHTML = '<p class="empty-state">No uncertainties surfaced yet.</p>';
  ignoredOutput.innerHTML = '<p class="empty-state">No ignored items yet.</p>';
  traceOutput.innerHTML = '<p class="empty-state">No trace entries yet.</p>';
}

function shortId(value) {
  if (!value) {
    return "Unknown";
  }
  return `${value.slice(0, 8)}...`;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function startProgressPolling() {
  stopProgressPolling();
  void pollProgress();
  progressTimer = window.setInterval(() => {
    void pollProgress();
  }, 1200);
}

function stopProgressPolling() {
  if (progressTimer !== null) {
    window.clearInterval(progressTimer);
    progressTimer = null;
  }
}

function toggleSummaryMetrics(signalCount, uncertaintyCount, traceCount, totalTokens) {
  const hasMetrics = signalCount > 0 || uncertaintyCount > 0 || traceCount > 0 || totalTokens > 0;
  summaryMetrics.hidden = !hasMetrics;
  summaryLayout.classList.toggle("summary-layout-compact", !hasMetrics);
}

sidebarToggle.addEventListener("click", () => {
  const collapsed = sidebar.classList.toggle("is-collapsed");
  sidebarToggle.textContent = collapsed ? "Show Sessions" : "Hide Sessions";
  sidebarToggle.setAttribute("aria-expanded", String(!collapsed));
});

runButton.addEventListener("click", () => {
  void runAnalysis();
});

chatForm.addEventListener("submit", (event) => {
  void submitChat(event);
});

void loadRunHistory();
