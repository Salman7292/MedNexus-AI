# API Reference

The MedNexus AI Flask backend exposes the following HTTP routes. All chat interactions use `POST /chat` with Server-Sent Events (SSE) for response streaming.

---

## Authentication Routes

### `GET /signup` · `POST /signup`
User registration page and form submission.

**POST body (form-data)**:
| Field | Type | Description |
|---|---|---|
| `username` | `string` | Desired username |
| `email` | `string` | User email address |
| `password` | `string` | Password (hashed server-side) |

**Response**: Redirect to `/login` on success.

---

### `GET /login` · `POST /login`
User login page and form submission.

**POST body (form-data)**:
| Field | Type | Description |
|---|---|---|
| `email` | `string` | Registered email |
| `password` | `string` | Password |

**Response**: Redirect to `/` on success; re-renders login page with error on failure.

---

### `GET /logout`
Terminates the current session.

**Response**: Redirect to `/login`.

---

### `GET /login/google`
Initiates the Google OAuth 2.0 flow. Redirects the browser to Google's consent screen.

---

### `GET /auth/callback`
Google OAuth callback URL. Exchanges the auth code for user info and creates/logs in the user.

---

## Page Routes

### `GET /`
Landing page — renders `templates/index.html` (specialist directory).

### `GET /specialists`
Specialist selection page — same as `/`.

### `GET /specialists/derma/consult`
Renders the Dermatologist (Dr. Zavian) chat interface.

### `GET /specialists/ent/consult`
Renders the ENT Specialist (Dr. Anees) chat interface.

### `GET /specialists/psych/consult`
Renders the Psychiatrist (Dr. Aria) chat interface.

### `GET /specialists/pharmacy/consult`
Renders the Pharmacist (Dr. Pharma) chat interface.

### `GET /specialists/general/consult` · `GET /consultation`
Renders the General Physician (Dr. Alara) chat interface. Both routes serve the same page.

---

## Chat Routes

### `POST /chat`
The primary chat endpoint. Accepts a user message and returns a streaming SSE response.

**Request** (`application/json`):
```json
{
  "message": "I have a red rash on my arm",
  "thread_id": "uuid-string",
  "specialist": "dermatologist",
  "image_path": "/static/dermatalogist_upload/img.jpg"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `message` | `string` | Yes | User's text input |
| `thread_id` | `string` | Yes | UUID identifying the conversation thread |
| `specialist` | `string` | Yes | One of: `dermatologist`, `ent`, `psychiatrist`, `pharmacist`, `general` |
| `image_path` | `string` | No | Server path of a recently uploaded image (if any) |

**Response** (`text/event-stream` — SSE):
```
data: I can see from your description

data:  that this could be contact dermatitis.

data: [DONE]
```

Each `data:` line contains a streamed token. The `[DONE]` event signals the end of the response.

---

### `GET /threads`
Returns the list of conversation threads for the current user and specialist.

**Query parameters**:
| Parameter | Type | Description |
|---|---|---|
| `specialist` | `string` | Filter threads by specialist slug |

**Response** (`application/json`):
```json
[
  {
    "thread_id": "abc-123",
    "first_message": "I have a rash on my arm",
    "created_at": "2026-07-01T10:00:00Z"
  }
]
```

---

### `GET /history/<thread_id>`
Returns the full message history for a given thread.

**Response** (`application/json`):
```json
{
  "thread_id": "abc-123",
  "messages": [
    {"role": "human", "content": "I have a rash on my arm"},
    {"role": "ai", "content": "I can see..."}
  ]
}
```

---

### `POST /edit`
Truncates a thread's history to a given message index, enabling branch-from-past-message editing.

**Request** (`application/json`):
```json
{
  "thread_id": "abc-123",
  "specialist": "dermatologist",
  "index": 4,
  "new_message": "Actually, the rash started two weeks ago"
}
```

**Response** (`application/json`):
```json
{"status": "ok"}
```

---

## Image Upload

Image uploads are handled inline within the specialist frontend pages via JavaScript `fetch`. The uploaded file is saved to the specialist's upload directory (e.g., `static/dermatalogist_upload/`) and the returned path is attached to the next `/chat` request.

> [!NOTE]
> There is no dedicated `/upload` route. Image handling is integrated into the specialist page logic.
