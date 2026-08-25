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

Set `OPENAI_API_KEY` in `AI/.env` before calling the insight API. The default
model is `gpt-5-mini` and can be changed with `OPENAI_MODEL`.

## Run

```bash
fastapi dev app/main.py
```

The service runs at `http://localhost:8000`.

- Health: `GET /health`
- Workbook summary, semantic region detection, blank/merged/style/type/formula-aware
  table boundaries, formula-reference analysis, and
  input/calculation/output/documentation/system sheet classification:
  `POST /api/v1/workbooks/summary`
- LLM-based structured workbook insights:
  `POST /api/v1/workbooks/insights`
- Swagger UI: `GET /docs`

## Test

```bash
pytest
```
