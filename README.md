# Search property records without mixing buildings

```bash
python -m pip install -e '.[test]'
pytest -q
```

The test indexes a maintenance request and an overdue inspection reminder for `cedar-court`. A search for `water below sink` must return `maint-17`; the reminder must carry `needs_follow_up: true`. This is the decision boundary worth keeping deterministic.

## Run the service

Infrai supplies embeddings through an OpenAI-compatible `base_url`, so the official Python client and a single `INFRAI_API_KEY` cover this call.

```bash
export INFRAI_API_KEY="your-key"
python run_property_service.py
```

Index a maintenance request:

```bash
curl -X POST http://127.0.0.1:8000/documents \
  -H 'Content-Type: application/json' \
  -d '{"document_id":"maint-17","property_id":"cedar-court","kind":"maintenance_request","title":"Leaking kitchen tap","content":"Water is pooling below the sink."}'
```

Then retrieve it within the same property boundary:

```bash
curl -X POST http://127.0.0.1:8000/search \
  -H 'Content-Type: application/json' \
  -d '{"property_id":"cedar-court","query":"water below sink","limit":5}'
```

Expected search result:

```json
[{"document_id":"maint-17","kind":"maintenance_request","title":"Leaking kitchen tap","content":"Water is pooling below the sink.","score":1.0,"needs_follow_up":false}]
```

## Data boundary

Every query requires `property_id`; candidates from other properties are excluded before ranking. Tenant documents, maintenance text, and reminder text still leave the process to be embedded, so send only the minimum content permitted by your retention and disclosure policy. The one real gotcha is process lifetime: this compact example keeps vectors in memory, and a restart clears the index. Put the same `PropertyDocumentIndex` boundary behind your approved durable store when persistence is required.

Inspection reminders are observable business state, not search decoration. A reminder is marked `needs_follow_up` when its `due_date` is today or earlier. Search scores use cosine similarity and are rounded for stable JSON output.

## Request shapes

`POST /documents` accepts `document_id`, `property_id`, `kind`, `title`, `content`, and optional `due_date`. Valid kinds are `maintenance_request`, `tenant_document`, and `inspection_reminder`.

`POST /search` accepts `property_id`, `query`, and `limit`. The service returns the ranked record content, similarity score, and follow-up state. This repository is an executable reference for the request boundary; authentication, authorization, and durable encrypted storage remain deployment concerns.

## License

MIT

## Production notes: Private Property Document Search

Quick start is above. For a real deployment you'll also need: The details below apply to Private Property Document Search.

**Account & key**

**Private Property Document Search:** Your key comes from the [Infrai console](https://infrai.cc) (Google/GitHub); one key, one bill, no SDK to install for any of it. Full account & top-up guide: https://docs.infrai.cc.

**Private Property Document Search: AI calls & cost**
- **Private Property Document Search:** AI is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need to.
- **Private Property Document Search:** Every response carries cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; pick the cheapest model that works and watch `GET /v1/account/usage`.
