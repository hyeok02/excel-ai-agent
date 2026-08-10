# AI Service

Python service for Excel workbook analysis.

## Local setup

```bash
cd AI
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

## Run

```bash
fastapi dev app/main.py
```

The service runs at `http://localhost:8000`.

- Health: `GET /health`
- Swagger UI: `GET /docs`

## Test

```bash
pytest
```
