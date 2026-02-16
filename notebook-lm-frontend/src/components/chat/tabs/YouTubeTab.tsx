import React, { useState } from 'react';
import { Youtube, Plus, Trash2 } from 'lucide-react';
import Button from '../../common/Button';
import Input from '../../common/Input';
import { useChat } from '../../../contexts/ChatContext';

const YouTubeTab: React.FC = () => {
  const { youtubeSources, addYouTubeSource, removeYouTubeSource } = useChat();
  const [url, setUrl] = useState('');

  const handleAdd = () => {
    if (url.trim()) {
      addYouTubeSource(url.trim());
      setUrl('');
    }
  };

  const handleRemove = (video: string) => {
    removeYouTubeSource(video);
  };

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold text-text_primary">YouTube Videos</h3>

      <div className="flex gap-2">
        <Input
          type="url"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="https://www.youtube.com/watch?v=..."
          className="flex-1"
        />
        <Button variant="primary" onClick={handleAdd}>
          <Plus className="w-4 h-4 mr-2" />
          Add
        </Button>
      </div>

      {youtubeSources.length === 0 ? (
        <div className="text-center py-8 text-text_secondary">
          <Youtube className="w-12 h-12 mx-auto mb-4 text-text_secondary/50" />
          <p>No YouTube videos added</p>
          <p className="text-sm mt-2">Add video URLs to index and search their content</p>
        </div>
      ) : (
        <div className="space-y-2">
          {youtubeSources.map((video, index) => (
            <div
              key={index}
              className="flex items-center justify-between p-3 bg-surface rounded-lg border border-border"
            >
              <a
                href={video}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm text-primary hover:text-primary_dark flex-1 truncate"
              >
                {video}
              </a>
              <button
                onClick={() => handleRemove(video)}
                className="ml-2 p-1 text-error hover:bg-error/10 rounded"
                aria-label="Remove video"
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

export default YouTubeTab;
