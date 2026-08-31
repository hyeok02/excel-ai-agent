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

Set `OPENAI_API_KEY` in `AI/.env` before calling the insight or Agent Planner API.
The Planner model defaults to `gpt-4.1-mini` and can be changed with
`OPENAI_PLANNER_MODEL`.

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
- Swagger UI: `GET /docs`

## Test

```bash
pytest
```
