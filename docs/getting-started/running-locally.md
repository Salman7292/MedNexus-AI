# Running Locally

Once dependencies are installed and `.env` credentials are set, you can run the MedNexus AI application locally.

## Starting the Application

With your virtual environment active, run the following command in the root of the project:

```bash
python app.py
```

You should see Flask launch the development server:

```text
 * Serving Flask app 'app'
 * Debug mode: on
 * Running on http://127.0.0.1:5000
 * Running on http://localhost:5000
```

---

## Accessing the Dashboard

Open your web browser and navigate to:
👉 **[http://localhost:5000](http://localhost:5000)**

1.  **Register a User**: Navigate to `/signup` and fill out your username (email format) and password. (Or authenticate via Google Sign-In if you have configured the Google client credentials).
2.  **Login**: Access the home dashboard.
3.  **Choose a Specialist**: Select an AI specialist to start a conversation.

---

## Verifying Local Storage (Databases)

The application automatically creates SQLite databases at startup to persist data. Verify that these files have been generated in your project root:
- `users.db`: Contains user credentials and hashes.
- `dermatologist.db`: Contains Dr. Zavian's checkpoint histories and user threads.
- `ent.db`: Contains Dr. Anees's data.
- `psychiatrist.db`: Contains Dr. Aria's data.
- `pharmacy_chats.db`: Contains Dr. Pharma's database logs.

---

## Stopping the Application

To shut down the Flask server, return to your terminal and press:

```key
Ctrl + C
```

To deactivate the Python virtual environment:

```bash
deactivate
```
