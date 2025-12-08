import React, { createContext, useContext, useReducer, useEffect, ReactNode } from 'react';
import { AuthService } from '../services/authService';
import { Storage } from '../utils/storage';
import { AuthContextType, AuthState } from '../types/auth.types';
import { User, LoginCredentials, SignupCredentials } from '../types/api.types';

// Initial state
const initialState: AuthState = {
  user: Storage.getUser(),
  token: Storage.getToken(),
  isAuthenticated: !!Storage.getToken(),
  isLoading: false,
};

// Action types
type AuthAction =
  | { type: 'LOGIN_START' }
  | { type: 'LOGIN_SUCCESS'; payload: { user: User; token: string } }
  | { type: 'LOGIN_FAILURE' }
  | { type: 'LOGOUT' }
  | { type: 'SET_LOADING'; payload: boolean };

// Reducer
const authReducer = (state: AuthState, action: AuthAction): AuthState => {
  switch (action.type) {
    case 'LOGIN_START':
      return { ...state, isLoading: true };
    case 'LOGIN_SUCCESS':
      return {
        ...state,
        user: action.payload.user,
        token: action.payload.token,
        isAuthenticated: true,
        isLoading: false,
      };
    case 'LOGIN_FAILURE':
      return {
        ...state,
        user: null,
        token: null,
        isAuthenticated: false,
        isLoading: false,
      };
    case 'LOGOUT':
      return {
        ...state,
        user: null,
        token: null,
        isAuthenticated: false,
        isLoading: false,
      };
    case 'SET_LOADING':
      return { ...state, isLoading: action.payload };
    default:
      return state;
  }
};

// Context
const AuthContext = createContext<AuthContextType | undefined>(undefined);

// Provider component
export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [state, dispatch] = useReducer(authReducer, initialState);

  // Verify token on mount
  useEffect(() => {
    const verifyToken = async () => {
      const token = Storage.getToken();
      if (token) {
        try {
          dispatch({ type: 'SET_LOADING', payload: true });
          const user = await AuthService.verifyToken();
          dispatch({ type: 'LOGIN_SUCCESS', payload: { user, token } });
        } catch (error) {
          // Token is invalid, clear storage
          Storage.clearAll();
          dispatch({ type: 'LOGOUT' });
        } finally {
          dispatch({ type: 'SET_LOADING', payload: false });
        }
      }
    };

    verifyToken();
  }, []);

  const login = async (credentials: LoginCredentials): Promise<void> => {
    try {
      dispatch({ type: 'LOGIN_START' });
      const response = await AuthService.login(credentials);
      
      // Store token and user data
      Storage.setToken(response.token);
      Storage.setUser({ user_id: response.user_id, username: response.username });
      
      dispatch({
        type: 'LOGIN_SUCCESS',
        payload: {
          user: { user_id: response.user_id, username: response.username },
          token: response.token,
        },
      });
    } catch (error) {
      dispatch({ type: 'LOGIN_FAILURE' });
      throw error;
    }
  };

  const signup = async (credentials: SignupCredentials): Promise<void> => {
    try {
      dispatch({ type: 'LOGIN_START' });
      const response = await AuthService.signup(credentials);
      
      // Store token and user data
      Storage.setToken(response.token);
      Storage.setUser({ user_id: response.user_id, username: response.username });
      
      dispatch({
        type: 'LOGIN_SUCCESS',
        payload: {
          user: { user_id: response.user_id, username: response.username },
          token: response.token,
        },
      });
    } catch (error) {
      dispatch({ type: 'LOGIN_FAILURE' });
      throw error;
    }
  };

  const logout = (): void => {
    Storage.clearAll();
    dispatch({ type: 'LOGOUT' });
  };

  const value: AuthContextType = {
    ...state,
    login,
    signup,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

// Custom hook
export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
