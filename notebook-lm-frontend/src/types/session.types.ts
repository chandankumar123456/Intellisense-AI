// Session Types

export interface SessionState {
  sessionId: string | null;
  expiresAt: Date | null;
  isLoading: boolean;
}

export interface SessionContextType extends SessionState {
  createSession: (userId: string) => Promise<void>;
  refreshSession: () => Promise<void>;
  clearSession: () => void;
}
