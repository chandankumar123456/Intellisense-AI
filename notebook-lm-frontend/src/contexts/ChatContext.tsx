import React, { createContext, useContext, useReducer, useEffect, ReactNode } from 'react';
import { ChatService } from '../services/chatService';
import { Storage } from '../utils/storage';
import { useAuth } from './AuthContext';
import { useSession } from './SessionContext';
import { ChatContextType, ChatState, Message, ChatPreferences } from '../types/chat.types';
import { ChatRequest, User } from '../types/api.types';

// Initial preferences
const defaultPreferences: ChatPreferences = {
  response_style: 'concise',
  max_length: 300,
  domain: 'general',
  model_name: 'llama-3.1-8b-instant',
  allow_agentic: false,
};


// Initial state
const getInitialState = (): ChatState => {
  const savedPreferences = Storage.getPreferences();
  const savedMessages = Storage.getMessages();
  return {
    messages: savedMessages || [],
    currentQuery: '',
    isLoading: false,
    activeTab: 'myfiles',
    preferences: savedPreferences || defaultPreferences,
    sessionId: null,
    files: [],
    webSources: [],
    youtubeSources: [],
  };
};

// Action types
type ChatAction =
  | { type: 'SET_MESSAGES'; payload: Message[] }
  | { type: 'ADD_MESSAGE'; payload: Message }
  | { type: 'UPDATE_MESSAGE'; payload: { id: string; content: string } }
  | { type: 'SET_CURRENT_QUERY'; payload: string }
  | { type: 'SET_LOADING'; payload: boolean }
  | { type: 'SET_ACTIVE_TAB'; payload: ChatState['activeTab'] }
  | { type: 'UPDATE_PREFERENCES'; payload: Partial<ChatPreferences> }
  | { type: 'SET_SESSION_ID'; payload: string | null }
  | { type: 'CLEAR_HISTORY' }
  | { type: 'ADD_FILE'; payload: any }
  | { type: 'REMOVE_FILE'; payload: string }
  | { type: 'ADD_WEB_SOURCE'; payload: string }
  | { type: 'REMOVE_WEB_SOURCE'; payload: string }
  | { type: 'ADD_YOUTUBE_SOURCE'; payload: string }
  | { type: 'REMOVE_YOUTUBE_SOURCE'; payload: string };

// Reducer
const chatReducer = (state: ChatState, action: ChatAction): ChatState => {
  switch (action.type) {
    case 'SET_MESSAGES':
      return { ...state, messages: action.payload };
    case 'ADD_MESSAGE':
      const newMessages = [...state.messages, action.payload];
      Storage.setMessages(newMessages);
      return { ...state, messages: newMessages };
    case 'UPDATE_MESSAGE':
      return {
        ...state,
        messages: state.messages.map((msg) =>
          msg.id === action.payload.id
            ? { ...msg, content: action.payload.content }
            : msg
        ),
      };
    case 'SET_CURRENT_QUERY':
      return { ...state, currentQuery: action.payload };
    case 'SET_LOADING':
      return { ...state, isLoading: action.payload };
    case 'SET_ACTIVE_TAB':
      return { ...state, activeTab: action.payload };
    case 'UPDATE_PREFERENCES':
      const newPreferences = { ...state.preferences, ...action.payload };
      Storage.setPreferences(newPreferences);
      return { ...state, preferences: newPreferences };
    case 'SET_SESSION_ID':
      return { ...state, sessionId: action.payload };
    case 'CLEAR_HISTORY':
      Storage.removeMessages();
      return { ...state, messages: [], currentQuery: '' };
    case 'ADD_FILE':
      return { ...state, files: [...state.files, action.payload] };
    case 'REMOVE_FILE':
      return { ...state, files: state.files.filter(f => f.id !== action.payload) };
    case 'ADD_WEB_SOURCE':
      if (state.webSources.includes(action.payload)) return state;
      return { ...state, webSources: [...state.webSources, action.payload] };
    case 'REMOVE_WEB_SOURCE':
      return { ...state, webSources: state.webSources.filter(s => s !== action.payload) };
    case 'ADD_YOUTUBE_SOURCE':
      if (state.youtubeSources.includes(action.payload)) return state;
      return { ...state, youtubeSources: [...state.youtubeSources, action.payload] };
    case 'REMOVE_YOUTUBE_SOURCE':
      return { ...state, youtubeSources: state.youtubeSources.filter(s => s !== action.payload) };
    default:
      return state;
  }
};

// Context
const ChatContext = createContext<ChatContextType | undefined>(undefined);

