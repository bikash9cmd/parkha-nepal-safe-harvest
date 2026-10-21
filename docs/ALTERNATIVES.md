# Alternatives considered

Eleven decisions, each with what I chose, what I rejected and when I would change my mind.

## ADR-001: Waiting periods come from a table, not from retrieval over label documents

**Chosen:** a 40-row CSV transcribed from the CIB&RC label claims, looked up by code.
**Rejected:** a Bedrock Knowledge Base over the label PDFs, letting the model read the waiting period out of retrieved chunks.

The label document is a long table where the same product appears on many crops with different
waiting periods. Chlorantraniliprole 18.5% SC is **3 days on tomato and 22 days on brinjal**, in
adjacent rows. Retrieval returns a chunk with both, and the model has to pick the right row; a
wrong pick here is not a hallucination anyone would notice, it is a plausible number. A table
lookup by (product, crop) cannot pick the wrong row.

RAG is still the right tool for the other half of the job: the advisory notes are prose (how to
spot fall armyworm, why you remove wilted brinjal shoots), and the model paraphrasing them is
fine because the gate stops any number or product it adds.

**I'd change this** if the label table had to cover thousands of products: then I'd still keep a
structured store (DynamoDB keyed on product#crop), but build it with an extraction pipeline and
human review, not hand transcription.

## ADR-002: BM25 plus lexicon tags, not embeddings or a vector store

**Chosen:** in-memory BM25 over 13 notes, with a boost for notes tagged with the crop and pest the
lexicon finds in the question. Recall@3 on the 21 eval questions that name a note: 21/21.
**Rejected:**

| Option | Why not now |
|---|---|
| Bedrock Knowledge Base on OpenSearch Serverless | Minimum ~$175/month for one OCU, for 13 documents. 25x the rest of the stack. |
| Bedrock Knowledge Base on S3 Vectors | Cheap storage, but adds a sync job, a second service in every answer's path and a network call, for a corpus that fits in 30 KB of RAM. |
| Titan Text Embeddings V2 in the function | Plausible next step. Cost is tiny (one embedding per question). It would help with paraphrases the lexicon doesn't know, but Nepali and romanised Nepali quality is unmeasured, and the lexicon is needed anyway for the gate. |

The interface is one function (`Corpus.search`), so swapping it is local. **I'd switch** when the
corpus passes a few hundred notes, or when real questions show retrieval misses that a lexicon
entry can't fix.

## ADR-003: Amazon Nova Lite

**Chosen:** Nova Lite through the APAC cross-region profile.
**Rejected:** Nova Pro (about 13x the model cost per token here; $31 vs $7 a month at 10,000
questions), larger third-party models on Bedrock (better Nepali, I expect, but several times the price for an
answer that the gate constrains to four to six sentences), Nova Micro (cheapest; untested on
Nepali, and it would be my first experiment).

The model's job is narrow: call the right tools, paraphrase a note, write short sentences in the
question's language. The gate and the template fallback mean a weaker model produces plainer
answers, not unsafe ones. That is what makes the cheap model a safe choice.

**I'd change this** if `make eval-bedrock` shows a high rewrite or fallback rate in Nepali. The
fallback rate is the metric that decides it, and there is an alarm on it.

## ADR-004: Hybrid routing: arithmetic never goes to the model

**Chosen:** questions the offline router reads as "harvest date" or "ban status" are answered by
templates; only free-form advice goes to Nova Lite.
**Rejected:** every question through the model.

"I sprayed X on Y yesterday, when can I harvest?" has exactly one right answer, computed in code.
A model adds latency, cost and a chance to say it differently and wrongly. On the evaluation set,
43% of answerable questions take the template route, which cuts the Bedrock bill (model plus
guardrail) by the same share: **$10.24 to $7.06 a month** at 10,000 questions. The 43% is my
question mix, not measured traffic.

**The risk:** the router misreads a question and gives a template answer to the wrong question.
It only takes the template route when it found a product, a crop and harvest wording; anything
less goes to the model. The router is scored on its own in the eval (33/33).

## ADR-005: My own gate, with the guardrail once on the question

**Chosen:** ApplyGuardrail on the question only; a deterministic gate on every answer.
**Rejected:**

- *Guardrail attached to every Converse call.* Billed on input and output of every call (three
  per advice question): $34 a month instead of $7 at 10,000 questions, for output checks the gate
  does better.
- *Bedrock contextual grounding check.* It scores whether an answer is supported by the source.
  "22 days" for chlorantraniliprole is supported by the tool results whether it is attached to
  brinjal or to tomato. The question here is not "is this text grounded?" but "is this number
  attached to the right product and crop?", which is a lookup.
- *Bedrock Guardrails Automated Reasoning checks.* Waiting-period rules are the kind of thing it
  is designed for. I haven't evaluated it; I'd test it first on whether it handles Nepali answers,
  since 15 of my 50 questions are Nepali or romanised.

The guardrail still earns its place on the input: denied topics (self-harm, poisoning, cosmetic
spraying), content filters and the prompt-attack filter catch phrasings `guard.py`'s patterns
don't.

## ADR-006: The data ships inside the Lambda package

**Chosen:** `data/` and `corpus/` are copied into the function package (228 KB).
**Rejected:** S3 or DynamoDB with hot reload.

Hot reload would let someone change the ban list without a deploy. That sounds like a feature
and is the opposite: a deploy runs the 50-question eval and the 290-mutation gate test in CI. A
mistyped row (a waiting period of 2 instead of 22) should fail a build, not reach a farmer in
seconds.

**I'd change this** when someone other than a developer maintains the table: then an upload
to S3 that triggers the same evaluation in a pipeline before promotion.

## ADR-007: Indian label claims as the waiting-period source

**Chosen:** CIB&RC *Major Uses of Pesticides*, with Nepal's ban list overriding it.
**Rejected:**

- *Nepal's registered-pesticide lists* give product registrations, not per-crop waiting periods.
- *Codex or EU MRLs* are residue limits, not "days to wait", and would need degradation models.
- *Generic "wait 7 days"* advice is wrong both ways: too long for broflanilide (1 day) and far too
  short for chlorantraniliprole on rice (47 days).

Most insecticides sold in Nepal are Indian-made and carry these claims on the label, so this is
also what the farmer can check on the bottle.

## ADR-008: A JSON API now; Viber and voice next

**Chosen:** an HTTP API that a web page, an agrovet's tablet or a chat bot can call.
**Considered for next:** a Viber bot (widely used in Nepal; the answers are already sized for a
chat bubble), and an IVR voice line for farmers who don't read, which would need Nepali
speech-to-text and text-to-speech and a much shorter answer style. SMS is a poor fit: Nepali
answers in Unicode SMS are 70 characters a segment.

## ADR-009: Lambda zip, not a container

Sodhnus needed a container image because pandas and pyarrow are 250 MB. Parkha's runtime
dependencies are boto3 and nepali-datetime; the package is 228 KB plus those. A zip deploys
faster, starts faster and needs no ECR repository.

## ADR-010: ap-south-1 with the APAC inference profile

Mumbai is the nearest AWS region to Nepal (I haven't measured latency from Nepal). The APAC cross-region profile spreads Nova Lite load across APAC regions, which
raises the effective quota; the IAM policy allows the model in any region for that reason.
Farmer questions are not personal data in the sense that would require in-country storage, and
phone numbers are redacted before logging.

## ADR-011: No photo diagnosis

**Rejected for now:** sending a photo of the damaged plant to Nova's image input and letting it name the pest.

A wrong identification leads to a wrong spray, and pest identification from a phone photo is
exactly where a confident model is least reliable (Tuta absoluta and Liriomyza leaf miners look
alike on a leaf). Parkha asks the farmer to name the crop and pest, and tells them to take the
photo and a sample to the Agriculture Knowledge Centre. **I'd add it** as a suggestion ("this
looks like it could be...; confirm with the AKC") only after measuring it on labelled photos
from Nepali fields.
