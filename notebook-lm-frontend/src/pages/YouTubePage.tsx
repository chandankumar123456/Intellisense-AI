import React from 'react';
import { Youtube } from 'lucide-react';

const YouTubePage: React.FC = () => {
  return (
    <div className="p-8">
      <div className="max-w-4xl mx-auto">
        <div className="flex items-center gap-3 mb-6">
          <Youtube className="w-6 h-6 text-primary" />
          <h1 className="text-3xl font-bold text-text_primary">YouTube Videos</h1>
        </div>

        <div className="card">
          <p className="text-text_secondary text-center py-12">
            Index YouTube videos here. Add video URLs to search their content during chat queries.
          </p>
        </div>
      </div>
    </div>
  );
};

export default YouTubePage;
