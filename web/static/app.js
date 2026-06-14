const goalInput = document.querySelector("#goal");
const runBtn = document.querySelector("#run-btn");
const skill = document.querySelector("#skill");
const ollama = document.querySelector("#ollama");
const cloudCalls = document.querySelector("#cloud-calls");
const qdrant = document.querySelector("#qdrant");
const alwaysOn = document.querySelector("#always-on");
const contextList = document.querySelector("#context-list");
const vectorMemory = document.querySelector("#vector-memory");
const pitchProof = document.querySelector("#pitch-proof");
const graph = document.querySelector("#graph");
const blocked = document.querySelector("#blocked");
const score = document.querySelector("#score");
const scoreBar = document.querySelector("#score-bar");
const confidence = document.querySelector("#confidence");
const tasksPanel = document.querySelector("#tasks");
const draftsPanel = document.querySelector("#drafts");
const auditPanel = document.querySelector("#audit");

function card(title, body, extra = "") {
  return `<article class="card"><strong>${escapeHtml(title)}</strong><p>${escapeHtml(body)}</p>${extra}</article>`;
}

function linesCard(title, lines, extra = "") {
  return `<article class="card"><strong>${escapeHtml(title)}</strong>${lines
    .map((line) => `<p>${escapeHtml(line)}</p>`)
    .join("")}${extra}</article>`;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

async function getJson(url, options = {}) {
  const response = await fetch(url, {
    headers: { "content-type": "application/json" },
    ...options,
  });
  if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
  return response.json();
}

async function loadHealth() {
  const health = await getJson("/health");
  cloudCalls.textContent = health.cloud_llm_calls;
  ollama.textContent = health.ollama.available ? "online" : "offline fallback";
  qdrant.textContent = health.qdrant.available ? "online" : "offline fallback";
  alwaysOn.textContent = `${health.always_on.last_status} · ${health.always_on.runs}`;
}

function render(result) {
  const packet = result.context_packet;
  skill.textContent = packet.skill_label;
  score.textContent = `${packet.readiness_score}%`;
  scoreBar.value = packet.readiness_score;
  confidence.textContent = packet.confidence;

  contextList.innerHTML = packet.allowed_context
    .map((item) => card(item.title, item.text, `<span class="tag">${escapeHtml(item.source)}</span>`))
    .join("");

  graph.innerHTML = packet.graph_path
    .map((label, index) => `<div class="node" data-step="${index + 1}"><strong>${escapeHtml(label)}</strong></div>`)
    .join("");

  blocked.innerHTML = packet.blocked_context
    .map((item) =>
      card(
        item.title,
        item.redacted_preview,
        `<span class="tag">${escapeHtml(item.reasons.join(", "))}</span>`,
      ),
    )
    .join("");

  tasksPanel.innerHTML = result.tasks
    .map((task) => card(task.title, `${task.owner} · ${task.status} · due ${task.due}`, `<span class="tag">${task.priority}</span>`))
    .join("");

  draftsPanel.innerHTML = [
    ...result.drafts.outline.map((section) =>
      card(section.section, section.draft, `<span class="tag">${escapeHtml(section.citations.join(", "))}</span>`),
    ),
    ...result.drafts.followups.map((draft) =>
      card(`email: ${draft.to}`, `${draft.subject}\n${draft.body}`, draft.approval_required ? `<span class="tag">approval required</span>` : ""),
    ),
  ].join("");

  auditPanel.innerHTML = [
    card("goal", result.audit.goal),
    card("graph path", result.audit.graph_path_traversed.join(" -> ")),
    card("sources used", result.audit.sources_used.join(", ")),
    card("blocked context", result.audit.context_blocked.map((item) => `${item.id}: ${item.reasons.join("/")}`).join("; ")),
    card("runtime", `${result.audit.model_runtime.provider}; cloud calls: ${result.audit.model_runtime.cloud_calls}`),
  ].join("");
}

async function runAgent() {
  runBtn.disabled = true;
  runBtn.textContent = "running locally...";
  try {
    const seed = await getJson("/demo/seed", { method: "POST" });
    const result = await getJson("/agent/run", {
      method: "POST",
      body: JSON.stringify({ goal: goalInput.value, role: "grant_manager" }),
    });
    const vector = await getJson("/tools/vector_search", {
      method: "POST",
      body: JSON.stringify({ query: goalInput.value, limit: 3 }),
    });
    const pitch = await getJson("/demo/pitch");
    render(result);
    vectorMemory.innerHTML = linesCard(
      seed.vector_seed.available ? "qdrant seeded" : "qdrant fallback",
      [`${seed.vector_seed.points || 0} points`, seed.vector_seed.embedding_source || vector.embedding_source],
      `<span class="tag">${escapeHtml(vector.hits.map((hit) => hit.chunk_id).join(", ") || "fallback context")}</span>`,
    );
    pitchProof.innerHTML = linesCard(
      "rubric fit",
      [
        `local-first: ${pitch.rubric_mapping.local_first_always_on}`,
        `business value: ${pitch.rubric_mapping.business_value}`,
      ],
      `<span class="tag">${escapeHtml(pitch.technical_proof[3])}</span>`,
    );
  } finally {
    runBtn.disabled = false;
    runBtn.textContent = "run local agent";
  }
}

document.querySelectorAll(".tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((item) => item.classList.remove("active"));
    document.querySelectorAll(".tab-panel").forEach((item) => item.classList.remove("active"));
    tab.classList.add("active");
    document.querySelector(`#${tab.dataset.tab}`).classList.add("active");
  });
});

runBtn.addEventListener("click", runAgent);
loadHealth().catch(() => {
  ollama.textContent = "unknown";
});
runAgent();
