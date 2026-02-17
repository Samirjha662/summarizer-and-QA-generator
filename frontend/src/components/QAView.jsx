import React, { useState } from 'react';
import axios from 'axios';
import { HelpCircle, Key, Send, Download, Loader2 } from 'lucide-react';
import { motion } from 'framer-motion';

const QAView = ({ text }) => {
    const [apiKey, setApiKey] = useState('');
    const [qaPairs, setQaPairs] = useState('');
    const [loading, setLoading] = useState(false);
    const [generated, setGenerated] = useState(false);

    const generateQA = async () => {
        if (!apiKey) {
            alert("Please enter your OpenAI API Key.");
            return;
        }

        setLoading(true);
        try {
            const response = await axios.post('http://localhost:8000/generate-qa', {
                text: text,
                api_key: apiKey
            });
            setQaPairs(response.data.qa_pairs);
            setGenerated(true);
        } catch (error) {
            console.error("Error generating Q&A:", error);
            alert("Failed to generate Q&A. Check your API key.");
        } finally {
            setLoading(false);
        }
    };

    const downloadQA = () => {
        const element = document.createElement("a");
        const file = new Blob([qaPairs], { type: 'text/plain' });
        element.href = URL.createObjectURL(file);
        element.download = "qa_pairs.txt";
        document.body.appendChild(element);
        element.click();
    };

    return (
        <div className="bg-white rounded-2xl shadow-xl overflow-hidden border border-slate-100 mt-8">
            <div className="p-6 bg-gradient-to-r from-emerald-50 to-white border-b border-emerald-100">
                <h2 className="text-2xl font-bold text-slate-800 flex items-center gap-2">
                    <HelpCircle className="w-6 h-6 text-emerald-600" />
                    Q&A Generator
                </h2>
                <p className="text-slate-500 mt-1">Generate conceptual questions and answers from the text.</p>
            </div>

            <div className="p-6 space-y-6">
                {!generated && (
                    <div className="flex flex-col sm:flex-row gap-4 items-end">
                        <div className="flex-1 w-full">
                            <label className="block text-sm font-medium text-slate-700 mb-1">OpenAI API Key</label>
                            <div className="relative">
                                <Key className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                                <input
                                    type="password"
                                    value={apiKey}
                                    onChange={(e) => setApiKey(e.target.value)}
                                    placeholder="sk-..."
                                    className="w-full pl-10 pr-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-transparent outline-none transition-all"
                                />
                            </div>
                            <p className="text-xs text-slate-500 mt-1">Required for Q&A generation functionality.</p>
                        </div>

                        <button
                            onClick={generateQA}
                            disabled={loading}
                            className="px-6 py-2 bg-emerald-600 text-white rounded-lg font-medium hover:bg-emerald-700 transition-colors shadow-lg flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed h-[42px]"
                        >
                            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                            Generate Q&A
                        </button>
                    </div>
                )}

                {generated && (
                    <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        className="space-y-4"
                    >
                        <div className="p-6 bg-slate-50 rounded-xl border border-slate-200 text-slate-700 whitespace-pre-wrap leading-relaxed">
                            {qaPairs}
                        </div>

                        <div className="flex justify-between items-center bg-emerald-50 p-4 rounded-lg border border-emerald-100">
                            <span className="text-sm text-emerald-800 font-medium">Generated successfully!</span>
                            <button
                                onClick={downloadQA}
                                className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-emerald-700 bg-white border border-emerald-200 rounded-lg hover:bg-emerald-50 transition-colors shadow-sm"
                            >
                                <Download className="w-4 h-4" />
                                Download Q&A
                            </button>
                        </div>
                    </motion.div>
                )}
            </div>
        </div>
    );
};

export default QAView;
