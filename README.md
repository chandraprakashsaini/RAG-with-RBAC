# RAG RBAC API

A FastAPI-based Retrieval-Augmented Generation (RAG) system with role-based access control, document chunking strategies, vector search via ChromaDB, Gemini-powered chat with SSE streaming, and an admin dashboard frontend.

## Features

- **🔐 RBAC Authentication** — JWT-based auth with role-based access control (admin, analyst, manager, executive, viewer)
- **📄 Document Chunking** — Multiple strategies: fixed, recursive, sentence, and token-approximate
- **🔍 Vector Search** — ChromaDB persistent storage with cosine similarity search
- **💬 Chat with SSE Streaming** — LLM-powered chat with real-time token streaming via Server-Sent Events
- **🧠 RAG Pipeline** — Retrieve relevant chunks → build context with chat history → Gemini LLM
- **📋 Document Management** — CRUD operations for documents with chunk preview
- **🖥️ Admin Dashboard** — Built-in SPA frontend with chat, document management, vector search, and admin panel
- **⚡ Async First** — Native async SQLAlchemy + async ChromaDB operations
- **🛡️ Structured Error Handling** — Global exception handlers with JSON logging

## Architecture

```
app/
├── core/               # App config, security, auth, exceptions
│   ├── application.py  # FastAPI app factory (CORS, lifespan, static mount)
│   ├── config.py       # Pydantic settings (env vars)
│   ├── security.py     # JWT create/decode, password hashing
│   ├── auth.py         # get_current_user, require_role dependencies
│   └── exceptions.py   # Global exception handlers
├── db/                 # Database models, connections
│   ├── models.py       # SQLAlchemy ORM (User, Role, Chat, ChatMessage)
│   ├── connection.py   # Async SQLAlchemy engine + session factory
│   └── chroma.py       # ChromaDB client singleton (telemetry disabled)
├── llms/               # LLM provider
│   └── provider.py     # LangChain GoogleGenerativeAI (optional dep)
├── models/             # Pydantic request/response schemas
├── routes/             # API endpoint routers
│   ├── auth.py         # Login, register, roles, /me
│   ├── chat.py         # Chat CRUD + messages + SSE stream
│   ├── chunking.py     # Preview, ingest, search
│   ├── documents.py    # Document CRUD + chunk listing
│   └── health.py       # Health check
├── services/           # Business logic layer
│   ├── rag_service.py  # RAG pipeline: retrieval → context → LLM
│   ├── chat_service.py # Chat CRUD + send_message (sync + stream)
│   ├── chunking_service.py
│   └── vector_store_service.py
└── utils/              # Low-level utilities
    └── chunking.py     # Chunk text implementations

frontend/               # SPA admin dashboard
├── index.html          # App shell
├── css/style.css       # Dark theme, responsive layout
└── js/
    ├── app.js          # Hash router, auth guard, sidebar layout
    ├── api.js          # API client (fetch + XHR SSE streaming)
    └── pages/
        ├── login.js    # Login / Register
        ├── admin.js    # Role management
        ├── documents.js# Upload, search, view/delete chunks
        ├── chat.js     # Chat UI with SSE streaming
        └── search.js   # Vector search + ingest
```

## Quick Start

### Prerequisites

