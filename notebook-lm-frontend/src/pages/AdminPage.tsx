import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
    Upload, Database, Activity, FileText, Wrench,
    Loader2, Trash2, Search, RefreshCw, CheckCircle,
    AlertTriangle, HardDrive, Zap, BarChart3, Clock,
    FileUp, X, ChevronDown, ChevronUp, Shield,
} from 'lucide-react';
import toast from 'react-hot-toast';
import adminService, {
    SystemStats,
    DocumentInfo,
    AuditEntry,
    PromotionCandidate,
    EvictionCandidate,
} from '../services/adminService';

type Tab = 'upload' | 'documents' | 'health' | 'audit' | 'maintenance';

const tabs: { id: Tab; label: string; icon: React.ElementType }[] = [
    { id: 'upload', label: 'Upload', icon: Upload },
    { id: 'documents', label: 'Documents', icon: Database },
    { id: 'health', label: 'System Health', icon: Activity },
    { id: 'audit', label: 'Audit Logs', icon: FileText },
    { id: 'maintenance', label: 'Maintenance', icon: Wrench },
];

// ═══════════════════════════════════════════════════
// MAIN ADMIN PAGE
// ═══════════════════════════════════════════════════

const AdminPage: React.FC = () => {
    const [activeTab, setActiveTab] = useState<Tab>('upload');

    return (
        <div className="p-4 sm:p-6 lg:p-8 overflow-y-auto h-full" style={{ background: 'var(--bg-primary)' }}>
            <div className="max-w-6xl mx-auto">
                {/* Header */}
                <div className="mb-6 sm:mb-8">
                    <div className="flex items-center gap-3 mb-2">
                        <div
                            className="w-10 h-10 sm:w-11 sm:h-11 rounded-glass-sm flex items-center justify-center flex-shrink-0"
                            style={{
                                background: 'linear-gradient(135deg, var(--accent-primary), var(--accent-secondary))',
                                boxShadow: '0 4px 16px var(--hover-glow)',
                            }}
                        >
                            <Shield className="w-5 h-5 text-white" />
                        </div>
                        <div>
                            <h1 className="text-xl sm:text-2xl font-semibold tracking-tight" style={{ color: 'var(--text-primary)' }}>
                                Admin Dashboard
                            </h1>
                            <p className="text-xs sm:text-sm" style={{ color: 'var(--text-muted)' }}>
                                Manage documents, monitor system health, and maintain your knowledge base
                            </p>
                        </div>
                    </div>
                </div>

                {/* Tab Bar */}
                <div
                    className="liquid-glass rounded-glass mb-6"
                    style={{ padding: '6px' }}
                >
                    <div className="z-content relative flex flex-wrap gap-1">
                        {tabs.map((tab) => {
                            const Icon = tab.icon;
                            const isActive = activeTab === tab.id;
                            return (
                                <button
                                    key={tab.id}
                                    onClick={() => setActiveTab(tab.id)}
                                    className="flex items-center gap-2 px-4 py-2.5 rounded-glass-sm text-sm font-medium transition-all duration-fast"
                                    style={{
                                        background: isActive
                                            ? 'linear-gradient(135deg, var(--accent-primary), var(--accent-secondary))'
                                            : 'transparent',
                                        color: isActive ? '#fff' : 'var(--text-secondary)',
                                        boxShadow: isActive ? '0 4px 16px var(--hover-glow)' : 'none',
                                    }}
                                    onMouseEnter={(e) => {
                                        if (!isActive) e.currentTarget.style.background = 'var(--hover-glow)';
                                    }}
                                    onMouseLeave={(e) => {
                                        if (!isActive) e.currentTarget.style.background = 'transparent';
                                    }}
                                >
                                    <Icon className="w-4 h-4" />
                                    <span className="hidden sm:inline">{tab.label}</span>
                                </button>
                            );
                        })}
                    </div>
                </div>

                {/* Tab Content */}
                <div className="animate-fade-in">
                    {activeTab === 'upload' && <UploadTab />}
                    {activeTab === 'documents' && <DocumentsTab />}
                    {activeTab === 'health' && <HealthTab />}
                    {activeTab === 'audit' && <AuditTab />}
                    {activeTab === 'maintenance' && <MaintenanceTab />}
                </div>
            </div>
        </div>
    );
};

