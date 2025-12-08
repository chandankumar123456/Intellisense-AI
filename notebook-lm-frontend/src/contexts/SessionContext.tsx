import React, { createContext, useContext, useReducer, useEffect, ReactNode } from 'react';
import { SessionService } from '../services/sessionService';
import { Storage } from '../utils/storage';
import { useAuth } from './AuthContext';
import { SessionContextType, SessionState } from '../types/session.types';
import { User } from '../types/api.types';

// Initial state
const initialState: SessionState = {
  sessionId: Storage.getSessionId(),
  expiresAt: null,
  isLoading: false,
};

// Action types
type SessionAction =
  | { type: 'CREATE_SESSION_START' }
  | { type: 'CREATE_SESSION_SUCCESS'; payload: { sessionId: string; expiresInSeconds: number } }
  | { type: 'CREATE_SESSION_FAILURE' }
  | { type: 'CLEAR_SESSION' }
  | { type: 'SET_LOADING'; payload: boolean };

// Reducer
const sessionReducer = (state: SessionState, action: SessionAction): SessionState => {
  switch (action.type) {
    case 'CREATE_SESSION_START':
      return { ...state, isLoading: true };
    case 'CREATE_SESSION_SUCCESS':
      const expiresAt = new Date(Date.now() + action.payload.expiresInSeconds * 1000);
      return {
        ...state,
        sessionId: action.payload.sessionId,
        expiresAt,
        isLoading: false,
      };
    case 'CREATE_SESSION_FAILURE':
      return { ...state, isLoading: false };
    case 'CLEAR_SESSION':
      return {
        ...state,
        sessionId: null,
        expiresAt: null,
        isLoading: false,
      };
    case 'SET_LOADING':
      return { ...state, isLoading: action.payload };
    default:
      return state;
  }
};

// Context
const SessionContext = createContext<SessionContextType | undefined>(undefined);

// Provider component
export const SessionProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [state, dispatch] = useReducer(sessionReducer, initialState);
  const { user, isAuthenticated } = useAuth();

  // Create session when user is authenticated
  useEffect(() => {
    if (isAuthenticated && user && !state.sessionId) {
      createSession(user.user_id);
    }
  }, [isAuthenticated, user]);

  // Check session expiration
  useEffect(() => {
    if (state.expiresAt) {
      const checkExpiration = setInterval(() => {
        if (state.expiresAt && new Date() >= state.expiresAt) {
          clearSession();
        }
      }, 60000); // Check every minute

      return () => clearInterval(checkExpiration);
    }
  }, [state.expiresAt]);

  const createSession = async (userId: string): Promise<void> => {
    try {
      dispatch({ type: 'CREATE_SESSION_START' });
      const response = await SessionService.createSession(userId);
      
      Storage.setSessionId(response.session_id);
      
      dispatch({
        type: 'CREATE_SESSION_SUCCESS',
        payload: {
          sessionId: response.session_id,
          expiresInSeconds: response.expires_in_seconds,
        },
      });
    } catch (error) {
      dispatch({ type: 'CREATE_SESSION_FAILURE' });
      throw error;
    }
  };

  const refreshSession = async (): Promise<void> => {
    if (user) {
      await createSession(user.user_id);
    }
  };

  const clearSession = (): void => {
    Storage.removeSessionId();
    dispatch({ type: 'CLEAR_SESSION' });
  };

  const value: SessionContextType = {
    ...state,
    createSession,
    refreshSession,
    clearSession,
  };

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
};

// Custom hook
export const useSession = (): SessionContextType => {
  const context = useContext(SessionContext);
  if (context === undefined) {
    throw new Error('useSession must be used within a SessionProvider');
  }
  return context;
};
