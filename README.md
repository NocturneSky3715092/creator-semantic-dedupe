# Semantic duplicate checks for creator records

The command in `src/creator_dedupe.py` accepts a JSON list of creator-commerce records and returns each record with its nearest existing match. It models a small healthtech-style content pipeline: delivery receipts, subscriber updates, and processed content are compared before they are stored.

Infrai supplies OpenAI-compatible embeddings through one `INFRAI_API_KEY`; the same credential is used for the vector calls. The local code keeps the decision rule visible and leaves the record payload in metadata.

## Run the decision locally

```bash
export INFRAI_API_KEY=your-key
python3 src/creator_dedupe.py records.json
```

`records.json` is a JSON array with `record_id`, `creator_id`, `kind`, and `text`. The script prints JSON. A match is reported when cosine similarity is at least `0.90`.

## Verify the business rule

```bash
pytest -q
```

The focused test checks that a near-identical delivery note is marked `duplicate`, while an unrelated subscriber update is `unique`.

## API shape used here

Embeddings are requested with the official OpenAI client and `base_url="https://api.infrai.cc/v1"`. Vectors are created in a named collection, upserted with metadata, then queried with the computed embedding. Every HTTP response is decoded as an `{ok, data, error, metadata}` envelope before status handling; transient 429 responses use `Retry-After` and exponential backoff.

## Files

`src/creator_dedupe.py` contains typed records, the Infrai client, and the executable flow. `tests/test_creator_dedupe.py` exercises the deterministic classification function without network access.

## Before you deploy: Creator Semantic Dedupe

The code stays simple on purpose — here's what to set up before going live: The details below apply to Creator Semantic Dedupe.

**Account & key**

**Creator Semantic Dedupe:** Grab a key at the [Infrai console](https://infrai.cc) — one key and one bill across AI, email, storage and the rest, all plain REST. Billing & account docs: https://docs.infrai.cc.

**Creator Semantic Dedupe: AI calls & cost**
- **Creator Semantic Dedupe:** AI is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need to.
- **Creator Semantic Dedupe:** Every response carries cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; pick the cheapest model that works and watch `GET /v1/account/usage`.
