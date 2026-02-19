import apiClient from './api';

// ── Student Knowledge API Service ──

export type UploadStatus =
  | 'queued'
  | 'processing'
  | 'indexed'
  | 'indexed_partial'
  | 'duplicate'
  | 'index_failed'
  | 'index_validation_failed'
  | 'processing_delayed'
  | 'extraction_failed'
  | 'invalid_source'
  | 'insufficient_content'
  | 'error';

export type SourceType = 'file' | 'youtube' | 'website';

export interface UploadRecord {
  upload_id: string;
  student_id: string;
  source_type: SourceType;
  source_uri: string;
  title: string;
  status: UploadStatus;
  chunk_count: number;
  token_count: number;
  tags: string[];
  is_private: boolean;
  created_at: string;
  error_reason: string | null;
  trace_path?: string;
  extraction_status?: string;
  validation_status?: string;
  stage_timeline?: any[];
}

export interface UploadResponse {
  upload_id: string;
  status: string;
  message: string;
}

export interface UploadListResponse {
  uploads: UploadRecord[];
  total: number;
}

const studentKnowledgeService = {
  // ── Upload Operations ──

  uploadFile: async (
    file: File,
    title?: string,
    tags?: string[]
  ): Promise<UploadResponse> => {
    const formData = new FormData();
    formData.append('file', file);
    if (title) formData.append('title', title);
    if (tags && tags.length > 0) formData.append('tags', tags.join(','));

    return apiClient.post('/student-knowledge/upload/file', formData, {
      headers: { 'Content-Type': undefined } as any,
      timeout: 120000, // 2 minutes for large files
    });
  },

  uploadUrl: async (
    url: string,
    sourceType: 'youtube' | 'website',
    title?: string,
    tags?: string[]
  ): Promise<UploadResponse> => {
    return apiClient.post('/student-knowledge/upload/url', {
      url,
      source_type: sourceType,
      title,
      tags,
    });
  },

  // ── Read Operations ──

  getUploads: async (): Promise<UploadListResponse> => {
    return apiClient.get('/student-knowledge/uploads');
  },

  getUploadStatus: async (uploadId: string): Promise<UploadRecord> => {
    return apiClient.get(`/student-knowledge/uploads/${uploadId}`);
  },

  // ── Lifecycle Operations ──

  deleteUpload: async (uploadId: string): Promise<{ message: string }> => {
    return apiClient.delete(`/student-knowledge/uploads/${uploadId}`);
  },

  reprocessUpload: async (uploadId: string): Promise<UploadResponse> => {
    return apiClient.post(`/student-knowledge/uploads/${uploadId}/reprocess`);
  },

  // ── Metadata Operations ──

  updateTags: async (
    uploadId: string,
    tags: string[],
    notes?: string
  ): Promise<{ message: string }> => {
    return apiClient.put(`/student-knowledge/uploads/${uploadId}/tags`, {
      tags,
      notes,
    });
  },

  togglePrivacy: async (
    uploadId: string,
    isPrivate: boolean
  ): Promise<{ message: string }> => {
    return apiClient.put(`/student-knowledge/uploads/${uploadId}/privacy`, {
      is_private: isPrivate,
    });
  },
};

export default studentKnowledgeService;
