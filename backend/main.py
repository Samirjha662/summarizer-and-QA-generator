from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import uvicorn
import shutil
import os

from backend.text_extractor import extract_text_from_pdf, clean_text
from backend.summarizer import generate_summary
from backend.question_generator import generate_qa_pairs

app = FastAPI(title="Intelligent PDF Summarizer API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # For development, allow all. In production, restrict to frontend domain.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class TextRequest(BaseModel):
    text: str
    summary_type: str = "concise" # concise or detailed

class QARequest(BaseModel):
    text: str
    api_key: Optional[str] = None

@app.get("/")
def read_root():
    return {"message": "Welcome to Intelligent PDF Summarizer API"}

@app.post("/extract-text")
async def extract_text(file: UploadFile = File(...)):
    try:
        # Save temp file
        temp_file = f"temp_{file.filename}"
        with open(temp_file, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        with open(temp_file, "rb") as f:
            raw_text = extract_text_from_pdf(f)
            
        cleaned_text = clean_text(raw_text)
        
        # Cleanup
        os.remove(temp_file)
        
        if not cleaned_text:
            raise HTTPException(status_code=400, detail="Could not extract text from PDF")
            
        return {"text": cleaned_text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/summarize")
async def summarize(request: TextRequest):
    try:
        summary = generate_summary(request.text, request.summary_type)
        return {"summary": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/generate-qa")
async def generate_qa(request: QARequest):
    try:
        if not request.api_key:
             # In a real app, we might fallback to a local model or return an error
             # For this demo, we require it as per original design or use a strict instruction
             pass
             
        qa_pairs = generate_qa_pairs(request.text, request.api_key)
        return {"qa_pairs": qa_pairs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
