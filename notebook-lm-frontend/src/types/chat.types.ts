// Chat Types

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  metadata?: {
    confidence?: number;
    warnings?: string[];
    citations?: string[];
    used_chunk_ids?: string[];
    retrieval_trace?: any;
    trace_id?: string;
    latency_ms?: number;
  };
}

export interface ChatPreferences {
  response_style: 'concise' | 'detailed' | 'simple' | 'exam';
  max_length: number;
  domain: string;
  model_name?: string;
  allow_agentic: boolean;
}

export interface ChatState {
  messages: Message[];
  currentQuery: string;
  isLoading: boolean;
  activeTab: 'myfiles' | 'web' | 'youtube' | 'preferences';
  preferences: ChatPreferences;
  sessionId: string | null;
}

export interface ChatContextType extends ChatState {
  sendMessage: (query: string) => Promise<void>;
  updatePreferences: (preferences: Partial<ChatPreferences>) => void;
  clearHistory: () => void;
  setActiveTab: (tab: ChatState['activeTab']) => void;
  setCurrentQuery: (query: string) => void;
}

export interface SourceTab {
  id: 'myfiles' | 'web' | 'youtube' | 'preferences';
  label: string;
  icon: string;
  component: string;
}

export interface RetrievalStats {
  vector?: {
    count: number;
    top_k: number;
    status: string;
  };
  keyword?: {
    count: number;
    top_k: number;
    status: string;
  };
  web?: {
    count: number;
    top_k: number;
    status: string;
  };
  youtube?: {
    count: number;
    top_k: number;
    status: string;
  };
}
