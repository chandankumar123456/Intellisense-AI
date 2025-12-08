import React from 'react';
import { useChat } from '../../../contexts/ChatContext';
import Input from '../../common/Input';

const PreferencesTab: React.FC = () => {
  const { preferences, updatePreferences } = useChat();

  return (
    <div className="space-y-6">
      <h3 className="text-lg font-semibold text-text_primary">Chat Preferences</h3>

      <div>
        <label className="block text-sm font-medium text-text_primary mb-2">
          Response Style
        </label>
        <select
          value={preferences.response_style}
          onChange={(e) =>
            updatePreferences({
              response_style: e.target.value as 'concise' | 'detailed' | 'simple' | 'exam',
            })
          }
          className="input-field"
        >
          <option value="concise">Concise</option>
          <option value="detailed">Detailed</option>
          <option value="simple">Simple</option>
          <option value="exam">Exam</option>
        </select>
      </div>

      <div>
        <label className="block text-sm font-medium text-text_primary mb-2">
          Max Length: {preferences.max_length}
        </label>
        <input
          type="range"
          min="100"
          max="1000"
          step="50"
          value={preferences.max_length}
          onChange={(e) =>
            updatePreferences({ max_length: parseInt(e.target.value) })
          }
          className="w-full"
        />
        <div className="flex justify-between text-xs text-text_secondary mt-1">
          <span>100</span>
          <span>1000</span>
        </div>
      </div>

      <div>
        <Input
          label="Domain"
          type="text"
          value={preferences.domain}
          onChange={(e) => updatePreferences({ domain: e.target.value })}
          placeholder="e.g., artificial intelligence"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-text_primary mb-2">
          Model
        </label>
        <select
          value={preferences.model_name || 'llama-3.1-8b-instant'}
          onChange={(e) => updatePreferences({ model_name: e.target.value })}
          className="input-field"
        >
          <option value="llama-3.1-8b-instant">llama-3.1-8b-instant</option>
        </select>
      </div>

      <div className="flex items-center gap-3">
        <input
          type="checkbox"
          id="allow-agentic"
          checked={preferences.allow_agentic}
          onChange={(e) => updatePreferences({ allow_agentic: e.target.checked })}
          className="w-4 h-4 text-primary border-border rounded focus:ring-primary"
        />
        <label htmlFor="allow-agentic" className="text-sm text-text_primary">
          Allow Agentic Mode
        </label>
      </div>
    </div>
  );
};

export default PreferencesTab;
