import React from 'react';
import { Globe } from 'lucide-react';

const WebSourcesPage: React.FC = () => {
  return (
    <div className="p-8">
      <div className="max-w-4xl mx-auto">
        <div className="flex items-center gap-3 mb-6">
          <Globe className="w-6 h-6 text-primary" />
          <h1 className="text-3xl font-bold text-text_primary">Web Sources</h1>
        </div>

        <div className="card">
          <p className="text-text_secondary text-center py-12">
            Manage your web sources here. Add URLs to search during chat queries.
          </p>
        </div>
      </div>
    </div>
  );
};

export default WebSourcesPage;
