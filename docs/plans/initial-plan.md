# Prediction Market Integrity Pipeline — Phased Build Plan

**Scope decision locked in:** batch + streaming pipeline, live alert feed, and one
clean API layer are must-have. OTel, CI, and MLflow are nice-to-have polish —
build them only if Phases 0–8 are done and stable.

Each phase below has a **Definition of Done** — something you can literally run
and look at to confirm the phase works, before moving to the next one. Don't
start a phase until the previous one's DoD passes.

---

## Phase 0 — Environment & Scoping

**Goal:** Nail down historical scope and get free-tier infra actually working
before writing pipeline code.

### Proposed historical scope

Full platform history (~1.3B trades) is not realistic to re-collect from
scratch on a free tier — that scale is what the pre-built public dataset is
for, not a from-scratch pull. `prediction-whale`'s 237K-trade number was
artificially small (capped at 2,000 trades/sub-market by design, not by
availability). Target something in between: uncapped per-market, but bounded
to a deliberately chosen slice.

**Markets:** ~150 markets by all-time volume, split evenly across 3
categories — politics/elections, sports, crypto/finance (BTC/ETH price
markets, Fed decisions). These three categories are the ones the Columbia and
Solidus reports flagged as having the widest range of wash-trading
concentration (sports highest, crypto lowest), so this scope gives a genuine
cross-category comparison to talk about, not just an arbitrary pile of
markets.

**Time window:** full trade history per market, no artificial per-market cap,
no date restriction — avoids the "high-volume markets under-sampled"
limitation the prior project had to honestly disclose.

