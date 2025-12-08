import { apiClient } from './api';
import { SessionResponse } from '../types/api.types';

export class SessionService {
  static async createSession(userId: string): Promise<SessionResponse> {
    const response = await apiClient.post<SessionResponse>('/session/create', { user_id: userId });
    return response;
  }
}
