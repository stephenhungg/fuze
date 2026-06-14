const goalInput = document.querySelector("#goal");
const userSelect = document.querySelector("#user-select");
const runBtn = document.querySelector("#run-btn");
const skill = document.querySelector("#skill");
const role = document.querySelector("#role");
const identityStatus = document.querySelector("#identity");
const ollama = document.querySelector("#ollama");
const cloudCalls = document.querySelector("#cloud-calls");
const qdrant = document.querySelector("#qdrant");
const alwaysOn = document.querySelector("#always-on");
const contextList = document.querySelector("#context-list");
const identityCard = document.querySelector("#identity-card");
const orgProfile = document.querySelector("#org-profile");
const vectorMemory = document.querySelector("#vector-memory");
const pitchProof = document.querySelector("#pitch-proof");
const agentMesh = document.querySelector("#agent-mesh");
const agentStream = document.querySelector("#agent-stream");
const sseStatus = document.querySelector("#sse-status");
const eventCount = document.querySelector("#event-count");
const policyCount = document.querySelector("#policy-count");
const approvalCount = document.querySelector("#approval-count");
const onboardingFlow = document.querySelector("#onboarding-flow");
const graph = document.querySelector("#graph");
const blocked = document.querySelector("#blocked");
const score = document.querySelector("#score");
const scoreBar = document.querySelector("#score-bar");
const confidence = document.querySelector("#confidence");
const tasksPanel = document.querySelector("#tasks");
const draftsPanel = document.querySelector("#drafts");
const approvalsPanel = document.querySelector("#approvals");
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
  identityStatus.textContent = health.identity.provider;
  alwaysOn.textContent = `${health.always_on.last_status} · ${health.always_on.runs}`;
}

async function loadUsers() {
  const data = await getJson("/identity/users");
  userSelect.innerHTML = data.users
    .map(
      (user) =>
        `<option value="${escapeHtml(user.id)}" data-role="${escapeHtml(user.role)}">${escapeHtml(user.name)} · ${escapeHtml(user.role)}</option>`,
    )
    .join("");
  userSelect.value = "morgan";
}

function render(result) {
  const packet = result.context_packet;
  skill.textContent = packet.skill_label;
  role.textContent = packet.role;
  score.textContent = `${packet.readiness_score}%`;
  scoreBar.value = packet.readiness_score;
  confidence.textContent = packet.confidence;

  identityCard.innerHTML = linesCard("identity adapter", [
    `${packet.user.name} · ${packet.user.title}`,
    `role: ${packet.role}`,
    `groups: ${packet.groups.join(", ")}`,
  ]);

  orgProfile.innerHTML = [
    linesCard("org profile", [
      packet.org_profile.name,
      `${packet.org_profile.staff_count} staff · ${packet.org_profile.volunteer_count} volunteers · ${packet.org_profile.active_grants} active grants`,
      packet.org_profile.risk_posture,
    ]),
    linesCard(
      "systems connected",
      packet.connectors.map((connector) => `${connector.label}: ${connector.status}`),
      `<span class="tag">${escapeHtml(packet.connectors.length)} connectors</span>`,
    ),
    linesCard(
      "operating metrics",
      packet.metrics.map((metric) => `${metric.label}: ${metric.value ?? "missing"} · ${metric.status}`),
      `<span class="tag">${escapeHtml(packet.metrics.length)} metrics</span>`,
    ),
  ].join("");

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

  renderApprovals(result.approvals);

  auditPanel.innerHTML = [
    card("goal", result.audit.goal),
    card("identity", `${result.audit.user.name} · ${result.audit.role}; groups: ${result.audit.groups.join(", ")}`),
    card("graph path", result.audit.graph_path_traversed.join(" -> ")),
    card("sources used", result.audit.sources_used.join(", ")),
    card("blocked context", result.audit.context_blocked.map((item) => `${item.id}: ${item.reasons.join("/")}`).join("; ")),
    card("runtime", `${result.audit.model_runtime.provider}; cloud calls: ${result.audit.model_runtime.cloud_calls}`),
  ].join("");
}

