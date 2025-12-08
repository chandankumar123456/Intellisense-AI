// API Types for Notebook LM Frontend

export interface User {
  user_id: string;
  username: string;
  exp?: number;
}

export interface LoginCredentials {
  username: string;
  password: string;
}

export interface SignupCredentials {
  username: string;
  password: string;
  confirmPassword: string;
}

export interface AuthResponse {
  user_id: string;
  username: string;
  token: string;
}

export interface SessionResponse {
  session_id: string;
  user_id: string;
  expires_in_seconds: number;
}

export interface ChatPreferences {
  response_style: 'concise' | 'detailed' | 'simple' | 'exam';
  max_length: number;
  domain: string;
  model_name?: string;
  max_output_tokens?: number;
  allow_agentic: boolean;
}

export interface ChatRequest {
  query: string;
  user_id: string;
  session_id: string;
  preferences: ChatPreferences;
  conversation_history: string[];
  allow_agentic: boolean;
  model_name?: string;
  max_output_tokens?: number;
}

export interface RetrievalTrace {
  trace_id: string;
  query: string;
  retrievers_used: string[];
  results: {
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
  };
}

export interface QueryUnderstanding {
  rewritten_query: string;
  intent: 'qa' | 'explain' | 'summarize' | 'compare' | 'exam' | 'debug' | 'none';
  retrievers_to_use: string[];
  retrieval_params: {
    top_k_vector: number;
    top_k_keyword: number;
    top_k_web: number;
    top_k_youtube: number;
  };
  style_preferences: {
    type: string;
    tone: string;
  };
}

export interface ChatResponse {
  answer: string;
  confidence: number;
  warnings: string[];
  citations: string[];
  used_chunk_ids: string[];
  retrieval_trace: RetrievalTrace;
  query_understanding: QueryUnderstanding;
  trace_id: string;
  latency_ms: number;
  raw_model_output?: string;
  metrics: Record<string, any>;
}

export interface ApiError {
  message: string;
  status_code: number;
  details?: any;
}
