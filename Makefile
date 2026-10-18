.PHONY: setup test evals run run-verifier run-split docker check

PY ?= .venv/bin/python

setup:
	python3 -m venv .venv
	$(PY) -m pip install -q -r requirements.txt

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
