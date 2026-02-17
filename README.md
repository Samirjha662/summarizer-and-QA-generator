# Intelligent PDF Summarizer & Q/A Generator

This application uses AI to summarize PDFs and generate Question-Answer pairs.
It features a **FastAPI** backend and a **React (Vite 5)** frontend.

## 🛠️ Setup

### 1. Backend Setup

1.  **Install Python Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
2.  **Start Backend Server**:
    ```bash
    uvicorn backend.main:app --reload --port 8000
    ```
    The API will run at `http://localhost:8000`.

### 2. Frontend Setup

1.  **Navigate to Frontend**:
    ```bash
    cd frontend
    ```
2.  **Install Node Dependencies**:
    ```bash
    npm install
    # If not already installed:
    # npm install axios lucide-react framer-motion clsx tailwind-merge
    ```
3.  **Start Frontend Server**:
    ```bash
    npm run dev
    ```
    The App will run at `http://localhost:5173`.

## ✨ Features

- **Text Extraction**: Extracts text from standard PDFs.
- **Summarization**: Generates Concise and Detailed summaries using Hugging Face Transformers.
- **Q&A Generation**: Uses OpenAI (via LangChain) to generate conceptual questions and answers.
- **Modern UI**: Built with React, Tailwind CSS, and Framer Motion for smooth animations.

## 📝 API Key
- The "Generate Q&A" feature requires an OpenAI API key. Enter it in the UI when prompted.