**Estimated scale:** plausibly 5–20 million trades across the full set
(extrapolating from the prior project's capped sample of a $1B market).
Comfortably past single-machine/pandas territory, legitimately motivating
Spark, while collectible via the free Data API within roughly a week of
incremental, rate-limited background collection.

**Kalshi matched set:** expand from the prior project's 6 hand-confirmed pairs
to roughly 20–30, pulling from the same 3 categories. Don't force matches
where embedding similarity is weak — report whatever number survives manual
confirmation honestly, even if it's lower than 30.

**Streaming scope:** top ~20–30 *currently active* markets by live volume,
refreshed periodically (e.g. daily) rather than a fixed list.

**Market selection method:** programmatic top-N-by-volume cut per category,
not hand-picked — stronger answer if asked how the sample was chosen.

**Fallback tiers** (start at Small, expand only after Phases 1–8 are proven):
| Tier | Markets | Est. trades | Use |
|---|---|---|---|
| Small (safe minimum) | 50 | ~2–5M | Build and debug the pipeline against this first |
| Medium (target) | 150 | ~5–20M | Full proposed scope above |
| Large (stretch) | 300+ | 30M+ | Only if collection goes faster than expected |

### Manual setup steps

**Databricks Free Edition**
- Sign up at databricks.com/learn/free-edition — do **not** use the trial
  signup flow (that one requires a card and bills against cloud costs)
- Create workspace (Free Edition gives one per account, no choice here)
- Unity Catalog: create a catalog + schema for this project (e.g.
  `prediction_markets.bronze`, `.silver`, `.gold`) via the SQL editor or a
  notebook — included by default on Free Edition
- Confirm serverless compute responds: run `spark.range(10).show()` in a new
  notebook

**GitHub — repo + CI**
- Create the repo (public, matching your existing portfolio pattern)
- Settings → Actions → confirm Actions are enabled (default-on for public
  repos, worth checking anyway)
- No secrets needed yet since Polymarket/Kalshi require no auth currently —
  if a Kalshi endpoint later needs a key, add it under Settings → Secrets and
  variables → Actions, never commit it directly

**Databricks ↔ GitHub connection**
- Workspace → Repos → link your GitHub repo via Git integration (Settings →
  Linked accounts → Git provider, generate a GitHub personal access token
  with repo scope, paste into Databricks)
- Lets you edit notebooks as `.py` files with Databricks cell markers
  (`# COMMAND ----------`) under real version control instead of living only
  in the notebook UI

**MLflow**
- No separate signup — built into every Databricks workspace including Free
  Edition. `mlflow.start_run()` in the clustering notebook is enough; runs
  appear under the Experiments tab automatically

**Kalshi API**
- The prior project's script hit `api.elections.kalshi.com` with no auth
  header and it worked, but current rate limits at this larger scope aren't
  independently confirmed — check Kalshi's docs directly before relying on
  it, since an undocumented rate limit is exactly the kind of thing that
  silently truncates a collection run until Phase 1's row-count check fails

**Hosting for the WebSocket listener, API, and dashboard**
- WebSocket listener (Phase 6) runs locally or on a small always-on box, not
  on Databricks, to avoid tripping the serverless fair-use quota
- Railway or Fly.io free tier for anything that needs to stay up 24/7 without
  your laptop being the host — same pattern already used for sed.i, not new
  tooling
- Dashboard (Phase 8): same Vercel/Railway pattern as sed.i
- Do **not** host the dashboard as a Databricks App — Free Edition apps are
  capped at one per account and auto-stop after 24 hours of runtime, needing
  a restart mechanism you don't need if you just reuse the existing
  Vercel/Railway pattern

**Tasks**
- Complete manual setup steps above
- Confirm Polymarket Data API + WebSocket reachable with no auth
- Set up local repo: `src/` layout (ingestor, matcher, features, detector,
  scorer, api), `tests/` mirroring it, pyproject/poetry

**Definition of Done**
- [ ] Can log into Databricks Free Edition workspace, run a trivial notebook
      (`spark.range(10).show()`), confirm serverless compute responds
- [ ] Unity Catalog schema created and queryable
- [ ] GitHub repo linked to Databricks Repos, a test commit shows up in both
      places
- [ ] A single test API call to `data-api.polymarket.com/trades` and the
      WebSocket endpoint both return data locally, saved to disk
- [ ] A single test call against the Kalshi trades endpoint succeeds with no
      auth, rate limit behavior noted
- [ ] Repo skeleton exists with placeholder test files for each module, `pytest`
      runs (even with 0 real tests yet) and exits 0

---

## Phase 1 — Batch Data Collection (ETL)

**Goal:** Re-collect trade history for the scoped historical window, honestly,
with real pagination/error handling — this is the ETL credibility phase.

**Tasks**
- Ingestor module: paginated collection from Data API, threaded/async, retry
  with exponential backoff + max retry count (fix the flat-2-second-sleep gap
  found in the prior project's code)
- Land raw responses as-is (Bronze): JSON/Parquet, one file per market or
  batched, no transformation yet
- Log collection errors to a file, not just stdout

**Definition of Done**
- [ ] Running the collection script end-to-end produces a Bronze dataset on
      disk with a row/file count that matches your logged "trades collected"
      total (no silent data loss)
- [ ] Deliberately kill the process mid-run and restart — it resumes without
      re-fetching everything from scratch (checkpointing works)
- [ ] Deliberately hit a bad market ID / malformed response — script logs the
      error to a file and continues, doesn't crash the whole run
- [ ] Unit tests for the pagination/retry logic pass against a mocked API

---

## Phase 2 — Cross-Platform Market Matching

**Goal:** Reuse and slightly improve the embedding-based matching approach —
same core idea, cleaned up, using Databricks' native Vector Search instead of
a flat scikit-learn cosine-similarity script. This is a cheap, genuine
Databricks-native swap: we're already computing the embeddings, so pointing
them at a managed vector index instead of `sklearn.cosine_similarity` turns a
generic-Python step into one that demonstrates the actual product, not just
Spark-as-a-cluster.

**Tasks**
- Sentence-transformer embeddings for Polymarket + Kalshi event titles
- Load embeddings into a Databricks Vector Search index instead of computing
  a raw cosine-similarity matrix by hand
- Query the index for nearest-neighbor matches with a proper assignment step
  (not pure greedy argmax — use scipy's linear_sum_assignment or similar to
  avoid double-mapping one Kalshi event to multiple Polymarket events)
- Human-reviewed final match list, same as before

**Definition of Done**
- [ ] Vector Search index created and queryable from a notebook
- [ ] Candidate matches file produced with similarity scores, sourced from the
      Vector Search index, not a hand-rolled similarity matrix
- [ ] No Kalshi event appears matched to more than one Polymarket event in the
      final confirmed list
- [ ] You've manually reviewed and confirmed the final match set, documented
      why each was accepted

---

## Phase 3 — Bronze → Silver: Schema Normalization (via Delta Live Tables)

**Goal:** Clean, typed, deduplicated trade data — the unglamorous but real ETL
step that justifies calling this a pipeline instead of a script. Built as a
Delta Live Tables pipeline rather than hand-written orchestration scripts:
this is the single most "Databricks-native" thing in the whole project
(pulled forward from the original Phase 10 polish list, since it's cheap
relative to how much it signals real product familiarity vs. treating
Databricks as a dumb Spark cluster).

**Tasks**
- Define the Bronze → Silver transformation as a DLT pipeline (declarative,
  not a manually orchestrated script)
- Unify Polymarket/Kalshi schemas into one trade table where possible
  (maker/taker perspective, consistent column names/types)
- Use DLT data quality expectations (`@dlt.expect`/`expect_or_drop`) to handle
  nulls/malformed rows explicitly and visibly, instead of silent pandas
  filtering
- Enable Unity Catalog lineage tracking on the pipeline, and actually look at
  it — don't just create a UC schema as a container and never open the
  lineage graph
- Write to Delta table on Databricks

**Definition of Done**
- [ ] DLT pipeline runs end-to-end and appears in the Pipelines UI, not a
      notebook run by hand
- [ ] Silver table exists in Delta Lake with a defined schema (write the schema
      down, don't just infer it ad hoc)
- [ ] At least one DLT expectation is deliberately violated by a bad test row,
      and you confirm it's caught/dropped/logged as expected, not silently
      passed through
- [ ] Row count in Silver + a documented "rows dropped and why" count adds up
      to Bronze row count — no unexplained data loss
- [ ] Unity Catalog lineage graph pulled up and screenshotted, showing
      Bronze → Silver provenance — something you can show in an interview, not
      just claim exists
- [ ] Can query the Silver table from a Databricks notebook and get sane
      aggregates (total volume, trade count, date range) that match your
      Bronze-layer sanity numbers from Phase 1

---

## Phase 4 — Distributed Feature Engineering + Clustering

**Goal:** The actual Spark/Databricks showcase step — replace single-machine
scikit-learn with distributed equivalents.

**Important constraint — read before starting this phase:** Databricks Free
Edition is serverless-only, and serverless compute does not support JAR
libraries or Spark-Context-level extensions in notebooks. GraphFrames
specifically breaks on serverless (confirmed by a Databricks community thread
where staff said classic compute clusters are required — Free Edition doesn't
offer those). **Adjusted plan:** use Spark for the expensive, genuinely
large-scale step — building the wallet co-trading edge table via distributed
groupBy over the full trade history — then export that edge table (much
smaller than raw trades; the prior project had 4.1M edges for 63K wallets)
and run Louvain community detection locally with `networkx`/`python-louvain`.
This is an honest architecture decision to state directly if asked, not a
workaround to hide: Spark builds the graph at scale, community detection runs
single-machine because Free Edition's serverless compute doesn't support
GraphFrames.

**Tasks**
- Wallet-level feature engineering (volume, frequency, timing entropy, buy
  ratio, etc.) via PySpark groupBy/window functions, not a Python for-loop
- Behavioral clustering via Spark MLlib (KMeans or Bisecting KMeans) instead
  of scikit-learn DBSCAN
- Wallet co-trading edge table built via distributed Spark groupBy, exported,
  then community detection (Louvain) run locally via networkx/python-louvain
- Write results to Gold Delta tables

**Definition of Done**
- [ ] Feature engineering job runs as a Spark job (check the Spark UI — confirm
      it's actually using multiple partitions/tasks, not silently collecting
      to driver and running in pandas)
- [ ] Clustering produces a stable result: same input → same cluster
      assignments (or documented seed) across two runs
- [ ] Edge table construction confirmed running as a distributed Spark job
      (again, check the Spark UI, not just wall-clock time)
- [ ] Local Louvain run on the exported edge table produces community
      counts/modularity in the same ballpark as the batch feature numbers (no
      orders-of-magnitude surprises)
- [ ] Time the Spark job — you should be able to say honestly "this took X
      minutes on Y rows," and X should be non-trivial (if it finishes in 2
      seconds on your scoped dataset, your scope might be too small to
      justify Spark)

---

## Phase 5 — Composite Integrity Score (fixed formula, single source of truth)

**Goal:** One documented scoring formula, computed once, with independent
(not double-counted) inputs — directly fixing the README/code mismatch and
correlated-input problems found in the prior project.

**Tasks**
- Define score components from genuinely independent signals: e.g. volume
  concentration (Gini), graph structure (modularity/centralization from
  Phase 4), and a third signal that isn't just another view of the same
  cluster flag
- Write the formula in exactly one place (a single function/config), and
  generate the README/docs section *from* that code, not by hand, so they
  can't drift apart again
- Document weight sensitivity (does the score move a lot under reasonable
  weight changes? say so if yes)

**Definition of Done**
- [ ] Score computed for every market in scope, stored in Gold table
- [ ] A docs-generation script (even a simple one) produces the "how this
      score is computed" text directly from the scoring code/config —
      manually diff them once to prove they can't silently diverge
- [ ] Sensitivity check: rerun with weights perturbed ±20%, log how much the
      score moves, document the range honestly

---

## Phase 6 — Streaming Layer

**Goal:** Live WebSocket ingestion, incremental feature computation, offline/
online parity with the batch baseline.

**Tasks**
- WebSocket listener running locally (not on Databricks, to avoid quota risk),
  writing to a local queue/file
- Scheduled micro-batch job feeding new trades into Databricks Structured
  Streaming, computing the same feature shapes as Phase 4 incrementally
- Compare streaming feature values against the Phase 4 batch baseline for the
  same market/window — this is the feature-store offline/online parity check

**Definition of Done**
- [ ] Local WebSocket listener runs for a sustained period (e.g. 1+ hour)
      without crashing or leaking memory, and the trade count it captures is
      plausible against what you'd expect for that market's activity level
- [ ] A micro-batch successfully lands new streaming data into the same Delta
      table structure as the batch layer (verifiable by querying both from one
      notebook)
- [ ] For a market with both historical and live data, the incrementally
      computed concentration/volume features are close to what a full batch
      recompute over the same window produces (define "close" — e.g. within
      a documented tolerance — and check it, don't just assert it)

---

## Phase 7 — Real-Time Alerting

**Goal:** The alert feed — the single most convincing "this is actually live"
element of the whole project.

**Tasks**
- Detector modules (fresh wallet, size anomaly, coordination-cluster match
  against Phase 4 baseline) each producing a confidence score
- Composite risk scorer combining them — document the weights and, if
  possible, tie the alert threshold to something measurable (e.g. backtest
  against markets already flagged by prior research) rather than an arbitrary
  cutoff
- Dedup logic so the same wallet/market doesn't spam alerts

**Definition of Done**
- [ ] Feed a known historical high-concentration market's trade sequence
      through the detector and confirm it actually fires an alert (a targeted
      test, not just "run it and hope")
- [ ] Feed a normal, low-concentration market through it and confirm it does
      *not* fire (checking for false positives on the easy case)
- [ ] Dedup: same wallet/market combo doesn't generate more than one alert
      within the dedup window, verified by a test

---

## Phase 8 — API Layer + Minimal UI

**Goal:** Expose the pipeline outputs through a real API, and a dashboard that
shows genuinely live data, not hardcoded cards.

**Tasks**
- FastAPI service reading from Gold tables + streaming outputs
- (Optional but recommended, matches your existing pattern) MCP server on top
- Dashboard: market list w/ status badges, market detail w/ live order book +
  concentration time series + baseline reference line, alert feed, visible
  limitations panel

**Definition of Done**
- [ ] API endpoint returns current score + recent alerts for a given market,
      queryable with curl, no hardcoded responses
- [ ] Dashboard's alert feed updates while you watch it, sourced from the same
      alert stream as Phase 7 — confirm by triggering a test alert and seeing
      it appear without a page reload/hardcoded refresh
- [ ] Every number shown in the UI can be traced back to a specific query
      against a specific table — if you can't answer "where does this number
      come from" for any UI element, it doesn't ship

---

## Phase 9 (Nice-to-have) — LLM Resolution-Ambiguity Flagging

**Goal:** The Applied-AI-specific feature — LLM as a structured extraction
component, not a chatbot bolted on. The upgrade here (borrowed from a proper
RAG-eval-harness pattern): the validation check isn't just a one-time report,
it's an actual **deploy gate** — if a pipeline change drops the agreement rate
below a threshold, the new version doesn't ship. That's a real MLOps pattern,
not just "I checked the numbers once."

**Tasks**
- Prompt design for extracting/flagging ambiguous resolution criteria language
  from market descriptions
- Define what "ambiguous" means concretely (vague thresholds, subjective
  judgment calls, missing edge cases) so the task is verifiable, not vibes
- Build a small labeled eval set (markets you've manually judged as clearly
  ambiguous vs. clearly clear) and an eval script that runs this check
  automatically, not just once by hand
- Wire the eval script into the deploy path (even a simple pre-deploy check in
  CI counts) so a regression in agreement rate blocks the update rather than
  silently shipping

**Definition of Done**
- [ ] Eval script runs against the labeled test set and reports agreement rate
      between the LLM's flags and your manual judgment — reported honestly,
      not assumed
- [ ] Deliberately regress the prompt (e.g. revert to a worse version) and
      confirm the eval gate actually blocks/flags the deploy — a targeted
      test of the gate itself, not just the detector
- [ ] Output is structured (not free text) and integrates into the Gold table
      /API, not a separate disconnected script

---

## Phase 10 (Nice-to-have) — Observability, CI

**Only after Phases 0–8 are solid.** (DLT and Unity Catalog lineage were
originally listed here as polish — both moved up into Phase 3, since they're
cheap relative to how much Databricks-native signal they carry. Setup-level
MLflow tracking is already required in Phase 4/9; what's left here is
observability and CI polish.)

- OTel spans on ingestion latency, feature computation time, alert dispatch
  latency — DoD: can pull a trace showing end-to-end latency for one trade
  event through the pipeline
- GitHub Actions running the test suite on push — DoD: a deliberately broken
  test fails the CI check
- MLflow tracking clustering/scoring runs — DoD: can pull up two different
  parameter runs in the MLflow UI and compare their silhouette scores/cluster
  counts side by side

---

## Appendix A — Feature Brainstorm (reference for Phases 6–9)

Beyond core clustering/causality detection, features that add a decision-
support layer:

1. **Real-time execution-cost / liquidity estimator** — from live order book
   depth: "if I buy $X right now, how much does price move / can I fill it."
   Different data path (order book, not trade history) from everything else.
2. **Live concentration alert** — batch-computed historical concentration
   baseline, streaming layer recomputes incrementally and alerts on threshold
   crossing relative to that baseline. This is the feature-store offline/
   online pattern made concrete — build even if nothing else on this list
   makes the cut.
3. **New-market early-warning score** — score a new market's first N trades
   against the shape of historically-flagged markets. Correlational, say so.
4. **Smart-money tracking** — batch-computed historical accuracy score per
   wallet, real-time flag when a historically-accurate wallet opens a large
   new position. Already exists commercially; differentiator is sharing one
   feature pipeline with the manipulation detector instead of being a
   separate tool.
5. **LLM resolution-ambiguity flagging** (Phase 9) — the Applied-AI-specific
   feature, distinct in kind from the rest.
6. **Cross-platform arb edge** — secondary feature riding on the Phase 2
   matching work, net of fees/friction. Not the headline.

**Architecture patterns to borrow, independent of feature choice:**
- Feature store pattern (offline/online parity) — the actual mechanism behind
  features #2 and #3
- MLflow tracking (Phase 10)
- Delta Live Tables — now built into Phase 3 as a required step, not optional
  polish, since it's Databricks' preferred declarative pipeline pattern and
  cheap relative to the signal it carries
- Lambda-architecture reconciliation — explicit job reconciling streaming
  (fast/approximate) against batch (source of truth) recompute

Pick 2 features spanning different data paths + 2 architecture patterns
(feature store + MLflow are cheap and high-signal) rather than spreading
across everything.

---

## Appendix B — Resume / Interview Claims (only claim what's actually verifiable)

**Data engineering**
- Built a distributed batch pipeline (PySpark, Delta Lake) processing [N]
  million transactional records into a Bronze/Silver/Gold architecture
- Implemented Spark Structured Streaming for near-real-time trade ingestion,
  reconciled against batch-computed baselines
- Designed a feature-store pattern with offline/online parity between batch
  and streaming scoring paths
- Orchestrated multi-stage pipeline with checkpointing and failure recovery

**ML / applied analytics**
- Distributed clustering (Spark MLlib) for behavioral archetype detection at
  scale, replacing single-machine scikit-learn approaches that don't
  distribute
- Graph-based community detection on a multi-million-edge transaction graph
  (Spark for edge construction, local Louvain for detection — be ready to
  explain this split honestly if asked)
- Designed and validated an unsupervised anomaly-scoring system with no
  ground-truth labels, including explicit false-positive characterization
- Correlational lead-lag analysis with honest reporting of non-significant
  results, not just positive findings
- Experiment tracking (MLflow) for reproducible parameter tuning

**Applied AI** (if Phase 9 is built)
- Used an LLM as a structured extraction/classification component in a data
  pipeline, not just a chat interface
- Designed prompts for a narrow, verifiable extraction task with a defined
  failure mode

**Software engineering maturity**
- Test coverage per module, not just notebooks
- Threshold/parameter decisions grounded in a cost function or backtest, not
  arbitrary constants
- Consistent, honest documentation — code and docs describe the same
  computation (docs generated from scoring code, not hand-written separately)

**Domain / product**
- On-chain and market-microstructure data analysis (order books, wallet
  behavior, network structure)
- Built for a real, currently-documented problem — cite the Columbia/Solidus
  findings if asked "how do you know this is a real problem"
- Explicit, stated limitations: no ground truth, correlational not causal,
  honestly scoped historical window

**Note:** this list earns interviews by being concretely true and defensible
under follow-up questions, not by its length. Expect exactly the kind of
follow-up the `prediction-whale` code review surfaced — "why doesn't your doc
match your code," "is this actually ML or just a heuristic" — and build with
that expectation from the start.

---

## Notes for working with Claude Code locally

- Do phases in order — later phases assume earlier DoDs actually pass, not
  just "the code ran without an error"
- At the end of each phase, before moving on: re-read this file's DoD list for
  that phase and check off each item explicitly, ideally with the actual
  command/output that proves it, not from memory
- If a DoD check fails, that's information, not a blocker to skip past — note
  what failed and why in a running log, since "what didn't work and why" is
  as useful in an interview as what did
