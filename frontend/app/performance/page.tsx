'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const EVAL_SESSION = 'performance-eval-session';

export default function PerformancePage() {
  const [metrics, setMetrics] = useState<any>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [statusText, setStatusText] = useState('');
  const [youtubeUrl, setYoutubeUrl] = useState('');

  // Add this new state variable near your other state declarations
  const [sources, setSources] = useState<string[]>([]);

  // Add this fetch function
  const fetchSources = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/ingest/sources/${EVAL_SESSION}`);
      const data = await res.json();
      if (data.status === 'success') {
        setSources(data.sources);
      }
    } catch (err) {
      console.error("Failed to fetch sources:", err);
    }
  };

  // Update your useEffect to fetch sources on mount
  useEffect(() => {
    const saved = localStorage.getItem('edurag_eval_results');
    if (saved) setMetrics(JSON.parse(saved));
    fetchSources(); // <-- Added
  }, []);

  // Hydrate from local storage on mount
  useEffect(() => {
    const saved = localStorage.getItem('edurag_eval_results');
    if (saved) setMetrics(JSON.parse(saved));
  }, []);

  const runEvaluationPipeline = async () => {
    setStatusText('Running RAGAS & Summary Evaluation...');
    const res = await fetch(`${API_BASE_URL}/api/evaluation/run`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: EVAL_SESSION }),
    });
    
    if (!res.ok) throw new Error('Evaluation generation failed.');
    const data = await res.json();
    
    setMetrics(data);
    localStorage.setItem('edurag_eval_results', JSON.stringify(data));
    setStatusText('Complete!');
  };

const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setIsProcessing(true);
    setStatusText(`Uploading ${file.name}...`);

    const formData = new FormData();
    formData.append('file', file);
    formData.append('session_id', EVAL_SESSION);
    
    const endpoint = file.type.startsWith('image/') ? '/api/ingest/image' : '/api/ingest/pdf';

    try {
      const res = await fetch(`${API_BASE_URL}${endpoint}`, { method: 'POST', body: formData });
      if (!res.ok) throw new Error('Upload failed');
      await fetchSources();
      // REMOVED: await runEvaluationPipeline();
      setStatusText(`Successfully ingested ${file.name}. Add more sources or run the evaluation.`);
    } catch (err: any) {
      setStatusText(`Error: ${err.message}`);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleYouTubeIngest = async () => {
    if (!youtubeUrl.trim()) return;
    setIsProcessing(true);
    setStatusText('Ingesting YouTube Video...');
    
    try {
      const res = await fetch(`${API_BASE_URL}/api/ingest/youtube`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: youtubeUrl, session_id: EVAL_SESSION }),
      });
      if (!res.ok) throw new Error('YouTube ingestion failed');
      
      setYoutubeUrl('');
      await fetchSources();
      // REMOVED: await runEvaluationPipeline();
      setStatusText('Successfully ingested YouTube video. Add more sources or run the evaluation.');
    } catch (err: any) {
      setStatusText(`Error: ${err.message}`);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleClearData = async () => {
    setIsProcessing(true);
    setStatusText('Clearing vector store...');
    try {
      await fetch(`${API_BASE_URL}/api/ingest/clear`, { method: 'POST' });
      localStorage.removeItem('edurag_eval_results');
      setMetrics(null);
      await fetchSources();
      setStatusText('Data cleared successfully.');
    } catch (err: any) {
      setStatusText(`Error: ${err.message}`);
    } finally {
      setIsProcessing(false);
    }
  };

  const MetricCard = ({ title, score }: { title: string, score: number }) => (
    <div className="bg-white border border-slate-200 p-5 rounded-2xl shadow-sm flex flex-col justify-between">
      <span className="text-sm font-semibold text-slate-600 capitalize">{title.replace('_', ' ')}</span>
      <div className="mt-4 flex items-end gap-2">
        <span className="text-3xl font-bold text-slate-900">{(score * 100).toFixed(0)}%</span>
        <span className="text-xs text-slate-400 mb-1">accuracy</span>
      </div>
      <div className="w-full bg-slate-100 h-2 mt-4 rounded-full overflow-hidden">
        <div 
          className={`h-full rounded-full transition-all duration-1000 ${score > 0.8 ? 'bg-emerald-500' : score > 0.6 ? 'bg-amber-400' : 'bg-red-500'}`} 
          style={{ width: `${score * 100}%` }}
        />
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-slate-50 p-10 font-sans text-slate-900">
      <div className="max-w-5xl mx-auto space-y-8">
        <header className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">RAG Performance Dashboard</h1>
            <p className="text-sm text-slate-500 mt-1">LLM-as-a-judge automated benchmarking.</p>
          </div>
          <div className="flex gap-3">
            <Link href="/" className="px-4 py-2 bg-white border border-slate-200 text-slate-700 rounded-xl text-sm font-medium hover:bg-slate-50 transition-colors shadow-sm">
              Back to Chat
            </Link>
            <button 
              onClick={handleClearData} 
              disabled={isProcessing}
              className="px-4 py-2 bg-red-50 text-red-600 border border-red-200 rounded-xl text-sm font-medium hover:bg-red-100 transition-colors shadow-sm disabled:opacity-50"
            >
              Clear Data
            </button>
          </div>
        </header>

        {/* Upload Controls */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4 relative group">
            <h3 className="font-semibold text-sm">Ingest PDF/Image for Evaluation</h3>
            <input type="file" accept=".pdf,image/*" onChange={handleFileUpload} disabled={isProcessing} className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-10" />
            <div className="w-full p-6 border-2 border-dashed border-slate-200 rounded-xl bg-slate-50 flex flex-col items-center justify-center gap-2 group-hover:border-blue-400 transition-colors">
              <span className="text-sm font-medium text-slate-600">Drag & drop or click to upload</span>
            </div>
          </div>

          <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
            <h3 className="font-semibold text-sm">Ingest YouTube for Evaluation</h3>
            <div className="flex gap-2">
              <input type="text" placeholder="YouTube URL..." value={youtubeUrl} onChange={(e) => setYoutubeUrl(e.target.value)} disabled={isProcessing} className="flex-1 px-4 py-2 text-sm bg-slate-50 border border-slate-200 rounded-xl outline-none focus:border-blue-400" />
              <button onClick={handleYouTubeIngest} disabled={isProcessing || !youtubeUrl} className="px-4 py-2 bg-slate-900 text-white rounded-xl text-sm font-medium disabled:opacity-50">
                Run
              </button>
            </div>
          </div>
        </div>

        {/* Active Library Section */}
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold text-sm text-slate-800">Current Evaluation Library</h3>
            <span className="text-xs font-bold bg-slate-100 text-slate-500 px-2.5 py-1 rounded-lg">
              {sources.length} {sources.length === 1 ? 'Source' : 'Sources'}
            </span>
          </div>
          
          {sources.length === 0 ? (
            <div className="p-6 bg-slate-50 rounded-xl border border-slate-200 border-dashed text-center">
              <p className="text-sm text-slate-500 font-medium">No sources uploaded for this evaluation session yet.</p>
            </div>
          ) : (
            <ul className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {sources.map((source, i) => (
                <li key={i} className="flex items-center gap-3 bg-slate-50 p-3 rounded-xl border border-slate-100 shadow-sm">
                  <div className="w-8 h-8 rounded-lg bg-white flex items-center justify-center shrink-0 border border-slate-200 shadow-sm">
                    {source.startsWith('YouTube') ? '🎥' : '📄'}
                  </div>
                  <span className="truncate text-sm text-slate-700 font-medium" title={source}>
                    {source.replace('YouTube: ', '')}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* --- NEW EVALUATION TRIGGER SECTION --- */}
        <div className="flex flex-col items-center justify-center p-8 bg-white border border-slate-200 rounded-2xl shadow-sm space-y-4">
          <p className="text-sm text-slate-500">Upload all required materials above, then run the benchmark.</p>
          <button 
            onClick={runEvaluationPipeline} 
            disabled={isProcessing}
            className="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-xl font-semibold shadow-sm transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            {isProcessing && statusText.includes('Evaluating') ? (
              <div className="w-4 h-4 border-2 border-white/20 border-t-white rounded-full animate-spin" />
            ) : null}
            Run RAGAS Evaluation
          </button>
        </div>

        {statusText && (
          <div className="p-4 bg-blue-50 border border-blue-200 text-blue-800 rounded-xl text-sm font-medium animate-pulse">
            {statusText}
          </div>
        )}

        {/* Results */}
        {metrics && (
          <div className="space-y-12 animate-in fade-in slide-in-from-bottom-4 duration-500">
            
            {/* RAGAS Section */}
            <section>
              <h2 className="text-xl font-bold mb-4">RAGAS Framework Scores</h2>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                {Object.entries(metrics.ragas_metrics).map(([key, val]) => (
                  <MetricCard key={key} title={key} score={val as number} />
                ))}
              </div>
              
              {/* Show the Q&A Pairs */}
              <div className="bg-white border border-slate-200 rounded-2xl overflow-hidden shadow-sm">
                <div className="px-5 py-4 bg-slate-50 border-b border-slate-200">
                  <h3 className="font-semibold text-sm text-slate-700">Synthetic Q&A Evaluation</h3>
                </div>
                <div className="divide-y divide-slate-100">
                  {metrics.qa_details?.map((qa: any, idx: number) => (
                    <div key={idx} className="p-5 space-y-3">
                      <div>
                        <span className="text-[11px] font-bold uppercase tracking-widest text-slate-400">Question {idx + 1}</span>
                        <p className="text-sm font-medium text-slate-900 mt-1">{qa.question}</p>
                      </div>
                      <div className="pl-4 border-l-2 border-blue-200">
                        <span className="text-[11px] font-bold uppercase tracking-widest text-blue-500">System Answer</span>
                        <p className="text-sm text-slate-700 mt-1">{qa.generated_answer}</p>
                      </div>
                      <div className="pl-4 border-l-2 border-emerald-200">
                        <span className="text-[11px] font-bold uppercase tracking-widest text-emerald-600">Ground Truth</span>
                        <p className="text-sm text-slate-700 mt-1">{qa.ground_truth}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </section>

            {/* Summary Section */}
            <section>
              <h2 className="text-xl font-bold mb-4">Summary Feature Scores</h2>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                {Object.entries(metrics.summary_metrics).map(([key, val]) => (
                  <MetricCard key={key} title={key} score={val as number} />
                ))}
              </div>
              
              {/* Show the Generated Summary */}
              <div className="bg-white border border-slate-200 rounded-2xl overflow-hidden shadow-sm">
                <div className="px-5 py-4 bg-slate-50 border-b border-slate-200">
                  <h3 className="font-semibold text-sm text-slate-700">Generated Summary Evaluated</h3>
                </div>
                <div className="p-5 text-sm text-slate-700 leading-relaxed whitespace-pre-wrap">
                  {metrics.summary_text}
                </div>
              </div>
            </section>

          </div>
        )}
      </div>
    </div>
  );
}