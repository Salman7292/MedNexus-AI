# API Endpoints (REST & SSE)

All client-to-server HTTP API routes exposed by MedNexus AI are defined in the central Flask controller (`app.py`).

---

## Authentication Endpoints

### 1. User Registration (`POST /signup`)
Creates a new user profile inside `users.db`. Enforces a strong password policy (at least 8 characters, 1 uppercase, 1 lowercase, 1 digit, 1 special character).

*   **Content Type**: `application/x-www-form-urlencoded`
*   **Parameters**:
    *   `username` (string, required): Desired username (must be a valid email format).
    *   `password` (string, required): Plaintext password (hashed with `pbkdf2:sha256` before storing).
*   **Responses**:
    *   `302 Found`: Redirects to `/login` on successful registration.
    *   `200 OK`: Re-renders `signup.html` with an error message on validation failure.

### 2. User Sign In (`POST /login`)
Authenticates credentials and establishes a Flask cookie-backed session.

*   **Content Type**: `application/x-www-form-urlencoded`
*   **Parameters**:
    *   `username` (string, required): The registered email address.
    *   `password` (string, required): The password.
*   **Responses**:
    *   `302 Found`: Redirects to `/` on success.
    *   `200 OK`: Re-renders `login.html` with error details on validation failure.

---

## Chat & History Endpoints

### 3. Retrieve Thread List (`GET /threads`)
Returns a list of all chat sessions for the logged-in user, filtered by specialist.

*   **Parameters**:
    *   `specialist` (string, required): Slug of the specialist (`derma`, `ent`, `psych`, `general`, or `pharmacy`).
*   **Response (`application/json`)**:
    ```json
    [
      {
        "thread_id": "8bbd95a5-4661-4b8b-aa41-cdc8febb17b2",
        "title": "Severe throat pain...",
        "date": "2026-07-10 16:03:14"
      }
    ]
    ```

### 4. Fetch Thread History (`GET /history/<thread_id>`)
Retrieves the full message history of a specific session from the SQLite checkpointer.

*   **Parameters**:
    *   `thread_id` (string, path parameter): The thread ID (e.g. `thread-uuid`).
    *   `specialist` (string, query parameter): Slug of the specialist.
*   **Response (`application/json`)**:
    ```json
    {
      "messages": [
        {
          "role": "user",
          "content": "Hello, my throat hurts."
        },
        {
          "role": "ai",
          "content": "Hello. I am Dr. Anees. When did the pain start?"
        }
      ]
    }
    ```

### 5. Send Message (`POST /chat`)
Submits a message (and an optional image attachment) to the agent's LangGraph compiled application. Streams responses via Server-Sent Events (SSE).

*   **Content Type**: `multipart/form-data` (or `application/json` for text-only messages)
*   **Parameters**:
    *   `message` (string, required): User's text message.
    *   `thread_id` (string, required): The UUID of the conversation thread.
    *   `specialist` (string, required): Slug of the specialist.
    *   `image` (file, optional): Image upload (lesion, throat photo, or lab report).
*   **Response (`text/event-stream`)**:
    *   Returns structured JSON chunks wrapped in SSE events:
        *   `data: {"type": "token", "content": "Hello"}` (incremental tokens)
        *   `data: {"type": "tool_start", "tool_name": "...", "args": {...}}` (triggers tool loading animation in UI)
        *   `data: {"type": "tool_end", "tool_name": "...", "output": "..."}` (tool execution result)
        *   `data: {"type": "error", "content": "..."}` (error alerts)

### 6. Edit Message (`POST /edit`)
Truncates the checkpoint history back to a given message index, and submits a new message to branch the conversation.

*   **Content Type**: `application/json`
*   **Parameters**:
    *   `thread_id` (string, required): Thread UUID.
    *   `index` (integer, required): Target message index to truncate from.
    *   `new_text` (string, required): New text prompt.
    *   `specialist` (string, required): Slug of the specialist.
*   **Response (`text/event-stream`)**:
    *   Streams the new response token sequence from the truncated point.