// ═══════════════════════════════════════════════════
// TAB 1: UPLOAD
// ═══════════════════════════════════════════════════

const UploadTab: React.FC = () => {
    const [file, setFile] = useState<File | null>(null);
    const [subject, setSubject] = useState('');
    const [topic, setTopic] = useState('');
    const [subtopic, setSubtopic] = useState('');
    const [syllabusKeywords, setSyllabusKeywords] = useState('');
    const [uploading, setUploading] = useState(false);
    const [recentUploads, setRecentUploads] = useState<{ name: string; docId: string; status: string }[]>([]);
    const [dragOver, setDragOver] = useState(false);
    const fileInputRef = useRef<HTMLInputElement>(null);

    const handleDrop = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        setDragOver(false);
        const droppedFile = e.dataTransfer.files[0];
        if (droppedFile) setFile(droppedFile);
    }, []);

    const handleUpload = async () => {
        if (!file) return;
        setUploading(true);
        try {
            const result = await adminService.uploadDocument(file, {
                subject,
                topic,
                subtopic,
                syllabus_keywords: syllabusKeywords,
            });
            toast.success(`${file.name} queued for smart ingestion!`);
            setRecentUploads((prev) => [
                { name: file.name, docId: result.document_id || '', status: 'processing' },
                ...prev.slice(0, 9),
            ]);
            setFile(null);
            setSubject('');
            setTopic('');
            setSubtopic('');
            setSyllabusKeywords('');
            if (fileInputRef.current) fileInputRef.current.value = '';
        } catch (err) {
            toast.error('Upload failed. Please try again.');
        } finally {
            setUploading(false);
        }
    };

    return (
        <div className="space-y-5">
            {/* Drop zone */}
            <div
                className={`liquid-glass rounded-glass transition-all duration-normal cursor-pointer`}
                style={{
                    padding: '32px',
                    borderStyle: dragOver ? 'dashed' : 'solid',
                    borderColor: dragOver ? 'var(--accent-primary)' : undefined,
                    background: dragOver ? 'var(--hover-glow)' : undefined,
                }}
                onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
                onDragLeave={() => setDragOver(false)}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
            >
                <div className="z-content relative flex flex-col items-center text-center">
                    <div
                        className="w-16 h-16 rounded-full flex items-center justify-center mb-4"
                        style={{
                            background: 'linear-gradient(135deg, var(--accent-primary), var(--accent-secondary))',
                            boxShadow: '0 8px 24px var(--hover-glow)',
                            opacity: 0.9,
                        }}
                    >
                        <FileUp className="w-7 h-7 text-white" />
                    </div>
                    <p className="text-sm font-medium mb-1" style={{ color: 'var(--text-primary)' }}>
                        {file ? file.name : 'Drag & drop your document here'}
                    </p>
                    <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
                        {file
                            ? `${(file.size / 1024 / 1024).toFixed(2)} MB — Click upload below`
                            : 'Supports PDF, TXT, MD files'}
                    </p>
                    {file && (
                        <button
                            onClick={(e) => { e.stopPropagation(); setFile(null); if (fileInputRef.current) fileInputRef.current.value = ''; }}
                            className="mt-2 flex items-center gap-1 text-xs px-3 py-1 rounded-pill"
                            style={{ background: 'rgba(239,68,68,0.1)', color: '#EF4444' }}
                        >
                            <X className="w-3 h-3" /> Remove
                        </button>
                    )}
                    <input
                        ref={fileInputRef}
                        type="file"
                        accept=".pdf,.txt,.md"
                        className="hidden"
                        onChange={(e) => { if (e.target.files?.[0]) setFile(e.target.files[0]); }}
                    />
                </div>
            </div>

            {/* Metadata form */}
            <div className="liquid-glass rounded-glass" style={{ padding: '20px' }}>
                <div className="z-content relative">
                    <h3 className="text-sm font-semibold mb-4" style={{ color: 'var(--text-primary)' }}>
                        Document Metadata
                    </h3>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                        <div>
                            <label className="block text-xs font-medium mb-1" style={{ color: 'var(--text-secondary)' }}>Subject</label>
                            <input className="input-field" value={subject} onChange={(e) => setSubject(e.target.value)} placeholder="e.g., Computer Science" />
                        </div>
                        <div>
                            <label className="block text-xs font-medium mb-1" style={{ color: 'var(--text-secondary)' }}>Topic</label>
                            <input className="input-field" value={topic} onChange={(e) => setTopic(e.target.value)} placeholder="e.g., Machine Learning" />
                        </div>
                        <div>
                            <label className="block text-xs font-medium mb-1" style={{ color: 'var(--text-secondary)' }}>Subtopic</label>
                            <input className="input-field" value={subtopic} onChange={(e) => setSubtopic(e.target.value)} placeholder="e.g., Neural Networks" />
                        </div>
                        <div>
                            <label className="block text-xs font-medium mb-1" style={{ color: 'var(--text-secondary)' }}>
                                Syllabus Keywords <span style={{ color: 'var(--text-muted)' }}>(comma-separated)</span>
                            </label>
                            <input
                                className="input-field"
                                value={syllabusKeywords}
                                onChange={(e) => setSyllabusKeywords(e.target.value)}
                                placeholder="e.g., CNN, gradient descent, backpropagation"
                            />
                        </div>
                    </div>
                    <div className="mt-4 flex justify-end">
                        <button
                            onClick={handleUpload}
                            disabled={!file || uploading}
                            className="btn-primary-liquid"
                            style={{ minHeight: '42px', padding: '0 28px', fontSize: '14px' }}
                        >
                            {uploading ? (
                                <>
                                    <Loader2 className="w-4 h-4 animate-spin z-content relative" />
                                    <span className="z-content relative">Uploading...</span>
                                </>
                            ) : (
                                <>
                                    <Upload className="w-4 h-4 z-content relative" />
                                    <span className="z-content relative">Upload & Index</span>
                                </>
                            )}
                        </button>
                    </div>
                </div>
            </div>

            {/* Recent uploads */}
            {recentUploads.length > 0 && (
                <div className="liquid-glass rounded-glass" style={{ padding: '16px' }}>
                    <div className="z-content relative">
                        <h3 className="text-sm font-semibold mb-3" style={{ color: 'var(--text-primary)' }}>Recent Uploads</h3>
                        <div className="space-y-2">
                            {recentUploads.map((u, i) => (
                                <div
                                    key={i}
                                    className="flex items-center justify-between py-2 px-3 rounded-glass-sm"
                                    style={{ background: 'var(--glass-surface)' }}
                                >
                                    <div className="flex items-center gap-2 min-w-0">
                                        <FileText className="w-4 h-4 flex-shrink-0" style={{ color: 'var(--accent-primary)' }} />
                                        <span className="text-sm truncate" style={{ color: 'var(--text-primary)' }}>{u.name}</span>
                                    </div>
                                    <span
                                        className="text-[11px] font-medium px-2 py-0.5 rounded-pill flex-shrink-0"
                                        style={{
                                            background: 'rgba(34,197,94,0.1)',
                                            color: '#22C55E',
                                        }}
                                    >
                                        {u.status}
                                    </span>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

// ═══════════════════════════════════════════════════
// TAB 2: DOCUMENTS
// ═══════════════════════════════════════════════════

const DocumentsTab: React.FC = () => {
    const [docs, setDocs] = useState<DocumentInfo[]>([]);
    const [loading, setLoading] = useState(true);
    const [search, setSearch] = useState('');
    const [deleting, setDeleting] = useState<string | null>(null);

    const fetchDocs = useCallback(async () => {
        setLoading(true);
        try {
            const result = await adminService.getDocuments(
                search ? { subject: search } : undefined
            );
            setDocs(result.documents || []);
        } catch {
            toast.error('Failed to load documents');
        } finally {
            setLoading(false);
        }
    }, [search]);

    useEffect(() => { fetchDocs(); }, [fetchDocs]);

    const handleDelete = async (docId: string) => {
        if (!window.confirm(`Delete document ${docId.slice(0, 8)}...? This removes it from all layers.`)) return;
        setDeleting(docId);
        try {
            await adminService.deleteDocument(docId);
            toast.success('Document deleted from all layers');
            fetchDocs();
        } catch {
            toast.error('Delete failed');
        } finally {
            setDeleting(null);
        }
    };

    return (
        <div className="space-y-4">
            {/* Search bar */}
            <div className="liquid-glass rounded-glass" style={{ padding: '12px 16px' }}>
                <div className="z-content relative flex items-center gap-3">
                    <Search className="w-4 h-4 flex-shrink-0" style={{ color: 'var(--text-muted)' }} />
                    <input
                        className="flex-1 bg-transparent border-none outline-none text-sm"
                        style={{ color: 'var(--text-primary)' }}
                        placeholder="Filter by subject..."
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                    />
                    <button onClick={fetchDocs} className="btn-liquid" style={{ minHeight: '34px', padding: '0 14px', fontSize: '12px' }}>
                        <RefreshCw className="w-3.5 h-3.5 z-content relative" />
                    </button>
                </div>
            </div>

            {/* Documents list */}
            {loading ? (
                <div className="flex justify-center py-12">
                    <Loader2 className="w-6 h-6 animate-spin" style={{ color: 'var(--accent-primary)' }} />
                </div>
            ) : docs.length === 0 ? (
                <div className="liquid-glass rounded-glass text-center" style={{ padding: '40px' }}>
                    <div className="z-content relative">
                        <Database className="w-10 h-10 mx-auto mb-3" style={{ color: 'var(--text-muted)', opacity: 0.5 }} />
                        <p className="text-sm" style={{ color: 'var(--text-muted)' }}>No documents indexed yet. Upload some in the Upload tab!</p>
                    </div>
                </div>
            ) : (
                <div className="space-y-2">
                    {docs.map((doc) => (
                        <div key={doc.doc_id} className="liquid-glass rounded-glass" style={{ padding: '14px 16px' }}>
                            <div className="z-content relative">
                                <div className="flex items-start justify-between gap-3">
                                    <div className="min-w-0 flex-1">
                                        <div className="flex items-center gap-2 mb-1.5">
                                            <span
                                                className="text-[10px] font-bold uppercase px-2 py-0.5 rounded-pill"
                                                style={{
                                                    background: doc.source_type === 'pdf' ? 'rgba(239,68,68,0.1)' : 'rgba(59,130,246,0.1)',
                                                    color: doc.source_type === 'pdf' ? '#EF4444' : '#3B82F6',
                                                }}
                                            >
                                                {doc.source_type}
                                            </span>
                                            {doc.subject && (
                                                <span className="text-[10px] font-medium px-2 py-0.5 rounded-pill"
                                                    style={{ background: 'var(--hover-glow)', color: 'var(--accent-primary)' }}>
                                                    {doc.subject}
                                                </span>
                                            )}
                                            {doc.topic && (
                                                <span className="text-[10px] font-medium px-2 py-0.5 rounded-pill"
                                                    style={{ background: 'var(--active-glow)', color: 'var(--accent-secondary)' }}>
                                                    {doc.topic}
                                                </span>
                                            )}
                                        </div>
                                        <p className="text-xs font-mono truncate" style={{ color: 'var(--text-secondary)' }}>
                                            {doc.source_url || doc.doc_id}
                                        </p>
                                        <div className="flex flex-wrap gap-4 mt-2 text-[11px]" style={{ color: 'var(--text-muted)' }}>
                                            <span>Chunks: <strong style={{ color: 'var(--text-primary)' }}>{doc.total_chunks}</strong></span>
                                            <span>Embedded: <strong style={{ color: '#22C55E' }}>{doc.embedded_chunks}</strong></span>
                                            <span>Importance: <strong style={{ color: 'var(--accent-primary)' }}>{doc.avg_importance.toFixed(2)}</strong></span>
                                            <span>Hits: <strong>{doc.total_hits}</strong></span>
                                        </div>
                                    </div>
                                    <button
                                        onClick={() => handleDelete(doc.doc_id)}
                                        disabled={deleting === doc.doc_id}
                                        className="flex-shrink-0 btn-liquid"
                                        style={{ minHeight: '32px', padding: '0 10px', color: '#EF4444' }}
                                    >
                                        {deleting === doc.doc_id ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Trash2 className="w-3.5 h-3.5 z-content relative" />}
                                    </button>
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
};

// ═══════════════════════════════════════════════════
// TAB 3: SYSTEM HEALTH
// ═══════════════════════════════════════════════════

const HealthTab: React.FC = () => {
    const [stats, setStats] = useState<SystemStats | null>(null);
    const [loading, setLoading] = useState(true);

    const fetchStats = useCallback(async () => {
        setLoading(true);
        try {
            const data = await adminService.getStats();
            setStats(data);
        } catch {
            toast.error('Failed to load stats');
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => { fetchStats(); }, [fetchStats]);

    if (loading || !stats) {
        return (
            <div className="flex justify-center py-16">
                <Loader2 className="w-6 h-6 animate-spin" style={{ color: 'var(--accent-primary)' }} />
            </div>
        );
    }

    const statCards = [
        { label: 'Total Chunks', value: stats.total_chunks, icon: Database, color: 'var(--accent-primary)' },
        { label: 'Embedded (Vector DB)', value: stats.embedded_chunks, icon: Zap, color: '#22C55E' },
        { label: 'Raw Only (Metadata)', value: stats.raw_chunks, icon: HardDrive, color: '#F59E0B' },
        { label: 'Unique Docs', value: stats.unique_documents, icon: FileText, color: 'var(--accent-secondary)' },
        { label: 'Total Query Hits', value: stats.total_query_hits, icon: BarChart3, color: '#3B82F6' },
        { label: 'Audit Logs', value: stats.audit_log_count, icon: Clock, color: '#8B5CF6' },
    ];

    return (
        <div className="space-y-5">
            {/* Stats grid */}
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                {statCards.map((card) => {
                    const Icon = card.icon;
                    return (
                        <div key={card.label} className="liquid-glass rounded-glass" style={{ padding: '16px' }}>
                            <div className="z-content relative">
                                <div className="flex items-center gap-2 mb-2">
                                    <Icon className="w-4 h-4" style={{ color: card.color }} />
                                    <span className="text-[11px] font-medium" style={{ color: 'var(--text-muted)' }}>{card.label}</span>
                                </div>
                                <p className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>
                                    {card.value.toLocaleString()}
                                </p>
                            </div>
                        </div>
                    );
                })}
            </div>

            {/* Avg Importance */}
            <div className="liquid-glass rounded-glass" style={{ padding: '16px' }}>
                <div className="z-content relative">
                    <h3 className="text-sm font-semibold mb-3" style={{ color: 'var(--text-primary)' }}>Average Importance Score</h3>
                    <div className="flex items-center gap-3">
                        <div className="flex-1 h-3 rounded-pill overflow-hidden" style={{ background: 'var(--glass-surface)' }}>
                            <div
                                className="h-full rounded-pill transition-all duration-slow"
                                style={{
                                    width: `${Math.min(100, stats.avg_importance * 100)}%`,
                                    background: 'linear-gradient(90deg, var(--accent-primary), var(--accent-secondary))',
                                }}
                            />
                        </div>
                        <span className="text-sm font-bold" style={{ color: 'var(--accent-primary)' }}>
                            {stats.avg_importance.toFixed(4)}
                        </span>
                    </div>
                </div>
            </div>

            {/* Subject & Topic breakdown */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {/* Subjects */}
                <div className="liquid-glass rounded-glass" style={{ padding: '16px' }}>
                    <div className="z-content relative">
                        <h3 className="text-sm font-semibold mb-3" style={{ color: 'var(--text-primary)' }}>Top Subjects</h3>
                        {stats.top_subjects.length === 0 ? (
                            <p className="text-xs" style={{ color: 'var(--text-muted)' }}>No subjects yet</p>
                        ) : (
                            <div className="space-y-2">
                                {stats.top_subjects.map((s) => (
                                    <div key={s.subject} className="flex items-center justify-between">
                                        <span className="text-xs truncate" style={{ color: 'var(--text-secondary)' }}>{s.subject}</span>
                                        <span className="text-xs font-bold ml-2" style={{ color: 'var(--accent-primary)' }}>{s.count}</span>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                </div>

                {/* Topics */}
                <div className="liquid-glass rounded-glass" style={{ padding: '16px' }}>
                    <div className="z-content relative">
                        <h3 className="text-sm font-semibold mb-3" style={{ color: 'var(--text-primary)' }}>Top Topics</h3>
                        {stats.top_topics.length === 0 ? (
                            <p className="text-xs" style={{ color: 'var(--text-muted)' }}>No topics yet</p>
                        ) : (
                            <div className="space-y-2">
                                {stats.top_topics.map((t) => (
                                    <div key={t.topic} className="flex items-center justify-between">
                                        <span className="text-xs truncate" style={{ color: 'var(--text-secondary)' }}>{t.topic}</span>
                                        <span className="text-xs font-bold ml-2" style={{ color: 'var(--accent-secondary)' }}>{t.count}</span>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                </div>
            </div>

            {/* Source types */}
            <div className="liquid-glass rounded-glass" style={{ padding: '16px' }}>
                <div className="z-content relative">
                    <h3 className="text-sm font-semibold mb-3" style={{ color: 'var(--text-primary)' }}>Source Type Breakdown</h3>
                    <div className="flex flex-wrap gap-3">
                        {stats.source_types.map((st) => (
                            <div
                                key={st.type}
                                className="flex items-center gap-2 px-3 py-2 rounded-glass-sm"
                                style={{ background: 'var(--glass-surface)' }}
                            >
                                <span className="text-xs font-bold uppercase" style={{ color: 'var(--accent-primary)' }}>{st.type}</span>
                                <span className="text-sm font-bold" style={{ color: 'var(--text-primary)' }}>{st.count}</span>
                            </div>
                        ))}
                    </div>
                </div>
            </div>

            <div className="flex justify-end">
                <button onClick={fetchStats} className="btn-liquid" style={{ fontSize: '12px', minHeight: '36px', padding: '0 16px' }}>
                    <RefreshCw className="w-3.5 h-3.5 z-content relative" />
                    <span className="z-content relative">Refresh</span>
                </button>
            </div>
        </div>
    );
};

// ═══════════════════════════════════════════════════
// TAB 4: AUDIT LOGS
// ═══════════════════════════════════════════════════

const AuditTab: React.FC = () => {
    const [audits, setAudits] = useState<AuditEntry[]>([]);
    const [loading, setLoading] = useState(true);
    const [expandedId, setExpandedId] = useState<string | null>(null);

    const fetchAudits = useCallback(async () => {
        setLoading(true);
        try {
            const result = await adminService.getAuditLogs(50);
            setAudits(result.audits || []);
        } catch {
            toast.error('Failed to load audit logs');
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => { fetchAudits(); }, [fetchAudits]);

    const confidenceColor = (c: number) => {
        if (c >= 0.7) return '#22C55E';
        if (c >= 0.4) return '#F59E0B';
        return '#EF4444';
    };

    return (
        <div className="space-y-3">
            <div className="flex items-center justify-between mb-2">
                <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
                    {audits.length} audit records
                </p>
                <button onClick={fetchAudits} className="btn-liquid" style={{ fontSize: '12px', minHeight: '34px', padding: '0 14px' }}>
                    <RefreshCw className="w-3.5 h-3.5 z-content relative" />
                </button>
            </div>

            {loading ? (
                <div className="flex justify-center py-12">
                    <Loader2 className="w-6 h-6 animate-spin" style={{ color: 'var(--accent-primary)' }} />
                </div>
            ) : audits.length === 0 ? (
                <div className="liquid-glass rounded-glass text-center" style={{ padding: '40px' }}>
                    <div className="z-content relative">
                        <FileText className="w-10 h-10 mx-auto mb-3" style={{ color: 'var(--text-muted)', opacity: 0.5 }} />
                        <p className="text-sm" style={{ color: 'var(--text-muted)' }}>No audit logs yet. Verify some claims first!</p>
                    </div>
                </div>
            ) : (
                audits.map((audit) => {
                    const isExpanded = expandedId === audit.audit_id;
                    return (
                        <div
                            key={audit.audit_id}
                            className="liquid-glass rounded-glass cursor-pointer transition-all duration-fast"
                            style={{
                                padding: '12px 16px',
                                borderLeft: `3px solid ${confidenceColor(audit.overall_confidence)}`,
                            }}
                            onClick={() => setExpandedId(isExpanded ? null : audit.audit_id)}
                        >
                            <div className="z-content relative">
                                <div className="flex items-start justify-between gap-3">
                                    <div className="min-w-0 flex-1">
                                        <p className="text-sm font-medium truncate" style={{ color: 'var(--text-primary)' }}>
                                            {audit.query || 'No query'}
                                        </p>
                                        <div className="flex flex-wrap gap-3 mt-1 text-[11px]" style={{ color: 'var(--text-muted)' }}>
                                            <span>Type: <strong>{audit.type || audit.input_type}</strong></span>
                                            <span>Claims: <strong>{audit.claims_count}</strong></span>
                                            <span style={{ color: confidenceColor(audit.overall_confidence) }}>
                                                Confidence: <strong>{(audit.overall_confidence * 100).toFixed(0)}%</strong>
                                            </span>
                                        </div>
                                    </div>
                                    <div className="flex items-center gap-2 flex-shrink-0">
                                        <span className="text-[10px]" style={{ color: 'var(--text-muted)' }}>
                                            {audit.recorded_at ? new Date(audit.recorded_at).toLocaleString() : ''}
                                        </span>
                                        {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                                    </div>
                                </div>

                                {isExpanded && (
                                    <div className="mt-3 pt-3" style={{ borderTop: '1px solid var(--border-subtle)' }}>
                                        <div className="grid grid-cols-2 gap-2 text-xs" style={{ color: 'var(--text-secondary)' }}>
                                            <p><strong>Audit ID:</strong> <span className="font-mono text-[11px]">{audit.audit_id}</span></p>
                                            <p><strong>User:</strong> {audit.user_id || 'anonymous'}</p>
                                        </div>
                                        {audit.warnings && audit.warnings.length > 0 && (
                                            <div className="mt-2 flex flex-wrap gap-1">
                                                {audit.warnings.map((w, i) => (
                                                    <span
                                                        key={i}
                                                        className="text-[10px] px-2 py-0.5 rounded-pill"
                                                        style={{ background: 'rgba(245,158,11,0.1)', color: '#F59E0B' }}
                                                    >
                                                        <AlertTriangle className="w-3 h-3 inline mr-1" />{w}
                                                    </span>
                                                ))}
                                            </div>
                                        )}
                                    </div>
                                )}
                            </div>
                        </div>
                    );
                })
            )}
        </div>
    );
};

// ═══════════════════════════════════════════════════
// TAB 5: MAINTENANCE
// ═══════════════════════════════════════════════════

const MaintenanceTab: React.FC = () => {
    const [promotionCandidates, setPromotionCandidates] = useState<PromotionCandidate[]>([]);
    const [evictionCandidates, setEvictionCandidates] = useState<EvictionCandidate[]>([]);
    const [loading, setLoading] = useState(true);

    const fetchData = useCallback(async () => {
        setLoading(true);
        try {
            const [promo, evict] = await Promise.all([
                adminService.getPromotionCandidates(),
                adminService.getEvictionCandidates(),
            ]);
            setPromotionCandidates(promo.candidates || []);
            setEvictionCandidates(evict.candidates || []);
        } catch {
            toast.error('Failed to load maintenance data');
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => { fetchData(); }, [fetchData]);

    if (loading) {
        return (
            <div className="flex justify-center py-16">
                <Loader2 className="w-6 h-6 animate-spin" style={{ color: 'var(--accent-primary)' }} />
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* Promotion candidates */}
            <div className="liquid-glass rounded-glass" style={{ padding: '20px' }}>
                <div className="z-content relative">
                    <div className="flex items-center gap-2 mb-4">
                        <Zap className="w-4 h-4" style={{ color: '#22C55E' }} />
                        <h3 className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
                            Promotion Candidates
                        </h3>
                        <span className="text-[11px] font-medium px-2 py-0.5 rounded-pill" style={{ background: 'rgba(34,197,94,0.1)', color: '#22C55E' }}>
                            {promotionCandidates.length}
                        </span>
                    </div>
                    <p className="text-xs mb-3" style={{ color: 'var(--text-muted)' }}>
                        Raw chunks with high query counts that should be promoted to the vector index for faster retrieval.
                    </p>
                    {promotionCandidates.length === 0 ? (
                        <div className="text-center py-6">
                            <CheckCircle className="w-8 h-8 mx-auto mb-2" style={{ color: '#22C55E', opacity: 0.5 }} />
                            <p className="text-xs" style={{ color: 'var(--text-muted)' }}>No promotion candidates — all frequently queried chunks are already embedded!</p>
                        </div>
                    ) : (
                        <div className="space-y-2 max-h-64 overflow-y-auto">
                            {promotionCandidates.map((c) => (
                                <div key={c.id} className="flex items-start justify-between gap-3 py-2 px-3 rounded-glass-sm" style={{ background: 'var(--glass-surface)' }}>
                                    <div className="min-w-0">
                                        <p className="text-xs truncate" style={{ color: 'var(--text-primary)' }}>{c.chunk_text?.slice(0, 100) || c.id}</p>
                                        <p className="text-[11px]" style={{ color: 'var(--text-muted)' }}>
                                            Hits: <strong>{c.query_count}</strong> · Importance: <strong>{c.importance_score?.toFixed(2)}</strong>
                                        </p>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            </div>

            {/* Eviction candidates */}
            <div className="liquid-glass rounded-glass" style={{ padding: '20px' }}>
                <div className="z-content relative">
                    <div className="flex items-center gap-2 mb-4">
                        <Trash2 className="w-4 h-4" style={{ color: '#EF4444' }} />
                        <h3 className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
                            Eviction Candidates
                        </h3>
                        <span className="text-[11px] font-medium px-2 py-0.5 rounded-pill" style={{ background: 'rgba(239,68,68,0.1)', color: '#EF4444' }}>
                            {evictionCandidates.length}
                        </span>
                    </div>
                    <p className="text-xs mb-3" style={{ color: 'var(--text-muted)' }}>
                        Embedded chunks with low usage and importance that could be removed from the vector index to save storage.
                    </p>
                    {evictionCandidates.length === 0 ? (
                        <div className="text-center py-6">
                            <CheckCircle className="w-8 h-8 mx-auto mb-2" style={{ color: '#22C55E', opacity: 0.5 }} />
                            <p className="text-xs" style={{ color: 'var(--text-muted)' }}>No eviction candidates — all embedded chunks are actively used!</p>
                        </div>
                    ) : (
                        <div className="space-y-2 max-h-64 overflow-y-auto">
                            {evictionCandidates.map((c) => (
                                <div key={c.id} className="flex items-start justify-between gap-3 py-2 px-3 rounded-glass-sm" style={{ background: 'var(--glass-surface)' }}>
                                    <div className="min-w-0">
                                        <p className="text-xs truncate" style={{ color: 'var(--text-primary)' }}>{c.chunk_text?.slice(0, 100) || c.id}</p>
                                        <p className="text-[11px]" style={{ color: 'var(--text-muted)' }}>
                                            Importance: <strong>{c.importance_score?.toFixed(2)}</strong> · Last queried: <strong>{c.last_queried_at || 'never'}</strong>
                                        </p>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            </div>

            <div className="flex justify-end">
                <button onClick={fetchData} className="btn-liquid" style={{ fontSize: '12px', minHeight: '36px', padding: '0 16px' }}>
                    <RefreshCw className="w-3.5 h-3.5 z-content relative" />
                    <span className="z-content relative">Refresh</span>
                </button>
            </div>
        </div>
    );
};

export default AdminPage;
