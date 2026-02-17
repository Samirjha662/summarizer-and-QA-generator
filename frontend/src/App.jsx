import React, { useState } from 'react';
import FileUpload from './components/FileUpload';
import SummaryView from './components/SummaryView';
import QAView from './components/QAView';
import axios from 'axios';
import { BookOpen } from 'lucide-react';

function App() {
  const [extractedText, setExtractedText] = useState('');
  const [isUploading, setIsUploading] = useState(false);
  const [fileName, setFileName] = useState('');

  const handleFileSelected = async (file) => {
    setIsUploading(true);
    setFileName(file.name);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await axios.post('http://localhost:8000/extract-text', formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });
      setExtractedText(response.data.text);
    } catch (error) {
      console.error("Error uploading file:", error);
      alert("Failed to extract text from PDF.");
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 pb-20">
      {/* Header */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-50">
        <div className="max-w-5xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-indigo-600 rounded-lg flex items-center justify-center text-white">
              <BookOpen className="w-5 h-5" />
            </div>
            <h1 className="text-xl font-bold text-slate-900 tracking-tight">Intelligent Summarizer</h1>
          </div>
          <div className="text-sm text-slate-500 font-medium">
            v1.0.0
          </div>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-6 py-12">
        <div className="space-y-12">

          {/* File Upload Section */}
          <section className="space-y-6 text-center">
            <div className="space-y-2">
              <h1 className="text-4xl font-extrabold text-slate-900 tracking-tight">
                Summarize Books & PDFs with AI
              </h1>
              <p className="text-lg text-slate-500 max-w-2xl mx-auto">
                Instantly generate concise summaries and conceptual questions from any PDF document.
              </p>
            </div>

            <FileUpload onFileSelected={handleFileSelected} isUploading={isUploading} />
          </section>

          {/* Results Section */}
          {extractedText && (
            <div className="animate-in fade-in slide-in-from-bottom-8 duration-700">
              <div className="flex items-center gap-2 mb-6 ml-1">
                <div className="w-2 h-2 rounded-full bg-green-500"></div>
                <span className="text-sm font-medium text-slate-500">Processing: {fileName}</span>
              </div>

              <SummaryView text={extractedText} />
              <QAView text={extractedText} />
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

export default App;
