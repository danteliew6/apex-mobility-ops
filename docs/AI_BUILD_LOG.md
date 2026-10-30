# AI build log: Apex Mobility live operations lakehouse (anonymized)

Evidence of how this build was produced with an AI coding assistant (Claude Code). It is a curated, anonymized record of the
build session, not a verbatim transcript: the original demo was built for a real prospect, so customer-identifying names,
workspace hosts and personal identifiers were replaced ("Apex Mobility"), and all data is synthetic. Per-stage run output is in `evidence/`.

## 1. Selecting and preparing the submission
- Reviewed my demo builds against the FE Bar requirements (Lakeflow pipeline, trained and served ML model, Genie agent, app).
  Chose the ride-hailing operations demo because it covers all of them end to end (Lakeflow Job + DQ pipeline, Unity Catalog
  governance, XGBoost models on Model Serving, Genie, Lakebase, AppKit app, one Declarative Automation Bundle).
- Created an anonymized copy: replaced customer, fleet-brand, email-domain, workspace and personal identifiers, removed logos,
  screenshots, build output and assistant config, then scanned every commit in history for leftovers (clean).
- Published it as a standalone repo and committed each fix separately so the history shows the work.

## 2. Replicating the bundle into a fresh workspace: defects found and fixed
Each fix is its own commit. The AI diagnosed from job/pipeline error output; I reviewed each change.

| # | Symptom | Root cause | Fix |
|---|---|---|---|
| 1 | Pipeline create rejected | Library include path used a single `*` glob | Use `**` |
| 2 | Bootstrap task: `__file__` not defined | Serverless launcher does not define it | Fall back to `sys.argv[0]` |
| 3 | `No module named common` | `runpy.run_path` does not add the script dir to `sys.path` | Add script dir and repo root to `sys.path` |
| 4 | `fact_trip` not found in `gen_bronze` | Task order: bronze reads the table facts creates | Swap task dependencies |
| 5 | Serving-gold SQL parse error | A `;` inside a comment split a statement | Strip comment lines before splitting |
| 6 | MLflow experiment path missing | `/Shared/apex_ml` did not exist | Create the folder |
| 7 | DQ pipeline failed on rerun | Rewritten source tables break a non-append streaming source | Full refresh in the bootstrap job |
| 8 | Governed tables read as empty; ML trained on no rows | Anonymization replaced the admin email in the access allowlist, so the running identity matched no row filter exemption | Add the running identity to the admin allowlist in `gen_dims.py` |
| 9 | Demand-forecast task `NameError: _emit` | Helper defined only in the other training script | Define it |
| 10 | Synced tables blocked | Caller lacks `CREATE CATALOG` on the metastore | Added `lakebase/direct_load.py` fallback (psql COPY into the same `public.*` tables) |
| 11 | App create rejected | Workspace requires Databricks Apps to deploy from a git repo | Deploy from a `fevm-deploy` branch carrying built artifacts and queries retargeted to the workspace catalog |

Result: bootstrap job succeeded (data, DQ pipeline, governance, metric views, both models, serving gold), Genie space and
dashboard deployed, five gold tables loaded into Lakebase Postgres (700 / 886 / 120 / 82,521 / 35 rows), app running.

## 3. Decisions and trade-offs (mine)
- Kept `main` anonymized; workspace-specific values live only on the `fevm-deploy` branch.
- Chose the direct-load Lakebase fallback over waiting for a metastore grant. Trade-off: a one-time snapshot instead of a
  managed sync; documented in `lakebase/direct_load.py`.
- Governance page stays on the SQL warehouse because Unity Catalog masks and row filters do not propagate to Lakebase.
- Outcome figures (no-driver rate, surge) are stated as targets, not measured results, because the data is synthetic.

## 4. How the AI was used
Claude Code did the mechanical anonymization, ran and monitored jobs, read failing task output, proposed and applied the fixes
above, and drafted the form answers and deck. I set requirements, approved outward-facing actions (creating and publishing
the repo, deploying to my workspace), made the design decisions above, and verified results against the workspace.
