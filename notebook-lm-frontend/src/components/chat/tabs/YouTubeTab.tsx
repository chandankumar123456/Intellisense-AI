import React, { useState } from 'react';
import { Youtube, Plus, Trash2 } from 'lucide-react';
import { useChat } from '../../../contexts/ChatContext';

const YouTubeTab: React.FC = () => {
  const { youtubeSources, addYouTubeSource, removeYouTubeSource } = useChat();
  const [url, setUrl] = useState('');

  const handleAdd = () => {
    if (url.trim()) { addYouTubeSource(url.trim()); setUrl(''); }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') handleAdd();
  };

  return (
    <div className="space-y-4">
      <h3 className="text-sm font-semibold text-text_primary">YouTube Videos</h3>

      {/* Input + Button — aligned row */}
      <div className="flex items-stretch gap-2">
        <input
          type="url"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="https://youtube.com/watch?v=..."
          className="input-field flex-1"
          style={{ minHeight: '42px', fontSize: '13px' }}
          aria-label="YouTube video URL"
        />
        <button
          onClick={handleAdd}
          disabled={!url.trim()}
          className="btn-primary-liquid flex-shrink-0"
          style={{ minHeight: '42px', padding: '0 16px', fontSize: '13px' }}
          aria-label="Add YouTube video"
        >
          <Plus className="w-4 h-4 z-content relative" />
          <span className="z-content relative">Add</span>
        </button>
      </div>

      {youtubeSources.length === 0 ? (
        <div className="text-center py-8">
          <Youtube className="w-10 h-10 mx-auto mb-3" style={{ color: 'var(--text-muted)', opacity: 0.5 }} />
          <p className="text-sm text-text_secondary">No YouTube videos added</p>
          <p className="text-xs text-text_muted mt-1.5">Add video URLs to index and search their content</p>
        </div>
      ) : (
        <div className="space-y-2">
          {youtubeSources.map((video, index) => (
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
                href={video}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs flex-1 truncate transition-colors"
                style={{ color: 'var(--accent-primary)' }}
                onMouseEnter={(e) => { e.currentTarget.style.color = 'var(--accent-primary-dark)'; }}
                onMouseLeave={(e) => { e.currentTarget.style.color = 'var(--accent-primary)'; }}
              >
                {video}
              </a>
              <button
                onClick={() => removeYouTubeSource(video)}
                className="ml-2 flex items-center justify-center rounded-glass-sm transition-all duration-fast flex-shrink-0 active:scale-[0.9]"
                style={{
                  width: '32px', height: '32px',
                  background: 'transparent',
                  color: 'var(--text-muted)',
                }}
                onMouseEnter={(e) => { e.currentTarget.style.background = 'rgba(239,68,68,0.08)'; e.currentTarget.style.color = '#EF4444'; }}
                onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'var(--text-muted)'; }}
                aria-label="Remove video"
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

export default YouTubeTab;
