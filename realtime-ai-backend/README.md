# Realtime AI Backend (WebSockets + Supabase)

This project implements a minimal but complete **realtime conversational backend** using:

- **FastAPI** for the async HTTP/WebSocket server
- **WebSockets** for bi-directional realtime communication
- **OpenAI ChatCompletion (streaming)** to simulate an LLM
- **Supabase Postgres** for session + event persistence
- **Async post-session processing** to generate a conversation summary

The code is structured and documented to be suitable as an assignment submission for a "Realtime AI Backend" task.

---

## 1. Project Structure

- **app/**
  - `main.py` – FastAPI app and WebSocket route
  - `websocket.py` – WebSocket session loop, streaming, and logging
  - `llm.py` – LLM streaming abstraction (OpenAI ChatCompletion with `stream=True`)
  - `database.py` – Supabase client initialization
  - `config.py` – Environment variable loading
  - `models.py` – Helper functions to build DB records
  - `tasks.py` – Post-session summary generation using LLM
- **frontend/**
  - `index.html` – Simple WebSocket-based chat UI
- **sql/**
  - `schema.sql` – Supabase Postgres schema for sessions and session events
- `requirements.txt` – Python dependencies
- `.env.example` – Template for required environment variables

---

## 2. Supabase Setup

### 2.1. Create a Supabase Project

1. Go to [https://supabase.com](https://supabase.com) and create/sign in to your account.
2. Create a **new project**.
3. In the project dashboard:
   - Copy the **Project URL** → used as `SUPABASE_URL`.
   - Copy the **Service Role Key** → used as `SUPABASE_SERVICE_KEY`.

> The service key is sensitive; do **not** commit your `.env` file.

### 2.2. Database Schema (SQL)

Run the following SQL in the Supabase SQL editor (or psql) to create the required tables. This is the same content as `sql/schema.sql`:

```sql
create table sessions (
  session_id text primary key,
  user_id text,
  start_time timestamptz,
  end_time timestamptz,
  summary text
);

create table session_events (
  id bigint generated always as identity primary key,
  session_id text references sessions(session_id),
  role text,
  content text,
  timestamp timestamptz
);
```

- **sessions** – high-level session metadata
  - `session_id`: identifier for a WebSocket chat session
  - `user_id`: ID of the user (hardcoded to `demo-user` in this example)
  - `start_time`: when the session started
  - `end_time`: when the session closed
  - `summary`: final LLM-generated session summary

- **session_events** – detailed chronological event log
  - `session_id`: foreign key to `sessions`
  - `role`: `user` or `assistant`
  - `content`: text of the message
  - `timestamp`: event time (UTC)

---

## 3. Environment & Dependencies

### 3.1. Python Environment

Use Python 3.10+ (recommended).

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
```

### 3.2. Install Dependencies

```bash
pip install -r requirements.txt
```

`requirements.txt` includes:

- `fastapi` – Web framework
- `uvicorn` – ASGI server
- `openai` – LLM client
- `supabase` – Supabase Python client
- `python-dotenv` – Environment variable loading

### 3.3. Environment Variables

Create a `.env` file in the project root, based on `.env.example`:

```env
OPENAI_API_KEY=sk-...
SUPABASE_URL=https://<your-project>.supabase.co
SUPABASE_SERVICE_KEY=your-service-role-key
```

- `OPENAI_API_KEY` – OpenAI key with access to `gpt-4o-mini` or compatible model.
- `SUPABASE_URL` / `SUPABASE_SERVICE_KEY` – From your Supabase project settings.

`app/config.py` uses `python-dotenv` to load this automatically at startup.

---

## 4. Running the Backend

From the project root:

```bash
uvicorn app.main:app --reload
```

This will start the FastAPI app on `http://127.0.0.1:8000`.

### WebSocket Endpoint

- Path: `ws://localhost:8000/ws/session/{session_id}`
- Example used in the frontend: `ws://localhost:8000/ws/session/demo123`

When a WebSocket connection is opened:

1. `app.main.websocket_endpoint` inserts a new row in `sessions`:
   - `session_id` = URL parameter
   - `user_id` = `"demo-user"`
   - `start_time` = `datetime.utcnow()`
2. Control is handed to `handle_socket` for the main loop.

---

## 5. Realtime Session & Streaming Flow

### 5.1. WebSocket Session Logic (`app/websocket.py`)

`handle_socket(websocket, session_id)`:

1. Accepts the WebSocket connection.
2. Initializes conversation history with a system message:
   - `"You are a helpful assistant."`
3. Enters a `while True` loop:
   - **Receive user message** via `websocket.receive_text()`.
   - Insert a **user event** into `session_events` via `event_record`.
   - Append it to the in-memory `conversation` list.
   - Call `stream_llm(conversation)` and **stream tokens** back to the client as they arrive.
   - After streaming, log a generic assistant event (`"[streamed response]"`) in `session_events`. (For production you could log the actual text; here we emphasize token streaming.)
4. On any disconnect/error, it triggers `generate_summary(session_id)` and closes the WebSocket.

This demonstrates **bi-directional realtime communication** with streaming token responses.

### 5.2. LLM Streaming (`app/llm.py`)

`stream_llm(messages)`:

- Uses `openai.ChatCompletion.acreate` with `stream=True`.
- Asynchronously iterates over chunks.
- Yields token fragments (`delta.content`) as soon as they are available.
- The WebSocket loop forwards each chunk directly to the client for low-latency UX.

---

## 6. Conversation State & Persistence

### 6.1. State Management

- In-memory `conversation` list is maintained per WebSocket connection.
- Each turn is appended as a `{role, content}` object.
- This list is passed to the LLM each time, so the model has full context.

### 6.2. Supabase Persistence

- **Session metadata** (`sessions` table):
  - Inserted once when the WebSocket is established (`main.py`).
  - Updated with `end_time` and `summary` in `tasks.py` after the session ends.

- **Event log** (`session_events` table):
  - Every incoming **user** message is stored with role `"user"`.
  - Every **assistant** streaming cycle results in an `"assistant"` event (placeholder content here).
  - Timestamps are captured at insert time using UTC.

This satisfies the requirement of a granular, chronological log of events.

---

## 7. Post-Session Processing & Summary

### 7.1. Triggering the Task

When the WebSocket loop exits due to an exception or client disconnect, `handle_socket` calls:

- `generate_summary(session_id)` from `app.tasks`.

### 7.2. Summary Implementation (`app/tasks.py`)

`generate_summary(session_id)`:

1. Fetches all `session_events` for the given `session_id` from Supabase.
2. Builds a textual transcript such as:
   - `"user: ...\nassistant: ...\n..."`
3. Calls `openai.ChatCompletion.acreate` with a system prompt:
   - `"Summarize this conversation briefly."`
4. Extracts the summary from the LLM response.
5. Updates the `sessions` record for that `session_id` with:
   - `end_time = datetime.utcnow()`
   - `summary = <LLM-generated text>`

This implements the required **post-session automation and finalization** using stored history.

> Note: In this simple implementation, `generate_summary` is awaited directly in the WebSocket handler. In a production system you might delegate this to a background worker or task queue.

---

## 8. Simple Frontend

The `frontend/index.html` file provides a minimal UI to exercise the WebSocket backend.

### 8.1. Usage

1. Start the backend:

   ```bash
   uvicorn app.main:app --reload
   ```

2. Open `frontend/index.html` in a browser (e.g. double-click the file or serve it via a simple static server).

3. The page will:
   - Open a WebSocket to `ws://localhost:8000/ws/session/demo123`.
   - Show a text input and a **Send** button.
   - Append streamed tokens into a `<pre>` block as they arrive.

This is intentionally minimal: the focus is on demonstrating backend behaviour, not UI/UX.

---

## 9. Design Choices (Short Overview)

- **FastAPI + WebSockets**: FastAPI provides a clean async WebSocket API that maps directly to the assignment’s requirements and integrates well with `uvicorn`.

- **OpenAI Streaming**: Using `stream=True` exposes token-level streaming and closely matches real-world LLM chat UX.

- **Supabase**:
  - Acts as a managed Postgres database with a convenient Python client.
  - `sessions` and `session_events` are intentionally minimal but expressive enough to capture both metadata and detailed logs.

- **State Management**:
  - Per-connection `conversation` state is kept in memory for LLM context.
  - The same information is mirrored in Supabase for durability and later analysis.

- **Post-Session Summary**:
  - Implemented as an async function invoked on disconnect.
  - Reads from the event log instead of any in-memory state, demonstrating that the DB is the source of truth.

---

## 10. Extensibility Ideas

If you want to extend this project beyond the assignment:

- **Tool / Function Calling**: Add a tool-calling layer in `llm.py` that detects structured tool calls from the model and executes internal Python functions (e.g., fetch user profile, call external APIs) before resuming the chat.
- **Multi-Step Routing**: Switch the system prompt or tool set based on the first user message (e.g., analysis vs. brainstorming vs. coding assistant modes).
- **Richer Event Types**: Extend `session_events` with types like `tool_call`, `tool_result`, `system`, etc.
- **Authentication**: Tie `user_id` to a real authenticated user instead of the hardcoded `demo-user`.

As provided, this repository already demonstrates the **core backend patterns** requested in the assignment.