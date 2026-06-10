# NextBench v0.2 — Working Status

Scope: NextBench-only. Webdev-model training, BaaB website, and Playground (Phase 2) are tracked in `../CONTEXT.md` and `../RELEASE.md` — do not mix them in.

Last updated: 2026-06-10 (post-eval, post-fix).

## v0.2 is shippable

- **443-task corpus**, 16 categories, fresh full eval against all 12 panel models (no merge math).
- Audit complete: 41 panel-impossible brittleness fixes ([fix_v02_panel_brittleness.py](scripts/fix_v02_panel_brittleness.py)) + 14 tight-max-lines fixes ([fix_v02_tight_max_lines.py](scripts/fix_v02_tight_max_lines.py)) + 7 post-fix saturated tasks retired ([retire_v02_saturated.py](scripts/retire_v02_saturated.py)) + 11 broken source URLs swapped ([fix_v02_broken_urls.py](scripts/fix_v02_broken_urls.py)).
- BaaB Next pretrain-4k-v2 (step-10000) evaluated as ablation; not on public leaderboard (0.2pp below step-8000).
- [LEADERBOARD.md](LEADERBOARD.md) and [REPORT.md](REPORT.md) updated with final v0.2 numbers.
- **Headline:** BaaB Next 1B (Pretrain 2K) at **84.2%, #3 of 12**, inside a 0.22pp top-3 cluster with codestral 22B (#2, 84.3%) and qwen2.5-coder 7B (#4, 84.1%).

---

## Current state

| Dimension | Value |
|---|---|
| Corpus size | **450 tasks** across 16 categories |
| Schema version | `1.0` |
| Benchmark version | `0.2-candidate` (bumps to `0.2` on promote) |
| Grader | `grade.py` — 4 deterministic signals (`pattern_hit`, `no_forbidden`, `regex_hit`, `length_ok`) |
| Panel | 12 models (10 ollama + 2 baab-next-1b litgpt checkpoints) |
| Smoke-test pass | 100% — every task's `ideal_output` scores 4/4 against its own checks |

### Category distribution (post-dedup + v0.2 batches)

```
58 react
54 server-actions
52 nextjs
38 api-routes
32 database
29 auth
25 tailwind
25 hooks
24 form
23 typescript
22 utils
20 middleware
18 payments
12 testing               (new in v0.2)
10 performance           (new in v0.2)
 8 typescript-advanced   (new in v0.2)
```

---

## What this session did (2026-06-09 → 2026-06-10)

1. **Generated batches 002d–f and 003a–k** — 11 capability batches, +118 new tasks across `middleware`, `testing`, `auth`, `server-actions`, `api-routes`, `database`, `performance`, `typescript-advanced`, `nextjs`, `react`, `form`. Three new categories created (`testing`, `performance`, `typescript-advanced`).
2. **Built a self-review rubric** — 6 dimensions (distinctness, false-positive, false-negative, anti-pattern, diagnostic clarity, difficulty calibration) + 6 critique classes. Runs proactively per batch. Caught 6 brittleness / prompt-only-token bugs before they shipped.
3. **Smoke test for v0.1 corpus** — added `smoke_test_ideals.py` + `scan_universal_failures.py`. Found 8 v0.1 universal failures and fixed them (`fix_v01_bugs.py`); each panel model gained +4–6 points.
4. **Dedup audit** — 27 saturated tasks (12/12 model pass) + 50 redundant-cluster tasks → 77 retired via `propose_dedup.py` / `apply_dedup.py`. Recovery log at `retired_v01.jsonl`.
5. **v0.2 panel-failure fixes** — 4 tasks reworked (`edge_runtime`, `form_data_parse`, `signed_url_redirect`, `subdomain_routing`).
6. **Promoted to corpus** — `tasks/` reached 450; all categories pass smoke test.

---

## Running right now (eval batch on the 172 new task_ids)

Identified 172 task_ids in current corpus that aren't in `outputs/*.jsonl` (the pre-dedup snapshot has 355 rows; 77 retired + 172 new added = 450).

Filter file: [new_task_ids_v02.txt](new_task_ids_v02.txt).

