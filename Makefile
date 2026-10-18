.PHONY: setup setup-agents test evals run run-verifier run-split run-mcp run-a2a docker check

PY ?= .venv/bin/python

setup:
	python3 -m venv .venv
	$(PY) -m pip install -q -r requirements.txt

# Adds ADK + MCP + A2A for the permit-review use case (needs Python >= 3.11)
setup-agents:
	python3 -m venv .venv
	$(PY) -m pip install -q -r requirements-agents.txt

test:
	$(PY) -m pytest -q

evals:
	$(PY) -m evals.run_evals

run:
	$(PY) -m uvicorn api.main:app --host 127.0.0.1 --port $${PORT:-8000}

docker:
	docker build -t aquacarbon-dc .

check: test evals
	node --check static/app.js

run-verifier:
	$(PY) -m uvicorn verifier_service.app:app --host 127.0.0.1 --port 8100

# API with the verifier as a separate process (start `make run-verifier` first)
run-split:
	VERIFIER_URL=http://127.0.0.1:8100 $(PY) -m uvicorn api.main:app --host 127.0.0.1 --port $${PORT:-8000}

# Permit-review use case (see docs/AGENTIC_REVIEW.md)
run-mcp:
	PYTHONPATH=. $(PY) -m mcp_server.server

run-a2a:
	PYTHONPATH=. $(PY) -m uvicorn a2a_verifier.app:app --host 127.0.0.1 --port $${A2A_PUBLIC_PORT:-8300}
