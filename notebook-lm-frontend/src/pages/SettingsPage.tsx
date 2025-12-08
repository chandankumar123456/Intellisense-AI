import React from 'react';
import { Settings as SettingsIcon } from 'lucide-react';

const SettingsPage: React.FC = () => {
  return (
    <div className="p-8">
      <div className="max-w-4xl mx-auto">
        <div className="flex items-center gap-3 mb-6">
          <SettingsIcon className="w-6 h-6 text-primary" />
          <h1 className="text-3xl font-bold text-text_primary">Settings</h1>
        </div>

        <div className="card">
          <p className="text-text_secondary text-center py-12">
            User preferences and settings will be available here.
          </p>
        </div>
      </div>
    </div>
  );
};

export default SettingsPage;
