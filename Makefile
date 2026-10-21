PY ?= python

.PHONY: setup demo serve eval eval-bedrock gate-eval cost test lint validate-infra build

setup:            ## virtualenv with dev dependencies
	$(PY) -m venv .venv && .venv/bin/pip install -r requirements-dev.txt

demo:             ## questions in English, Nepali and romanised Nepali (rules backend, no AWS)
	$(PY) -m parkha ask "I sprayed chlorantraniliprole on my brinjal yesterday. When can I harvest?" --today 2026-10-21
	$(PY) -m parkha ask "hijo cauli ma neem chhareko, kahile tipna milchha?" --today 2026-10-21
	$(PY) -m parkha ask "गोलभेडामा टुटा लाग्यो, के गर्ने?" --today 2026-10-21
	$(PY) -m parkha ask "cabbage diamondback moth what to spray" --today 2026-10-21
	$(PY) -m parkha ask "Is Furadan banned?" --today 2026-10-21

serve:            ## HTTP API on :8000 (try /docs)
	$(PY) -m parkha serve

eval:             ## the 50-question evaluation, rules backend -> eval/results/rules.json
	$(PY) eval/run_eval.py

eval-bedrock:     ## the same set against Amazon Nova Lite (needs AWS credentials and model access)
	$(PY) eval/run_eval.py --backend bedrock

gate-eval:        ## how many wrong answers the safety gate catches, and how many right ones it rejects
	$(PY) eval/gate_mutations.py

cost:             ## monthly cost model behind docs/COST.md
	$(PY) scripts/cost_model.py

test:
	$(PY) -m pytest -q

lint:
	ruff check . && ruff format --check .

validate-infra:   ## lint the SAM/CloudFormation template
	cfn-lint infra/template.yaml

build:            ## the Lambda package (code + label tables + notes) in build/lambda
	./infra/build.sh
