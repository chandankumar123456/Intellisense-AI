import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useAuth } from '../contexts/AuthContext';
import studentKnowledgeService, {
    UploadRecord,
    UploadStatus,
} from '../services/studentKnowledgeService';
import toast from 'react-hot-toast';
import {
    Upload, Link as LinkIcon, Trash2, RefreshCw, Tag, Lock, Unlock,
    FileText, Youtube, Globe, AlertCircle, CheckCircle2, Loader2,
    Clock, X, Plus, BookOpen,
} from 'lucide-react';

// ── Status badge colors ──
// ── Status badge colors ──
const statusConfig: Record<UploadStatus, { color: string; bg: string; icon: React.ElementType; label?: string }> = {
    queued: { color: '#f59e0b', bg: 'rgba(245,158,11,0.12)', icon: Clock },
    processing: { color: '#3b82f6', bg: 'rgba(59,130,246,0.12)', icon: Loader2 },
    indexed: { color: '#10b981', bg: 'rgba(16,185,129,0.12)', icon: CheckCircle2 },
    indexed_partial: { color: '#f59e0b', bg: 'rgba(245,158,11,0.12)', icon: AlertCircle, label: 'Partial Index' },
    duplicate: { color: '#8b5cf6', bg: 'rgba(139,92,246,0.12)', icon: BookOpen, label: 'Duplicate' },
    index_failed: { color: '#ef4444', bg: 'rgba(239,68,68,0.12)', icon: X, label: 'Index Failed' },
    index_validation_failed: { color: '#ef4444', bg: 'rgba(239,68,68,0.12)', icon: AlertCircle, label: 'Validation Failed' },
    processing_delayed: { color: '#f59e0b', bg: 'rgba(245,158,11,0.12)', icon: Clock, label: 'Delayed' },
    extraction_failed: { color: '#ef4444', bg: 'rgba(239,68,68,0.12)', icon: AlertCircle, label: 'Extraction Failed' },
    invalid_source: { color: '#ef4444', bg: 'rgba(239,68,68,0.12)', icon: AlertCircle, label: 'Invalid Source' },
    insufficient_content: { color: '#f59e0b', bg: 'rgba(245,158,11,0.12)', icon: AlertCircle, label: 'No Content' },
    error: { color: '#ef4444', bg: 'rgba(239,68,68,0.12)', icon: AlertCircle },
};

const sourceIcons: Record<string, React.ElementType> = {
    file: FileText,
    youtube: Youtube,
    website: Globe,
};

