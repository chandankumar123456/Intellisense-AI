// Local Storage Utilities

const STORAGE_KEYS = {
  AUTH_TOKEN: 'notebook_lm_token',
  USER_DATA: 'notebook_lm_user',
  SESSION_ID: 'notebook_lm_session',
  PREFERENCES: 'notebook_lm_preferences',
  MESSAGES: 'notebook_lm_messages',
  CONVERSATION_HISTORY: 'notebook_lm_conversation_history',
} as const;

export class Storage {
  // Auth token
  static getToken(): string | null {
    return localStorage.getItem(STORAGE_KEYS.AUTH_TOKEN);
  }

  static setToken(token: string): void {
    localStorage.setItem(STORAGE_KEYS.AUTH_TOKEN, token);
  }

  static removeToken(): void {
    localStorage.removeItem(STORAGE_KEYS.AUTH_TOKEN);
  }

  // User data
  static getUser(): any | null {
    const user = localStorage.getItem(STORAGE_KEYS.USER_DATA);
    return user ? JSON.parse(user) : null;
  }

  static setUser(user: any): void {
    localStorage.setItem(STORAGE_KEYS.USER_DATA, JSON.stringify(user));
  }

  static removeUser(): void {
    localStorage.removeItem(STORAGE_KEYS.USER_DATA);
  }

  // Session ID
  static getSessionId(): string | null {
    return localStorage.getItem(STORAGE_KEYS.SESSION_ID);
  }

  static setSessionId(sessionId: string): void {
    localStorage.setItem(STORAGE_KEYS.SESSION_ID, sessionId);
  }

  static removeSessionId(): void {
    localStorage.removeItem(STORAGE_KEYS.SESSION_ID);
  }

  // Chat preferences
  static getPreferences(): any | null {
    const preferences = localStorage.getItem(STORAGE_KEYS.PREFERENCES);
    return preferences ? JSON.parse(preferences) : null;
  }

  static setPreferences(preferences: any): void {
    localStorage.setItem(STORAGE_KEYS.PREFERENCES, JSON.stringify(preferences));
  }

  static removePreferences(): void {
    localStorage.removeItem(STORAGE_KEYS.PREFERENCES);
  }

  // Messages
  static getMessages(): any[] | null {
    const messages = localStorage.getItem(STORAGE_KEYS.MESSAGES);
    return messages ? JSON.parse(messages) : null;
  }

  static setMessages(messages: any[]): void {
    localStorage.setItem(STORAGE_KEYS.MESSAGES, JSON.stringify(messages));
  }

  static removeMessages(): void {
    localStorage.removeItem(STORAGE_KEYS.MESSAGES);
  }

  // Conversation History
  static getConversationHistory(): any[] | null {
    const history = localStorage.getItem(STORAGE_KEYS.CONVERSATION_HISTORY);
    return history ? JSON.parse(history) : null;
  }

  static setConversationHistory(history: any[]): void {
    localStorage.setItem(STORAGE_KEYS.CONVERSATION_HISTORY, JSON.stringify(history));
  }

  static removeConversationHistory(): void {
    localStorage.removeItem(STORAGE_KEYS.CONVERSATION_HISTORY);
  }

  // Clear all data
  static clearAll(): void {
    Object.values(STORAGE_KEYS).forEach(key => {
      localStorage.removeItem(key);
    });
  }
}
