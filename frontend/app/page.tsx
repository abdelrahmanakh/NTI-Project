'use client';
import React, { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import { Citation, ChatMessage, ChatSession } from './types';
import Link from 'next/link'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function EducationalChatbot() {
  // --- Sessions & History State ---
  const [sessions, setSessions] = useState<ChatSession[]>([
    {
      id: 'default-session',
      title: 'New Discussion',
      createdAt: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      messages: [
        {
          id: 'welcome',
          role: 'assistant',
          content: 'Hello! I am your AI learning assistant. Upload documents or YouTube links on the right panel, then ask me anything about your materials.',
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        },
      ],
      uploadedFiles: [], // Initialize isolated files array
    },
  ]);
  const [currentSessionId, setCurrentSessionId] = useState<string>('default-session');

  // --- Derived State for Active Session ---
  const currentSession = sessions.find((s) => s.id === currentSessionId) || sessions[0];
  const uploadedFiles = currentSession.uploadedFiles || [];

  // --- Chat State ---
  const [inputMessage, setInputMessage] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // --- Tool Selection State ---
  const [selectedTool, setSelectedTool] = useState<string>('chat');
  const [isToolMenuOpen, setIsToolMenuOpen] = useState(false);
  const [isMounted, setIsMounted] = useState(false);

  // --- Resizable Panels State ---
  const [leftWidth, setLeftWidth] = useState(256);
  const [rightWidth, setRightWidth] = useState(384);
  const [isDraggingLeft, setIsDraggingLeft] = useState(false);
  const [isDraggingRight, setIsDraggingRight] = useState(false);

  // --- Right Panel State (Sources & Citations) ---
  const [activeTab, setActiveTab] = useState<'sources' | 'inspector' | 'preview'>('inspector');
  const [selectedCitation, setSelectedCitation] = useState<Citation | null>(null);
  const [previewData, setPreviewData] = useState<{ url: string; type: 'pdf' | 'youtube' | 'image'; title: string } | null>(null);
  const [youtubeUrl, setYoutubeUrl] = useState('');
  const [isUploading, setIsUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState<string | null>(null);

  // --- Helper: Add file to active session ---
  const addFileToSession = (fileName: string) => {
    setSessions((prev) =>
      prev.map((session) =>
        session.id === currentSessionId
          ? { ...session, uploadedFiles: [...(session.uploadedFiles || []), fileName] }
          : session
      )
    );
  };

  // --- Resizing Event Listeners ---
  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (isDraggingLeft) {
        const newWidth = Math.max(200, Math.min(e.clientX, 500));
        setLeftWidth(newWidth);
      } else if (isDraggingRight) {
        const newWidth = Math.max(300, Math.min(window.innerWidth - e.clientX, 800));
        setRightWidth(newWidth);
      }
    };
    const handleMouseUp = () => {
      setIsDraggingLeft(false);
      setIsDraggingRight(false);
    };
    if (isDraggingLeft || isDraggingRight) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
    }
    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isDraggingLeft, isDraggingRight]);

  const toolsList = [
    { id: 'chat', label: 'Chat', icon: ' ' },
    { id: 'summarize', label: 'Summarize', icon: ' ' },
    { id: 'explain', label: 'Explain Topic', icon: ' ' },
    { id: 'quiz', label: 'Generate Quiz', icon: ' ' },
    { id: 'flashcards', label: 'Flashcards', icon: ' ' },
    { id: 'study-guide', label: 'Study Guide', icon: ' ' },
    { id: 'podcast', label: 'Podcast', icon: ' ' },
  ];

  // Auto-scroll chat to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [currentSession.messages, isStreaming]);

  // --- Local Storage Synchronization ---
  useEffect(() => {
    setIsMounted(true);
    // Note: edurag_files is removed since uploadedFiles is now part of edurag_sessions
    const savedSessions = localStorage.getItem('edurag_sessions');
    if (savedSessions) setSessions(JSON.parse(savedSessions));
    const savedSessionId = localStorage.getItem('edurag_current_session');
    if (savedSessionId) setCurrentSessionId(savedSessionId);
  }, []);

  useEffect(() => {
    if (isMounted) {
      localStorage.setItem('edurag_sessions', JSON.stringify(sessions));
      localStorage.setItem('edurag_current_session', currentSessionId);
    }
  }, [sessions, currentSessionId, isMounted]);

  // --- Handlers: Chat Session Management ---
  const handleNewChat = () => {
    // Generate new unique session ID instead of clearing the database
    const newSessionId = `session-${Date.now()}`;
    const resetSession: ChatSession = {
      id: newSessionId,
      title: 'New Discussion',
      createdAt: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      messages: [
        {
          id: `welcome-${Date.now()}`,
          role: 'assistant',
          content: 'Hello! I am your AI learning assistant. Upload documents or YouTube links on the right panel, then ask me anything about your materials.',
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        },
      ],
      uploadedFiles: [], // Clean slate for the new session
    };
    
    setSessions((prev) => [resetSession, ...prev]);
    setCurrentSessionId(newSessionId);
    setSelectedCitation(null);
    setUploadStatus(null);
    setYoutubeUrl('');
  };

  // --- Handlers: Ingestion ---
  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setIsUploading(true);
    setUploadStatus(`Uploading and processing ${file.name}...`);
    
    const formData = new FormData();
    formData.append('file', file);
    formData.append('session_id', currentSessionId); // Inject active session ID

    const isImage = file.type.startsWith('image/');
    const endpoint = isImage ? '/api/ingest/image' : '/api/ingest/pdf';
    
    try {
      const res = await fetch(`${API_BASE_URL}${endpoint}`, {
        method: 'POST',
        body: formData,
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Upload failed');
      
      addFileToSession(file.name); // Append to session state
      setUploadStatus(`Uploaded ${file.name} successfully! (${data.chunks_processed} chunks)`);
    } catch (err: any) {
      setUploadStatus(`Error: ${err.message}`);
    } finally {
      setIsUploading(false);
    }
  };

  const handleYouTubeIngest = async () => {
    if (!youtubeUrl.trim()) return;
    setIsUploading(true);
    setUploadStatus('Extracting YouTube transcript & generating embeddings...');
    
    try {
      const res = await fetch(`${API_BASE_URL}/api/ingest/youtube`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: youtubeUrl, session_id: currentSessionId }), // Inject active session ID
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'YouTube ingestion failed');
      
      addFileToSession(`YouTube: ${youtubeUrl}`); // Append to session state
      setYoutubeUrl('');
      setUploadStatus(`YouTube video indexed! (${data.chunks_processed} chunks)`);
    } catch (err: any) {
      setUploadStatus(`Error: ${err.message}`);
    } finally {
      setIsUploading(false);
    }
  };

  // --- Handlers: Chat Stream & Tools Handling ---
  const handleSendMessage = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    const isToolWithoutInput = ['summarize', 'study-guide'].includes(selectedTool);
    if (isStreaming || uploadedFiles.length === 0) return;
    if (!isToolWithoutInput && !inputMessage.trim()) return;
    
    const userQuery = inputMessage.trim();
    const displayMessage = isToolWithoutInput 
        ? `Generate ${toolsList.find(t => t.id === selectedTool)?.label}`
        : userQuery;
        
    setInputMessage('');
    
    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: displayMessage,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };
    const assistantMessageId = `assistant-${Date.now()}`;
    const initialAssistantMessage: ChatMessage = {
      id: assistantMessageId,
      role: 'assistant',
      content: '',
      citations: [],
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };
    
    setSessions((prev) =>
      prev.map((session) =>
        session.id === currentSessionId
          ? {
              ...session,
              title: session.messages.length === 1 ? displayMessage.slice(0, 24) + '...' : session.title,
              messages: [...session.messages, userMessage, initialAssistantMessage],
            }
          : session
      )
    );
    
    setIsStreaming(true);
    
    try {
      if (selectedTool === 'chat') {
        // ==========================================
        // 1. STANDARD STREAMING CHAT
        // ==========================================
        const response = await fetch(`${API_BASE_URL}/api/tutor/chat`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ question: userQuery, top_k: 4, session_id: currentSessionId }), // Inject session ID
        });
        
        if (!response.body) throw new Error('No response stream received');
        const reader = response.body.getReader();
        const decoder = new TextDecoder('utf-8');
        let buffer = '';
        
        while (true) {
          const { value, done } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n\n');
          buffer = lines.pop() || '';
          
          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const rawJson = line.replace('data: ', '').trim();
              if (!rawJson) continue;
              
              try {
                const event = JSON.parse(rawJson);
                if (event.type === 'citations') {
                  const citations: Citation[] = event.data;
                  setSessions((prev) =>
                    prev.map((session) =>
                      session.id === currentSessionId
                        ? { ...session, messages: session.messages.map((msg) => msg.id === assistantMessageId ? { ...msg, citations } : msg) }
                        : session
                    )
                  );
                  if (citations.length > 0) {
                    setSelectedCitation(citations[0]);
                    setActiveTab('inspector');
                  }
                } else if (event.type === 'token') {
                  setSessions((prev) =>
                    prev.map((session) =>
                      session.id === currentSessionId
                        ? { ...session, messages: session.messages.map((msg) => msg.id === assistantMessageId ? { ...msg, content: msg.content + event.data } : msg) }
                        : session
                    )
                  );
                } else if (event.type === 'done') {
                  setIsStreaming(false);
                }
              } catch (err) {
                console.error('Error parsing SSE event:', err);
              }
            }
          }
        }
      } else {
        // ==========================================
        // 2. NON-STREAMING TOOL API CALLS
        // ==========================================
        let endpoint = '';
        // Inject session_id into tool payloads
        const payload: any = { top_k: 6, session_id: currentSessionId };
        
        switch (selectedTool) {
          case 'summarize': endpoint = '/api/tools/summarize'; break;
          case 'study-guide': endpoint = '/api/tools/study-guide'; break;
          case 'explain': 
            endpoint = '/api/tools/explain';
            payload.topic = userQuery;
            break;
          case 'podcast':
            endpoint = '/api/tools/podcast';
            payload.topic = userQuery;
            break;
          case 'quiz': endpoint = '/api/tools/quiz'; break;
          case 'flashcards': endpoint = '/api/tools/flashcards'; break;
        }
        
        const response = await fetch(`${API_BASE_URL}${endpoint}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || 'Tool execution failed');
        
        // Format the JSON response into readable markdown text
        let finalResponseText = '';
        if (selectedTool === 'quiz' && data.questions) {
          finalResponseText = "### Practice Quiz\n\n" + data.questions.map((q: any, i: number) => 
            `**${i + 1}. ${q.question}**\n` + 
            q.options.map((o: any) => `- ${o.text}`).join('\n') + 
            `\n\n*Answer:* ${q.correct_option_id}\n*Explanation:* ${q.explanation}`
          ).join('\n\n---\n\n');
        } else if (selectedTool === 'flashcards' && data.flashcards) {
          finalResponseText = "### Study Flashcards\n\n" + data.flashcards.map((f: any, i: number) => 
            `**Card ${i + 1}:**\n*Front:* ${f.front}\n*Back:* ${f.back}`
          ).join('\n\n---\n\n');
        } else if (selectedTool === 'podcast') {
          finalResponseText = `  **Podcast Ready!** [Listen to Audio](${data.audio_url})\n\n### Script:\n${data.script}`;
        } else {
          finalResponseText = data.data || JSON.stringify(data);
        }
        
        setSessions((prev) =>
          prev.map((session) =>
            session.id === currentSessionId
              ? {
                  ...session,
                  messages: session.messages.map((msg) =>
                    msg.id === assistantMessageId
                      ? { ...msg, content: finalResponseText }
                      : msg
                  ),
                }
              : session
          )
        );
      }
    } catch (error: any) {
      console.error('Error in chat/tool processing:', error);
      setSessions((prev) =>
        prev.map((session) =>
          session.id === currentSessionId
            ? {
                ...session,
                messages: session.messages.map((msg) =>
                  msg.id === assistantMessageId
                    ? { ...msg, content: `Error: ${error.message || 'Failed to reach AI service'}` }
                    : msg
                ),
              }
            : session
        )
      );
    } finally {
      setIsStreaming(false);
    }
  };
  if (!isMounted) {
    return <div className="flex h-screen w-full bg-slate-50 items-center justify-center text-slate-400">Loading...</div>;
  }

  return (
    <div 
      className="flex h-screen w-full bg-slate-50 text-slate-900 font-sans overflow-hidden antialiased selection:bg-blue-200 selection:text-blue-900"
      style={{ 
        cursor: isDraggingLeft || isDraggingRight ? 'col-resize' : 'default',
        userSelect: isDraggingLeft || isDraggingRight ? 'none' : 'auto' 
      }}
    >
      
      {/* ========================================================= */}
      {/* 1. LEFT SIDEBAR: Navigation & History                     */}
      {/* ========================================================= */}
      <nav 
        style={{ width: `${leftWidth}px` }}
        className="flex-shrink-0 bg-[#0a0a0a] text-slate-300 flex flex-col border-r border-slate-800 z-20 relative"
      >
        <div className="px-3 pb-4 space-y-2">
          <Link href="/performance" className="w-full flex items-center justify-center gap-2 py-2.5 px-4 border border-white/10 hover:bg-white/10 text-slate-300 rounded-xl font-medium text-sm transition-all duration-200">
            <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 0 1 3 19.875v-6.75ZM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V8.625ZM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V4.125Z" /></svg>
            Evaluation Dashboard
          </Link>
        </div>
        <div className="p-5 flex items-center justify-between">
          <h1 className="text-sm font-semibold text-white tracking-wide">EduRAG Assistant</h1>
        </div>

        <div className="px-3 pb-4">
          <button
            onClick={handleNewChat}
            aria-label="Start a new chat"
            className="w-full flex items-center justify-center gap-2 py-2.5 px-4 bg-white/10 hover:bg-white/20 text-white rounded-xl font-medium text-sm transition-all duration-200"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" /></svg>
            New Chat
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-3 py-2 space-y-1 [&::-webkit-scrollbar]:hidden [-ms-overflow-style:none] [scrollbar-width:none]">
          <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500 px-3 block mb-3">
            Recent Sessions
          </span>
          {sessions.map((session) => {
            const isActive = session.id === currentSessionId;
            return (
              <button
                key={session.id}
                onClick={() => {
                  setCurrentSessionId(session.id);
                  const lastAssistantMsg = [...session.messages].reverse().find((m) => m.role === 'assistant' && m.citations?.length);
                  if (lastAssistantMsg?.citations?.length) {
                    setSelectedCitation(lastAssistantMsg.citations[0]);
                  }
                }}
                className={`w-full text-left p-3 rounded-xl text-sm transition-all duration-200 flex flex-col group ${
                  isActive 
                    ? 'bg-blue-600/10 text-blue-400 font-medium' 
                    : 'text-slate-400 hover:bg-white/5 hover:text-slate-200'
                }`}
              >
                <span className="truncate w-full block">{session.title}</span>
                <span className={`text-[11px] mt-1 ${isActive ? 'text-blue-500/70' : 'text-slate-600 group-hover:text-slate-400'}`}>
                  {session.createdAt}
                </span>
              </button>
            );
          })}
        </div>
      </nav>

      {/* LEFT DRAG HANDLE */}
      <div 
        onMouseDown={() => setIsDraggingLeft(true)}
        className="w-1.5 -ml-[3px] z-50 cursor-col-resize hover:bg-blue-500/50 active:bg-blue-500 transition-colors"
      />

      {/* ========================================================= */}
      {/* 2. MIDDLE PANEL: Main Chat Interface                      */}
      {/* ========================================================= */}
      <main className="flex-1 flex flex-col bg-white relative min-w-[400px] shadow-[-4px_0_24px_rgba(0,0,0,0.02)] z-10">
        
        {/* Header */}
        <header className="h-16 border-b border-slate-100 px-6 flex items-center justify-between bg-white/90 backdrop-blur-md sticky top-0 z-10">
          <div>
            <h2 className="font-semibold text-slate-800 text-sm">{currentSession.title}</h2>
            <p className="text-[11px] text-slate-500 font-medium">Grounding responses in verified context</p>
          </div>
        </header>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-6 space-y-8 scroll-smooth">
          {currentSession.messages.map((msg) => {
            const isUser = msg.role === 'user';
            return (
              <div key={msg.id} className={`flex flex-col w-full ${isUser ? 'items-end' : 'items-start'}`}>
                <div
                  className={`max-w-[85%] md:max-w-[75%] p-4 sm:p-5 rounded-2xl text-[15px] leading-relaxed shadow-sm transition-all ${
                    isUser
                      ? 'bg-slate-900 text-white rounded-br-sm'
                      : 'bg-white text-slate-800 border border-slate-200 rounded-bl-sm shadow-[0_2px_12px_rgba(0,0,0,0.02)]'
                  }`}
                >
                  <div className="w-full break-words prose prose-sm max-w-none prose-p:leading-relaxed prose-pre:bg-slate-800 prose-pre:text-slate-100">
                    <ReactMarkdown
                      components={{
                        h1: ({ node, ...props }) => <h1 className="text-xl font-bold mt-6 mb-3 text-inherit" {...props} />,
                        h2: ({ node, ...props }) => <h2 className="text-lg font-bold mt-5 mb-3 text-inherit" {...props} />,
                        h3: ({ node, ...props }) => <h3 className="text-base font-semibold mt-4 mb-2 text-inherit" {...props} />,
                        p: ({ node, ...props }) => <p className="mb-4 last:mb-0" {...props} />,
                        ul: ({ node, ...props }) => <ul className="list-disc pl-5 mb-4 space-y-2 marker:text-slate-400" {...props} />,
                        ol: ({ node, ...props }) => <ol className="list-decimal pl-5 mb-4 space-y-2 marker:text-slate-400" {...props} />,
                        li: ({ node, ...props }) => <li className="" {...props} />,
                        strong: ({ node, ...props }) => <strong className="font-semibold text-inherit" {...props} />,
                        a: ({ node, ...props }) => <a className="text-blue-600 hover:text-blue-700 underline underline-offset-4 decoration-blue-300" target="_blank" rel="noopener noreferrer" {...props} />,
                      }}
                    >
                      {msg.content || (isStreaming ? 'Thinking...' : '')}
                    </ReactMarkdown>
                  </div>

                  {/* Grounded Citation Badges */}
                  {!isUser && msg.citations && msg.citations.length > 0 && (
                    <div className="mt-4 pt-4 border-t border-slate-100 flex flex-wrap gap-2 items-center">
                      <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mr-1">Sources</span>
                      {msg.citations.map((cite, index) => (
                        <button
                          key={index}
                          onClick={() => {
                            setSelectedCitation(cite);
                            setActiveTab('inspector');
                          }}
                          className={`text-xs px-3 py-1.5 rounded-lg border font-medium transition-all duration-200 ${
                            selectedCitation?.chunk_id === cite.chunk_id
                              ? 'bg-blue-50 text-blue-700 border-blue-200 shadow-sm ring-1 ring-blue-100'
                              : 'bg-slate-50 text-slate-600 border-slate-200 hover:bg-slate-100 hover:border-slate-300'
                          }`}
                        >
                            {cite.source === 'youtube' || cite.video_id ? '▶ YouTube' : `📄 ${cite.source.slice(0, 16)}...`}
                            {cite.start_timestamp && (
                              <span className="ml-1.5 px-1 py-0.5 bg-black/5 rounded text-[10px] opacity-90">[{cite.start_timestamp}]</span>
                            )}
                            {!cite.start_timestamp && cite.page !== 'N/A' && cite.page !== 'unknown' && cite.page !== 0 && cite.page !== '0' && (
                              <span className="ml-1.5 px-1 py-0.5 bg-black/5 rounded text-[10px] opacity-90">p.{cite.page}</span>
                            )}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
                <span className="text-[11px] text-slate-400 mt-2 px-1 font-medium">{msg.timestamp}</span>
              </div>
            );
          })}
          <div ref={messagesEndRef} className="h-4" />
        </div>

        {/* Input Area */}
        <div className="p-6 bg-gradient-to-t from-white via-white to-transparent pt-10">
          <div className="max-w-4xl mx-auto relative">
            {uploadedFiles.length === 0 && (
              <div className="absolute -top-12 left-1/2 -translate-x-1/2 bg-slate-800 text-white text-xs font-medium px-4 py-2 rounded-full shadow-lg flex items-center gap-2 animate-bounce">
                <span>⚠️</span> Please upload a PDF or YouTube link first
              </div>
            )}
            
            <form 
              onSubmit={handleSendMessage} 
              className="flex gap-3 items-end p-2 bg-slate-50 border border-slate-200 rounded-2xl shadow-sm focus-within:ring-2 focus-within:ring-blue-500/20 focus-within:border-blue-400 transition-all"
            >
              <div className="relative mb-1 ml-1">
                <button
                  type="button"
                  onClick={() => setIsToolMenuOpen(!isToolMenuOpen)}
                  disabled={isStreaming || uploadedFiles.length === 0}
                  className="p-2.5 text-slate-400 hover:text-slate-700 bg-white hover:bg-slate-100 border border-slate-200 rounded-xl transition-colors disabled:opacity-50 disabled:cursor-not-allowed shadow-sm"
                  aria-label="Select Assistant Tool"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-5 h-5">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6A2.25 2.25 0 016 3.75h2.25A2.25 2.25 0 0110.5 6v2.25a2.25 2.25 0 01-2.25 2.25H6a2.25 2.25 0 01-2.25-2.25V6zM3.75 15.75A2.25 2.25 0 016 13.5h2.25a2.25 2.25 0 012.25 2.25V18a2.25 2.25 0 01-2.25 2.25H6A2.25 2.25 0 013.75 18v-2.25zM13.5 6a2.25 2.25 0 012.25-2.25H18A2.25 2.25 0 0120.25 6v2.25A2.25 2.25 0 0118 10.5h-2.25a2.25 2.25 0 01-2.25-2.25V6zM13.5 15.75a2.25 2.25 0 012.25-2.25H18a2.25 2.25 0 012.25 2.25V18A2.25 2.25 0 0118 20.25h-2.25A2.25 2.25 0 0113.5 18v-2.25z" />
                  </svg>
                </button>
                
                {isToolMenuOpen && (
                  <div className="absolute bottom-full left-0 mb-3 w-56 bg-white border border-slate-100 rounded-2xl shadow-xl overflow-hidden z-50 py-1">
                    {toolsList.map(tool => (
                      <button
                        key={tool.id}
                        type="button"
                        onClick={() => { setSelectedTool(tool.id); setIsToolMenuOpen(false); }}
                        className={`w-full text-left px-4 py-3 text-sm flex items-center gap-3 transition-colors ${
                          selectedTool === tool.id ? 'bg-blue-50/50 text-blue-700 font-semibold' : 'text-slate-600 hover:bg-slate-50'
                        }`}
                      >
                        <span className="text-lg">{tool.icon}</span> {tool.label}
                      </button>
                    ))}
                  </div>
                )}
              </div>

              {/* Dynamic Input/Textarea handling */}
              {['quiz', 'flashcards'].includes(selectedTool) ? (
                <input
                  type="number"
                  min="1"
                  max="30"
                  placeholder={`[${toolsList.find(t => t.id === selectedTool)?.label}] Enter number (e.g., 5)...`}
                  value={inputMessage}
                  onChange={(e) => setInputMessage(e.target.value)}
                  disabled={isStreaming || uploadedFiles.length === 0}
                  className="flex-1 py-3 px-3 bg-transparent border-0 focus:ring-0 text-[15px] outline-none disabled:text-slate-400 placeholder:text-slate-400"
                />
              ) : (
                <textarea
                  rows={1}
                  placeholder={
                    uploadedFiles.length === 0 
                      ? "Upload sources to begin..." 
                      : ['summarize', 'study-guide'].includes(selectedTool)
                      ? `[${toolsList.find(t => t.id === selectedTool)?.label}] Ready to generate.`
                      : `Ask a question about your documents...`
                  }
                  value={['summarize', 'study-guide'].includes(selectedTool) ? '' : inputMessage}
                  onChange={(e) => setInputMessage(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault();
                      handleSendMessage();
                    }
                  }}
                  disabled={isStreaming || uploadedFiles.length === 0 || ['summarize', 'study-guide'].includes(selectedTool)}
                  className="flex-1 py-3 px-2 bg-transparent border-0 focus:ring-0 text-[15px] resize-none max-h-32 min-h-[44px] disabled:text-slate-400 placeholder:text-slate-400 outline-none"
                />
              )}
              
              <button
                type="submit"
                disabled={isStreaming || uploadedFiles.length === 0 || (!['summarize', 'study-guide'].includes(selectedTool) && !inputMessage.trim())}
                className="mb-1 mr-1 p-3 bg-slate-900 hover:bg-slate-800 disabled:bg-slate-200 disabled:text-slate-400 text-white rounded-xl transition-all shadow-sm disabled:cursor-not-allowed flex items-center justify-center"
                aria-label="Send message"
              >
                {isStreaming ? (
                  <div className="w-5 h-5 border-2 border-white/20 border-t-white rounded-full animate-spin" />
                ) : (
                  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5">
                    <path d="M3.478 2.404a.75.75 0 0 0-.926.941l2.432 7.905H13.5a.75.75 0 0 1 0 1.5H4.984l-2.432 7.905a.75.75 0 0 0 .926.94 60.519 60.519 0 0 0 18.445-8.986.75.75 0 0 0 0-1.218A60.517 60.517 0 0 0 3.478 2.404Z" />
                  </svg>
                )}
              </button>
            </form>
          </div>
        </div>
      </main>

      {/* RIGHT DRAG HANDLE */}
      <div 
        onMouseDown={() => setIsDraggingRight(true)}
        className="w-1.5 -ml-[3px] z-50 cursor-col-resize hover:bg-blue-500/50 active:bg-blue-500 transition-colors"
      />

      {/* ========================================================= */}
      {/* 3. RIGHT PANEL: Inspector & Sources                       */}
      {/* ========================================================= */}
      <aside 
        style={{ width: `${rightWidth}px` }}
        className="flex-shrink-0 bg-slate-50/50 border-l border-slate-200 flex flex-col relative z-20"
      >
        <div className="flex p-2 gap-1 border-b border-slate-200 bg-white/50 backdrop-blur">
          {['inspector', 'sources', ...(previewData ? ['preview'] : [])].map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab as any)}
              className={`flex-1 py-2 text-[13px] font-semibold rounded-lg transition-all capitalize ${
                activeTab === tab
                  ? 'bg-white text-slate-800 shadow-sm border border-slate-200/60'
                  : 'text-slate-500 hover:bg-slate-100 hover:text-slate-700 border border-transparent'
              }`}
            >
              {tab === 'inspector' ? 'Evidence' : tab === 'sources' ? 'Library' : 'Preview'}
            </button>
          ))}
        </div>

        {/* Tab 1: Inspector (Restored conditional rendering) */}
        {activeTab === 'inspector' && (
          <div className="flex-1 p-5 overflow-y-auto space-y-4">
            {selectedCitation ? (
              <div className="space-y-4 animate-in fade-in slide-in-from-bottom-2 duration-300">
                
                {/* Matched Source Meta Box */}
                <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-3">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-[10px] font-bold uppercase tracking-widest text-blue-600 bg-blue-50 px-2.5 py-1 rounded-md">
                      Source Material
                    </span>
                    {selectedCitation.page && selectedCitation.page !== 'N/A' && selectedCitation.page !== 'unknown' && (
                      <span className="text-[10px] font-bold uppercase tracking-widest text-slate-600 bg-slate-100 px-2.5 py-1 rounded-md">
                        Page {selectedCitation.page}
                      </span>
                    )}
                    {selectedCitation.start_timestamp && (
                      <span className="text-[10px] font-bold uppercase tracking-widest text-amber-700 bg-amber-50 px-2.5 py-1 rounded-md">
                        {selectedCitation.start_timestamp} - {selectedCitation.end_timestamp}
                      </span>
                    )}
                  </div>
                  <h3 className="font-semibold text-sm text-slate-800 break-words leading-snug">{selectedCitation.source}</h3>
                </div>

                {/* Highlighted Evidence Box OR Live Viewers */}
                {(() => {
                  const isPdf = selectedCitation.source.toLowerCase().endsWith('.pdf');
                  
                  if (isPdf) {
                    const pageNum = selectedCitation.page && selectedCitation.page !== 'N/A' && selectedCitation.page !== 'unknown' 
                      ? selectedCitation.page 
                      : 1;
                    
                    const cleanSnippet = selectedCitation.snippet 
                      ? selectedCitation.snippet
                          .replace(/[^a-zA-Z0-9\s]/g, ' ')
                          .replace(/\s+/g, ' ')
                          .trim()
                          .split(' ')
                          .slice(0, 4)
                          .join(' ')
                      : '';
                    
                    const searchParam = cleanSnippet ? `&search="${encodeURIComponent(cleanSnippet)}"` : '';
                    const pdfUrl = `${API_BASE_URL}/api/files/${encodeURIComponent(selectedCitation.source)}#page=${pageNum}${searchParam}&view=FitH&toolbar=0`;

                    return (
                      <div className="flex flex-col h-[550px]">
                        <div className="flex justify-between items-center mb-2">
                          <label className="text-[11px] font-bold text-slate-500 uppercase tracking-widest ml-1">
                            Live Document Preview
                          </label>
                          <a href={pdfUrl} target="_blank" rel="noopener noreferrer" className="text-[11px] text-blue-600 font-semibold hover:underline bg-blue-50 px-3 py-1 rounded-lg transition-colors hover:bg-blue-100">
                            Open Tab ↗
                          </a>
                        </div>
                        <div className="flex-1 w-full bg-slate-200 rounded-2xl overflow-hidden border border-slate-200 shadow-sm">
                          <iframe
                            key={selectedCitation.chunk_id || pdfUrl} 
                            src={pdfUrl}
                            className="w-full h-full border-none"
                            title="PDF Source Preview"
                          />
                        </div>
                      </div>
                    );
                  }

                  const isYouTube = selectedCitation.source === 'youtube' || selectedCitation.video_id;
                  
                  if (isYouTube && selectedCitation.video_id) {
                    let startSeconds = 0;
                    if (selectedCitation.start_timestamp) {
                      const parts = selectedCitation.start_timestamp.split(':').map(Number);
                      if (parts.length === 3) {
                        startSeconds = (parts[0] * 3600) + (parts[1] * 60) + parts[2];
                      }
                    }
                    
                    const youtubeEmbedUrl = `https://www.youtube.com/embed/${selectedCitation.video_id}?start=${startSeconds}&autoplay=1`;

                    return (
                      <div className="flex flex-col h-[550px] gap-3">
                        <div>
                          <label className="text-[11px] font-bold text-slate-500 uppercase tracking-widest ml-1 block mb-2">
                            Live Video
                          </label>
                          <div className="w-full aspect-video bg-slate-900 rounded-2xl overflow-hidden shadow-sm flex-shrink-0">
                            <iframe
                              key={selectedCitation.chunk_id || youtubeEmbedUrl} 
                              src={youtubeEmbedUrl}
                              className="w-full h-full border-none"
                              title="YouTube Source Preview"
                              allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                              allowFullScreen
                            />
                          </div>
                        </div>
                        <div className="flex-1 flex flex-col overflow-hidden">
                          <label className="text-[11px] font-bold text-slate-500 uppercase tracking-widest ml-1 block mb-2">
                            Transcript
                          </label>
                          <div className="flex-1 p-5 bg-white border border-amber-200 shadow-[0_4px_20px_rgba(251,191,36,0.08)] rounded-2xl text-slate-700 text-sm leading-relaxed whitespace-pre-wrap font-mono overflow-y-auto custom-scrollbar">
                            {selectedCitation.snippet}
                          </div>
                        </div>
                      </div>
                    );
                  }

                  const isImage = /\.(jpeg|jpg|gif|png|webp)$/i.test(selectedCitation.source);
                  
                  if (isImage) {
                    const imageUrl = `${API_BASE_URL}/api/files/${encodeURIComponent(selectedCitation.source)}`;
                    return (
                      <div className="flex flex-col h-[550px] gap-3">
                        <div>
                          <div className="flex justify-between items-center mb-2">
                            <label className="text-[11px] font-bold text-slate-500 uppercase tracking-widest ml-1">
                              Live Image
                            </label>
                            <a href={imageUrl} target="_blank" rel="noopener noreferrer" className="text-[11px] text-blue-600 font-semibold hover:underline bg-blue-50 px-3 py-1 rounded-lg transition-colors hover:bg-blue-100">
                              Open Tab ↗
                            </a>
                          </div>
                          <div className="w-full h-64 bg-slate-100 rounded-2xl overflow-hidden shadow-sm flex-shrink-0 flex items-center justify-center p-2 border border-slate-200">
                            <img 
                              src={imageUrl} 
                              alt={selectedCitation.source} 
                              className="max-w-full max-h-full object-contain rounded-xl" 
                            />
                          </div>
                        </div>
                        <div className="flex-1 flex flex-col overflow-hidden">
                          <label className="text-[11px] font-bold text-slate-500 uppercase tracking-widest ml-1 block mb-2">
                            Description
                          </label>
                          <div className="flex-1 p-5 bg-white border border-amber-200 shadow-[0_4px_20px_rgba(251,191,36,0.08)] rounded-2xl text-slate-700 text-sm leading-relaxed whitespace-pre-wrap font-mono overflow-y-auto custom-scrollbar">
                            {selectedCitation.snippet}
                          </div>
                        </div>
                      </div>
                    );
                  }

                  return (
                    <div className="space-y-2">
                      <label className="text-[11px] font-bold text-slate-500 uppercase tracking-widest ml-1 block">
                        Retrieved Context
                      </label>
                      <div className="p-5 bg-white border border-amber-200 shadow-[0_4px_20px_rgba(251,191,36,0.08)] rounded-2xl text-slate-700 text-sm leading-relaxed whitespace-pre-wrap font-mono">
                        {selectedCitation.snippet}
                      </div>
                    </div>
                  );
                })()}
                
              </div>
            ) : (
              <div className="h-full flex flex-col items-center justify-center text-center p-8 text-slate-400">
                <div className="w-16 h-16 bg-slate-100 rounded-full flex items-center justify-center mb-4 border border-slate-200">
                  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-8 h-8 text-slate-300">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m3.75 9v6m3-3H9m1.5-12H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
                  </svg>
                </div>
                <h4 className="text-sm font-semibold text-slate-700 mb-1">No Evidence Selected</h4>
                <p className="text-xs text-slate-500">Click a source tag in the chat to inspect the original context.</p>
              </div>
            )}
          </div>
        )}

        {/* Tab 2: Sources */}
        {activeTab === 'sources' && (
          <div className="flex-1 p-6 overflow-y-auto space-y-8">
            <section className="space-y-3">
              <label className="text-[11px] font-bold uppercase tracking-widest text-slate-500">Upload Documents</label>
              <div className="relative group">
                <input
                  type="file"
                  accept=".pdf,image/*"
                  onChange={handleFileUpload}
                  disabled={isUploading}
                  className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-10"
                />
                <div className="w-full p-6 border-2 border-dashed border-slate-200 rounded-2xl bg-white flex flex-col items-center justify-center gap-2 group-hover:border-blue-400 group-hover:bg-blue-50/50 transition-colors">
                  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-8 h-8 text-slate-400 group-hover:text-blue-500"><path strokeLinecap="round" strokeLinejoin="round" d="M12 16.5V9.75m0 0l3 3m-3-3l-3 3M6.75 19.5a4.5 4.5 0 01-1.41-8.775 5.25 5.25 0 0110.233-2.33 3 3 0 013.758 3.848A3.752 3.752 0 0118 19.5H6.75z" /></svg>
                  <span className="text-sm font-medium text-slate-600">Drag & drop or click to browse</span>
                  <span className="text-[11px] text-slate-400">PDFs, Images</span>
                </div>
              </div>
            </section>

            <section className="space-y-3">
              <label className="text-[11px] font-bold uppercase tracking-widest text-slate-500">Import Video</label>
              <div className="flex gap-2">
                <input
                  type="text"
                  placeholder="Paste YouTube link..."
                  value={youtubeUrl}
                  onChange={(e) => setYoutubeUrl(e.target.value)}
                  disabled={isUploading}
                  className="flex-1 px-4 py-2.5 text-sm bg-white border border-slate-200 rounded-xl focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 outline-none transition-all shadow-sm"
                />
                <button
                  onClick={handleYouTubeIngest}
                  disabled={isUploading || !youtubeUrl.trim()}
                  className="px-4 py-2.5 bg-slate-900 hover:bg-slate-800 disabled:bg-slate-200 disabled:text-slate-400 text-white rounded-xl text-sm font-medium transition-all shadow-sm"
                >
                  Import
                </button>
              </div>
            </section>

            {uploadStatus && (
              <div className="p-4 bg-green-50 border border-green-200 text-green-800 rounded-xl text-sm font-medium flex items-start gap-2">
                <span>✓</span> {uploadStatus}
              </div>
            )}

            <section className="space-y-3">
              <label className="text-[11px] font-bold uppercase tracking-widest text-slate-500">Active Library</label>
              {uploadedFiles.length === 0 ? (
                <div className="p-6 bg-slate-100/50 rounded-2xl border border-slate-200 border-dashed text-center">
                  <p className="text-xs text-slate-500 font-medium">Your library is empty.</p>
                </div>
              ) : (
                <ul className="space-y-2">
                  {uploadedFiles.map((file, i) => (
                    <li key={i} className="flex items-center justify-between bg-white p-3 rounded-xl border border-slate-200 shadow-sm group hover:border-blue-200 transition-colors">
                      <div className="flex items-center gap-3 overflow-hidden">
                        <div className="w-8 h-8 rounded-lg bg-slate-50 flex items-center justify-center shrink-0 border border-slate-100">
                          {file.startsWith('YouTube:') ? '📺' : '📄'}
                        </div>
                        <span className="truncate text-sm text-slate-700 font-medium" title={file}>
                          {file.replace('YouTube: ', '')}
                        </span>
                      </div>
                      <button
                        onClick={() => {
                          const isYouTube = file.startsWith('YouTube: ');
                          const isImage = /\.(jpeg|jpg|gif|png|webp)$/i.test(file);
                          
                          if (isYouTube) {
                            const rawUrl = file.replace('YouTube: ', '').trim();
                            let embedUrl = rawUrl;
                            const videoIdMatch = rawUrl.match(/(?:youtu\.be\/|youtube\.com\/(?:embed\/|v\/|watch\?v=|watch\?.+&v=))([\w-]{11})/);
                            if (videoIdMatch && videoIdMatch[1]) {
                              embedUrl = `https://www.youtube.com/embed/${videoIdMatch[1]}`;
                            }
                            setPreviewData({ url: embedUrl, type: 'youtube', title: file });
                          } else {
                            const fileUrl = `${API_BASE_URL}/api/files/${encodeURIComponent(file)}`;
                            setPreviewData({ url: fileUrl, type: isImage ? 'image' : 'pdf', title: file });
                          }
                          setActiveTab('preview');
                        }}
                        className="opacity-0 group-hover:opacity-100 px-3 py-1.5 bg-blue-50 text-blue-600 hover:bg-blue-100 rounded-lg text-xs font-semibold transition-all shrink-0"
                      >
                        Preview
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          </div>
        )}

        {/* Tab 3: Embedded Iframe Preview (Restored conditional rendering) */}
        {activeTab === 'preview' && previewData && (
          <div className="flex-1 flex flex-col overflow-hidden bg-slate-100/50">
            <div className="p-4 border-b border-slate-200 bg-white flex justify-between items-center shadow-sm z-10">
              <span className="text-[13px] font-bold text-slate-700 truncate pr-4">{previewData.title}</span>
              <button 
                onClick={() => {
                  setPreviewData(null);
                  setActiveTab('sources');
                }} 
                className="text-xs font-semibold px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-600 rounded-lg transition-colors"
              >
                Close
              </button>
            </div>
            
            <div className="flex-1 w-full h-full bg-slate-200/50 p-4">
              <div className="w-full h-full bg-white rounded-xl overflow-hidden shadow-sm border border-slate-200">
                {previewData.type === 'youtube' ? (
                  <iframe
                    src={previewData.url}
                    className="w-full h-full border-none"
                    title="Source Preview"
                    allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                    allowFullScreen
                  />
                ) : previewData.type === 'image' ? (
                  <div className="w-full h-full flex items-center justify-center p-6 bg-slate-50">
                    <img src={previewData.url} alt={previewData.title} className="max-w-full max-h-full object-contain rounded-lg shadow-sm" />
                  </div>
                ) : (
                  <iframe
                    key={previewData.url} 
                    src={`${previewData.url}#view=FitH&toolbar=0`}
                    className="w-full h-full border-none"
                    title="Source Preview"
                  />
                )}
              </div>
            </div>
          </div>
        )}
      </aside>
    </div>
  );
}