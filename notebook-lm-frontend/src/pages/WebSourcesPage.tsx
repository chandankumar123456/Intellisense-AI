import React from 'react';
import { Globe, Plus } from 'lucide-react';

const WebSourcesPage: React.FC = () => {
  return (
    <div className="p-4 sm:p-6 lg:p-8 overflow-y-auto h-full" style={{ background: 'var(--bg-primary)' }}>
      <div className="max-w-4xl mx-auto">
        <div className="flex items-center gap-2.5 mb-6 sm:mb-8">
          <div
            className="w-9 h-9 sm:w-10 sm:h-10 rounded-glass-sm flex items-center justify-center flex-shrink-0"
            style={{ background: 'var(--hover-glow)', border: '1px solid var(--focus-ring)' }}
          >
            <Globe className="w-4 h-4 sm:w-5 sm:h-5" style={{ color: 'var(--accent-primary)' }} />
          </div>
          <h1 className="text-lg sm:text-xl font-semibold text-text_primary tracking-tight">Web Sources</h1>
        </div>

        <div className="card flex flex-col items-center py-12 sm:py-16">
          <div
            className="w-14 h-14 sm:w-16 sm:h-16 rounded-full flex items-center justify-center mb-4 sm:mb-5"
            style={{
              background: 'linear-gradient(135deg, var(--hover-glow), var(--active-glow))',
              border: '1px solid var(--focus-ring)',
            }}
          >
            <Globe className="w-6 h-6 sm:w-7 sm:h-7 z-content relative" style={{ color: 'var(--accent-primary)' }} />
          </div>
          <h2 className="text-base sm:text-lg font-semibold text-text_primary mb-2 z-content relative">No web sources yet</h2>
          <p className="text-xs sm:text-sm text-text_muted text-center max-w-sm mb-6 leading-relaxed z-content relative">
            Add URLs to index web content. These sources will be searchable during your chat queries for richer, more accurate answers.
          </p>
          <div className="flex flex-col sm:flex-row gap-3 z-content relative">
            <button
              className="btn-primary-liquid"
              style={{ minHeight: '42px', padding: '0 20px' }}
              aria-label="Add web source"
            >
              <Plus className="w-4 h-4 z-content relative" />
              <span className="z-content relative">Add Web Source</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default WebSourcesPage;
