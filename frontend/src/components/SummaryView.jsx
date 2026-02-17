import React, { useState } from 'react';
import axios from 'axios';
import { FileText, Download, Sparkles, Loader2 } from 'lucide-react';
import { motion } from 'framer-motion';

const SummaryView = ({ text }) => {
    const [summaryType, setSummaryType] = useState('concise');
    const [summary, setSummary] = useState('');
    const [loading, setLoading] = useState(false);
    const [generated, setGenerated] = useState(false);

    const generateSummary = async (type) => {
        setLoading(true);
        setSummaryType(type);
        try {
            const response = await axios.post('http://localhost:8000/summarize', {
                text: text,
                summary_type: type
            });
            setSummary(response.data.summary);
            setGenerated(true);
        } catch (error) {
            console.error("Error generating summary:", error);
            alert("Failed to generate summary.");
        } finally {
            setLoading(false);
        }
    };

    const downloadSummary = () => {
        const element = document.createElement("a");
        const file = new Blob([summary], { type: 'text/plain' });
        element.href = URL.createObjectURL(file);
        element.download = `${summaryType}_summary.txt`;
        document.body.appendChild(element);
        element.click();
    };

    return (
        <div className="bg-white rounded-2xl shadow-xl overflow-hidden border border-slate-100">
            <div className="p-6 bg-gradient-to-r from-indigo-50 to-white border-b border-indigo-100">
                <h2 className="text-2xl font-bold text-slate-800 flex items-center gap-2">
                    <Sparkles className="w-6 h-6 text-primary" />
                    AI Summary
                </h2>
                <p className="text-slate-500 mt-1">Generate concise or detailed summaries of your document.</p>
            </div>

            <div className="p-6">
                <div className="flex flex-wrap gap-4 mb-6">
                    <button
                        onClick={() => generateSummary('concise')}
                        disabled={loading}
                        className={`flex-1 py-3 px-4 rounded-xl font-medium transition-all duration-200 flex items-center justify-center gap-2
              ${summaryType === 'concise' && generated
                                ? 'bg-primary text-white shadow-lg ring-2 ring-indigo-200'
                                : 'bg-white border border-slate-200 text-slate-600 hover:bg-slate-50 hover:border-slate-300'}
            `}
                    >
                        {loading && summaryType === 'concise' ? <Loader2 className="w-5 h-5 animate-spin" /> : <FileText className="w-5 h-5" />}
                        Concise Summary
                    </button>

                    <button
                        onClick={() => generateSummary('detailed')}
                        disabled={loading}
                        className={`flex-1 py-3 px-4 rounded-xl font-medium transition-all duration-200 flex items-center justify-center gap-2
              ${summaryType === 'detailed' && generated
                                ? 'bg-secondary text-white shadow-lg ring-2 ring-pink-200'
                                : 'bg-white border border-slate-200 text-slate-600 hover:bg-slate-50 hover:border-slate-300'}
            `}
                    >
                        {loading && summaryType === 'detailed' ? <Loader2 className="w-5 h-5 animate-spin" /> : <FileText className="w-5 h-5" />}
                        Detailed Summary
                    </button>
                </div>

                {generated && (
                    <motion.div
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="space-y-4"
                    >
                        <div className="p-6 bg-slate-50 rounded-xl border border-slate-200 text-slate-700 leading-relaxed text-lg min-h-[200px]">
                            {summary}
                        </div>

                        <div className="flex justify-end">
                            <button
                                onClick={downloadSummary}
                                className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-slate-600 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 transition-colors"
                            >
                                <Download className="w-4 h-4" />
                                Download Text
                            </button>
                        </div>
                    </motion.div>
                )}
            </div>
        </div>
    );
};

export default SummaryView;
