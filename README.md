# 🐝 AgentHive: Multi-Agent Document Intelligence

AgentHive is a full-stack, modular, multi-agent AI system designed to automatically process, analyze, and interact with documents (PDFs, Excel spreadsheets, and CSVs). It uses a sophisticated orchestrator agent to route user queries to specialized sub-agents, providing accurate context-aware answers, structured data extraction, and dataset insights.

---

## ✨ Features

* **🧠 Smart Orchestrator Pipeline:** An orchestrator agent dynamically classifies user intents (summarization, search, data extraction, or dataset analysis) and routes queries to the best specialized agent.
* **📂 Automated Ingestion:** Easily upload PDFs, Excel files (`.xlsx`, `.xls`), and CSVs. Text is cleaned, chunked, and stored in a local FAISS vector store. Tabular data is loaded into Pandas DataFrames.
* **🗣️ Voice-Enabled:** Ask questions using your voice (via Web Speech API) and receive text-to-speech AI responses.
* **🧩 Specialized Agents:**
  * **Understanding Agent:** Handles semantic search across documents utilizing Google Gemini Embeddings and FAISS.
  * **Summarization Agent:** Generates concise, structured summaries tailored to user queries.
  * **Extraction Agent:** Automatically pulls out entities (emails, dates, names) and key-value pairs into valid JSON.
  * **Excel Insight Agent:** Analyzes datasets to uncover statistical trends, correlations, outliers, and generates narrative reports.
  * **Voice Agent:** Optimizes responses to sound natural for text-to-speech playback.
* **⚡ Modern Tech Stack:** 
  * **Backend:** Python, FastAPI, LangChain, FAISS, PyMuPDF, Pandas, Google Gemini API.
  * **Frontend:** React 18, TypeScript, Vite.

---

## 🛠️ Setup Instructions

### 1. Requirements
* [Python 3.10+](https://www.python.org/)
* [Node.js 18+](https://nodejs.org/)

### 2. Backend Setup
Navigate to the `backend` directory and set up the environment:

```bash
cd backend
python -m venv venv
# On Windows: venv\Scripts\activate
# On Mac/Linux: source venv/bin/activate

pip install -r requirements.txt
```

#### API Keys Configuration
Create a `.env` file in the `backend/` directory by copying the example:
```bash
cp .env.example .env
```
Inside `.env`, set your **Google Gemini API Key**:
```
GOOGLE_API_KEY=your-actual-api-key
MODEL_NAME=gemini-2.0-flash-lite
EMBEDDING_MODEL=models/embedding-001
UPLOAD_DIR=./uploads
```
*(You can get a Gemini API key from [Google AI Studio](https://aistudio.google.com/app/apikey))*

### 3. Frontend Setup
Navigate to the `frontend` directory and install dependencies:

```bash
cd ../frontend
npm install
```

---

## 🚀 Running the Application

### Option A: Using the Launcher (Windows)
At the root of the project, run the provided batch file:
```cmd
start.bat
```
This will automatically launch both the FastAPI backend and the Vite frontend in separate console windows.

### Option B: Manual Start

**1. Start Backend:**
```bash
cd backend
python main.py
# Server runs on http://localhost:8000
```

**2. Start Frontend:**
```bash
cd frontend
npm run dev
# Server runs on http://localhost:5173
```

**3. Access the application:**
Open your browser and navigate to **[http://localhost:5173](http://localhost:5173)**.

*(API documentation is available at [http://localhost:8000/docs](http://localhost:8000/docs))*

---

## 🏗️ Architecture

```
agenthive/
├── backend/                  # Python/FastAPI Backend
│   ├── agents/               # Specialized AI Agent logic
│   │   ├── orchestrator.py   # Query routing and intent classification
│   │   ├── ingestion.py      # PDF / Excel processing
│   │   ├── understanding.py  # Text chunking, FAISS Vector DB
│   │   ├── summarization.py  # LLM Summaries
│   │   ├── extraction.py     # JSON entity extraction
│   │   ├── excel_insight.py  # Pandas DataFrame analysis
│   │   └── voice.py          # Voice formatting
│   ├── core/                 # Config & Pydantic Schemas
│   ├── main.py               # FastAPI application entry point
│   └── requirements.txt      # Python dependencies
├── frontend/                 # React frontend
│   ├── src/                  # React components and API hooks
│   ├── package.json          # Node dependencies
│   └── vite.config.ts        # Vite configuration
└── start.bat                 # Windows startup script
```

## 🔐 Security Note
Do not commit your `.env` file or expose your API keys. The repository `.gitignore` is pre-configured to ignore `.env`, uploaded user documents, and model cache files.
