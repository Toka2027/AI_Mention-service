# Convenience commands for the AI Mention service.
# Tests can also be run from the repo root with: python -m pytest
# (configured via pytest.ini), or directly with: cd service_engine && python -m pytest -q

.PHONY: install install-capture browsers test run verify login smoke capture capture-qa deliver publish-prepare

install:
	cd service_engine && python -m pip install -r requirements.txt

# Operator machine only: real browser capture dependencies.
install-capture:
	cd service_engine && python -m pip install -r requirements-capture.txt

browsers:
	cd service_engine && python -m playwright install chromium

test:
	cd service_engine && python -m pytest -q

run:
	cd service_engine && python -m engine.main run --input inputs/1billionlinks.json --responses inputs/1billionlinks_responses.csv --order-id 2026-06-28-001 --out outputs

verify:
	cd service_engine && python -m engine.main verify --client-slug 1billionlinks --order-id 2026-06-28-001 --out outputs

# --- real browser capture (operator machine) --------------------------------

login:
	cd service_engine && python -m engine.main login --model chatgpt

smoke:
	cd service_engine && python -m engine.main capture --input inputs/1billionlinks.json --order-id 2026-06-28-001 --models chatgpt --smoke

capture:
	cd service_engine && python -m engine.main capture --input inputs/1billionlinks.json --order-id 2026-06-28-001 --models chatgpt --questions 1-25 --resume

capture-qa:
	cd service_engine && python -m engine.main capture-qa --input inputs/1billionlinks.json --order-id 2026-06-28-001 --model chatgpt --questions 1

deliver:
	cd service_engine && python -m engine.main deliver --input inputs/1billionlinks.json --responses inputs/1billionlinks_responses.csv --order-id 2026-06-28-001 --out outputs --require-evidence ChatGPT,Gemini,Perplexity

publish-prepare:
	cd service_engine && python -m engine.main publish-prepare --client-slug 1billionlinks --order-id 2026-06-28-001 --out outputs
