.PHONY: sync chat api app web preflight test smoke-hybrid miit-index eval db-up db-migrate db-ingest

UV ?= uv
PYTHON ?= $(UV) run python
NPM ?= npm

sync:
	$(UV) sync --extra app --extra aaa

db-up:
	@echo "Postgres: container programming-tutor-postgres, host port 5435 (see docker-compose.yml)"
	docker compose up -d db

db-migrate:
	$(PYTHON) scripts/aaa_bootstrap.py migrate

db-ingest:
	$(PYTHON) scripts/aaa_bootstrap.py ingest

preflight:
	$(PYTHON) scripts/preflight_tutor.py

api: preflight
	$(PYTHON) scripts/serve_aaa_api.py

web:
	cd web && $(NPM) run dev

app: preflight
	@echo "Starting API on port 8001 and Vite on http://localhost:5173"
	@echo "Run in two terminals: make api && make web"
	@$(MAKE) api

serve-api: api

chat:
	$(PYTHON) scripts/chat.py

test:
	$(PYTHON) -m pytest tests/ -q

smoke-hybrid:
	$(PYTHON) scripts/smoke_hybrid.py

eval:
	$(PYTHON) scripts/eval_tutor.py

miit-index:
	$(PYTHON) scripts/build_miit_index.py