// ── Main Page Component ──
const StudentKnowledgePage: React.FC = () => {
    const { user } = useAuth();
    const [uploads, setUploads] = useState<UploadRecord[]>([]);
    const [loading, setLoading] = useState(true);
    const [uploading, setUploading] = useState(false);

    // Upload form state
    const [uploadMode, setUploadMode] = useState<'file' | 'url'>('file');
    const [urlInput, setUrlInput] = useState('');
    const [urlType, setUrlType] = useState<'youtube' | 'website'>('youtube');
    const [titleInput, setTitleInput] = useState('');
    const [tagInput, setTagInput] = useState('');
    const [dragOver, setDragOver] = useState(false);
    const fileInputRef = useRef<HTMLInputElement>(null);
    const pollRef = useRef<NodeJS.Timeout | null>(null);

    // ── Fetch uploads ──
    const fetchUploads = useCallback(async () => {
        try {
            const data = await studentKnowledgeService.getUploads();
            setUploads(data.uploads || []);
        } catch (err) {
            console.error('Failed to fetch uploads:', err);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchUploads();
    }, [fetchUploads]);

    // ── Auto-poll for active uploads ──
    useEffect(() => {
        const hasActive = uploads.some(u => u.status === 'queued' || u.status === 'processing');
        if (hasActive) {
            pollRef.current = setInterval(fetchUploads, 3000);
        } else if (pollRef.current) {
            clearInterval(pollRef.current);
            pollRef.current = null;
        }
        return () => {
            if (pollRef.current) clearInterval(pollRef.current);
        };
    }, [uploads, fetchUploads]);

    // ── Handle file upload ──
    const handleFileUpload = async (files: FileList | null) => {
        if (!files || files.length === 0) return;
        const file = files[0];
        const tags = tagInput ? tagInput.split(',').map(t => t.trim()).filter(Boolean) : [];

        setUploading(true);
        try {
            const res = await studentKnowledgeService.uploadFile(file, titleInput || file.name, tags);
            toast.success(`Upload started: ${res.upload_id.slice(0, 8)}...`);
            setTitleInput('');
            setTagInput('');
            if (fileInputRef.current) fileInputRef.current.value = '';
            await fetchUploads();
        } catch (err: any) {
            toast.error(err?.response?.data?.detail || 'Upload failed');
        } finally {
            setUploading(false);
        }
    };

    // ── Handle URL upload ──
    const handleUrlUpload = async () => {
        if (!urlInput.trim()) {
            toast.error('Please enter a URL');
            return;
        }
        const tags = tagInput ? tagInput.split(',').map(t => t.trim()).filter(Boolean) : [];

        setUploading(true);
        try {
            const res = await studentKnowledgeService.uploadUrl(urlInput, urlType, titleInput || undefined, tags);
            toast.success(`URL queued: ${res.upload_id.slice(0, 8)}...`);
            setUrlInput('');
            setTitleInput('');
            setTagInput('');
            await fetchUploads();
        } catch (err: any) {
            toast.error(err?.response?.data?.detail || 'URL submission failed');
        } finally {
            setUploading(false);
        }
    };

    // ── Actions ──
    const handleDelete = async (uploadId: string) => {
        if (!window.confirm('Delete this upload and all its indexed chunks?')) return;
        try {
            await studentKnowledgeService.deleteUpload(uploadId);
            toast.success('Upload deleted');
            setUploads(prev => prev.filter(u => u.upload_id !== uploadId));
        } catch (err: any) {
            toast.error('Delete failed');
        }
    };

    const handleReprocess = async (uploadId: string) => {
        try {
            await studentKnowledgeService.reprocessUpload(uploadId);
            toast.success('Reprocessing started');
            fetchUploads();
        } catch (err: any) {
            toast.error('Reprocess failed');
        }
    };

    const handleTogglePrivacy = async (upload: UploadRecord) => {
        try {
            await studentKnowledgeService.togglePrivacy(upload.upload_id, !upload.is_private);
            setUploads(prev =>
                prev.map(u =>
                    u.upload_id === upload.upload_id ? { ...u, is_private: !u.is_private } : u
                )
            );
            toast.success(upload.is_private ? 'Made public' : 'Made private');
        } catch (err: any) {
            toast.error('Privacy toggle failed');
        }
    };

    // ── Drag & Drop ──
    const onDrop = (e: React.DragEvent) => {
        e.preventDefault();
        setDragOver(false);
        handleFileUpload(e.dataTransfer.files);
    };

    return (
        <div style={{ padding: '24px 32px', maxWidth: '1200px', margin: '0 auto' }}>
            {/* Header */}
            <div style={{ marginBottom: '32px' }}>
                <h1
                    style={{
                        fontSize: '28px',
                        fontWeight: 700,
                        color: 'var(--text-primary)',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '12px',
                        marginBottom: '8px',
                    }}
                >
                    <BookOpen style={{ width: '28px', height: '28px', color: 'var(--accent-primary)' }} />
                    My Knowledge
                </h1>
                <p style={{ color: 'var(--text-muted)', fontSize: '14px' }}>
                    Upload your own resources to enhance AI answers with your personal study materials.
                </p>
            </div>

            {/* Upload Card */}
            <div
                style={{
                    background: 'var(--glass-elevated)',
                    backdropFilter: 'blur(var(--glass-blur-heavy))',
                    border: '1px solid var(--glass-edge)',
                    borderRadius: '16px',
                    padding: '24px',
                    marginBottom: '28px',
                    boxShadow: '0 4px 24px var(--glass-shadow)',
                }}
            >
                {/* Mode Tabs */}
                <div style={{ display: 'flex', gap: '8px', marginBottom: '20px' }}>
                    {(['file', 'url'] as const).map((mode) => (
                        <button
                            key={mode}
                            onClick={() => setUploadMode(mode)}
                            style={{
                                padding: '8px 20px',
                                borderRadius: '10px',
                                border: 'none',
                                background: uploadMode === mode
                                    ? 'linear-gradient(135deg, var(--accent-primary), var(--accent-secondary))'
                                    : 'var(--glass-tint)',
                                color: uploadMode === mode ? '#fff' : 'var(--text-secondary)',
                                fontWeight: 600,
                                fontSize: '13px',
                                cursor: 'pointer',
                                transition: 'all 0.2s',
                                display: 'flex',
                                alignItems: 'center',
                                gap: '6px',
                            }}
                        >
                            {mode === 'file' ? <Upload size={14} /> : <LinkIcon size={14} />}
                            {mode === 'file' ? 'Upload File' : 'Add URL'}
                        </button>
                    ))}
                </div>

                {/* File Upload */}
                {uploadMode === 'file' && (
                    <div>
                        <div
                            onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
                            onDragLeave={() => setDragOver(false)}
                            onDrop={onDrop}
                            onClick={() => fileInputRef.current?.click()}
                            style={{
                                border: `2px dashed ${dragOver ? 'var(--accent-primary)' : 'var(--glass-edge)'}`,
                                borderRadius: '12px',
                                padding: '40px 20px',
                                textAlign: 'center',
                                cursor: 'pointer',
                                transition: 'all 0.2s',
                                background: dragOver ? 'rgba(122,140,255,0.05)' : 'transparent',
                                marginBottom: '16px',
                            }}
                        >
                            <Upload
                                size={32}
                                style={{ color: dragOver ? 'var(--accent-primary)' : 'var(--text-muted)', marginBottom: '12px' }}
                            />
                            <p style={{ color: 'var(--text-secondary)', fontSize: '14px', margin: 0 }}>
                                Drop a file here or <span style={{ color: 'var(--accent-primary)', fontWeight: 600 }}>click to browse</span>
                            </p>
                            <p style={{ color: 'var(--text-muted)', fontSize: '12px', marginTop: '6px' }}>
                                PDF, TXT, DOCX, MD, HTML • Max 50MB
                            </p>
                            <input
                                ref={fileInputRef}
                                type="file"
                                accept=".pdf,.txt,.md,.docx,.html,.htm"
                                style={{ display: 'none' }}
                                onChange={(e) => handleFileUpload(e.target.files)}
                            />
                        </div>
                    </div>
                )}

                {/* URL Upload */}
                {uploadMode === 'url' && (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                        <div style={{ display: 'flex', gap: '8px' }}>
                            {(['youtube', 'website'] as const).map((type) => (
                                <button
                                    key={type}
                                    onClick={() => setUrlType(type)}
                                    style={{
                                        padding: '6px 14px',
                                        borderRadius: '8px',
                                        border: urlType === type ? '1px solid var(--accent-primary)' : '1px solid var(--glass-edge)',
                                        background: urlType === type ? 'rgba(122,140,255,0.1)' : 'transparent',
                                        color: urlType === type ? 'var(--accent-primary)' : 'var(--text-muted)',
                                        fontSize: '12px',
                                        fontWeight: 500,
                                        cursor: 'pointer',
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: '4px',
                                    }}
                                >
                                    {type === 'youtube' ? <Youtube size={13} /> : <Globe size={13} />}
                                    {type === 'youtube' ? 'YouTube' : 'Website'}
                                </button>
                            ))}
                        </div>
                        <input
                            type="url"
                            value={urlInput}
                            onChange={(e) => setUrlInput(e.target.value)}
                            placeholder={urlType === 'youtube' ? 'https://youtube.com/watch?v=...' : 'https://example.com/article'}
                            style={{
                                width: '100%',
                                padding: '10px 14px',
                                borderRadius: '10px',
                                border: '1px solid var(--glass-edge)',
                                background: 'var(--glass-tint)',
                                color: 'var(--text-primary)',
                                fontSize: '14px',
                                outline: 'none',
                                boxSizing: 'border-box',
                            }}
                        />
                    </div>
                )}

                {/* Title & Tags (shared) */}
                <div style={{ display: 'flex', gap: '12px', marginTop: '12px', flexWrap: 'wrap' }}>
                    <input
                        type="text"
                        value={titleInput}
                        onChange={(e) => setTitleInput(e.target.value)}
                        placeholder="Title (optional)"
                        style={{
                            flex: '1 1 200px',
                            padding: '8px 12px',
                            borderRadius: '8px',
                            border: '1px solid var(--glass-edge)',
                            background: 'var(--glass-tint)',
                            color: 'var(--text-primary)',
                            fontSize: '13px',
                            outline: 'none',
                        }}
                    />
                    <input
                        type="text"
                        value={tagInput}
                        onChange={(e) => setTagInput(e.target.value)}
                        placeholder="Tags (comma-separated)"
                        style={{
                            flex: '1 1 200px',
                            padding: '8px 12px',
                            borderRadius: '8px',
                            border: '1px solid var(--glass-edge)',
                            background: 'var(--glass-tint)',
                            color: 'var(--text-primary)',
                            fontSize: '13px',
                            outline: 'none',
                        }}
                    />
                </div>

                {/* Submit Button (for URL mode) */}
                {uploadMode === 'url' && (
                    <button
                        onClick={handleUrlUpload}
                        disabled={uploading || !urlInput.trim()}
                        style={{
                            marginTop: '16px',
                            padding: '10px 24px',
                            borderRadius: '10px',
                            border: 'none',
                            background: uploading
                                ? 'var(--glass-tint)'
                                : 'linear-gradient(135deg, var(--accent-primary), var(--accent-secondary))',
                            color: '#fff',
                            fontWeight: 600,
                            fontSize: '14px',
                            cursor: uploading ? 'not-allowed' : 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '8px',
                            opacity: uploading ? 0.6 : 1,
                        }}
                    >
                        {uploading ? <Loader2 size={16} className="animate-spin" /> : <Plus size={16} />}
                        {uploading ? 'Submitting...' : 'Add URL'}
                    </button>
                )}
            </div>

            {/* Uploads List */}
            <div>
                <div
                    style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        marginBottom: '16px',
                    }}
                >
                    <h2 style={{ fontSize: '18px', fontWeight: 600, color: 'var(--text-primary)', margin: 0 }}>
                        Uploads ({uploads.length})
                    </h2>
                    <button
                        onClick={fetchUploads}
                        style={{
                            padding: '6px 12px',
                            borderRadius: '8px',
                            border: '1px solid var(--glass-edge)',
                            background: 'transparent',
                            color: 'var(--text-muted)',
                            fontSize: '12px',
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '4px',
                        }}
                    >
                        <RefreshCw size={12} />
                        Refresh
                    </button>
                </div>

                {loading ? (
                    <div style={{ textAlign: 'center', padding: '48px', color: 'var(--text-muted)' }}>
                        <Loader2 size={28} className="animate-spin" style={{ margin: '0 auto 12px' }} />
                        <p>Loading uploads...</p>
                    </div>
                ) : uploads.length === 0 ? (
                    <div
                        style={{
                            textAlign: 'center',
                            padding: '48px',
                            background: 'var(--glass-tint)',
                            borderRadius: '16px',
                            border: '1px solid var(--glass-edge)',
                        }}
                    >
                        <BookOpen size={40} style={{ color: 'var(--text-muted)', marginBottom: '12px' }} />
                        <p style={{ color: 'var(--text-secondary)', fontSize: '15px', fontWeight: 500 }}>
                            No uploads yet
                        </p>
                        <p style={{ color: 'var(--text-muted)', fontSize: '13px' }}>
                            Upload files or add URLs to build your personal knowledge base.
                        </p>
                    </div>
                ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                        {uploads.map((upload) => {
                            const StatusIcon = statusConfig[upload.status]?.icon || Clock;
                            const cfg = statusConfig[upload.status] || statusConfig.queued;
                            const SourceIcon = sourceIcons[upload.source_type] || FileText;

                            return (
                                <div
                                    key={upload.upload_id}
                                    style={{
                                        background: 'var(--glass-elevated)',
                                        backdropFilter: 'blur(var(--glass-blur))',
                                        border: '1px solid var(--glass-edge)',
                                        borderRadius: '14px',
                                        padding: '16px 20px',
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: '16px',
                                        transition: 'all 0.2s',
                                    }}
                                >
                                    {/* Source icon */}
                                    <div
                                        style={{
                                            width: '40px',
                                            height: '40px',
                                            borderRadius: '10px',
                                            background: 'var(--glass-tint)',
                                            display: 'flex',
                                            alignItems: 'center',
                                            justifyContent: 'center',
                                            flexShrink: 0,
                                        }}
                                    >
                                        <SourceIcon size={18} style={{ color: 'var(--text-secondary)' }} />
                                    </div>

                                    {/* Info */}
                                    <div style={{ flex: 1, minWidth: 0 }}>
                                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                                            <span
                                                style={{
                                                    fontSize: '14px',
                                                    fontWeight: 600,
                                                    color: 'var(--text-primary)',
                                                    overflow: 'hidden',
                                                    textOverflow: 'ellipsis',
                                                    whiteSpace: 'nowrap',
                                                }}
                                            >
                                                {upload.title || upload.source_uri}
                                            </span>
                                            {upload.is_private && (
                                                <Lock size={12} style={{ color: 'var(--text-muted)', flexShrink: 0 }} />
                                            )}
                                        </div>
                                        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
                                            {/* Status Badge */}
                                            <span
                                                style={{
                                                    display: 'inline-flex',
                                                    alignItems: 'center',
                                                    gap: '4px',
                                                    padding: '2px 8px',
                                                    borderRadius: '6px',
                                                    background: cfg.bg,
                                                    color: cfg.color,
                                                    fontSize: '11px',
                                                    fontWeight: 600,
                                                    textTransform: 'uppercase',
                                                    letterSpacing: '0.5px',
                                                }}
                                            >
                                                <StatusIcon
                                                    size={11}
                                                    className={upload.status === 'processing' ? 'animate-spin' : ''}
                                                />
                                                {cfg.label || upload.status}
                                            </span>
                                            {upload.chunk_count > 0 && (
                                                <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                                                    {upload.chunk_count} chunks • {upload.token_count?.toLocaleString()} tokens
                                                </span>
                                            )}
                                            {upload.tags && upload.tags.length > 0 && (
                                                <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
                                                    {upload.tags.slice(0, 3).map((tag) => (
                                                        <span
                                                            key={tag}
                                                            style={{
                                                                padding: '1px 6px',
                                                                borderRadius: '4px',
                                                                background: 'var(--glass-tint)',
                                                                color: 'var(--text-muted)',
                                                                fontSize: '10px',
                                                            }}
                                                        >
                                                            {tag}
                                                        </span>
                                                    ))}
                                                </div>
                                            )}
                                            {upload.error_reason && (
                                                <span style={{ fontSize: '11px', color: '#ef4444' }}>
                                                    {upload.error_reason}
                                                </span>
                                            )}
                                        {/* Show Extraction/Validation specific errors if available */}
                                        {!upload.error_reason && upload.extraction_status && upload.extraction_status !== 'ok' && (
                                            <span style={{ fontSize: '11px', color: '#ef4444' }}>
                                                Extraction: {upload.extraction_status}
                                            </span>
                                        )}
                                        {!upload.error_reason && upload.validation_status && upload.validation_status !== 'valid' && (
                                            <span style={{ fontSize: '11px', color: '#ef4444' }}>
                                                Validation: {upload.validation_status}
                                            </span>
                                        )}
                                    </div>
                                </div>

                                    {/* Actions */ }
                            <div style={{ display: 'flex', gap: '6px', flexShrink: 0 }}>
                                <button
                                    onClick={() => handleTogglePrivacy(upload)}
                                    title={upload.is_private ? 'Make Public' : 'Make Private'}
                                    style={actionBtnStyle}
                                >
                                    {upload.is_private ? <Unlock size={14} /> : <Lock size={14} />}
                                </button>
                                {(upload.status === 'error' || upload.status === 'indexed') && (
                                    <button
                                        onClick={() => handleReprocess(upload.upload_id)}
                                        title="Reprocess"
                                        style={actionBtnStyle}
                                    >
                                        <RefreshCw size={14} />
                                    </button>
                                )}
                                <button
                                    onClick={() => handleDelete(upload.upload_id)}
                                    title="Delete"
                                    style={{ ...actionBtnStyle, color: '#ef4444' }}
                                >
                                    <Trash2 size={14} />
                                </button>
                            </div>
                                </div>
                );
                        })}
            </div>
                )}
        </div>
        </div >
    );
};

// ── Shared action button style ──
const actionBtnStyle: React.CSSProperties = {
    padding: '6px',
    borderRadius: '8px',
    border: '1px solid var(--glass-edge)',
    background: 'transparent',
    color: 'var(--text-muted)',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    transition: 'all 0.15s',
};

export default StudentKnowledgePage;
