import React from 'react';
import { Youtube } from 'lucide-react';

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

        <div className="card">
          <p className="text-sm text-text_muted text-center py-10 sm:py-12 z-content relative">
            Index YouTube videos here. Add video URLs to search their content during chat queries.
          </p>
        </div>
      </div>
    </div>
  );
};

export default YouTubePage;