// Provider component
export const ChatProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [state, dispatch] = useReducer(chatReducer, getInitialState());
  const { user } = useAuth();
  const { sessionId } = useSession();

  // Update session ID when it changes
  useEffect(() => {
    dispatch({ type: 'SET_SESSION_ID', payload: sessionId });
  }, [sessionId]);

  const sendMessage = async (query: string): Promise<void> => {
    if (!user || !sessionId || !query.trim()) {
      return;
    }

    try {
      dispatch({ type: 'SET_LOADING', payload: true });
      dispatch({ type: 'SET_CURRENT_QUERY', payload: '' });

      // Add user message
      const userMessage: Message = {
        id: `user-${Date.now()}`,
        role: 'user',
        content: query,
        timestamp: new Date(),
      };
      dispatch({ type: 'ADD_MESSAGE', payload: userMessage });

      // Prepare conversation history
      const conversationHistory = state.messages
        .filter((msg) => msg.role === 'assistant')
        .map((msg) => msg.content);

      // Create chat request
      const request: ChatRequest = {
        query,
        user_id: user.user_id,
        session_id: sessionId,
        preferences: state.preferences,
        conversation_history: conversationHistory,
        allow_agentic: state.preferences.allow_agentic,
        model_name: state.preferences.model_name,
        max_output_tokens: undefined,
      };

      // Send request
      const response = await ChatService.sendQuery(request);

      // Add assistant message
      const assistantMessage: Message = {
        id: `assistant-${Date.now()}`,
        role: 'assistant',
        content: response.answer,
        timestamp: new Date(),
        metadata: {
          confidence: response.confidence,
          warnings: response.warnings,
          citations: response.citations,
          used_chunk_ids: response.used_chunk_ids,
          retrieval_trace: response.retrieval_trace,
          trace_id: response.trace_id,
          latency_ms: response.latency_ms,
        },
      };
      dispatch({ type: 'ADD_MESSAGE', payload: assistantMessage });
    } catch (error) {
      console.error('Error sending message:', error);
      // Add error message
      const errorMessage: Message = {
        id: `error-${Date.now()}`,
        role: 'assistant',
        content: 'Sorry, I encountered an error processing your request. Please try again.',
        timestamp: new Date(),
      };
      dispatch({ type: 'ADD_MESSAGE', payload: errorMessage });
    } finally {
      dispatch({ type: 'SET_LOADING', payload: false });
    }
  };

  const updatePreferences = (preferences: Partial<ChatPreferences>): void => {
    dispatch({ type: 'UPDATE_PREFERENCES', payload: preferences });
  };

  const clearHistory = (): void => {
    dispatch({ type: 'CLEAR_HISTORY' });
  };

  const setActiveTab = (tab: ChatState['activeTab']): void => {
    dispatch({ type: 'SET_ACTIVE_TAB', payload: tab });
  };

  const setCurrentQuery = (query: string): void => {
    dispatch({ type: 'SET_CURRENT_QUERY', payload: query });
  };

  const addFile = async (file: File): Promise<void> => {
    if (!user) return;

    const tempId = `file-${Date.now()}`;
    // Add optimistic update
    const newFile: any = {
      id: tempId,
      name: file.name,
      type: file.type,
      size: file.size,
      status: 'uploading' as const,
    };
    dispatch({ type: 'ADD_FILE', payload: newFile });

    try {
      const response = await ChatService.ingestFile(file, user.user_id);

      // Update file with real ID and status
      // We need a way to update a specific file in the list. 
      // Current reducer only has ADD/REMOVE. 
      // For now, I'll remove the temp one and add the "complete" one with the doc ID.
      // Better way: Update reducer to support UPDATE_FILE_STATUS, but this works for now.

      dispatch({ type: 'REMOVE_FILE', payload: tempId });

      const completedFile = {
        ...newFile,
        id: response.document_id,
        status: 'complete' as const,
      };
      dispatch({ type: 'ADD_FILE', payload: completedFile });

    } catch (error) {
      console.error('File upload failed:', error);
      dispatch({ type: 'REMOVE_FILE', payload: tempId });
      // Ideally show error toast
      const errorFile = { ...newFile, status: 'error' as const };
      dispatch({ type: 'ADD_FILE', payload: errorFile });
    }
  };

  const removeFile = (fileId: string): void => {
    dispatch({ type: 'REMOVE_FILE', payload: fileId });
  };

  const addWebSource = async (url: string): Promise<void> => {
    if (!user) return;
    try {
      dispatch({ type: 'ADD_WEB_SOURCE', payload: url });
      await ChatService.ingestUrl(url, 'web', user.user_id);
    } catch (error) {
      console.error("Failed to ingest web source:", error);
      dispatch({ type: 'REMOVE_WEB_SOURCE', payload: url });
    }
  };

  const removeWebSource = (url: string): void => {
    dispatch({ type: 'REMOVE_WEB_SOURCE', payload: url });
  };

  const addYouTubeSource = async (url: string): Promise<void> => {
    if (!user) return;
    try {
      dispatch({ type: 'ADD_YOUTUBE_SOURCE', payload: url });
      await ChatService.ingestUrl(url, 'youtube', user.user_id);
    } catch (error) {
      console.error("Failed to ingest YouTube source:", error);
      dispatch({ type: 'REMOVE_YOUTUBE_SOURCE', payload: url });
    }
  };

  const removeYouTubeSource = (url: string): void => {
    dispatch({ type: 'REMOVE_YOUTUBE_SOURCE', payload: url });
  };

  const value: ChatContextType = {
    ...state,
    sendMessage,
    updatePreferences,
    clearHistory,
    setActiveTab,
    setCurrentQuery,
    addFile,
    removeFile,
    addWebSource,
    removeWebSource,
    addYouTubeSource,
    removeYouTubeSource,
  };

  return <ChatContext.Provider value={value}>{children}</ChatContext.Provider>;
};

// Custom hook
export const useChat = (): ChatContextType => {
  const context = useContext(ChatContext);
  if (context === undefined) {
    throw new Error('useChat must be used within a ChatProvider');
  }
  return context;
};

