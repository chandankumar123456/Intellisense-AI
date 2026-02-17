import React, { useState } from 'react';
import { Globe, Plus, Trash2 } from 'lucide-react';
import { useChat } from '../../../contexts/ChatContext';

const WebTab: React.FC = () => {
  const { webSources, addWebSource, removeWebSource } = useChat();
  const [url, setUrl] = useState('');

  const handleAdd = () => {
    if (url.trim()) { addWebSource(url.trim()); setUrl(''); }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') handleAdd();
  };

  return (
    <div className="space-y-4">
      <h3 className="text-sm font-semibold text-text_primary">Web Sources</h3>

      {/* Input + Button — aligned row */}
      <div className="flex items-stretch gap-2">
        <input
          type="url"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="https://example.com"
          className="input-field flex-1"
          style={{ minHeight: '42px', fontSize: '13px' }}
          aria-label="Web source URL"
        />
        <button
          onClick={handleAdd}
          disabled={!url.trim()}
          className="btn-primary-liquid flex-shrink-0"
          style={{ minHeight: '42px', padding: '0 16px', fontSize: '13px' }}
          aria-label="Add web source"
        >
          <Plus className="w-4 h-4 z-content relative" />
          <span className="z-content relative">Add</span>
        </button>
      </div>

      {webSources.length === 0 ? (
        <div className="text-center py-8">
          <Globe className="w-10 h-10 mx-auto mb-3" style={{ color: 'var(--text-muted)', opacity: 0.5 }} />
          <p className="text-sm text-text_secondary">No web sources added</p>
          <p className="text-xs text-text_muted mt-1.5">Add URLs to search during queries</p>
        </div>
      ) : (
        <div className="space-y-2">
          {webSources.map((source, index) => (
            <div
              key={index}
              className="flex items-center justify-between rounded-glass-sm group"
              style={{
                padding: '10px 12px',
                minHeight: '42px',
                background: 'var(--glass-surface)',
                border: '1px solid var(--border-subtle)',
              }}
            >
              <a
                href={source}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs flex-1 truncate transition-colors"
                style={{ color: 'var(--accent-primary)' }}
                onMouseEnter={(e) => { e.currentTarget.style.color = 'var(--accent-primary-dark)'; }}
                onMouseLeave={(e) => { e.currentTarget.style.color = 'var(--accent-primary)'; }}
              >
                {source}
              </a>
              <button
                onClick={() => removeWebSource(source)}
                className="ml-2 flex items-center justify-center rounded-glass-sm transition-all duration-fast flex-shrink-0 active:scale-[0.9]"
                style={{
                  width: '32px', height: '32px',
                  background: 'transparent',
                  color: 'var(--text-muted)',
                }}
                onMouseEnter={(e) => { e.currentTarget.style.background = 'rgba(239,68,68,0.08)'; e.currentTarget.style.color = '#EF4444'; }}
                onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'var(--text-muted)'; }}
                aria-label="Remove source"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default WebTab;
