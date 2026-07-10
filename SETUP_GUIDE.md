# 🏥 Smart AI Hospital | **Ultimate Setup Guide**

Welcome to the **Smart AI Hospital** project. Follow this premium guide to initialize your environment, install dependencies, and launch the application seamlessly.

---

## ⚡ **Prerequisites**
Before proceeding, ensure you have the following installed on your machine:
*   🐍 **Python 3.9+** (Check with `python --version`)
*   📦 **Pip** (Python Package Manager)
*   🔑 **Active API Keys** (Groq, Pinecone, Google, Tavily, Moondream)

---

## 🚀 **Step-by-Step Installation**

### 💻 **Windows** *(PowerShell / CMD)*
1.  **Navigate to Project Folder:**
    ```powershell
    cd "d:\archive\main desing 12th version - Copy"
    ```
2.  **Create Virtual Environment:**
    ```powershell
    python -m venv venv
    ```
3.  **Activate Environment:**
    *   **PowerShell:** `.\venv\Scripts\Activate.ps1`
    *   **CMD:** `.\venv\Scripts\activate`
4.  **Install Libraries:**
    ```powershell
    pip install -r requirements.txt
    ```
5.  **Launch App:**
    ```powershell
    python app.py
    ```

---

### 🍎 **macOS / Linux** *(Terminal)*
1.  **Navigate to Project Folder:**
    ```bash
    cd "d:/archive/main desing 12th version - Copy"
    ```
2.  **Create Virtual Environment:**
    ```bash
    python3 -m venv venv
    ```
3.  **Activate Environment:**
    ```bash
    source venv/bin/activate
    ```
4.  **Install Libraries:**
    ```bash
    pip install --upgrade pip
    pip install -r requirements.txt
    ```
5.  **Launch App:**
    ```bash
    python3 app.py
    ```

---

## ⚙️ **Configuration (.env)**

> [!IMPORTANT]
> Your environment variables are stored in the `.env` file at the root. Ensure it contains your **active API keys** as shown below:

```env
GROQ_API_KEY="your_api_key"
GOOGLE_API_KEY="your_api_key"
PINECONE_API_KEY="your_api_key"
TAVILY_API_KEY="your_api_key"
```

---

## 🌐 **Accessing the System**

Once the server started, open your favorite browser and visit:
👉 **[http://localhost:5000](http://localhost:5000)**

---

## 🛠️ **Troubleshooting**

> [!TIP]
> **Common Fixes:**
> *   **Command Not Found:** Try using `python3` instead of `python`.
> *   **Missing Modules:** Ensure the `(venv)` indicator is visible in your terminal before running.
> *   **Port Conflict:** If port 5000 is used, specify a different port in the `if __name__ == "__main__":` block of `app.py`.

---
*Created by Antigravity AI - Professional Edition*
