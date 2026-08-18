# Design Report — Computer-Use Automation System

## 1. Problem

Legacy banking UIs have no API. To automate a task, something has to look at
the screen, figure out what to click, and do it reliably every time after
that — without paying an LLM to "look and think" on every single run.

This system splits that into two phases:

- **Discovery** — an LLM (Claude 3.5 Sonnet, vision) watches screenshots once
  and works out the click-by-click steps needed to reach a goal.
- **Replay** — those steps are saved as a JSON "recipe" (`CapabilityArtifact`)
  and re-run deterministically, with zero LLM involvement, forever after.

Safety and Escalation wrap both phases so a bad or ambiguous step never
silently corrupts data, and never just crashes — it's handed to a human.

## 2. Architecture

```
main.py  ──► DiscoveryAgent ──► BrowserManager (Playwright)
                             ├─► VisionClient (Claude 3.5 Sonnet)
                             └─► ResponseParser ──► CapabilityArtifact (Pydantic) ──► artifacts/*.json

replay.py ──► ReplayEngine  ──► SafetyGuard        (blocks disallowed actions before they run)
                             ├─► ParameterResolver  (${param} substitution + required-param checks)
                             ├─► StepExecutor       (maps one AutomationStep -> one BrowserManager call)
                             ├─► ErrorPolicy        (reads the artifact's own error_handlers)
                             └─► EscalationHandler  (writes evidence/escalations.jsonl on unrecoverable failure)
```

Each class has exactly one responsibility, and each file only imports what it
strictly needs:

| Layer | File | Job |
|---|---|---|
| Browser control | `src/agent/browser.py` | Playwright wrapper — click, type, read, screenshot |
| Vision | `src/agent/vision.py` | Talks to Claude, extracts JSON from its response |
| Parsing | `src/agent/parser.py` | Converts raw Claude JSON into a validated `CapabilityArtifact`; saves/loads artifacts |
| Orchestration | `src/agent/agent.py` | Sequences browser → vision → parser, then verifies discovered steps and requests one live selector repair when needed |
| Schema | `src/artifacts/schema.py` | Pydantic models: the artifact's data contract |
| Parameters | `src/replay/parameter_resolver.py` | Validates required inputs, substitutes `${name}` placeholders |
| Step execution | `src/replay/step_executor.py` | Maps a declarative `action` string to one Playwright call |
| Error handling | `src/replay/error_policy.py` | Looks up an artifact's declared recovery strategy per step |
| Replay orchestration | `src/replay/engine.py` | Runs all steps in order, applies safety/error-policy/escalation |
| Guardrails | `src/safety/policy.py`, `guard.py` | Allowlist of actions, max-steps limit, enforced before execution |
| Redaction | `src/safety/redaction.py` | Masks account/balance-like numbers before logging |
| Human handoff | `src/escalation/handler.py`, `intervention.py` | Appends an audit record and optionally pauses for an operator before retrying |
| Mock target | `target_app/` | Flask banking app (controller → service → repository → DB) used as the automation target |

No file in `src/replay/` imports Claude or the `anthropic` package — that
boundary is the entire point of "replay has zero LLM cost."

## 3. Key Design Decisions

**Pydantic for the artifact schema.** An artifact is untrusted-ish input by
the time it reaches replay (hand-edited JSON, or LLM-produced JSON with
possible mistakes). Pydantic validates its shape at load time instead of
letting bad data reach the browser.

**Deterministic replay is a hard requirement, not an optimization.** Once
discovered, a flow must run the same way every time, with no LLM variability
and no per-run API cost. `ReplayEngine` never imports vision/LLM code.

**Every step declares its own selector strategy (`ElementTarget`).** CSS
selector is primary; XPath/coordinates/accessibility-label exist as fallback
strategies for UIs where a stable CSS hook doesn't exist (common in legacy
apps).

**Error handling is declared per-step in the artifact itself
(`error_handlers`), not hardcoded in the engine.** `ErrorPolicy` just looks up
what the artifact says to do (`retry` / `skip` / `business_outcome` /
`escalate`). If a step has no declared handler, the default is **escalate**
— fail safe, never guess silently.

