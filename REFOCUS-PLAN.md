# Refocus Plan: Ollama Automation Harness

**Date:** 2025-02-12
**Classification:** Feature Creep
**Verdict:** Refocus — strip scaffolding, sharpen core, ship lean

---

## Problem Statement

76% of the codebase (6,600+ lines) is infrastructure for a product that doesn't exist yet — a distributed, multi-tenant automation service. The actual product is a single-user CLI tool. The core is solid (2,150 lines); the rest is dead weight.

| Layer | Lines | % of Codebase | Integrated? |
|-------|-------|---------------|-------------|
| Core business logic (`core/`) | 1,057 | 12% | Yes |
| Essential utils (config, errors, logger, validation, secrets, version, environment) | 2,963 | 34% | Yes |
| Error tracking (`utils/error_tracking.py`) | 615 | 7% | Yes (6 callsites in `main.py`) |
| **Telemetry + Metrics + Monitoring** | **1,585** | **18%** | **No** (CLI display only) |
| Scripts (deploy, rollback, package, setup, bump) | 2,198 | 25% | Partial |
| CLI (`cli.py`) | 751 | 9% | Yes |

---

## Phase 1: Cut Dead Code (Immediate)

### 1.1 Remove `utils/telemetry.py` (470 lines)

**Why:** Zero calls from the main automation loop. Only used at `cli.py:590` for the `metrics` subcommand display. Defines `track_event()`, `track_command()`, `track_llm_request()`, `track_error()`, `track_performance()` — none of which are ever called during operation.

**Dependencies:**
- `cli.py:590` — `from utils.telemetry import get_telemetry_summary` (remove import, simplify `cmd_metrics`)
- `utils/metrics.py` — telemetry imports from metrics, not the reverse (safe to remove)
- `tests/test_telemetry.py` — remove test file

### 1.2 Remove `utils/metrics.py` (484 lines)

**Why:** Implements Counter, Gauge, Histogram, Timer classes with Prometheus export. This is a metrics registry for a distributed service — not a CLI tool. Only accessed through `cli.py:589` (`cmd_metrics`) and consumed by the telemetry/monitoring modules being removed.

**Dependencies:**
- `cli.py:589` — `from utils.metrics import get_registry` (remove import, replace `cmd_metrics`)
- `utils/telemetry.py` — being removed (Phase 1.1)
- `utils/monitoring.py` — being removed (Phase 1.3)
- `tests/test_metrics.py` — remove test file

### 1.3 Remove `utils/monitoring.py` (631 lines)

**Why:** Health checks, error rate tracking, performance monitoring, alert thresholds. These are service-level observability patterns. Only used at `cli.py:646` for the `status` subcommand. The `check` subcommand (which actually checks system health) does NOT use this module — it has its own implementation in `cli.py:cmd_check()`.

**Dependencies:**
- `cli.py:646` — `from utils.monitoring import get_status` (remove import, replace `cmd_status`)
- `tests/test_monitoring.py` — remove test file

### 1.4 Replace `cli.py` `metrics` and `status` subcommands

**Current:** These import telemetry/metrics/monitoring to display runtime data.

**Replace with:** Minimal stubs that report basic info (version, uptime, log file location, config status). Roughly 40 lines total replacing 130+ lines of integration code.

### 1.5 Remove `docs/openapi-spec.yaml` and `docs/postman/`

**Why:** This is a CLI application. It has zero HTTP endpoints. An OpenAPI spec and Postman collection are misleading — they suggest the tool is a REST service. The `openapi-spec.yaml` header (line 6-8) even acknowledges this: *"While this is a CLI application (not a web service)..."*

**Files to remove:**
- `docs/openapi-spec.yaml`
- `docs/postman/ollama-harness-collection.json`
- `docs/postman/ollama-harness-environment.json`

**Docs to update:** Remove references from `README.md` lines 297-298 (API Collections section).

### 1.6 Remove `pytest-asyncio` from `requirements-dev.txt`

**Why:** The entire codebase is synchronous. Zero async functions, zero `await` statements, zero async test fixtures. This dependency does nothing.

**Net result of Phase 1:**
- **Lines removed:** ~1,585 (utils) + ~400 (tests) + ~100 (cli simplification) + ~17,000 (openapi/postman) = ~19,000+ lines
- **Files removed:** 6 source/doc files, 3 test files
- **Runtime behavior:** Identical for all core operations
- **Lost:** `metrics` and `status` CLI subcommands lose detailed output (replaced with basic stubs)

---

## Phase 2: Trim Over-Scoped Infrastructure (Short-term)

### 2.1 Remove `scripts/deploy.py` (489 lines) and `scripts/rollback.py` (624 lines)

