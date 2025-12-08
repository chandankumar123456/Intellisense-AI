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
  | { type: 'CLEAR_HISTORY' };

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

  const value: ChatContextType = {
    ...state,
    sendMessage,
    updatePreferences,
    clearHistory,
    setActiveTab,
    setCurrentQuery,
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
