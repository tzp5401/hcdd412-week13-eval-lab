# HCDD 412 — Week 13 Starter: Evaluating an AI Feature

A small "AI feature" (a campus FAQ assistant called CampusConnect), a deterministic **mock LLM**, and a working **eval harness**. Your job this week is to treat the assistant like production software: write evals, find a real failure, fix it by changing the prompt, and put an eval gate in CI.

Everything runs on your own machine. No cloud account, no API key, no cost.

## What's in the box

| Path | What it is |
|---|---|
| `app/assistant.py` | The AI feature: retrieve policy lines, build a prompt, call the model, return answer + metadata |
| `app/prompts/v1.txt` | Prompt version 1 (versioned prompts are part of the lesson) |
| `app/data/policies.json` | The six campus policies the assistant may answer from |
| `app/server.py` | Tiny HTTP wrapper (`POST /ask`, `GET /health`) |
| `mock_llm/server.py` | The mock model. **Read its docstring**: it explains exactly how it behaves |
| `evals/cases.jsonl` | Six starter eval cases (you will add more) |
| `evals/run_evals.py` | Eval runner; exits non-zero when the gate fails |
| `tests/` | Unit tests for the plumbing and for the eval harness |
| `docker-compose.yml` | The whole system with one command |

There is deliberately **no `.github/workflows/` folder**. Building the CI pipeline is part of the assignment.

## Quick start — Option A: Docker (recommended; this is also your Week 13 team-project requirement)

```bash
cp .env.example .env
docker compose up --build
```

In a second terminal:

```bash
curl -s -X POST http://127.0.0.1:8000/ask -H "Content-Type: application/json" \
  -d "{\"question\": \"When is the library open on Friday?\"}"
```

(PowerShell: use `Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/ask -ContentType "application/json" -Body '{"question":"When is the library open on Friday?"}'`)

Stop with `Ctrl+C`, then `docker compose down`. See the **Docker Compose Packaging Guide** posted with this week's module for Windows, Mac (Apple silicon), and Codespaces notes.

## Quick start — Option B: plain Python

```bash
python -m venv .venv
# macOS/Linux: source .venv/bin/activate     Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
python mock_llm/server.py          # leave running in one terminal (listens on port 9000)
```

In a second terminal (same virtual environment):

```bash
python evals/run_evals.py
pytest
flake8 app evals tests --max-line-length 100
```

## What you should see first

The starter evals **fail on purpose**: 4 of 6 cases pass, so the gate fails (exit code 1). Two cases ask questions the policies do not cover, and the v1 prompt lets the model invent a confident answer. That is the same failure pattern as this week's reading. Your lab is to prove it with evals, fix it, and keep it fixed.

## How the mock model behaves (so you can reason about it)

- If a policy line supports the question, it answers from that line.
- If nothing supports the question **and** the system prompt says to use only the provided context, it replies that it does not have that information.
- Otherwise it makes up a confident answer.

Real models behave like a noisy version of this. The mock is deterministic so your evals are repeatable.

## The lab in one paragraph

Part 1: add at least 10 more eval cases (including edge cases and out-of-scope questions). Part 2: create `app/prompts/v2.txt`, show with evals that it fixes the failures without breaking passing cases, and set `PROMPT_VERSION=v2`. Part 3: implement `regression_gate()` in `evals/run_evals.py`, un-skip its tests, and add your own. Part 4: build a GitHub Actions workflow that runs unit tests, lint, and evals on every pull request and blocks the merge on failure. Full instructions are in the Week 13 Lab Guide.

## Rules of the road

- Never commit `.env`, API keys, or tokens. If you add a live-model option, it must be optional and keyed from your own environment.
- Keep ports bound to `127.0.0.1` in `docker-compose.yml`. Do not publish the mock LLM.
- Disclose AI assistance in your submission, per the course AI Usage Policy.

*Advanced / for Week 14:* setting `MOCK_COMPLIANCE=naive` makes the mock obey instructions hidden inside retrieved text, simulating a model that is vulnerable to prompt injection. You will use this in the Week 14 pen-test lab. Leave it at `strict` for Week 13.
