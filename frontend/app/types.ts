export interface Citation {
    source: string;
    page?: number | string;
    snippet: string;
    chunk_id?: string;
    start_timestamp?: string;
    end_timestamp?: string;
    url?: string;
    video_id?: string;
  }
  
  export interface ChatMessage {
    id: string;
    role: 'user' | 'assistant';
    content: string;
    citations?: Citation[];
    timestamp: string;
  }
  
  export interface ChatSession {
    id: string;
    title: string;
    createdAt: string;
    messages: ChatMessage[];
    uploadedFiles: string[];
  }