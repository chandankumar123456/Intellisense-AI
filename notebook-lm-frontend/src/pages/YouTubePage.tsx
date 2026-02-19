import React from 'react';
import { Youtube, Plus, Play } from 'lucide-react';

const YouTubePage: React.FC = () => {
  return (
    <div className="p-4 sm:p-6 lg:p-8 overflow-y-auto h-full" style={{ background: 'var(--bg-primary)' }}>
      <div className="max-w-4xl mx-auto">
        <div className="flex items-center gap-2.5 mb-6 sm:mb-8">
          <div
            className="w-9 h-9 sm:w-10 sm:h-10 rounded-glass-sm flex items-center justify-center flex-shrink-0"
            style={{ background: 'var(--hover-glow)', border: '1px solid var(--focus-ring)' }}
          >
            <Youtube className="w-4 h-4 sm:w-5 sm:h-5" style={{ color: 'var(--accent-primary)' }} />
          </div>
          <h1 className="text-lg sm:text-xl font-semibold text-text_primary tracking-tight">YouTube Videos</h1>
        </div>

        <div className="card flex flex-col items-center py-12 sm:py-16">
          <div
            className="w-14 h-14 sm:w-16 sm:h-16 rounded-full flex items-center justify-center mb-4 sm:mb-5"
            style={{
              background: 'linear-gradient(135deg, var(--hover-glow), var(--active-glow))',
              border: '1px solid var(--focus-ring)',
            }}
          >
            <Play className="w-6 h-6 sm:w-7 sm:h-7 z-content relative" style={{ color: 'var(--accent-secondary)' }} />
          </div>
          <h2 className="text-base sm:text-lg font-semibold text-text_primary mb-2 z-content relative">No videos indexed yet</h2>
          <p className="text-xs sm:text-sm text-text_muted text-center max-w-sm mb-6 leading-relaxed z-content relative">
            Add YouTube video URLs to index their transcripts. You can then ask questions about video content in your chat sessions.
          </p>
          <button
            className="btn-primary-liquid z-content relative"
            style={{ minHeight: '42px', padding: '0 20px' }}
            aria-label="Add YouTube video"
          >
            <Plus className="w-4 h-4 z-content relative" />
            <span className="z-content relative">Add YouTube Video</span>
          </button>
        </div>
      </div>
    </div>
  );
};

export default YouTubePage;
