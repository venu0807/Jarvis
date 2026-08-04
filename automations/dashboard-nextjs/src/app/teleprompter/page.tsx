"use client";
import React, { useEffect, useState, useRef } from "react";

interface Transcript {
  text: string;
  is_final: boolean;
}

interface AIAnswer {
  question: string;
  answer: string;
}

export default function Teleprompter() {
  const [transcripts, setTranscripts] = useState<Transcript[]>([]);
  const [aiAnswers, setAiAnswers] = useState<AIAnswer[]>([]);
  const [status, setStatus] = useState<string>("Connecting to Ghost Listener...");
  const wsRef = useRef<WebSocket | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Scroll to bottom when new answers arrive
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [transcripts, aiAnswers]);

  useEffect(() => {
    const connectWs = () => {
      const ws = new WebSocket("ws://localhost:8005/ws");
      
      ws.onopen = () => {
        setStatus("✅ Connected to Ghost Listener (Waiting for interview audio...)");
      };

      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        
        if (data.type === "transcript") {
            // Keep the last 10 transcripts to avoid clutter
            setTranscripts(prev => [...prev.slice(-9), { text: data.text, is_final: data.is_final }]);
        } else if (data.type === "ai_answer") {
            setAiAnswers(prev => [...prev, { question: data.question, answer: data.answer }]);
        }
      };

      ws.onclose = () => {
        setStatus("❌ Disconnected. Retrying in 3s...");
        setTimeout(connectWs, 3000);
      };
      
      wsRef.current = ws;
    };

    connectWs();
    return () => wsRef.current?.close();
  }, []);

  return (
    <div className="min-h-screen bg-[#0a0a0a] text-white font-sans p-8 flex flex-col items-center">
      
      {/* Header */}
      <div className="w-full max-w-5xl mb-8 flex justify-between items-center border-b border-gray-800 pb-4">
        <div>
          <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent">
            Live Teleprompter
          </h1>
          <p className="text-gray-400 text-sm mt-1">Real-Time Interview Assistant (phi4-mini)</p>
        </div>
        <div className={`px-4 py-2 rounded-full text-sm font-semibold flex items-center gap-2 ${status.includes('✅') ? 'bg-green-500/10 text-green-400 border border-green-500/20' : 'bg-red-500/10 text-red-400 border border-red-500/20'}`}>
            <span className={`w-2 h-2 rounded-full ${status.includes('✅') ? 'bg-green-400 animate-pulse' : 'bg-red-400'}`}></span>
            {status}
        </div>
      </div>

      <div className="w-full max-w-5xl grid grid-cols-1 lg:grid-cols-3 gap-6 h-[75vh]">
        
        {/* Left Column: Live Audio Transcript */}
        <div className="col-span-1 bg-[#121212] border border-gray-800 rounded-2xl p-6 flex flex-col overflow-hidden relative shadow-2xl">
          <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-blue-500 to-transparent"></div>
          <h2 className="text-xl font-semibold mb-4 text-gray-200 flex items-center gap-2">
            🎙️ Live Audio
          </h2>
          <div className="flex-1 overflow-y-auto space-y-3 scrollbar-hide">
            {transcripts.length === 0 ? (
                <p className="text-gray-500 italic text-sm">Listening for interviewer...</p>
            ) : (
                transcripts.map((t, i) => (
                    <div key={i} className={`text-sm ${t.is_final ? 'text-gray-300' : 'text-gray-500 animate-pulse'}`}>
                        {t.text}
                    </div>
                ))
            )}
            <div ref={bottomRef} />
          </div>
        </div>

        {/* Right Column: AI Answers */}
        <div className="col-span-2 bg-[#121212] border border-purple-500/30 rounded-2xl p-6 flex flex-col shadow-2xl shadow-purple-900/10 relative">
          <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-purple-500 to-blue-500"></div>
          <h2 className="text-xl font-semibold mb-6 text-purple-400 flex items-center gap-2">
            🧠 AI Teleprompter
          </h2>
          
          <div className="flex-1 overflow-y-auto space-y-6 scrollbar-hide pr-2">
            {aiAnswers.length === 0 ? (
                <div className="h-full flex flex-col items-center justify-center text-gray-600">
                    <svg className="w-16 h-16 mb-4 opacity-20" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" /></svg>
                    <p>Answers will appear here when a technical question is detected.</p>
                </div>
            ) : (
                aiAnswers.map((ans, i) => (
                    <div key={i} className="bg-[#1a1a1a] rounded-xl p-5 border border-gray-800 transition-all hover:border-purple-500/50">
                        <p className="text-sm text-gray-400 mb-3 border-b border-gray-800 pb-2">
                            <span className="font-semibold text-blue-400">Q:</span> {ans.question}
                        </p>
                        <div className="text-gray-100 text-lg leading-relaxed whitespace-pre-wrap font-medium">
                            {ans.answer}
                        </div>
                    </div>
                ))
            )}
            <div ref={bottomRef} />
          </div>
        </div>

      </div>
    </div>
  );
}