| Stream | Script | Status |
|---|---|---|
| Ollama panel (10 models × 172 tasks) | `scripts/run_panel_v02.sh` → `outputs_new/` | qwen3-coder:30b done (7.8 min). qwen2.5-coder:7b mid-run. 8 more queued. ETA ~40 min from start. |
| Baab panel (2 litgpt checkpoints × 172 tasks) | `scripts/run_baab_v02.sh` → `outputs_new/` | Pretrain 2K mid-run (~50 min remaining at CPU speed). Pretrain 4K queued. |
| Log files | `/tmp/panel_v02.log`, `/tmp/baab_v02.log` | Heartbeat lines every 30s. |

`run_eval.py` + `run_eval_litgpt.py` both gained `--task-ids <file>` and `--append` flags this session so the incremental eval is reproducible.

---

## Queued next (post-eval)

1. **Merge outputs** — `scripts/merge_and_regrade_v02.py` joins `outputs/` (drop 77 retired) + `outputs_new/` into `outputs_450/`, overwriting `checks` on each row with the current task's checks so post-promotion fixes take effect.
2. **Re-grade** — run `grade.py` over `outputs_450/` to compute the 450-task leaderboard.
3. **Universal-failure scan** — `scripts/scan_universal_failures.py --outputs-dir outputs_450` to surface any panel-impossible new tasks. Expect 4–6 bugs based on prior batches.
4. **Fix panel-surfaced bugs** — surgical edits to `tasks/*.jsonl`, re-grade.
5. **Update docs** — `LEADERBOARD.md`, `REPORT.md`, `ANALYSIS_v0.1.md` (likely renamed `ANALYSIS_v0.2.md`).

---

## Deferred / mechanical (do before public v0.2 announce)

- [ ] Tag `v0.2` on GitHub
- [ ] Push HF Hub dataset card (see `HF_UPLOAD.md`)
- [ ] `framework_version` + `task_class` (`pattern_knowledge` / `ecosystem_specific`) metadata sweep across all 450 tasks
- [ ] Fix `candidates/v02/scripts/promote_to_corpus.py` `tasks_v02_only/` overwrite bug (writes "w" mode — non-blocking, but ovewrites prior batch promotions)

---

## What lives where (so the next session doesn't have to re-derive)

| File | Role |
|---|---|
| `tasks/*.jsonl` | Canonical 450-task corpus |
| `outputs/*.jsonl` | v0.1 snapshot of model outputs (355 rows, pre-dedup) — kept as historical record |
| `outputs_new/*.jsonl` | v0.2 incremental outputs on the 172 new task_ids (this session) |
| `outputs_450/*.jsonl` | Merged + regraded — produced post-eval. Source of truth for v0.2 leaderboard. |
| `retired_v01.jsonl` | Recovery log of 77 retired tasks (saturated + redundant) |
| `dedup_proposal.json` | The proposal generated by `propose_dedup.py` and applied |
| `candidates/v02/candidates_00{2d,2e,2f,3a..3k}.jsonl` | Source batches that promoted into `tasks/` |
| `scripts/run_panel_v02.sh`, `scripts/run_baab_v02.sh` | Eval launchers (this session) |
| `scripts/merge_and_regrade_v02.py` | Merge old+new outputs, overwrite checks |
| `scripts/scan_universal_failures.py` | Find tokens every model misses → likely bug |
| `scripts/smoke_test_ideals.py` (in `candidates/v02/scripts/`) | Verify ideal_output scores 4/4 on its own checks |
| `STATUS.md` | This file. Update on every state change. |

---

## Open question (parked, decision needed before announce)

- **NextBench standalone domain** — buy `nextbench.dev` / `nextbench.ai`? Deferred until v0.1 / v0.2 has traction (see `../RELEASE.md`).
- **License headline** — corpus is MIT per task metadata, but the leaderboard methodology section in `REPORT.md` should call this out before announce.

---

## After v0.2 ships

Next phase is **BaaB Playground** at `play.baablabs.com` (spec in `../RELEASE.md`, Phase 2) — code editor + completion + Generate button, no auth/billing/chat. Triggers only after NextBench gets attention. Do not start before v0.2 is public.
