---
phase: 1
slug: foundation-router
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-02
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|---------|-------|
| **Framework** | pytest 9.0.2 |
| **Config file** | `tests/pytest.ini` — Wave 0 creates |
| **Quick run command** | `pytest tests/test_router.py tests/test_types.py -v` |
| **Full suite command** | `pytest tests/ -v` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_router.py -v`
- **After every plan wave:** Run `pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 1-01-01 | 01 | 1 | INFRA-01 | unit | `pytest tests/test_types.py -v` | ⬜ W0 | ⬜ pending |
| 1-01-02 | 01 | 1 | INFRA-01 | unit | `pytest tests/test_config.py -v` | ⬜ W0 | ⬜ pending |
| 1-02-01 | 01 | 1 | CORE-01, CORE-02, META-01, META-02 | unit | `pytest tests/test_router.py -v` | ⬜ W0 | ⬜ pending |
| 1-02-02 | 01 | 1 | CORE-03, INFRA-03 | unit | `pytest tests/test_circuit_breaker.py -v` | ⬜ W0 | ⬜ pending |
| 1-02-03 | 01 | 1 | CORE-04 | integration | `pytest tests/test_cli.py -v` | ⬜ W0 | ⬜ pending |
| 1-03-01 | 01 | 1 | OUT-02 (JSONL logging) | integration | `pytest tests/test_logging.py -v` | ⬜ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_types.py` — stubs for SceneType, MainConflict, AgentSpec, RouterResult dataclasses
- [ ] `tests/test_config.py` — stubs for ROI thresholds, max_hops config
- [ ] `tests/test_router.py` — stubs for scene classification, main conflict extraction
- [ ] `tests/test_circuit_breaker.py` — stubs for hop counter, circuit_open error
- [ ] `tests/test_cli.py` — stubs for CLI entry point
- [ ] `tests/test_logging.py` — stubs for JSONL append
- [ ] `tests/conftest.py` — shared fixtures (router instance, sample inputs)
- [ ] `pytest.ini` — config (addopts = -v --tb=short)
- [ ] `pip install pydantic>=2.0` — verify Pydantic 2.x on Python 3.14.3

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|---------|-------------|------------|-------------------|
| Scene classification < 2 seconds | CORE-01 | Needs wall-clock timing of router.analyze() | `python -c "import time; t0=time.time(); Router().analyze('...'); print(f'{(time.time()-t0)*1000:.0f}ms')"` |
| ROI block returns "止亏" | CORE-04 | Requires LLM-simulated ROI-negative scenario | Manual test: `python -m decision_system "要不要免费送鞋给这个0粉丝网红"` |

*All automated: Wave 0 stubs cover unit-level behavior; manual timing/integration tests above*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
