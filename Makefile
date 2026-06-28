# Convenience commands for the AI Mention service.
# Tests can also be run from the repo root with: python -m pytest
# (configured via pytest.ini), or directly with: cd service_engine && python -m pytest -q

.PHONY: install test run verify

install:
	cd service_engine && python -m pip install -r requirements.txt

test:
	cd service_engine && python -m pytest -q

run:
	cd service_engine && python -m engine.main run --input inputs/1billionlinks.json --responses inputs/1billionlinks_responses.csv --order-id 2026-06-28-001 --out outputs

verify:
	cd service_engine && python -m engine.main verify --client-slug 1billionlinks --order-id 2026-06-28-001 --out outputs
