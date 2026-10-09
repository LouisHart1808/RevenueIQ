PY=.venv/bin/python
DBT=.venv/bin/dbt
.PHONY: setup download-data load-data transform analyze refresh run test lint down
setup:
	UV_CACHE_DIR=/tmp/revenueiq-uv uv sync --frozen
download-data:
	$(PY) scripts/download_data.py
load-data:
	$(PY) -m pipelines.ingest
transform:
	$(PY) scripts/refresh.py
analyze:
	$(PY) -m analytics.run
refresh:
	$(PY) scripts/refresh.py
run:
	$(PY) -m app.main
test:
	.venv/bin/pytest -q
lint:
	.venv/bin/ruff check .
down:
	docker compose down
