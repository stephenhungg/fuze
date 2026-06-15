const goalInput = document.querySelector("#goal");
const userSelect = document.querySelector("#user-select");
const runBtn = document.querySelector("#run-btn");
const briefStatus = document.querySelector("#brief-status");
const staffBrief = document.querySelector("#staff-brief");
const skill = document.querySelector("#skill");
const role = document.querySelector("#role");
const identityStatus = document.querySelector("#identity");
const ollama = document.querySelector("#ollama");
const cloudCallEls = document.querySelectorAll("#cloud-calls, [data-cloud-calls]");
const qdrant = document.querySelector("#qdrant");
const alwaysOn = document.querySelector("#always-on");
const contextList = document.querySelector("#context-list");
const identityCard = document.querySelector("#identity-card");
const orgProfile = document.querySelector("#org-profile");
const ingestionStatus = document.querySelector("#ingestion-status");
const vectorMemory = document.querySelector("#vector-memory");
const contextCore = document.querySelector("#context-core");
const pitchProof = document.querySelector("#pitch-proof");
const agentMesh = document.querySelector("#agent-mesh");
const directoryManagement = document.querySelector("#directory-management");
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
const routeViews = document.querySelectorAll("[data-route-view]");
const routeLinks = document.querySelectorAll("[data-route]");
const authForm = document.querySelector("#auth-form");
const authUser = document.querySelector("#auth-user");
const adminAuthForm = document.querySelector("#admin-auth-form");
const adminUser = document.querySelector("#admin-user");
const chatForm = document.querySelector("#chat-form");
const chatThread = document.querySelector("#chat-thread");
let previewMode = false;

function card(title, body, extra = "") {
  return `<article class="card"><strong>${escapeHtml(sentenceCase(title))}</strong><p>${escapeHtml(body)}</p>${extra}</article>`;
}

function linesCard(title, lines, extra = "") {
  return `<article class="card"><strong>${escapeHtml(sentenceCase(title))}</strong>${lines
    .map((line) => `<p>${escapeHtml(line)}</p>`)
    .join("")}${extra}</article>`;
}

function briefCard(label, value, detail, tone = "") {
  return `<article class="brief-card ${escapeHtml(tone)}">
    <span>${escapeHtml(sentenceCase(label))}</span>
    <strong>${escapeHtml(value)}</strong>
    <p>${escapeHtml(detail)}</p>
  </article>`;
}

