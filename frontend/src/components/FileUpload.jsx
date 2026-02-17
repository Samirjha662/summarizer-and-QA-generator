import React, { useState, useRef } from 'react';
import { Upload, FileText, CheckCircle, Loader2 } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const FileUpload = ({ onFileSelected, isUploading }) => {
    const [dragActive, setDragActive] = useState(false);
    const inputRef = useRef(null);

    const handleDrag = (e) => {
        e.preventDefault();
        e.stopPropagation();
        if (e.type === "dragenter" || e.type === "dragover") {
            setDragActive(true);
        } else if (e.type === "dragleave") {
            setDragActive(false);
        }
    };

    const handleDrop = (e) => {
        e.preventDefault();
        e.stopPropagation();
        setDragActive(false);
        if (e.dataTransfer.files && e.dataTransfer.files[0]) {
            handleFile(e.dataTransfer.files[0]);
        }
    };

    const handleChange = (e) => {
        e.preventDefault();
        if (e.target.files && e.target.files[0]) {
            handleFile(e.target.files[0]);
        }
    };

    const handleFile = (file) => {
        if (file.type === "application/pdf") {
            onFileSelected(file);
        } else {
            alert("Please upload a PDF file.");
        }
    };

    const onButtonClick = () => {
        inputRef.current.click();
    };

    return (
        <div
            className={`relative w-full max-w-xl mx-auto p-8 border-2 border-dashed rounded-xl transition-all duration-300 ease-in-out
        ${dragActive ? "border-primary bg-primary/5" : "border-slate-300 bg-white"}
      `}
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
        >
            <input
                ref={inputRef}
                type="file"
                className="hidden"
                multiple={false}
                onChange={handleChange}
                accept=".pdf"
            />

            <div className="flex flex-col items-center justify-center text-center space-y-4">
                <AnimatePresence mode="wait">
                    {isUploading ? (
                        <motion.div
                            key="loading"
                            initial={{ scale: 0.8, opacity: 0 }}
                            animate={{ scale: 1, opacity: 1 }}
                            exit={{ scale: 0.8, opacity: 0 }}
                        >
                            <Loader2 className="w-16 h-16 text-primary animate-spin" />
                            <p className="mt-2 text-primary font-medium">Extracting text...</p>
                        </motion.div>
                    ) : (
                        <motion.div
                            key="upload"
                            initial={{ scale: 0.8, opacity: 0 }}
                            animate={{ scale: 1, opacity: 1 }}
                            exit={{ scale: 0.8, opacity: 0 }}
                            className="flex flex-col items-center"
                        >
                            <div className="p-4 bg-indigo-50 rounded-full mb-2">
                                <Upload className="w-8 h-8 text-primary" />
                            </div>
                            <h3 className="text-xl font-semibold text-slate-800">Upload your PDF</h3>
                            <p className="text-slate-500 mt-1 mb-4">Drag and drop or click to browse</p>
                            <button
                                onClick={onButtonClick}
                                className="px-6 py-2 bg-primary text-white rounded-lg font-medium hover:bg-indigo-700 transition-colors shadow-lg hover:shadow-xl"
                            >
                                Select File
                            </button>
                        </motion.div>
                    )}
                </AnimatePresence>
            </div>

            {dragActive && (
                <div className="absolute inset-0 w-full h-full bg-primary/10 rounded-xl" pointerEvents="none"></div>
            )}
        </div>
    );
};

export default FileUpload;
