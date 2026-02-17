import React, { useRef } from 'react';
import { FileText, Upload, X } from 'lucide-react';
import { useChat } from '../../../contexts/ChatContext';

const MyFilesTab: React.FC = () => {
  const { files, addFile, removeFile } = useChat();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleUploadClick = () => { fileInputRef.current?.click(); };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      await addFile(file);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-text_primary">My Files</h3>
        <input
          type="file"
          ref={fileInputRef}
          onChange={handleFileChange}
          className="hidden"
          accept=".pdf,.txt,.md,.doc,.docx"
        />
        <button
          onClick={handleUploadClick}
          className="btn-liquid flex-shrink-0"
          style={{ minHeight: '36px', padding: '6px 14px', fontSize: '13px' }}
          aria-label="Upload file"
        >
          <Upload className="w-4 h-4 z-content relative" />
          <span className="z-content relative">Upload</span>
        </button>
      </div>

      {files.length === 0 ? (
        <div className="text-center py-8">
          <FileText className="w-10 h-10 mx-auto mb-3" style={{ color: 'var(--text-muted)', opacity: 0.5 }} />
          <p className="text-sm text-text_secondary">No files uploaded yet</p>
          <p className="text-xs text-text_muted mt-1.5">Upload documents to search through them</p>
        </div>
      ) : (
        <div className="space-y-2">
          {files.map((file) => (
            <div
              key={file.id}
              className="flex items-center justify-between rounded-glass-sm group"
              style={{
                padding: '10px 12px',
                minHeight: '42px',
                background: 'var(--glass-surface)',
                border: '1px solid var(--border-subtle)',
                transition: 'all 180ms cubic-bezier(0.22, 1, 0.36, 1)',
              }}
              onMouseEnter={(e) => { e.currentTarget.style.boxShadow = '0 2px 8px var(--glass-shadow)'; }}
              onMouseLeave={(e) => { e.currentTarget.style.boxShadow = 'none'; }}
            >
              <div className="flex items-center gap-2.5 overflow-hidden flex-1 min-w-0">
                <FileText className="w-4 h-4 flex-shrink-0" style={{ color: 'var(--accent-primary)' }} />
                <div className="truncate min-w-0">
                  <p className="text-xs font-medium text-text_primary truncate">{file.name}</p>
                  <p className="text-[11px] text-text_muted">
                    {(file.size / 1024).toFixed(1)} KB
                  </p>
                </div>
              </div>
              <button
                onClick={() => removeFile(file.id)}
                className="ml-2 flex items-center justify-center rounded-glass-sm transition-all duration-fast flex-shrink-0 opacity-0 group-hover:opacity-100 active:scale-[0.9]"
                style={{
                  width: '28px', height: '28px',
                  background: 'transparent',
                  color: 'var(--text-muted)',
                }}
                onMouseEnter={(e) => { e.currentTarget.style.background = 'rgba(239,68,68,0.08)'; e.currentTarget.style.color = '#EF4444'; }}
                onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'var(--text-muted)'; }}
                aria-label="Remove file"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default MyFilesTab;