**Safety is enforced before the browser ever touches a step**, not after.
`SafetyGuard.check_step()` runs before every action; `check_artifact()` runs
once up front to reject an artifact with too many steps (basic DoS/runaway
guard against a malformed or malicious artifact file).

**Sensitive data is redacted at the logging boundary**, not scattered
throughout the codebase as ad-hoc string masking — one function
(`src/safety/redaction.py`), one place to fix if the masking rule ever needs
to change.

**`target_app` uses enterprise-style layering** (Controller → Service →
Repository) with Flask `MethodView` resource classes — one class per URL, one
method per HTTP verb, no `if request.method` branching. This was a deliberate
choice for this assignment (fintech-adjacent take-home) even though the mock
app itself is just a test fixture, not the graded deliverable.

## 4. Trade-offs Considered

- **Flask `MethodView` vs. plain `@route` functions per verb**: chose
  `MethodView` because it keeps one URL → one route registration, and gives a
  single place to later attach cross-cutting decorators (auth, rate limits)
  per resource.
- **Retry inside `ReplayEngine` vs. a separate retry decorator**: kept retry
  logic inline in `_run_step_with_recovery` since it needs access to the
  artifact's declared `ErrorHandler` per step — a generic decorator would
  have needed the same context passed in anyway.
- **`text=View Details` Playwright selector for post-search navigation**:
  the mock app's search results page has no stable CSS id/class on that link,
  so a Playwright text-selector was used as a pragmatic fallback — exactly
  the kind of selector fragility `ElementTarget`'s multiple strategies are
  meant to accommodate in a real legacy app.

## 5. Testing Strategy

- `tests/test_enterprise_layers.py` — `target_app`'s repository/service layer
  against the real SQLite mock DB.
- `tests/test_safety_and_escalation.py` — `SafetyGuard`, redaction,
  `EscalationHandler`, `ErrorPolicy`, all pure-logic, no browser needed.
- `test_agent_modules.py` (repo root, legacy) — exercises the real
  parse → serialize → save → load pipeline using a hardcoded mock Claude
  response, so it validates end-to-end plumbing without an API key. **Known
  issue:** it writes into the real `artifacts/` folder as a side effect, and
  uses `return True/False` instead of `assert`, which is a weaker signal than
  the two test files above.
- Manual end-to-end verification (recorded in this repo's history): running
  `replay.py` against a live `target_app` instance for both the success path
  (`{"status": "success", "outputs": {"balance": "$12750.25"}}`) and a forced
  failure path (confirmed `evidence/escalations.jsonl` gets a real audit
  record written).

Run everything with:
```bash
pytest -q
```

## 6. Known Limitations / Not Yet Done

- **Discovery verification uses example values inferred from the goal** for
  parameterized lookup flows. It stops before human-approval steps and does not
  execute sensitive mutations during discovery.
- **Interactive human handoff is opt-in.** Run replay without `--headless` and
  add `--interactive`; the browser stays open when a step fails, the operator
  performs the suggested action, presses Enter, and the same step is retried.

## 7. How to Run

```bash
# Setup
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
playwright install chromium
cp .env.example .env   # add your ANTHROPIC_API_KEY for discovery only

# Start the mock bank app
python -m flask --app target_app.app run --port 5050

# Discovery (needs ANTHROPIC_API_KEY)
python main.py --goal "Look up member M001 and read their savings balance" \
  --target "http://127.0.0.1:5050/members/search"

# Replay (no API key needed)
python replay.py --artifact artifacts/<file>.json \
  --target "http://127.0.0.1:5050/members/search" --params '{"member_id": "M001"}'

# Replay with human intervention and resume (visible browser required)
python replay.py --artifact artifacts/<file>.json \
  --target "http://127.0.0.1:5050/members/search" \
  --params '{"member_id": "M001"}' --interactive

# Tests
pytest -q
```
