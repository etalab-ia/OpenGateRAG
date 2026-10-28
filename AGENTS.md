# OpenGateRAG

Coding conventions for this repository. OpenGateRAG stores **collections** and **documents** for OpenGateLLM users and searches them. Meilisearch indexes the documents and computes their embeddings.

This file describes the **target** architecture of the revamp. When this repo has no example of a pattern yet, ask the user for input.

Commit messages follow Conventional Commits (`feat:`, `fix(ci):`, `chore:`).

---

## Architecture

```
opengaterag/api/
  domain/<context>/    entities, errors, ports (repository / query / index), views. No FastAPI, SQL, httpx or third-party libs
  use_cases/<area>/    Command, UseCase, UseCaseSuccess, execute()
  infrastructure/
    fastapi/           endpoints, schemas, HTTP exceptions, AccessController, routes.py (RouterName, EndpointRoute)
    postgres/          models.py, Postgres*Repository / Postgres*Query, AutocommitSession
    meilisearch/       MeilisearchChunkIndex, index bootstrap, filter builder
    opengatellm/       OpenGateLLMAuthenticatedUserQuery (GET /v1/me)
    text/              document parser (PyMuPDF, html-to-markdown), text splitter (LangChain), tokenizer (tiktoken)
    configuration.py   Settings + get_configuration(). Read lazily: never at import time outside main.py / alembic/env.py
    context.py         GlobalContext: process-wide handles (engine, shared httpx clients)
    logging.py         configure_logging(). Modules use logging.getLogger(__name__)
  app.py               create_app: router registration, monitoring, unified docs
  dependencies.py      DI factories
  lifespan.py          builds GlobalContext, runs the Meilisearch bootstrap, closes clients
opengaterag/docs/      unified Swagger/ReDoc merging the OpenGateLLM schema (unchanged)
```

**Dependency rule:** `infrastructure → use_cases → domain`. A domain port never mentions Meilisearch, Postgres or OpenGateLLM types.

### Domain map

| Context | Entities / views | Ports → adapters |
|---|---|---|
| `collection` | `Collection`, `CollectionVisibility`, `CollectionView` (+ document count) | `CollectionRepository` → `PostgresCollectionRepository`, `CollectionQuery` → `PostgresCollectionQuery` |
| `document` | `Document`, `Chunk` (internal value object, never exposed as a resource) | `DocumentRepository` → `PostgresDocumentRepository`, `DocumentParser`, `TextSplitter`, `Tokenizer` → `infrastructure/text/` |
| `search` | `SearchMethod`, `MetadataFilter`, `SearchResult` | `ChunkIndex` → `MeilisearchChunkIndex` |
| `user` | `User` (storage limit, public-collection right), `AuthenticatedUserView` | `UserRepository` → `PostgresUserRepository`, `AuthenticatedUserQuery` → `OpenGateLLMAuthenticatedUserQuery` |

### Domain rules

- A user **reads** their own collections and every public collection, including the documents in them and search over them. A user **writes** only to collections they own.
- A collection the user cannot read returns `CollectionNotFoundError`, never a "forbidden" error, so the API does not reveal that another user's private collection exists. The same applies to documents.
- Making a collection public requires `user.create_public_collection`.
- Storage = the sum of document sizes in tokens across the user's collections. Check `current + new document <= storage_limit`, where `null` means unlimited, **before** writing anything.
- The `user` row is upserted on the user's first write with `settings.storage_default_limit`. Existing rows, including raised limits, are never overwritten. `collection.user_id` is the OpenGateLLM user id, with no foreign key to `user`.

---

## API surface

| Route | Verbs |
|---|---|
| `/v1/collections` | `POST`, `GET` (paginated) |
| `/v1/collections/{collection_id}` | `GET`, `PATCH` (full replacement), `DELETE` |
| `/v1/documents` | `POST` (multipart, file required), `GET` (paginated) |
| `/v1/documents/{document_id}` | `GET`, `DELETE` |
| `/v1/search` | `POST` |

There are **no chunk endpoints**. Chunks are an internal detail of indexing: they have no id in the API and cannot be listed, fetched, added or deleted. A search result carries `content`, `score`, `document_id`, `collection_id` and `metadata`. It is not an addressable resource.

