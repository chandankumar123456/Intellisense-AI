import api from './api';

export interface StorageConfig {
    mode: 'aws' | 'local';
    aws_region?: string;
    s3_bucket_name?: string;
    pinecone_env?: string;
    pinecone_index_name?: string;
}

export interface StorageStatus {
    mode: 'aws' | 'local';
    files_adapter: string;
    vectors_adapter: string;
    metadata_adapter: string;
}

export interface StorageTestResult {
    storage_type: string;
    status: 'ok' | 'error';
    message: string;
    details?: any;
}

const adminStorageService = {
    // Get current status of storage adapters
    // Get current status of storage adapters
    getStatus: async (): Promise<StorageStatus> => {
        const response = await api.get('/admin/storage/status');
        return response;
    },

    // Get current redacted configuration
    getConfig: async (): Promise<StorageConfig> => {
        const response = await api.get('/admin/storage/config');
        return response;
    },

    // Update configuration (e.g. switch mode)
    updateConfig: async (config: Partial<StorageConfig> & {
        aws_access_key_id?: string;
        aws_secret_access_key?: string;
        pinecone_api_key?: string;
    }): Promise<{ status: string; mode: string }> => {
        const response = await api.post('/admin/storage/config', config);
        return response;
    },

    // Run verification tests
    testStorage: async (): Promise<StorageTestResult[]> => {
        const response = await api.post('/admin/storage/test');
        return response;
    }
};

export default adminStorageService;
