# Deploying to AWS

Everything is in [`template.yaml`](template.yaml) (AWS SAM). Region: **ap-south-1** (Mumbai), the
nearest to Nepal (ADR-010 in [docs/ALTERNATIVES.md](../docs/ALTERNATIVES.md)).

## Prerequisites

- An AWS account and credentials (`aws configure`)
- [AWS SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html)
- **Model access for Amazon Nova Lite** in the Bedrock console for ap-south-1 (and the regions the
  APAC inference profile routes to)

## Deploy

```bash
make build                       # code + data/ + corpus/ into build/lambda (about 228 KB)
sam build --template-file infra/template.yaml
sam deploy --guided --region ap-south-1
#   Backend:  hybrid (default), bedrock, or rules for no Bedrock spend at all
#   OpsEmail: to receive alarms and the budget warning (confirm the email AWS sends)
```

## Try it

```bash
API=<ApiUrl from the outputs>
curl -s $API/health
curl -s $API/ask -H 'content-type: application/json' \
  -d '{"question": "हिजो काउलीमा नीम छरें, कहिले टिप्न मिल्छ?"}'
curl -s $API/feedback -H 'content-type: application/json' -d '{"answer_id": "<from /ask>", "helpful": true}'
```

## Evaluate the deployed model

```bash
PARKHA_BEDROCK_REGION=ap-south-1 make eval-bedrock
```

This runs the 50 questions through Nova Lite and writes `eval/results/bedrock.json` with the
rewrite and fallback for each. Set `PARKHA_GUARDRAIL_ID` and `PARKHA_GUARDRAIL_VERSION` (stack
outputs) to include the guardrail.

## Changing the ban list or the label table

Edit `data/*.csv`, then `make test eval gate-eval` locally; CI runs the same. Deploy only from a
green build. The data is in the package on purpose, so this is the only way it changes (ADR-006).

## Changing the guardrail

`AWS::Bedrock::GuardrailVersion` snapshots the guardrail. After editing its policies, change the
version's `Description` so CloudFormation creates a new version; the function reads it from its
environment.

## Tear down

```bash
sam delete
```

## What's verified and what isn't

- `cfn-lint infra/template.yaml` passes, and CI runs it.
- The Lambda handler is tested against mocked DynamoDB (`tests/test_api_handlers.py`): redaction,
  crisis questions not stored, feedback, bad requests. The assembled package in `build/lambda`
  answers a question when imported on its own.
- The Bedrock path (Converse with tool use, ApplyGuardrail, rewrite, every fallback, hybrid routing)
  is tested against a scripted stand-in returning real Converse response shapes.
- **Not done:** deploying the stack and calling Nova Lite. Expect small fixes on a first deploy
  (model access, the inference-profile ARN in the IAM policy, guardrail topic wording).