**Read endpoints never call Meilisearch.** Document counts, sizes and chunk counts are stored in Postgres when a document is written.

---

## Meilisearch

**Terminology.** "Document" always means an OpenGateRAG document, which is a Postgres row. A Meilisearch record is a **chunk**, and a search match is a **hit**. Keep Meilisearch's word "document" inside the SDK and HTTP calls of `infrastructure/meilisearch/`.

**One index for all chunks** (`dependencies.meilisearch.index_name`), not one index per collection. Each record:

```json
{ "id": "42-0", "collection_id": 7, "document_id": 42, "position": 0, "content": "...", "metadata": { "source_title": "..." } }
```

- `id` = `<document_id>-<position>`. Meilisearch ids accept only `[A-Za-z0-9_-]`.
- `searchableAttributes` = `["content"]`, so keyword search never matches ids or metadata. `filterableAttributes` covers `collection_id`, `document_id` and the metadata fields. `index_language` maps to `localizedAttributes` on `content`.
- Every search filters on `collection_id IN [...]`, computed from the collections the user can read. Request ids are intersected with that list, never trusted as sent.

**Embedding is done by Meilisearch.** A `rest` embedder calls OpenGateLLM's `/v1/embeddings` (`"input": ["{{text}}", "{{..}}"]`, `"data": [{"embedding": "{{embedding}}"}, "{{..}}"]`). OpenGateRAG never calls `/v1/embeddings` and never sends `_vectors`.

- The embedder `url` is resolved **from the Meilisearch container**, so it is configured separately from `opengatellm.url`.
- The embedder authenticates with a dedicated OpenGateLLM **service key**. Embedding consumption is therefore not billed to the caller's key, and search responses have no `usage` field.
- `documentTemplateMaxBytes` defaults to **400** and silently truncates the text sent to the embedder. Derive it from the maximum chunk size (characters × 4 bytes), and keep that maximum within the embedding model's context.

**Bootstrap** (`lifespan.py`) creates the index and its settings when they are missing. When the index already exists and its embedder settings (`source`, `url`, `request`, `response`, `dimensions`, `documentTemplate`, `documentTemplateMaxBytes`) differ from the configuration, the API **refuses to start** and names the fields that differ. Most of these changes make Meilisearch re-embed every chunk, so a restart must never trigger that. Do not compare `apiKey`: Meilisearch returns it partially hidden.

**Tasks.** Meilisearch writes are asynchronous. A `ChunkIndex` method returns only after its task has finished (bounded wait, `task_timeout`). Task uids never leave the adapter. A failed task with a known `error.code` maps to a domain error, and an unknown code is raised. Meilisearch processes an index's tasks in the order they were enqueued, so a compensating delete enqueued after a timed-out add still wins.

**Search mapping** (adapter only):

| Domain | Meilisearch |
|---|---|
| `lexical` | no `hybrid` parameter, so the query is not embedded |
| `semantic` / `hybrid` | `hybrid: {embedder, semanticRatio: 1.0 / 0.5}` |
| `score_threshold` | `rankingScoreThreshold`, with `showRankingScore: true` (valid for every method) |
| metadata `eq` / `sw` / `co` | `=` / `STARTS WITH` / `CONTAINS` (experimental `containsFilter`, which bootstrap checks) |

`rff_k` and `ew` (ends with) have no Meilisearch equivalent and are removed. Never post-filter hits in Python. Filter strings are built by one function in the adapter that quotes and escapes values. Metadata keys are validated against a pattern at the HTTP boundary. `offset + limit` cannot exceed `pagination.maxTotalHits` (1000 by default).

### Two stores, no transaction

Postgres is the source of truth for ownership and access. Meilisearch holds the searchable chunks. **Never hold a Postgres transaction open across a Meilisearch call**, because indexing waits on embedding.

- **Create document:** check collection → parse → count tokens → check storage → split → insert row (committed) → index chunks. If indexing fails, enqueue a delete of the document's chunks, delete the row, and return the error.
- **Delete document or collection:** delete the chunks in Meilisearch and wait, **then** delete in Postgres. If the Postgres delete fails, the result is a document without chunks, which is visible and can be deleted again. The reverse order would leave chunks without a document: content the user believes is deleted but that search can still return.

