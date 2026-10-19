# AI Service

Python service for Excel workbook analysis.

## Local setup

```bash
cd AI
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
cp .env.example .env
```

Set `OPENAI_API_KEY` in `AI/.env` before calling the insight, Agent Planner, or
workbook Q&A API.
The Planner model defaults to `gpt-4.1-mini` and can be changed with
`OPENAI_PLANNER_MODEL`. Q&A and approval-based Excel update proposals default to
the pinned `gpt-4.1-2025-04-14` snapshot and can be changed with
`OPENAI_QA_MODEL` and `OPENAI_WRITEBACK_MODEL`.

## Run

```bash
fastapi dev app/main.py
```

The service runs at `http://localhost:8000`.

- Health: `GET /health`
- Workbook summary, semantic region detection, single-row and multi-row hierarchical header paths,
  blank/merged/style/type/formula-aware table boundaries, formula-reference analysis, and
  input/calculation/output/documentation/system sheet classification:
  `POST /api/v1/workbooks/summary`
- LLM-based structured workbook insights:
  `POST /api/v1/workbooks/insights`
  - each insight returns fact, verified cause or null, business impact,
    recommendation, source evidence, and confidence
  - deterministic validation verifies exact matches, keeps partial matches visible
    for user review, and removes only results with missing content or evidence
- Registered Agent Tool metadata: `GET /api/v1/agent/tools`
- Structured Agent execution plan from a user intent and workbook:
  `POST /api/v1/agent/plans`
  - multipart fields: `intent`, `file`
  - returns the objective, user value, expected deliverable, evidence requirements,
    success criteria, and ordered Tool steps without executing them
- Execute a structured plan and return per-step success, failure, skipped state,
  Tool output, and source evidence: `POST /api/v1/agent/executions`
- Generate fact, verified cause, impact, recommendation, evidence, and confidence
  from an Agent execution: `POST /api/v1/agent/insights`
  - returns verified, review-needed, and blocked counts without hiding useful partial results
- Ask a natural-language question about one workbook:
  `POST /api/v1/workbooks/questions`
  - multipart fields: `question`, `file`
  - selects registered Agent Tools from the question and returns an answer only when
    the cited sheet and cell evidence exists in the executed Tool results
- Swagger UI: `GET /docs`

## Q&A source handling

- Source fields can be bound by a unique complete label with a unit annotation.
  Explicit currency, scale, year and column selections still constrain the
  answer; selecting a valid source cell does not authorize changing the requested
  unit or performing an exchange-rate conversion. Competing scopes require
  clarification rather than an arbitrary model choice.
- Ambiguous source candidates also expose bounded `clarification_options` for
  the UI. A clicked option sends `context.selection` with `source_question` and
  `option_id`; the current workbook digest, candidate cells and canonical
  question are revalidated before any model call. Candidates preserve the
  original question's operations and constraints; selection only narrows the
  source scope and never grants a verification badge by itself. Saved options
  survive conversation restoration, but expired source files, stale choices and
  cross-file choices cannot execute.
- Two-table joins use typed keys and validate cardinality within the selected
  population. Unmatched left rows and unknown group membership remain visible
  as limited results. Relevant duplicate keys still block the join; additional
  key suggestions come from source columns and are never applied automatically.
- Missing formula caches can be recovered from bounded internal inputs using
  supported arithmetic, conditional aggregates (`SUMIF(S)`, `COUNTIF(S)`,
  `AVERAGEIF(S)`) and exact lookup modes (`INDEX`, `MATCH`, `VLOOKUP`, `HLOOKUP`,
  `XLOOKUP`). Recovered answers retain their input-cell lineage and are marked
  as recalculated, not as original saved Excel results. Unsupported array,
  approximate-match, locale-sensitive or external-data operations remain
  unavailable; `IFERROR` cannot turn unknown inputs into a verified zero.
- Static workbook/sheet-scoped names and supported Excel table references can
  resolve to original rectangular ranges, including table data, headers, totals
  and unambiguous current-row references. The same resolver is used by aggregate
  and lookup functions. Dynamic names, multi-area references, missing/excluded
  sheets, missing calculated-column values and unsupported structured-reference
  syntax stay unavailable. Package metadata has separate size limits; no
  external refresh or workbook rewrite is performed.
