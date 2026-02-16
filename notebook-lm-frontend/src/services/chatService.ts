import { apiClient } from './api';
import { ChatRequest, ChatResponse } from '../types/api.types';

export class ChatService {
  /**
   * Send chat query with streaming support
   */
  static async sendQuery(
    request: ChatRequest,
    onChunk?: (chunk: string) => void
  ): Promise<ChatResponse> {
    // For now, use regular POST request
    // In future, can be extended to support Server-Sent Events (SSE) or WebSocket
    const response = await apiClient.post<ChatResponse>('/v1/chat/query', request);

    // Simulate streaming if onChunk callback provided (for future SSE implementation)
    if (onChunk && response.answer) {
      // This is a placeholder - real streaming would use SSE or WebSocket
      const words = response.answer.split(' ');
      for (let i = 0; i < words.length; i++) {
        setTimeout(() => {
          onChunk(words[i] + (i < words.length - 1 ? ' ' : ''));
        }, i * 50);
      }
    }

    return response;
  }

  /**
   * Send streaming query (future implementation with SSE)
   */
  static async sendStreamingQuery(
    request: ChatRequest,
    onChunk: (chunk: string) => void,
    onComplete: (response: ChatResponse) => void,
    onError: (error: Error) => void
  ): Promise<void> {
    // Placeholder for future SSE/WebSocket implementation
    // This would use EventSource or WebSocket for real-time streaming
    try {
      const response = await this.sendQuery(request, onChunk);
      onComplete(response);
    } catch (error) {
      onError(error as Error);
    }
  }
  /**
   * Ingest a file (PDF, TXT, MD)
   */
  static async ingestFile(file: File, userId: string): Promise<{ document_id: string }> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('user_id', userId);

    // apiClient.post handles JSON by default, need to handle FormData
    // Assuming apiClient is an axios instance or similar wrapper
    // If it's a wrapper that forces JSON, we might need to bypass it or configure it
    // Let's assume standard axios usage for now, but check apiClient implementation if it fails
    return await apiClient.post<{ document_id: string }>('/ingest/file', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  }

  /**
   * Ingest a URL (Web or YouTube)
   */
  static async ingestUrl(url: string, type: 'web' | 'youtube', userId: string): Promise<{ document_id: string }> {
    return await apiClient.post<{ document_id: string }>('/ingest/url', {
      url,
      type,
      user_id: userId,
    });
  }
}