function sentenceCase(value) {
  const text = String(value);
  return text ? `${text[0].toUpperCase()}${text.slice(1)}` : text;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function setCloudCalls(value) {
  cloudCallEls.forEach((element) => {
    element.textContent = value;
  });
}

async function getJson(url, options = {}) {
  const response = await fetch(url, {
    headers: { "content-type": "application/json" },
    ...options,
  });
  if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
  return response.json();
}

function normalizeRoute(pathname) {
  if (pathname === "/auth" || pathname === "/onboarding" || pathname === "/app" || pathname === "/admin/login" || pathname === "/admin") return pathname;
  return "/";
}

function renderRoute(pathname = window.location.pathname) {
  const route = normalizeRoute(pathname);
  routeViews.forEach((view) => {
    view.classList.toggle("active", view.dataset.routeView === route);
  });
  routeLinks.forEach((link) => {
    const linkRoute = normalizeRoute(new URL(link.href).pathname);
    link.classList.toggle("active", linkRoute === route || (route === "/admin" && linkRoute === "/admin/login"));
  });
  document.body.dataset.currentRoute = route.slice(1) || "landing";
  document.documentElement.dataset.motion = canAnimate() ? "gsap" : "static";
  window.scrollTo({ top: 0, left: 0 });
  animateRoute(route);
}

function navigateTo(pathname) {
  const route = normalizeRoute(pathname);
  if (window.location.pathname !== route) {
    window.history.pushState({}, "", route);
  }
  renderRoute(route);
}

function canAnimate() {
  return Boolean(window.gsap) && !window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

function animateRoute(route) {
  if (!canAnimate()) return;
  const view = document.querySelector(`[data-route-view="${route}"]`);
  if (!view) return;
  window.gsap.killTweensOf(view.querySelectorAll("[data-count-to], .landing-hero-asset, .landing-node"));
  window.gsap.fromTo(
    view,
    { autoAlpha: 0, y: 8 },
    { autoAlpha: 1, y: 0, duration: 0.28, ease: "power2.out", overwrite: "auto" },
  );
  window.gsap.fromTo(
    view.querySelectorAll(
      ".message, .landing-brief, .landing-statement, .landing-band, .landing-system-grid article, .onboarding-board article, .admin-section, .auth-panel, .auth-side",
    ),
    { autoAlpha: 0, y: 10 },
    { autoAlpha: 1, y: 0, duration: 0.32, stagger: 0.035, ease: "power2.out", overwrite: "auto" },
  );
  if (route === "/") {
    animateLanding(view);
  }
}

function animateChat() {
  if (!canAnimate() || !chatThread) return;
  window.gsap.fromTo(
    chatThread.querySelectorAll(".message"),
    { autoAlpha: 0, y: 8 },
    { autoAlpha: 1, y: 0, duration: 0.24, stagger: 0.04, ease: "power2.out", overwrite: "auto" },
  );
}

function animateLanding(view) {
  const image = view.querySelector(".landing-hero-asset");
  const nodes = view.querySelectorAll(".landing-node");

  if (image) {
    window.gsap.fromTo(
      image,
      { scale: 1.1, x: 18, autoAlpha: 0.68 },
      { scale: 1.04, x: 0, autoAlpha: 1, duration: 1.1, ease: "power3.out", overwrite: "auto" },
    );
  }

  window.gsap.fromTo(
    nodes,
    { autoAlpha: 0, y: 14 },
    { autoAlpha: 1, y: 0, duration: 0.55, stagger: 0.08, delay: 0.18, ease: "power2.out", overwrite: "auto" },
  );

  view.querySelectorAll("[data-count-to]").forEach((element) => {
    const target = Number(element.dataset.countTo || 0);
    const state = { value: 0 };
    window.gsap.to(state, {
      value: target,
      duration: 0.9,
      delay: 0.12,
      ease: "power2.out",
      overwrite: "auto",
      onUpdate: () => {
        element.textContent = String(Math.round(state.value));
      },
    });
  });
}

function updateLandingParallax() {
  if (!canAnimate() || document.body.dataset.currentRoute !== "landing") return;
  const image = document.querySelector(".landing-hero-asset");
  if (!image) return;
  const progress = Math.min(window.scrollY / Math.max(window.innerHeight, 1), 1);
  window.gsap.to(image, {
    y: progress * 24,
    scale: 1.04 + progress * 0.025,
    duration: 0.28,
    ease: "power2.out",
    overwrite: "auto",
  });
}

const previewUsers = [
  { id: "morgan", name: "Morgan", title: "Grant Manager", role: "grant_manager", groups: ["cn=grant-team"] },
  { id: "alex", name: "Alex", title: "Executive Director", role: "executive_director", groups: ["cn=executive"] },
  { id: "casey", name: "Casey", title: "Case Manager", role: "case_manager", groups: ["cn=case-management"] },
];

const previewResult = {
  context_packet: {
    skill_label: "Nonprofit Grants",
    role: "grant_manager",
    readiness_score: 72,
    confidence: "high",
    user: { id: "morgan", name: "Morgan", title: "Grant Manager", email: "morgan@harborlight.local" },
    groups: ["cn=grant-team"],
    org_profile: {
      name: "Harbor Light Community Services",
      staff_count: 42,
      volunteer_count: 186,
      active_grants: 7,
      risk_posture: "moderate; high sensitivity around minors, addresses, and case notes.",
    },
    connectors: [
      { label: "microsoft 365 sharepoint", status: "connected" },
      { label: "google drive", status: "connected" },
      { label: "donor crm csv export", status: "watching" },
      { label: "case management secure folder", status: "restricted" },
    ],
    metrics: [
      { label: "may meals served", value: 1284, status: "above target" },
      { label: "may youth attendance", value: 412, status: "above target" },
      { label: "may volunteer hours", value: "missing", status: "waiting on Jordan" },
      { label: "food cost variance", value: "+6.4%", status: "acceptable" },
    ],
    allowed_context: [
      {
        id: "grant_requirements-1",
        title: "anderson reporting requirements",
        source: "grant_requirements.txt",
        text: "anderson foundation report due june 20. include meals served, youth attendance, may volunteer hours, budget variance, and one approved anonymized participant story.",
        citations: ["grant_requirements.txt#chunk-1"],
        metadata: { derived_from: "preview" },
      },
      {
        id: "finance_export_may-1",
        title: "may budget variance",
        source: "finance_export_may.csv",
        text: "may food purchasing ran 6.4 percent over baseline because attendance exceeded forecast. finance marked the variance acceptable.",
        citations: ["finance_export_may.csv#chunk-1"],
        metadata: { derived_from: "preview" },
      },
    ],
    blocked_context: [
      {
        id: "case_notes-1",
        title: "raw case note",
        source: "case_notes.txt",
        redacted_preview: "[redacted] raw case note contains minor identity and address details.",
        reasons: ["restricted role", "pii", "external output blocked"],
      },
    ],
    missing_info: [
      {
        label: "may volunteer hours",
        owner: "Jordan",
        impact: "required by the Anderson Foundation report.",
      },
    ],
    graph_path: ["Anderson Foundation", "Grant Agreement", "Reporting Requirements", "Program Metrics", "Missing Volunteer Hours", "Jordan"],
  },
  tasks: [
    { title: "ask Jordan for May volunteer hours", owner: "Jordan", status: "open", due: "today", priority: "high" },
    { title: "confirm attendance data", owner: "Sarah", status: "open", due: "today", priority: "high" },
    { title: "prepare report outline", owner: "Morgan", status: "ready", due: "jun 20", priority: "medium" },
  ],
  approvals: [
    {
      id: "approval-external-report-export",
      title: "external report export",
      reason: "funder-facing report needs executive review before leaving the org.",
      source: "anderson report packet",
      status: "pending",
      owner_role: "executive_director",
    },
    {
      id: "approval-third-anonymized-story",
      title: "third anonymized story",
      reason: "story is pending program lead approval.",
      source: "story_consent_tracker.csv",
      status: "pending",
      owner_role: "program_lead",
    },
  ],
  drafts: {
    outline: [
      {
        section: "impact summary",
        draft: "Harbor Light exceeded May meal and attendance targets while one volunteer-hours field remains pending.",
        citations: ["program_metrics.csv#may", "grant_requirements.txt#chunk-1"],
      },
    ],
    followups: [
      {
        to: "jordan@harborlight.local",
        subject: "May volunteer hours for Anderson report",
        body: "Can you send the final May volunteer hours today?",
        approval_required: false,
      },
    ],
  },
  audit: {
    goal: "get us ready for the anderson foundation report",
    user: { name: "Morgan" },
    role: "grant_manager",
    groups: ["cn=grant-team"],
    graph_path_traversed: ["Anderson Foundation", "Grant Agreement", "Reporting Requirements", "Program Metrics", "Missing Volunteer Hours", "Jordan"],
    sources_used: ["grant_requirements.txt#chunk-1", "finance_export_may.csv#chunk-1"],
    context_blocked: [{ id: "case_notes-1", reasons: ["pii", "external output blocked"] }],
    model_runtime: { provider: "preview fallback", cloud_calls: 0 },
  },
};

const previewIngestion = {
  status: "preview",
  files_seen: 13,
  chunks_created: 64,
  pii_chunks: 7,
  restricted_files: ["case_notes.txt", "story_consent_tracker.csv"],
  connector_counts: { sharepoint: 5, google_drive: 4, crm_export: 1, secure_case_folder: 3 },
};

const previewContextCore = {
  server: { name: "fuze-context-core", style: "local-mcp", cloud_llm_calls: 0 },
  selected_context: previewResult.context_packet.allowed_context,
  graph_traversal: { path: previewResult.context_packet.graph_path, nodes: previewResult.context_packet.graph_path.map((label) => ({ label })) },
  hybrid_retrieval: {
    rank_fusion: { algorithm: "reciprocal_rank_fusion", rankers: ["dense", "lexical", "graph"] },
    query_plan: { retrieval_stages: ["dense_vector_qdrant", "lexical_sparse_store", "graph_neighbor_expansion", "reciprocal_rank_fusion"] },
    reranked_hits: Array.from({ length: 6 }, (_, index) => ({ chunk_id: `preview-${index}` })),
  },
};

const previewDirectory = {
  source: {
    source: "microsoft entra id / active directory simulator",
    login: "oidc/saml",
    provisioning: "scim 2.0",
    last_sync: "preview",
  },
  groups: [
    { display_name: "executive leadership", mapped_role: "executive_director" },
    { display_name: "grant team", mapped_role: "grant_manager" },
    { display_name: "program staff", mapped_role: "program_lead" },
    { display_name: "case management", mapped_role: "case_manager" },
    { display_name: "volunteer operations", mapped_role: "volunteer_coordinator" },
    { display_name: "board viewers", mapped_role: "board_viewer" },
  ],
};

const previewAccess = {
  user: { name: "Morgan", role: "grant_manager" },
  allowed_count: 28,
  blocked_count: 36,
  decision: "role mapping applied before context packet assembly",
};

const previewMesh = {
  agents: [
    { label: "Index Agent", kind: "memory", status: "watching", description: "keeps local docs, qdrant, and graph memory fresh." },
    { label: "Policy Agent", kind: "governance", status: "ready", description: "blocks pii and role-restricted context." },
    { label: "Grant Readiness Agent", kind: "workflow", status: "running", description: "turns private context into tasks, drafts, and approvals." },
  ],
  events: [
    { agent_id: "index-agent", type: "preview", message: "preview mode is showing the last known demo state", created_at: "static" },
  ],
  event_count: 1,
};

const previewEval = {
  case_count: 3,
  average_score: 1,
  retrieval_contract: "dense+lexical+graph rrf with policy-aware rerank",
  passed: true,
  cloud_llm_calls: 0,
};

function renderPreview() {
  previewMode = true;
  if (!userSelect.options.length) {
    userSelect.innerHTML = previewUsers
      .map((user) => `<option value="${escapeHtml(user.id)}" data-role="${escapeHtml(user.role)}">${escapeHtml(user.name)} · ${escapeHtml(user.role)}</option>`)
      .join("");
    userSelect.value = "morgan";
  }
  setCloudCalls("0");
  ollama.textContent = "gb10 live / preview fallback";
  qdrant.textContent = "gb10 live / preview fallback";
  identityStatus.textContent = "ad/entra simulator";
  alwaysOn.textContent = "preview";
  render(previewResult);
  renderIngestion(previewIngestion);
  renderContextCore(previewContextCore);
  renderDirectory(previewDirectory, previewAccess);
  renderAgents(previewMesh);
  vectorMemory.innerHTML = linesCard("Qdrant preview", ["64 ingested chunks", "nomic-embed-text on gb10"], `<span class="tag">grant_requirements.txt, volunteers.csv</span>`);
  pitchProof.innerHTML = linesCard(
    "Rubric fit",
    ["local-first: gb10 service, local ollama, qdrant, always-on monitor, cloud calls 0", "business value: grant readiness workflow for nonprofit teams"],
    `<span class="tag">frontend preview; live api runs on gb10</span>`,
  );
  renderContextEval(previewEval);
}

async function loadHealth() {
  const health = await getJson("/health");
  setCloudCalls(health.cloud_llm_calls);
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
  userSelect.value = localStorage.getItem("fuze-user") || "morgan";
}

function render(result) {
  const packet = result.context_packet;
  skill.textContent = packet.skill_label;
  role.textContent = packet.role;
  score.textContent = `${packet.readiness_score}%`;
  scoreBar.value = packet.readiness_score;
  confidence.textContent = packet.confidence;
  renderStaffBrief(result);
  renderChat(result);

  identityCard.innerHTML = linesCard("Identity adapter", [
    `${packet.user.name} · ${packet.user.title}`,
    `role: ${packet.role}`,
    `groups: ${packet.groups.join(", ")}`,
  ]);

  orgProfile.innerHTML = [
    linesCard("Org profile", [
      packet.org_profile.name,
      `${packet.org_profile.staff_count} staff · ${packet.org_profile.volunteer_count} volunteers · ${packet.org_profile.active_grants} active grants`,
      packet.org_profile.risk_posture,
    ]),
    linesCard(
      "Systems connected",
      packet.connectors.map((connector) => `${connector.label}: ${connector.status}`),
      `<span class="tag">${escapeHtml(packet.connectors.length)} connectors</span>`,
    ),
    linesCard(
      "Operating metrics",
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
    card("Goal", result.audit.goal),
    card("Identity", `${result.audit.user.name} · ${result.audit.role}; groups: ${result.audit.groups.join(", ")}`),
    card("Graph path", result.audit.graph_path_traversed.join(" -> ")),
    card("Sources used", result.audit.sources_used.join(", ")),
    card("Blocked context", result.audit.context_blocked.map((item) => `${item.id}: ${item.reasons.join("/")}`).join("; ")),
    card("Runtime", `${result.audit.model_runtime.provider}; cloud calls: ${result.audit.model_runtime.cloud_calls}`),
  ].join("");
}

function renderChat(result) {
  if (!chatThread) return;
  const packet = result.context_packet;
  const pendingApprovals = result.approvals.filter((approval) => approval.status === "pending").length;
  const urgentTasks = result.tasks.filter((task) => task.priority === "high").length;
  const missing = packet.missing_info[0];
  const topTasks = result.tasks.slice(0, 3);
  const sourceNames = result.audit.sources_used.slice(0, 4).join(", ");
  chatThread.innerHTML = [
    `<article class="message user-message"><span>${escapeHtml(packet.user.name)}</span><p>${escapeHtml(result.audit.goal)}</p></article>`,
    `<article class="message assistant-message"><span>fuze</span><p>${escapeHtml(`You are ${packet.readiness_score}% ready. I found ${urgentTasks} urgent tasks, ${pendingApprovals} approval gates, and one missing owner update from ${missing.owner}.`)}</p></article>`,
    `<article class="message assistant-message"><span>next actions</span><ul>${topTasks
      .map((task) => `<li><strong>${escapeHtml(sentenceCase(task.title))}</strong><small>${escapeHtml(`${task.owner} · ${task.status} · due ${task.due}`)}</small></li>`)
      .join("")}</ul></article>`,
    `<article class="message assistant-message"><span>policy</span><p>${escapeHtml(`${packet.blocked_context.length} sensitive context item(s) stayed blocked. I can draft inside fuze, but external export waits for executive approval.`)}</p></article>`,
    `<article class="message system-message"><span>local context</span><p>${escapeHtml(`cloud calls: ${result.audit.model_runtime.cloud_calls}; sources: ${sourceNames}`)}</p></article>`,
  ].join("");
  animateChat();
}

function renderStaffBrief(result) {
  const packet = result.context_packet;
  const pendingApprovals = result.approvals.filter((approval) => approval.status === "pending").length;
  const urgentTasks = result.tasks.filter((task) => task.priority === "high").length;
  const blockedCount = packet.blocked_context.length;
  const nextTask = result.tasks[0];
  const missing = packet.missing_info[0];
  briefStatus.textContent = pendingApprovals ? "Needs review" : "On track";
  staffBrief.innerHTML = [
    briefCard("Report readiness", `${packet.readiness_score}%`, "Good enough to draft, still waiting on one key update", "ready"),
    briefCard("Needs attention", `${urgentTasks} urgent task${urgentTasks === 1 ? "" : "s"}`, nextTask ? `${nextTask.owner}: ${sentenceCase(nextTask.title)}` : "No urgent tasks right now", "attention"),
    briefCard("Waiting on", missing.owner, sentenceCase(missing.impact), "waiting"),
    briefCard("Approval queue", `${pendingApprovals} item${pendingApprovals === 1 ? "" : "s"}`, pendingApprovals ? "Review before anything leaves the org" : "Nothing waiting on leadership", "approval"),
    briefCard("Safe sharing", `${blockedCount} blocked`, "Sensitive notes stay inside fuze unless policy allows them", "safe"),
  ].join("");
}

function renderApprovals(approvals) {
  if (!approvals.length) {
    approvalsPanel.innerHTML = card("No approval gates", "Nothing is waiting on a human right now.");
    return;
  }

  approvalsPanel.innerHTML = approvals
    .map((approval) => {
      const closed = approval.status !== "pending";
      const tagClass = closed ? approval.status : "";
      const decision = closed
        ? `<span class="tag ${escapeHtml(tagClass)}">${escapeHtml(sentenceCase(approval.status))} by ${escapeHtml(approval.decided_by)}</span>`
        : `<span class="tag">Pending · ${escapeHtml(approval.owner_role)}</span>`;
      const actions = closed
        ? ""
        : `<div class="approval-actions">
            <button type="button" data-approval="${escapeHtml(approval.id)}" data-decision="approved">Approve</button>
            <button type="button" data-approval="${escapeHtml(approval.id)}" data-decision="rejected">Reject</button>
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

function renderDirectory(data, preview) {
  const mappedGroups = data.groups
    .map((group) => `${group.display_name}: ${group.mapped_role}`)
    .slice(0, 6);
  directoryManagement.innerHTML = [
    linesCard("Directory source", [
      data.source.source,
      `${data.source.login} login · ${data.source.provisioning} provisioning`,
      `last sync: ${data.source.last_sync}`,
    ]),
    linesCard("Group role mappings", mappedGroups, `<span class="tag">${escapeHtml(data.groups.length)} groups</span>`),
    linesCard("Access preview", [
      `${preview.user.name} · ${preview.user.role}`,
      `${preview.allowed_count} allowed · ${preview.blocked_count} blocked for external output`,
      preview.decision,
    ]),
  ].join("");
}

function renderIngestion(result) {
  ingestionStatus.innerHTML = linesCard(
    "Sample ingestion",
    [
      `${result.files_seen} files · ${result.chunks_created} chunks`,
      `${result.pii_chunks} pii chunk(s) · ${result.restricted_files.length} restricted/non-exportable files`,
      Object.entries(result.connector_counts)
        .map(([connector, count]) => `${connector}: ${count}`)
        .join(", "),
    ],
    `<span class="tag">${escapeHtml(result.status)}</span>`,
  );
}

function renderContextCore(result) {
  const sources = result.selected_context.map((item) => item.source);
  const path = result.graph_traversal.path.slice(0, 6).join(" -> ");
  const fusion = result.hybrid_retrieval.rank_fusion;
  const stages = result.hybrid_retrieval.query_plan.retrieval_stages.slice(0, 4).join(" -> ");
  contextCore.innerHTML = [
    linesCard(
      result.server.name,
      [
        `${result.server.style} · cloud calls ${result.server.cloud_llm_calls}`,
        `${fusion.algorithm} · ${fusion.rankers.join("+")}`,
        `${result.hybrid_retrieval.reranked_hits.length} reranked hit(s) · ${result.graph_traversal.nodes.length} graph node(s)`,
        stages,
        path,
      ],
      `<span class="tag">${escapeHtml(sources.join(", ") || "policy-filtered")}</span>`,
    ),
  ].join("");
}

function renderContextEval(result) {
  pitchProof.innerHTML += linesCard(
    "Retrieval eval",
    [
      `${result.case_count} golden case(s) · average ${Math.round(result.average_score * 100)}%`,
      result.retrieval_contract,
      result.passed ? "all cases passed" : "needs review",
    ],
    `<span class="tag">${escapeHtml(result.cloud_llm_calls)} cloud calls</span>`,
  );
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
  runBtn.textContent = "Running locally...";
  try {
    const selectedUser = userSelect.value || "morgan";
    const selectedRole = userSelect.selectedOptions[0]?.dataset.role || "grant_manager";
    const seed = await getJson("/demo/seed", { method: "POST" });
    const ingestion = await getJson("/ingestion/run", { method: "POST" });
    const result = await getJson("/agent/run", {
      method: "POST",
      body: JSON.stringify({ goal: goalInput.value, role: selectedRole, user_id: selectedUser }),
    });
    const vector = await getJson("/tools/vector_search", {
      method: "POST",
      body: JSON.stringify({ query: goalInput.value, limit: 3 }),
    });
    const context = await getJson("/context/query", {
      method: "POST",
      body: JSON.stringify({
        question: goalInput.value,
        role: selectedRole,
        user_id: selectedUser,
        external: true,
        limit: 6,
      }),
    });
    const pitch = await getJson("/demo/pitch");
    const evalResult = await getJson("/context/eval");
    const directory = await getJson("/identity/directory");
    const accessPreview = await getJson(`/identity/access-preview/${encodeURIComponent(selectedUser)}`);
    const mesh = await getJson("/agents/status");
    previewMode = false;
    render(result);
    renderIngestion(ingestion);
    renderContextCore(context);
    renderDirectory(directory, accessPreview);
    renderAgents(mesh);
    vectorMemory.innerHTML = linesCard(
      seed.vector_seed.available ? "Qdrant seeded" : "Qdrant fallback",
      [`${seed.vector_seed.points || 0} points`, seed.vector_seed.embedding_source || vector.embedding_source],
      `<span class="tag">${escapeHtml(vector.hits.map((hit) => hit.chunk_id).join(", ") || "fallback context")}</span>`,
    );
    pitchProof.innerHTML = linesCard(
      "Rubric fit",
      [
        `local-first: ${pitch.rubric_mapping.local_first_always_on}`,
        `business value: ${pitch.rubric_mapping.business_value}`,
      ],
      `<span class="tag">${escapeHtml(pitch.technical_proof[3])}</span>`,
    );
    renderContextEval(evalResult);
  } catch (error) {
    renderPreview();
    sseStatus.textContent = "preview";
  } finally {
    runBtn.disabled = false;
    runBtn.textContent = "Run local agent";
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
    sseStatus.textContent = previewMode ? "preview" : "reconnecting";
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

routeLinks.forEach((link) => {
  link.addEventListener("click", (event) => {
    const url = new URL(link.href);
    if (url.origin !== window.location.origin) return;
    event.preventDefault();
    navigateTo(url.pathname);
  });
});

window.addEventListener("popstate", () => {
  renderRoute();
});

window.addEventListener("scroll", updateLandingParallax, { passive: true });

authForm?.addEventListener("submit", (event) => {
  event.preventDefault();
  const selectedUser = authUser?.value || "morgan";
  localStorage.setItem("fuze-user", selectedUser);
  if (userSelect.options.length) {
    userSelect.value = selectedUser;
  }
  navigateTo("/app");
  runAgent();
});

adminAuthForm?.addEventListener("submit", (event) => {
  event.preventDefault();
  const selectedUser = adminUser?.value || "alex";
  localStorage.setItem("fuze-admin-user", selectedUser);
  navigateTo("/admin");
});

chatForm?.addEventListener("submit", (event) => {
  event.preventDefault();
  runAgent();
});

if (!chatForm) {
  runBtn.addEventListener("click", runAgent);
}
userSelect.addEventListener("change", () => {
  localStorage.setItem("fuze-user", userSelect.value);
  runAgent();
});
approvalsPanel.addEventListener("click", (event) => {
  const button = event.target.closest("[data-approval][data-decision]");
  if (!button) return;
  decideApproval(button.dataset.approval, button.dataset.decision, button).catch(() => {
    button.disabled = false;
  });
});
renderRoute();
loadUsers().then(runAgent).catch(() => {
  renderPreview();
});
loadHealth().catch(() => {
  renderPreview();
});
getJson("/onboarding/flow").then(renderOnboarding).catch(() => {
  onboardingFlow.innerHTML = card("Onboarding unavailable", "Admin flow did not load.");
});
Promise.all([getJson("/identity/directory"), getJson("/identity/access-preview/morgan")])
  .then(([directory, preview]) => renderDirectory(directory, preview))
  .catch(() => {
    renderDirectory(previewDirectory, previewAccess);
  });
getJson("/ingestion/status").then(renderIngestion).catch(() => {
  renderIngestion(previewIngestion);
});
connectEventStream();
setInterval(() => {
  getJson("/agents/status").then(renderAgents).catch(() => {});
  loadHealth().catch(() => {});
}, 10000);
