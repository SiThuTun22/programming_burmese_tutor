.PHONY: data train eval chat serve serve-api app preflight check smoke smoke-quality test sync sync-data download-adapter upload-adapter

UV ?= uv
PYTHON ?= $(UV) run python

sync:
	$(UV) sync --extra app --extra data --extra train

sync-data:
	$(UV) sync --extra data

data:
	$(PYTHON) scripts/build_book_voice_dataset.py
	$(PYTHON) scripts/validate_dataset.py
	$(PYTHON) scripts/audit_quality.py
	$(PYTHON) scripts/terminology_lint.py
	$(PYTHON) scripts/build_chat_format.py

train:
	$(PYTHON) scripts/train_sft.py

eval:
	$(PYTHON) -u scripts/run_eval_inference.py
	$(PYTHON) scripts/evaluate.py

chat:
	$(PYTHON) scripts/chat.py

preflight:
	$(PYTHON) scripts/preflight_tutor.py

download-adapter:
	$(PYTHON) scripts/download_adapter.py

upload-adapter:
	$(PYTHON) scripts/upload_adapter.py

app: preflight
	$(PYTHON) scripts/serve_gradio.py

serve: app

serve-api:
	$(PYTHON) scripts/serve_api.py

test:
	$(PYTHON) -m pytest tests/ -q

check: test
	$(PYTHON) scripts/validate_dataset.py

smoke:
	$(PYTHON) scripts/smoke_tutor.py

smoke-quality:
	$(PYTHON) scripts/smoke_quality.py
