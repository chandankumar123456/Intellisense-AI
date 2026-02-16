import React, { useState } from 'react';
import { Globe, Plus, Trash2 } from 'lucide-react';
import Button from '../../common/Button';
import Input from '../../common/Input';
import { useChat } from '../../../contexts/ChatContext';

const WebTab: React.FC = () => {
  const { webSources, addWebSource, removeWebSource } = useChat();
  const [url, setUrl] = useState('');

  const handleAdd = () => {
    if (url.trim()) {
      addWebSource(url.trim());
      setUrl('');
    }
  };

  const handleRemove = (source: string) => {
    removeWebSource(source);
  };

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold text-text_primary">Web Sources</h3>

      <div className="flex gap-2">
        <Input
          type="url"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="https://example.com"
          className="flex-1"
        />
        <Button variant="primary" onClick={handleAdd}>
          <Plus className="w-4 h-4 mr-2" />
          Add
        </Button>
      </div>

      {webSources.length === 0 ? (
        <div className="text-center py-8 text-text_secondary">
          <Globe className="w-12 h-12 mx-auto mb-4 text-text_secondary/50" />
          <p>No web sources added</p>
          <p className="text-sm mt-2">Add URLs to search during queries</p>
        </div>
      ) : (
        <div className="space-y-2">
          {webSources.map((source, index) => (
            <div
              key={index}
              className="flex items-center justify-between p-3 bg-surface rounded-lg border border-border"
            >
              <a
                href={source}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm text-primary hover:text-primary_dark flex-1 truncate"
              >
                {source}
              </a>
              <button
                onClick={() => handleRemove(source)}
                className="ml-2 p-1 text-error hover:bg-error/10 rounded"
                aria-label="Remove source"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default WebTab;