function renderApprovals(approvals) {
  if (!approvals.length) {
    approvalsPanel.innerHTML = card("no approval gates", "nothing is waiting on a human right now.");
    return;
  }

  approvalsPanel.innerHTML = approvals
    .map((approval) => {
      const closed = approval.status !== "pending";
      const tagClass = closed ? approval.status : "";
      const decision = closed
        ? `<span class="tag ${escapeHtml(tagClass)}">${escapeHtml(approval.status)} by ${escapeHtml(approval.decided_by)}</span>`
        : `<span class="tag">pending · ${escapeHtml(approval.owner_role)}</span>`;
      const actions = closed
        ? ""
        : `<div class="approval-actions">
            <button type="button" data-approval="${escapeHtml(approval.id)}" data-decision="approved">approve</button>
            <button type="button" data-approval="${escapeHtml(approval.id)}" data-decision="rejected">reject</button>
          </div>`;
      return card(
        approval.title,
        `${approval.reason}\nsource: ${approval.source}`,
        `${decision}${actions}`,
      );
    })
    .join("");
}

function renderAgents(mesh) {
  agentMesh.innerHTML = mesh.agents
    .map((agent) => linesCard(agent.label, [`${agent.kind} · ${agent.status}`, agent.description]))
    .join("");
  agentStream.innerHTML = mesh.events
    .slice(0, 8)
    .map((event) => card(`${event.agent_id} · ${event.type}`, event.message, `<span class="tag">${escapeHtml(event.created_at)}</span>`))
    .join("");
  eventCount.textContent = mesh.event_count;
  policyCount.textContent = mesh.events.filter((event) => event.agent_id === "policy-agent").length;
  approvalCount.textContent = mesh.events.filter((event) => event.agent_id === "approval-agent").length;
}

function renderObservability(summary) {
  eventCount.textContent = summary.events_buffered;
  policyCount.textContent = summary.agent_counts["policy-agent"] || 0;
  approvalCount.textContent = summary.agent_counts["approval-agent"] || 0;
}

function renderOnboarding(data) {
  onboardingFlow.innerHTML = data.flow
    .map((step) =>
      linesCard(
        step.label,
        [`${step.owner} · ${step.status}`, step.details],
        `<span class="tag">${escapeHtml(step.id)}</span>`,
      ),
    )
    .join("");
}

async function refreshApprovals() {
  const data = await getJson("/approvals");
  renderApprovals(data.approvals);
}

async function decideApproval(id, status, button) {
  button.disabled = true;
  await getJson(`/approvals/${encodeURIComponent(id)}/decision`, {
    method: "POST",
    body: JSON.stringify({
      status,
      actor: userSelect.value || "morgan",
      note: "demo approval decision from dashboard",
    }),
  });
  await refreshApprovals();
  const mesh = await getJson("/agents/status");
  renderAgents(mesh);
}

async function runAgent() {
  runBtn.disabled = true;
  runBtn.textContent = "running locally...";
  try {
    const selectedUser = userSelect.value || "morgan";
    const selectedRole = userSelect.selectedOptions[0]?.dataset.role || "grant_manager";
    const seed = await getJson("/demo/seed", { method: "POST" });
    const result = await getJson("/agent/run", {
      method: "POST",
      body: JSON.stringify({ goal: goalInput.value, role: selectedRole, user_id: selectedUser }),
    });
    const vector = await getJson("/tools/vector_search", {
      method: "POST",
      body: JSON.stringify({ query: goalInput.value, limit: 3 }),
    });
    const pitch = await getJson("/demo/pitch");
    const mesh = await getJson("/agents/status");
    render(result);
    renderAgents(mesh);
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

function connectEventStream() {
  if (!window.EventSource) {
    sseStatus.textContent = "polling";
    return;
  }

  const source = new EventSource("/events/stream");
  source.addEventListener("open", () => {
    sseStatus.textContent = "live";
  });
  source.addEventListener("agent_event", () => {
    getJson("/agents/status").then(renderAgents).catch(() => {});
  });
  source.addEventListener("observability", (event) => {
    renderObservability(JSON.parse(event.data));
  });
  source.addEventListener("error", () => {
    sseStatus.textContent = "reconnecting";
  });
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
userSelect.addEventListener("change", runAgent);
approvalsPanel.addEventListener("click", (event) => {
  const button = event.target.closest("[data-approval][data-decision]");
  if (!button) return;
  decideApproval(button.dataset.approval, button.dataset.decision, button).catch(() => {
    button.disabled = false;
  });
});
loadUsers().then(runAgent).catch(() => {
  userSelect.innerHTML = '<option value="morgan">Morgan · grant_manager</option>';
  runAgent();
});
loadHealth().catch(() => {
  ollama.textContent = "unknown";
});
getJson("/onboarding/flow").then(renderOnboarding).catch(() => {
  onboardingFlow.innerHTML = card("onboarding unavailable", "admin flow did not load.");
});
connectEventStream();
setInterval(() => {
  getJson("/agents/status").then(renderAgents).catch(() => {});
  loadHealth().catch(() => {});
}, 10000);
