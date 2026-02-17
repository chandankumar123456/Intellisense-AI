import React from 'react';
import { useChat } from '../../../contexts/ChatContext';

const PreferencesTab: React.FC = () => {
  const { preferences, updatePreferences } = useChat();

  return (
    <div className="space-y-5">
      <h3 className="text-sm font-semibold text-text_primary">Chat Preferences</h3>

      {/* Response Style */}
      <div>
        <label className="block text-xs font-medium text-text_secondary mb-1.5">Response Style</label>
        <select
          value={preferences.response_style}
          onChange={(e) =>
            updatePreferences({
              response_style: e.target.value as 'concise' | 'detailed' | 'simple' | 'exam',
            })
          }
          className="input-field"
          style={{ minHeight: '42px', fontSize: '13px' }}
        >
          <option value="concise">Concise</option>
          <option value="detailed">Detailed</option>
          <option value="simple">Simple</option>
          <option value="exam">Exam</option>
        </select>
      </div>

      {/* Max Length Slider */}
      <div>
        <label className="block text-xs font-medium text-text_secondary mb-1.5">
          Max Length: <span className="font-semibold text-text_primary">{preferences.max_length}</span>
        </label>
        <input
          type="range"
          min="100"
          max="1000"
          step="50"
          value={preferences.max_length}
          onChange={(e) => updatePreferences({ max_length: parseInt(e.target.value) })}
          className="w-full"
          style={{ accentColor: 'var(--accent-primary)', height: '6px' }}
        />
        <div className="flex justify-between text-[11px] mt-1" style={{ color: 'var(--text-muted)' }}>
          <span>100</span>
          <span>1000</span>
        </div>
      </div>

      {/* Domain */}
      <div>
        <label className="block text-xs font-medium text-text_secondary mb-1.5">Domain</label>
        <input
          type="text"
          value={preferences.domain}
          onChange={(e) => updatePreferences({ domain: e.target.value })}
          placeholder="e.g., artificial intelligence"
          className="input-field"
          style={{ minHeight: '42px', fontSize: '13px' }}
        />
      </div>

      {/* Model */}
      <div>
        <label className="block text-xs font-medium text-text_secondary mb-1.5">Model</label>
        <select
          value={preferences.model_name || 'llama-3.1-8b-instant'}
          onChange={(e) => updatePreferences({ model_name: e.target.value })}
          className="input-field"
          style={{ minHeight: '42px', fontSize: '13px' }}
        >
          <option value="llama-3.1-8b-instant">llama-3.1-8b-instant</option>
        </select>
      </div>

      {/* Agentic toggle */}
      <label
        htmlFor="allow-agentic"
        className="flex items-center gap-3 cursor-pointer rounded-glass-sm"
        style={{
          padding: '10px 12px',
          minHeight: '42px',
          background: preferences.allow_agentic ? 'var(--hover-glow)' : 'transparent',
          border: `1px solid ${preferences.allow_agentic ? 'var(--focus-ring)' : 'var(--border-subtle)'}`,
          transition: 'all 180ms cubic-bezier(0.22, 1, 0.36, 1)',
        }}
      >
        <input
          type="checkbox"
          id="allow-agentic"
          checked={preferences.allow_agentic}
          onChange={(e) => updatePreferences({ allow_agentic: e.target.checked })}
          style={{ accentColor: 'var(--accent-primary)', width: '18px', height: '18px', flexShrink: 0 }}
        />
        <span className="text-xs font-medium text-text_primary select-none">Allow Agentic Mode</span>
      </label>
    </div>
  );
};

export default PreferencesTab;
