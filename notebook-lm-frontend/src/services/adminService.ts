import apiClient from './api';

// ── Admin API Service ──

export interface SystemStats {
    total_chunks: number;
    embedded_chunks: number;
    raw_chunks: number;
    unique_documents: number;
    avg_importance: number;
    total_query_hits: number;
    audit_log_count: number;
    top_subjects: { subject: string; count: number }[];
    top_topics: { topic: string; count: number }[];
    source_types: { type: string; count: number }[];
}

export interface DocumentInfo {
    doc_id: string;
    source_type: string;
    source_url: string;
    subject: string;
    topic: string;
    total_chunks: number;
    embedded_chunks: number;
    avg_importance: number;
    created_at: string;
    total_hits: number;
}

export interface AuditEntry {
    audit_id: string;
    query: string;
    input_type: string;
    claims_count: number;
    overall_confidence: number;
    user_id: string;
    recorded_at: string;
    warnings: string[];
    type: string;
}

export interface PromotionCandidate {
    id: string;
    doc_id: string;
    query_count: number;
    importance_score: number;
    chunk_text: string;
}

export interface EvictionCandidate {
    id: string;
    doc_id: string;
    importance_score: number;
    last_queried_at: string;
    chunk_text: string;
}

const adminService = {
    // System stats
    getStats: async (): Promise<SystemStats> => {
        return apiClient.get('/api/admin/stats');
    },

    // Documents
    getDocuments: async (filters?: {
        subject?: string;
        topic?: string;
        user_id?: string;
    }): Promise<{ documents: DocumentInfo[]; count: number }> => {
        return apiClient.get('/api/admin/documents', { params: filters });
    },

    deleteDocument: async (docId: string): Promise<any> => {
        return apiClient.delete(`/api/admin/documents/${docId}`);
    },

    // Upload
    uploadDocument: async (
        file: File,
        metadata: {
            user_id?: string;
            subject?: string;
            topic?: string;
            subtopic?: string;
            syllabus_keywords?: string;
        }
    ): Promise<any> => {
        const formData = new FormData();
        formData.append('file', file);
        if (metadata.user_id) formData.append('user_id', metadata.user_id);
        if (metadata.subject) formData.append('subject', metadata.subject);
        if (metadata.topic) formData.append('topic', metadata.topic);
        if (metadata.subtopic) formData.append('subtopic', metadata.subtopic);
        if (metadata.syllabus_keywords) formData.append('syllabus_keywords', metadata.syllabus_keywords);

        return apiClient.post('/api/evilearn/ingest/file', formData, {
            headers: { 'Content-Type': 'multipart/form-data' },
            timeout: 120000,
        });
    },

    // Audit logs
    getAuditLogs: async (limit = 50): Promise<{ audits: AuditEntry[]; count: number }> => {
        return apiClient.get('/api/admin/audit/recent', { params: { limit } });
    },

    // Maintenance
    getPromotionCandidates: async (threshold = 10): Promise<{ candidates: PromotionCandidate[]; count: number }> => {
        return apiClient.get('/api/evilearn/admin/promotion-candidates', { params: { threshold } });
    },

    getEvictionCandidates: async (months = 6): Promise<{ candidates: EvictionCandidate[]; count: number }> => {
        return apiClient.get('/api/evilearn/admin/eviction-candidates', { params: { months } });
    },

    // Metadata search
    searchMetadata: async (filters: {
        subject?: string;
        topic?: string;
        doc_id?: string;
        min_importance?: number;
        embedded_only?: boolean;
        limit?: number;
    }): Promise<{ results: any[]; count: number }> => {
        return apiClient.get('/api/admin/metadata/search', { params: filters });
    },
};

export default adminService;