- **Python 3.12+** (required — the codebase uses PEP 604 union syntax like `str | None` and other 3.10+ features; `pyproject.toml` enforces `requires-python = ">=3.12"`)
- pip or [uv](https://docs.astral.sh/uv/)

> **Common pitfall:** if `uvicorn main:app` fails with `TypeError: unsupported operand type(s) for |: 'type' and 'NoneType'`, you are running the system Python (e.g. 3.8) instead of the project venv. Activate the venv first (see below) or run `.venv/bin/uvicorn main:app --reload` directly.

### Installation

```bash
git clone <repo-url> && cd project-1

# Create a venv using Python 3.12+ (use an explicit path if `python` is 3.8)
python3.12 -m venv .venv && source .venv/bin/activate

# Core dependencies
pip install -e .

# Dev dependencies (for testing)
pip install -e ".[dev]"
```

If you have `uv` installed, you can sync directly from the lockfile (it will create/use `.venv` with the correct Python):

```bash
uv sync
source .venv/bin/activate
```

### Configuration

Create a `.env` file in the project root (all values optional with sensible defaults):

```env
DEBUG=false
DATABASE_URL=sqlite+aiosqlite:///./app.db
CHROMA_DIR=./data/chroma
CHROMA_COLLECTION=documents
EMBEDDING_MODEL=all-MiniLM-L6-v2
JWT_SECRET=<generate-a-secure-random-secret-at-least-32-chars>
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=60
GEMINI_API_KEY=your-google-ai-key
GEMINI_MODEL=gemini-2.0-flash
RAG_TOP_K=5
LOG_LEVEL=INFO
LOG_FORMAT=json

# Security / operational settings
SEED_DEMO_DATA=false
CORS_ORIGINS=["http://localhost:8000"]
MAX_UPLOAD_BYTES=25000000
LLM_TIMEOUT=60
LOGIN_RATE_LIMIT=5/minute
```

> **Security:** `JWT_SECRET` is validated at startup — the default value is rejected. Generate a strong secret (e.g. `python -c "import secrets; print(secrets.token_urlsafe(48))"`). `SEED_DEMO_DATA=true` creates demo users (with the password `password123`); only enable this for local development.

> **CORS in dev mode:** when `DEBUG=true`, CORS allows any `http://localhost:*` or `http://127.0.0.1:*` origin so you can run a separate frontend dev server (e.g. Vite on port 5173, Create React App on port 3000). In production (`DEBUG=false`), only the origins listed in `CORS_ORIGINS` are allowed.

### Database

Tables are auto-created on first startup. When `SEED_DEMO_DATA=true`, demo users are inserted automatically (intended for local development only):

| Email               | Password     | Role     |
|---------------------|-------------|----------|
| alice@example.com   | password123 | admin    |
| bob@example.com     | password123 | analyst  |
| carol@example.com   | password123 | manager  |
| dave@example.com    | password123 | executive|
| eve@example.com     | password123 | viewer   |

### Run

> **Important:** always activate the venv (`source .venv/bin/activate`) before running, so you use the project's Python 3.12 and installed dependencies. Running `uvicorn` against the system Python will fail with `TypeError: unsupported operand type(s) for |`.

```bash
# After activating the venv:
uvicorn main:app --reload

# Or, without activating, invoke the venv binary directly:
.venv/bin/uvicorn main:app --reload
```

Open `http://localhost:8000` for the admin dashboard.
API docs at `http://localhost:8000/docs`.

## API Reference

### Authentication

All endpoints except `/health` and `/auth/login` require a Bearer JWT token.

#### POST /auth/login

```
{
  "email": "your-email@example.com",
  "password": "your-password"
}
```

Response: `{ "access_token": "...", "user": {...} }`

#### POST /auth/register (admin only)

```
{
  "email": "newuser@example.com",
  "full_name": "New User",
  "password": "secure_password",
  "role_id": "22222222-2222-..."
}
```

#### GET /auth/me — Returns the authenticated user's profile

#### POST /auth/roles (admin only) — Create a new role
#### GET /auth/roles (admin only) — List all roles

### Document Chunking

#### POST /api/v1/chunk-preview — Preview chunking without storing

```json
{
  "text": "Your long text here...",
  "chunking": {
    "strategy": "recursive",
    "chunk_size": 600,
    "chunk_overlap": 100
  }
}
```

#### POST /api/v1/ingest (admin, analyst, manager) — Chunk and store in vector DB

#### POST /api/v1/search — Semantic search across chunks

```json
{
  "query": "What does the document say about retention policy?",
  "top_k": 5,
  "document_id": "aaaaaaaa-..."
}
```

### Document Management

#### POST /api/v1/documents (admin, analyst, manager) — Upload document with chunking
#### DELETE /api/v1/documents/{id} (admin, manager) — Delete document and chunks
#### GET /api/v1/documents/{id}/chunks — Get paginated chunks (`?limit=10&offset=0`)

### Chat

#### POST /api/v1/chats — Create a new chat

```json
{ "title": "My Chat" }
```

#### GET /api/v1/chats — List chats for the authenticated user
#### GET /api/v1/chats/{id} — Get chat with message history
#### DELETE /api/v1/chats/{id} — Delete a chat

#### POST /api/v1/chats/{id}/messages — Send message (sync response)

```json
{ "content": "What is the retention policy?" }
```

Returns the assistant response + retrieved context chunks.

#### POST /api/v1/chats/{id}/messages/stream — Send message (SSE stream)

Returns `text/event-stream`:

```
event: chunks
data: [{"id":"...", "content":"...", "score": 0.85, ...}]

data: {"token": "The retention policy..."}

data: {"token": " requires..."}

event: done
data: {}
```

### Health

#### GET /health — `{"status": "ok"}`

## Chunking Strategies

| Strategy       | Description |
|----------------|-------------|
| `fixed`        | Fixed-size character windows with configurable overlap |
| `recursive`    | Split by separators (`\n\n`, `\n`, `. `, ` `) and merge (default) |
| `sentence`     | Group sentence blocks respecting max sentences and chunk size |
| `token_approx` | Token-size approximation using character-to-token ratio |

## Frontend

The admin dashboard is served at `/` and includes:

| Route | Page |
|-------|------|
| `#login` / `#register` | Auth pages |
| `#chats` / `#chats/{id}` | Chat list + live chat with SSE streaming |
| `#documents` | Upload docs, search, view/delete chunks |
| `#search` | Vector search + content ingest |
| `#admin` | Role management, current user profile |

### RAG Flow

```
User message → save to DB → get chat history → retrieve top-k chunks from ChromaDB
→ build prompt (system + context + history + question) → Gemini LLM
→ stream tokens via SSE → save full response to DB → done
```

Without `GEMINI_API_KEY`, the system returns a mock response showing what was retrieved.

## Python Version Requirement

This project requires **Python 3.12+**. The codebase relies on modern syntax and features that are not available in 3.8/3.9/3.10/3.11:

- PEP 604 union types (`str | None`, `list[str] | None`) — requires 3.10+
- `match`/`case` statements where used — requires 3.10+
- Pydantic v2 / SQLAlchemy 2.0 async patterns tuned for 3.12

`pyproject.toml` enforces this via `requires-python = ">=3.12"`, and `uv.lock` pins 3.12-compatible wheels.

### Optional LLM / embedding dependencies

For full RAG functionality (Gemini + sentence-transformers embeddings), ensure the following are installed (they are already in `pyproject.toml` dependencies):

```bash
pip install langchain-google-genai sentence-transformers
```

Without `GEMINI_API_KEY` set, the system falls back to a `FallbackLLM` mock so the API still responds.

## Development

```bash
# Run tests
python -m pytest tests/ -v

# With coverage
python -m pytest --cov=app tests/
```

### Project Standards

- **Python 3.12+** with modern typing (`list[str]`, `str | None`)
- **Async SQLAlchemy 2.0** with `aiosqlite`
- **Pydantic v2** for request/response validation
- **Structured logging** with JSON format in production
- **Role-based access control** via FastAPI dependencies
- **Layer separation**: routes → services → models/utils/db

## License

MIT