---

## Naming

| Kind | Pattern | Example |
|---|---|---|
| Use case file / class | `_<verb><noun>usecase.py` / `<Verb><Noun>UseCase` | `_createdocumentusecase.py` / `CreateDocumentUseCase` |
| Command / success | `<Verb><Noun>Command` / `<Verb><Noun>UseCaseSuccess` | `CreateDocumentCommand` |
| Domain error | `<Noun><Problem>Error` | `CollectionNotFoundError`, `StorageLimitExceededError` |
| Port file | `_<noun>repository.py`, `_<noun>query.py`, `_<noun>index.py` | `_chunkindex.py` |
| Adapter file | `_<tech><noun><kind>.py` (singular) | `_postgresdocumentrepository.py`, `_meilisearchchunkindex.py` |
| HTTP exception | `<Noun><Problem>HTTPException` | `CollectionNotFoundHTTPException` |
| Request body / response | `Create<Noun>Body`, `Update<Noun>Body` / `<Noun>Response`, `<Noun>sResponse` | `CollectionsResponse` |
| DI factory | `<verb>_<noun>_use_case_factory` | `create_document_use_case_factory` |

Verbs: `Create`, `Update`, `Delete`, `GetOne` (by id), `Get<Plural>` (list). Never `Get<Noun>` for a single resource.

## Code

- **Entities** are Pydantic `BaseModel`. **Errors, commands and successes** are `@dataclass`.
- **Use cases:** one file per operation. Domain errors are **returned, never raised**. The whole flow sits in `execute()` and branches with `match`/`case`. A step may be extracted into a method that returns `Value | Error`, as long as `execute()` does the `match`. From `execute()` alone, a reader must see every path a request can take. Helpers are `@staticmethod`s on the class, not module functions.
- **Repositories** return `Entity | DomainError`. They map only known `IntegrityError` constraint names and re-raise any other. Never `text(f"...")` an `ORDER BY`: map the sort enum to a column.
- **Auth:** `AccessController` is a `Security` dependency that returns the `AuthenticatedUserView`. Endpoints take it as a parameter and pass `user.id` into the command. There is no request-scoped global.
- **Endpoints** are thin: build the command, call `execute()`, `match` the result, and map each error to its HTTP exception in `infrastructure/fastapi/endpoints/exceptions.py`. Never wrap a use case in `try/except Exception`.
- **Routes:** `RouterName` (switchable routers + `module_path`) and `EndpointRoute` (mount paths) are separate enums. Never build an `EndpointRoute` from a `RouterName`. A module without a `RouterName` member is never imported.
- **Responses** carry `object` (`"collection"`, `"document"`, `"search_result"`, `"list"`). Paginated lists are `{object: "list", total, offset, limit, data}`. Build them with `Response.model_validate(entity, from_attributes=True)`, never a hand-written mapper. Foreign keys are `*_id` (`user_id`, not `owner`). Timestamps are Unix `int` in the API and timezone-aware UTC `datetime` everywhere else.
- **`Update<Noun>Body` is a full replacement:** every persisted field is required.
- **Sessions:** `get_postgres_session` (transactional) serves collection CRUD and reads. `get_autocommit_postgres_session` serves every use case that calls Meilisearch (create/delete document, delete collection, search). Choose in the DI factory, and never mix the two in one use case.
- **HTTP clients** (Meilisearch, OpenGateLLM) are shared `httpx.AsyncClient`s created in the lifespan, not one client per request. The official `meilisearch` Python client is synchronous and would block the event loop.
- **Imports:** relative single-dot imports only for siblings and `__init__.py` re-exports, absolute imports everywhere else. A module never imports from its own package root.

## Reference implementations

The first slice of each pattern. Copy it when adding the same kind of code. Paths are relative to `opengaterag/api/` unless they start with `.github/`.

