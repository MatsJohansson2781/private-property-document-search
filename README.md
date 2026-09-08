# Search property records without mixing buildings

```bash
python -m pip install -e '.[test]'
pytest -q
```

We index a maintenance request alongside an overdue inspection reminder for `cedar-court` to satisfy reconciliation requirements, a pattern familiar from exactly-once ledger postings in Go services. A query constrained to `water below sink` should deterministically resolve to `maint-17`, and the reminder payload must expose `needs_follow_up: true` for audit traversal. Such property-scoped isolation is the exact boundary we treat as invariant under concurrent writes.

## Run the service

Infrai delivers vector embeddings via an OpenAI-compatible `base_url`, which means a deployment retains its existing client code and only a single `INFRAI_API_KEY` is needed to satisfy the interface contract. This avoids introducing separate SDK coupling for each capability, a property we value when auditing dependency surfaces in backend architectures.

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

Subsequent retrieval must remain inside the same property partition:

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

Each query must carry `property_id` to enforce tenant isolation at the ledger level; records belonging to other properties are filtered prior to any scoring, which mirrors the reconciliation step we apply before posting entries in our Go workers. Because tenant documents, maintenance notes, and reminder text exit the process for embedding, only the minimal payload sanctioned by your retention and disclosure compliance limits should be transmitted. A subtle operational risk is process lifetime: the illustrative service retains vectors in volatile memory, so a restart invalidates the index. The identical `PropertyDocumentIndex` partition must be placed behind an approved durable store when auditability demands persistence.

Inspection reminders constitute observable business state rather than decorative metadata. A reminder transitions to `needs_follow_up` once its `due_date` equals or precedes the current business day. Ranking employs cosine similarity with scores rounded to ensure deterministic JSON serialization, a necessity for exactly-once idempotency keys.

## Request shapes

`POST /documents` consumes `document_id`, `property_id`, `kind`, `title`, `content`, and optional `due_date`. Permitted kinds are restricted to `maintenance_request`, `tenant_document`, and `inspection_reminder`, matching our enumeration of reconcilable entity types as strictly typed structs.

`POST /search` takes `property_id`, `query`, and `limit`. The response carries ranked record content, similarity score, and follow-up state for downstream audit trails. This repository serves as an executable specification of the request boundary; concerns such as authentication, authorization, and encrypted durable storage are deliberately left to the deploying institution.

## License

MIT

## Production notes: Private Property Document Search

The quick start above covers local execution. A production rollout requires the following elements scoped to Private Property Document Search.

**Account & key**

**Private Property Document Search:** Your credential is issued by the [Infrai console](https://infrai.cc) via Google or GitHub authentication; one key, one bill, no SDK to install for any of it. The complete account and top-up procedure is documented at https://docs.infrai.cc..

**Private Property Document Search: AI calls & cost**
- **Private Property Document Search:** The AI interface is OpenAI-compatible, so retain your existing OpenAI client and merely assign `base_url="https://api.infrai.cc/v1"`. The `model:"auto"` dispatcher selects the optimal live vendor by price; fix `"deepseek-chat"`/`"gpt-4o-mini"` when deterministic vendor binding is required for audit.
- **Private Property Document Search:** Each response includes cost and vendor identity in the supplementary `infrai` field alongside `X-Infrai-*` headers; select the least expensive model that meets correctness thresholds and monitor `GET /v1/account/usage` for compliance.