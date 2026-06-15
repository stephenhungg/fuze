# Fuze — Pre-Hackathon Brief

## 1. TL;DR
- **Shipping:** On-prem governed multi-agent hub on Dell GB10 — nonprofit grant reporting as wedge, regulated SMBs as the TAM story.
- **Killer feature:** Role-switch policy denial — same prompt, same model, one role streams, the other gets a line-numbered policy citation. GPU meter proves it's one local box.
- **Win condition:** Live 45-sec role-switch + policy-deny + approval on GB10 with `nvidia-smi` visible. Everything else is supporting cast.

## 2. Slide 1 Hook
> **Fuze: the on-prem agent hub for organizations that can't send their data to OpenAI — governed multi-agent on one GB10, starting with the $200B nonprofit grant economy.**

## 3. The Wow Moment
Split-screen on GB10. Role dropdown: `program_manager` -> ask for donor SSN list -> red card: *"blocked by policy: donor_pii_access requires exec_director, policy.yaml:47"*. Switch to `exec_director` -> same prompt streams a clean draft. Right pane: `nvidia-smi` showing **one** model, one process, VRAM flat. 8 seconds. Unreplicable by any cloud single-agent tool. Close: *"this is what your IT director has been asking for since ChatGPT shipped."*

## 4. Six-Hour Punch List (≤360 min)
- [ ] **Role switcher** in `web/index.html` + `X-Role` header — **30m**
- [ ] **PolicyDenial with file:line citation** in `/query` (THE money shot) — **55m**
- [x] **GB10 terminal proof** (`offline/gb10_proof.sh` -> hostname, nvidia-smi, service status, live `fuze-api` logs) — **35m**
- [ ] **Streaming UI + live GPU meter** side panel (500ms refresh) — **40m**
- [ ] **NemoClaw/OpenClaw adapter** swap (eligibility — non-negotiable) — **60m**
- [ ] **Audit timeline view** (closing beat) — **40m**
- [ ] **3x rehearsal w/ timer + ethernet-unplug dry run** — **35m**
- [ ] **6-slide deck + 60s submission video (role-switch in first 5s)** — **55m**

**Cut from scope:** Google Drive connector, approval queue UI, real identity adapter, event bus, additional verticals. Mock the queue, narrate the agents.

## 5. Three-Minute Demo Script

| Time | Screen | Voiceover |
|---|---|---|
| 0:00-0:15 | Single screenshot: Maria, ED of $2M nonprofit | "Maria runs Hopeworks. One IT person. Board wants SOC2. Cloud agents are off the table." |
| 0:15-0:35 | Dashboard, GB10 pill green, Q2 report task | "This is fuze. Running on the box behind me. Never leaves the building." |
| 0:35-1:05 | Role: `program_manager`. Prompt: donor PII summary. Red denial card with `policy.yaml:47` | "Watch. Same prompt, program manager role. Blocked. Real citation, real line number." |
| 1:05-1:35 | Switch role -> `exec_director`. Same prompt streams. nvidia-smi pinned, GPU spikes, VRAM flat at ~70GB | "Switch to exec director. Same model. Same GPU. Now it streams. One box. One model. Role-scoped governance." |
| 1:35-2:05 | Audit timeline scrolls: retrieval -> policy decision -> draft -> approver -> timestamps | "Every step logged. Funder asks how you generated this — here's the receipt." |
| 2:05-2:25 | **Unplug ethernet.** Toast: offline. Regenerate summary. Still streams. | "Quick proof. Unplugged. Still works. Because it was never reaching out." |
| 2:25-3:00 | Architecture ring: 5 agents around event bus, GB10 underneath | "One box, one model, five governed agents, zero cloud. Thanks." |

## 6. Pitch Deck Outline
1. **Fuze** — on-prem agent hub for orgs that can't send data to OpenAI.
2. **Nonprofits are locked out of agents** — $200B in grants moves on PDFs because data can't leave the building.
3. **Fuze: governed multi-agent on your box** — five agents, shared event bus, one GB10.
4. **The role switch** — same prompt, same model, one role denied with citation, one streams.
5. **Why it only works local** — unified memory lets policy filter context *before* the prompt is built.
6. **Demo recap** — drafted, filtered, approved, audited in 90s on the box in this room.
7. **Ask** — 3 GB10 dev units for design partners, NeMo fine-tuning support, EF intro.

## 7. Top Risks + Mitigations
- **Live 5-stage demo crashes on stage.** -> Hybrid: pre-record downstream agents (auditor/monitor/drafter montage), live ONLY the role-switch + denial + approval. Record full fallback video at 7pm, keep GB10 visible regardless.
- **NemoClaw/OpenShell version drift on demo box.** -> Verify preinstalled versions at 10am, freeze, no `pip install -U` after noon. Pin known-good OpenClaw tag.
- **Reads as "RAG chatbot with extra steps."** -> Lead with Maria human story (15s) before any tech. Story first, governance second. Keep nonprofits as explicit wedge; one line on TAM expansion, don't dilute.

## 8. Ask Organizers at 10am
- Exact **NemoClaw version** preinstalled on demo GB10 — and is it tech-checked or just pitch-mentioned for "stack used" credit?
- **OpenShell policy YAML** — must we use an NVIDIA reference template, or can we author `fuze-policy.yaml` ourselves?
- Can we **pre-pull Ollama models**, or is the box wiped at 10am? (Llama 3.3 70B Q4 = ~40GB download = first hour gone.)
- Are **two GB10s clustered** via 200Gb QSFP available, or single-box only?
- Does **OpenShell `inference.local` routing** to localhost Ollama count as fulfilling the "demo MUST run locally" requirement visibly?