- Follow-up hints re-read the current workbook's cited cells, their corresponding
  column headers, section captions and number formats within the existing size
  budget. Wide-table fields are not replaced by the first few columns. Previous
  answer prose is not evidence, and inferred context does not receive
  request-wide verification.
- Q&A retains its bounded prefix index (50,000 populated cells / 10,000 indexed
  rows per sheet), but can stream a selected table's original rectangle when
  that index or the analysis sample is incomplete. Counts, filtered lookups,
  row lists, numeric statistics and bounded value frequencies require a complete
  source scan and request/column/unit checks before receiving verification.
  Hidden rows and native table totals are excluded; unknown values are not zero.
  Partial reads never turn a sampled population into a verified total.
  Inferred tables fail closed at ambiguous repeated/changed headers, subtotal
  markers and numeric-to-text section transitions instead of silently combining
  populations. Explicit hidden-column requests remain supported. Source cell
  coordinates must agree with the scanned row and column, including malformed
  worksheet XML. Small verified header anchors preserve large-range follow-ups
  without treating previous answer prose as evidence.
- Single-table grouped counts and numeric statistics use up to three typed
  source dimensions. Filters run before grouping; sums, means and extrema use
  every matching original row before groups are ranked. Numeric row top/bottom-N
  keeps at most N+1 candidates (N <= 100) while checking every candidate's sort
  value and unit. Group state is bounded to 1,000 groups, 12,000 accumulators and
  512,000 key-label characters. Exceeding a bound discards the partial result.
  Numeric/text/boolean keys stay distinct, blank keys form an explicit group,
  and a blank numeric population is never replaced by zero. Stable ties follow
  source occurrence order; cutoff ties are disclosed. Without an explicit N,
  output is limited to 50 rows/groups with an explicit display-limit notice.
  Grouping dimensions, aggregate operation and ranking direction/count/metric
  are checked independently of the generated plan. Bounded witness rows cannot
  prove a population-wide source-rank permutation.
- Aggregate predicates (`having`) run after the complete filtered population is
  grouped. They do not substitute source-row filters. Shares of numeric sums or
  row counts use the full filtered total before HAVING, ranking and display
  limits. Output includes numerator, denominator and percentage; percentage
  predicates compare exact cross products rather than rounded display values.
  Unknown aggregates, mixed units, negative contributions and zero denominators
  cannot receive a certified share. Independent source-bound request checks
  reject missing/invented stages, metrics, operators or thresholds.
- Exact distinct counts use one to three typed source columns, globally or per
  group. Composite keys are counted as tuples, not independent-column counts.
  Missing/whitespace keys and incomplete tuples are excluded explicitly; unknown
  formula results are not blanks. State is bounded to 100,000 retained keys and
  8,000,000 key characters across all groups. Global counts never sum group counts.
- Per-group top/bottom-N retains at most N+1 candidates per group and checks every
  eligible row. It is separate from ranking group aggregates or globally ranked
  rows. Entity requests require nonblank identities that are unique throughout
  each group, not just among the winners. The common source columns supply those
  identities; no workbook/department/customer names are built into the engine.
  Limits are 1,000 partitions, 10,000 retained rows, 2,000,000 retained value
  characters and 500 displayed rows (whole groups only). Identity proofs are
  bounded to 100,000 keys / 8,000,000 characters. Display omissions and cutoff
  ties are explicit; failed computations discard the entire partial answer.
- Original-source reads share a request-local budget: 2,000,000 rectangular
  cells, 250,000 rows, 16 reads and 20 seconds of source-read work. Exact small
  cell/range requests and bounded follow-up evidence can also read beyond the
  prefix, without merging disjoint reads into a falsely complete index.
  Arbitrary ratios between columns, distinct-count shares, changed denominator
  populations, include-all-ties and ambiguous ranking metrics remain unavailable.
  Entity rankings that require aggregating multiple rows per entity first are
  not substituted with raw-row rankings. Ambiguous table boundaries, missing formula caches and budget exhaustion
  also remain limited/unavailable where full proof is absent.
  This is not unlimited-size upload support: initial workbook parsing still
  loads workbook structure in memory, and generic search, joins and formula
  dependency resolution retain their own existing coverage limits.

These paths do not modify workbooks, execute macros or refresh external links.
Offline tests cover the deterministic execution and verification contracts;
they do not establish the accuracy of a live model's interpretation of every
natural-language question.

## Test

```bash
pytest
```
