# MedNexus AI Medical Specialists

MedNexus AI is a comprehensive web platform featuring AI-powered medical specialists (Dermatology, ENT, Psychiatry, Pharmacy, and General Physician) that offer instant, precise diagnostics, care plans, and medical analysis.

This guide provides full instructions on how to set up, install, and run this project locally on both Windows and macOS.

## Prerequisites

Before you begin, ensure you have the following installed on your system:
- **Python 3.9+** (Python 3.10 or 3.11 recommended)
- **Git** (optional, for cloning the repository)

---

## 💻 Windows Installation & Setup

Open **Command Prompt** or **PowerShell** and follow these steps:

### 1. Navigate to your project directory
If you haven't already, navigate to the folder where the project is located:
```cmd
cd path\to\your\project_folder
```
*(For example: `cd "d:\archive\main desing 12th version - Copy"`)*

### 2. Create a Virtual Environment
It is highly recommended to use a virtual environment to keep dependencies isolated so they don't interfere with other Python projects on your system.
```cmd
python -m venv venv
```

### 3. Activate the Virtual Environment
Activate the environment you just created. You must do this every time you work on the project.
```cmd
venv\Scripts\activate
```
*Note: Once activated, you should see `(venv)` at the beginning of your command prompt line.*

### 4. Install Dependencies
Install all the required Python packages from the `requirements.txt` file.
```cmd
pip install -r requirements.txt
```

---

## 🍏 macOS / Linux Installation & Setup

Open your **Terminal** application and follow these steps:

### 1. Navigate to your project directory
Navigate to the folder containing your project files:
```bash
cd /path/to/your/project_folder
```

### 2. Create a Virtual Environment
Create an isolated Python environment for the project:
```bash
python3 -m venv venv
```

### 3. Activate the Virtual Environment
Activate the environment. You must do this every time before running the app.
```bash
source venv/bin/activate
```
*Note: Your terminal prompt will change to show `(venv)` on the left side.*

### 4. Install Dependencies
Install all required libraries using `pip`:
```bash
pip install -r requirements.txt
```

---

## 🔑 Environment Variables (.env Setup)

This project relies on several third-party APIs (Groq, Pinecone, Tavily, LangSmith, Google OAuth, etc.). 

1. Ensure there is a file named `.env` in the root directory of your project.
2. If it does not exist, create one.
3. Your `.env` file should contain the necessary API keys formatted like this:

```env
GROQ_API_KEY="your_groq_api_key_here"
PINECONE_API_KEY="your_pinecone_api_key_here"
TAVILY_API_KEY="your_tavily_api_key_here"
LANGSMITH_TRACING=true
LANGSMITH_ENDPOINT="https://api.smith.langchain.com"
LANGSMITH_API_KEY="your_langsmith_api_key_here"
LANGSMITH_PROJECT="Dermatlogist"
MOONDREAM_KEY="your_moondream_key_here"
GOOGLE_API_KEY="your_google_api_key_here"
GOOGLE_CLIENT_ID="your_google_client_id_here"
GOOGLE_CLIENT_SECRET="your_google_client_secret_here"
```

*(Note: Replace the placeholder values with your actual API keys if you are setting this up from scratch).*

---

## 🚀 Running the Application

Once your virtual environment is activated and dependencies are installed, you can start the application.

### On both Windows and Mac:

Run the Flask application with the following command:
```bash
python app.py
```

You should see terminal output indicating that the server is running, usually looking like this:
```
 * Serving Flask app 'app'
 * Debug mode: off
 * Running on http://127.0.0.1:5000
```

### Accessing the App
Open your web browser (Chrome, Firefox, Safari, Edge) and navigate to:
**http://127.0.0.1:5000** or **http://localhost:5000**

---

## 🛑 Stopping the Application

To stop the server, go back to your terminal or command prompt window and press:
**`Ctrl + C`**

To deactivate and exit your virtual environment when you are done working:
```bash
deactivate
```