**Why:** Remote SSH deployment and rollback automation for a local CLI tool. `deploy.py` supports deploying to remote hosts via SSH, Docker registries, and PyPI. `rollback.py` maintains deployment backups and restore points. This infrastructure is for a SaaS product, not a pip-installable CLI.

**Keep:** `scripts/bump_version.py` (274 lines), `scripts/package.py` (382 lines), `scripts/setup_wizard.py` (429 lines) — these serve local development/distribution.

**Makefile impact:** Remove or stub `make deploy` and `make rollback` targets if they exist.

### 2.2 Remove enterprise compliance docs

**Files:**
- `docs/compliance-review.md`
- `docs/penetration-test.md`
- `docs/exploratory-testing.md`
- `docs/code-audit.md`

**Why:** Enterprise compliance artifacts for a v1.0 open-source CLI tool with zero production deployments. These add maintenance burden and create an impression of a more mature product than exists.

**Keep:** `SECURITY.md` (vulnerability reporting is appropriate for any public repo).

### 2.3 Simplify `Dockerfile.prod`

**Current:** 106-line multi-stage build with health checks, non-root user, bytecode compilation.

**Replace with:** Single-stage Dockerfile (~30 lines). Keep the regular `Dockerfile` and `docker-compose.yml` for development/testing. A production Docker image is premature — there's no production deployment target.

**Net result of Phase 2:**
- **Lines removed:** ~1,113 (scripts) + compliance docs + Dockerfile simplification
- **Maintenance burden reduced significantly**

---

## Phase 3: Strengthen the Core (Medium-term)

### 3.1 Expand `_infer_action_type()` in `core/safety.py:138-159`

**Current:** Recognizes 8 action types via simple string matching. The permission system's power is gated by this function's ability to map commands to action types.

**Improve:**
- Add regex-based matching
- Recognize `pip install`, `npm`, `apt-get`, `brew` as `install_package`
- Recognize `docker`, `kubectl` commands
- Recognize `ssh`, `scp` as `remote_command`
- Add action type for `format_code` and `lint_code` (currently defined in permissions.yaml but never inferred)

### 3.2 Make permissions more expressive

**Current:** Simple keyword → permission level mapping.

**Add:**
- Glob/regex patterns for dangerous keywords (e.g., `rm -r*` catches `rm -r`, `rm -rf`, `rm -ri`)
- Conditional rules (e.g., "allow git push only to specific branches")
- Project-scoped config (`.ollama-harness.yaml` in project root overrides global)

### 3.3 Add real integration tests

**Current:** 10,923 lines of tests, but everything is mocked. No test actually:
- Calls Ollama (even when available)
- Writes to the sandbox and verifies file content
- Runs a real subprocess and checks the result
- Verifies the end-to-end classify → permission → execute → log pipeline

**Add:** A `tests/integration/` suite that runs with a real Ollama instance (skipped via marker when unavailable). Test the actual pipeline, not just individual mocked units.

### 3.4 Improve interactive UX

**Current:** Bare `input()` prompts with no history, no completion, no color.

**Add:**
- Command history (readline)
- Colored output for decisions/risk levels
- Summary of what the sandbox contains
- `help` command within the interactive loop

---

## Phase 4: Decide the Product's Future (Strategic)

### Option A: Stay as CLI tool
- Cut all remaining service infrastructure
- Focus on pip distribution (`pip install ollama-harness`)
- Add shell integration (pipe support, exit codes, machine-readable output)
- This is the path this plan assumes

### Option B: Evolve into an automation service
- Restore monitoring/telemetry (but actually wire them into the runtime)
- Add HTTP API layer
- Add multi-user support
- This is a different product — fork or major version bump

**Recommendation:** Option A. Ship a focused CLI tool first. The monitoring/service infrastructure can be rebuilt if and when there's a real need — not speculatively.

---

## Summary

| Phase | Action | Lines Cut | Priority |
|-------|--------|-----------|----------|
| 1 | Remove telemetry/metrics/monitoring, OpenAPI/Postman, pytest-asyncio | ~19,000+ | Now |
| 2 | Remove deploy/rollback scripts, compliance docs, simplify Dockerfile.prod | ~1,500+ | This week |
| 3 | Expand action inference, improve permissions, add real tests, improve UX | +500-1,000 | Next sprint |
| 4 | Decide CLI vs service direction | N/A | Before v1.1 |

**After Phase 1+2, the codebase ratio flips:**
- Core + essential utils: ~70% of codebase (was 24%)
- Infrastructure: ~30% of codebase (was 76%)

This is a project that does one thing. Make it do that one thing exceptionally well.
