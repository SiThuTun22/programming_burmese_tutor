.PHONY: sync chat serve serve-api app preflight test smoke-hybrid miit-index

UV ?= uv
PYTHON ?= $(UV) run python

sync:
	$(UV) sync --extra app

preflight:
	$(PYTHON) scripts/preflight_tutor.py

app: preflight
	$(PYTHON) scripts/serve_gradio.py

serve: app

serve-api:
	$(PYTHON) scripts/serve_api.py

chat:
	$(PYTHON) scripts/chat.py

test:
	$(PYTHON) -m pytest tests/ -q

smoke-hybrid:
	$(PYTHON) scripts/smoke_hybrid.py

miit-index:
	$(PYTHON) scripts/build_miit_index.py