| Pattern | Reference |
|---|---|
| Domain context (entities, view, errors, ports) | `domain/collection/` |
| Use case | `use_cases/collections/_createcollectionusecase.py` |
| Postgres repository | `infrastructure/postgres/_postgrescollectionrepository.py` |
| Postgres query (view) | `infrastructure/postgres/_postgrescollectionquery.py` |
| Read-access check in a use case | `use_cases/collections/_getonecollectionusecase.py` (`Collection.is_readable_by`) |
| HTTP adapter on a shared client | `infrastructure/opengatellm/_opengatellmauthenticateduserquery.py` |
| Endpoint, error mapping, auth | `infrastructure/fastapi/endpoints/collections.py`, `accesscontroller.py` |
| DI factory | `create_collection_use_case_factory` in `dependencies.py` |
| Unit use case test | `tests/unit/use_case/collections/test_createcollectionusecase.py` |
| Unit domain test | `tests/unit/domain/collection/test_collectionentities.py` |
| Integration endpoint / Postgres tests | `tests/integration/endpoints/test_get_one_collection.py`, `tests/integration/postgres/` |

---

## Tests

`.github/workflows/run_tests.yml` runs two jobs on pull requests: unit (which also writes the coverage badge `.github/badges/coverage.json`: CI writes that file, never edit it by hand) and integration (Postgres from `compose.example.yml`; add Meilisearch with its first slice).

> **TODO: no e2e job yet.** The e2e OpenGateLLM (`.github/tests/config.opengatellm.yml`) embeds through the Albert API and needs an `ALBERT_ADMIN_API_KEY` Actions secret. Add the job back once that secret is set.

Integration tests create the `TEST_POSTGRES_URL` database (default `postgresql+asyncpg://postgres:changeme@localhost:5432/opengaterag_test`) from the models, and roll back every test.

| Layer | Path | Covers |
|---|---|---|
| Unit use case | `opengaterag/api/tests/unit/use_case/<area>/` | every distinct `execute()` branch. Ports are mocked with `create_autospec(Port, instance=True, spec_set=True)`, never a bare mock |
| Unit domain | `opengaterag/api/tests/unit/domain/<context>/test_<context>entities.py` | entity methods |
| Integration endpoint | `opengaterag/api/tests/integration/endpoints/` | happy path, one row per mapped error (mocked use case). No per-endpoint auth or request-validation tests. `AuthenticatedUserQuery` is stubbed, never OpenGateLLM |
| Integration Postgres | `opengaterag/api/tests/integration/postgres/` | persist/read, constraints, access filters |
| Integration Meilisearch | `opengaterag/api/tests/integration/meilisearch/` | real Meilisearch with a deterministic stub embedder: bootstrap, add/delete by filter, `metadata.<key>` filters, filter escaping, task failure mapping. Never mock the Meilisearch HTTP API |
| e2e | `.github/tests/e2e/` | full stack against a real OpenGateLLM (semantic and hybrid ranking). No refresh hooks: writes are visible once they return |

Assert only what the test is about, not every field of the response. Unit test names start with `test_should_`. Mocks are prefixed `mock_`. Use `# Arrange` / `# Act` / `# Assert`. Every test directory has an `__init__.py`.

## Commands

```bash
pip install -e ".[test]"
docker compose --file compose.example.yml up --wait --detach postgres meilisearch
alembic -c opengaterag/api/alembic.ini upgrade head          # new revision: revision --autogenerate -m "<slug>", test upgrade AND downgrade
uvicorn opengaterag.api.main:app --reload
pytest opengaterag/api/tests/unit
pytest opengaterag/api/tests/integration
ruff check --fix . && ruff format .
```

## Principles

1. Smallest correct diff. Do not mix feature work with unrelated cleanup.
2. Names reveal intent. A comment explains a *why* the code cannot, never what the next line does.
3. YAGNI. Extract a shared helper only when the pattern already exists twice.
4. Fail explicitly: return known domain errors and re-raise unknown failures.
5. Keep `config.example.yml`, `.env.example`, both compose files and the README in sync with the configuration in the same change.
6. `AGENTS.md` is the source of truth for conventions. When a pattern lands or changes, update this file in the same change, and record the first slice of each pattern as its reference implementation.

## Deferred to the end of the revamp

- **Quota management and viewing usage.** Rethink the storage quota as a whole: what a document's size means and how it is counted, how `storage_limit` is enforced, and how a user sees their usage against their limit (one per-user "used / limit" figure, not a size on each collection). Collection responses deliberately carry no `size` until then.
