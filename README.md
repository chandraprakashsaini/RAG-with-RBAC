## RAG RBAC API

This project now uses a scalable folder structure with layered modules (`routes`, `services`, `models`, `utils`, `db`, `llms`) and supports multiple document chunking strategies selected per API request.

ChromaDB is now wired as a persistent vector store at `./data/chroma` using collection name `documents`.

### Run

```bash
uvicorn main:app --reload
```

### Database migrations (Alembic)

```bash
# apply all migrations
alembic upgrade head

# create a new migration from model changes
alembic revision --autogenerate -m "describe change"

# apply one step back
alembic downgrade -1
```

### Chunking strategies

- `fixed`: fixed-size character windows with overlap
- `recursive`: split by separators and merge into bounded chunks (default)
- `sentence`: group sentence blocks
- `token_approx`: token-size approximation using character ratios

### API examples

`POST /chunk-preview`

Use `POST /api/v1/chunk-preview`

```json
{
  "text": "Your long text here...",
  "chunking": {
    "strategy": "recursive",
    "chunk_size": 600,
    "chunk_overlap": 100,
    "separators": ["\n\n", "\n", ". ", " "],
    "max_sentences_per_chunk": 5,
    "estimated_chars_per_token": 4
  }
}
```

`POST /ingest`

Use `POST /api/v1/ingest`

```json
{
  "document_id": "aaaaaaaa-1111-1111-1111-111111111111",
  "text": "Document content...",
  "chunking": {
    "strategy": "sentence",
    "chunk_size": 700,
    "chunk_overlap": 80,
    "max_sentences_per_chunk": 4
  }
}
```

`POST /api/v1/search`

```json
{
  "query": "What does the document say about retention policy?",
  "top_k": 5,
  "document_id": "aaaaaaaa-1111-1111-1111-111111111111"
}
```
