# RAG RBAC API

A FastAPI-based Retrieval-Augmented Generation (RAG) system with role-based access control, document chunking strategies, vector search via ChromaDB, and chat completions.

## Features

- **🔐 RBAC Authentication** — JWT-based auth with role-based access control (admin, analyst, manager, executive, viewer)
- **📄 Document Chunking** — Multiple strategies: fixed, recursive, sentence, and token-approximate
- **🔍 Vector Search** — ChromaDB persistent storage with cosine similarity search
- **💬 Chat Completions** — LLM-powered chat with message history
- **📋 Document Management** — CRUD operations for documents with chunk preview
- **⚡ Async First** — Native async SQLAlchemy + async ChromaDB operations
- **🛡️ Structured Error Handling** — Global exception handlers with JSON logging

## Architecture

```
app/
├── core/           # App config, security, auth, exceptions
│   ├── config.py
│   ├── security.py
│   ├── auth.py
│   └── exceptions.py
├── db/             # Database models, connections
│   ├── models.py
│   ├── connection.py
│   └── chroma.py
├── models/         # Pydantic request/response schemas
│   ├── chunking.py
│   ├── chat.py
│   └── vector.py
├── routes/         # API endpoint routers
│   ├── auth.py
│   ├── chat.py
│   ├── chunking.py
│   ├── documents.py
│   └── health.py
├── services/       # Business logic layer
│   ├── chunking_service.py
│   ├── chat_service.py
│   └── vector_store_service.py
├── llms/           # LLM provider abstraction
│   └── provider.py
└── utils/          # Low-level utilities
    └── chunking.py
```

## Quick Start

### Prerequisites

- Python 3.12+
- pip or uv

### Installation

```bash
# Clone the repository
git clone <repo-url> && cd project-1

# Create a virtual environment
python -m venv .venv && source .venv/bin/activate

# Install dependencies
pip install -e .

# Install dev dependencies (for testing)
pip install -e ".[dev]"
```

### Configuration

Create a `.env` file in the project root (all values are optional with sensible defaults):

```env
DEBUG=false
DATABASE_URL=sqlite+aiosqlite:///./app.db
CHROMA_DIR=./data/chroma
CHROMA_COLLECTION=documents
EMBEDDING_MODEL=all-MiniLM-L6-v2
JWT_SECRET=change-me-in-production
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=60
LOG_LEVEL=INFO
LOG_FORMAT=json
```

### Database Setup

```bash
# Apply all pending migrations
alembic upgrade head

# Seed the database with default roles and users
# (Migrations include admin, analyst, manager, executive, viewer roles)
```

Default seeded users:

| Name   | Email                     | Role     | Password Hash         |
|--------|---------------------------|----------|-----------------------|
| Alice  | alice.admin@example.com   | admin    | dummy_hash_admin_123  |
| Bob    | bob.analyst@example.com   | analyst  | dummy_hash_analyst_123|
| Carol  | carol.manager@example.com | manager  | dummy_hash_manager_123|
| Dave   | dave.executive@example.com| executive| dummy_hash_executive_123|
| Eve    | eve.viewer@example.com    | viewer   | dummy_hash_viewer_123 |

> **Note:** These hashes are placeholder values. In production, use properly bcrypt-hashed passwords via the `/auth/register` endpoint.

### Run

```bash
uvicorn main:app --reload
```

API is available at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

## API Reference

### Authentication

All endpoints except `/health` and `/auth/login` require a Bearer JWT token.

#### POST /auth/login

Authenticate and receive a JWT token.

```json
{
  "email": "alice.admin@example.com",
  "password": "dummy_hash_admin_123"
}
```

Response:

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "user": {
    "id": "aaaaaaaa-1111-1111-1111-111111111111",
    "email": "alice.admin@example.com",
    "full_name": "Alice Admin",
    "role_id": "11111111-1111-1111-1111-111111111111",
    "is_active": true,
    "created_at": "2026-05-27T20:05:00+00:00",
    "updated_at": "2026-05-27T20:05:00+00:00"
  }
}
```

#### POST /auth/register (admin only)

```json
{
  "email": "newuser@example.com",
  "full_name": "New User",
  "password": "secure_password",
  "role_id": "22222222-2222-2222-2222-222222222222"
}
```

#### GET /auth/me

Returns the authenticated user's profile.

#### POST /auth/roles (admin only)

```json
{
  "name": "custom_role",
  "description": "Custom role description"
}
```

#### GET /auth/roles (admin only)

Lists all available roles.

### Document Chunking

#### POST /api/v1/chunk-preview

Preview how a text will be chunked without storing it.

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

#### POST /api/v1/ingest (admin, analyst, manager)

Chunk and store a document in the vector database.

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

### Vector Search

#### POST /api/v1/search

Search for chunks semantically similar to a query.

```json
{
  "query": "What does the document say about retention policy?",
  "top_k": 5,
  "document_id": "aaaaaaaa-1111-1111-1111-111111111111"
}
```

### Document Management

#### POST /api/v1/documents (admin, analyst, manager)

Create a document with chunking.

```json
{
  "text": "Document content to chunk and store...",
  "chunking": {
    "strategy": "recursive",
    "chunk_size": 800,
    "chunk_overlap": 120
  }
}
```

#### DELETE /api/v1/documents/{document_id} (admin, manager)

Delete a document and all its chunks.

#### GET /api/v1/documents/{document_id}/chunks

Get paginated chunks for a document.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| limit     | int  | 10      | Chunks per page |
| offset    | int  | 0       | Pagination offset |

### Chat

#### POST /api/v1/chats

Create a new chat conversation.

```json
{
  "title": "My Chat"
}
```

#### GET /api/v1/chats

List all chats for the authenticated user.

#### GET /api/v1/chats/{chat_id}

Get a chat with its message history.

#### POST /api/v1/chats/{chat_id}/messages

Send a message and get an LLM-generated response.

```json
{
  "content": "What is the retention policy?"
}
```

#### DELETE /api/v1/chats/{chat_id}

Delete a chat and its messages.

### Health

#### GET /health

```json
{
  "status": "ok"
}
```

## Chunking Strategies

| Strategy       | Description |
|----------------|-------------|
| `fixed`        | Fixed-size character windows with configurable overlap |
| `recursive`    | Split by separators (`\n\n`, `\n`, `. `, ` `) and merge into bounded chunks (default) |
| `sentence`     | Group sentence blocks respecting max sentences and chunk size |
| `token_approx` | Token-size approximation using character-to-token ratio |

## Development

### Running Tests

```bash
# Unit tests
python -m pytest tests/unit/ -v

# Integration tests
python -m pytest tests/integration/ -v

# All tests with coverage
python -m pytest --cov=app tests/
```

### Creating Migrations

```bash
# Auto-generate a migration from model changes
alembic revision --autogenerate -m "describe change"

# Apply all pending migrations
alembic upgrade head

# Rollback one step
alembic downgrade -1
```

### Project Standards

- **Python 3.12+** with modern typing (`list[str]`, `str | None`, etc.)
- **Async SQLAlchemy 2.0** with `aiosqlite` for non-blocking DB access
- **Pydantic v2** for request/response validation
- **Structured logging** with JSON format in production
- **Role-based access control** enforced via FastAPI dependencies
- **Layer separation**: routes → services → models/utils/db

## License

MIT
