import React from 'react';
import { FileText, Globe, Youtube, Sliders } from 'lucide-react';
import { SourceTab } from '../../types/chat.types';
import MyFilesTab from './tabs/MyFilesTab';
import WebTab from './tabs/WebTab';
import YouTubeTab from './tabs/YouTubeTab';
import PreferencesTab from './tabs/PreferencesTab';

interface SourceTabsProps {
  activeTab: SourceTab['id'];
  onTabChange: (tab: SourceTab['id']) => void;
}

const tabs: SourceTab[] = [
  { id: 'myfiles', label: 'My files', icon: 'FileText', component: 'MyFilesTab' },
  { id: 'web', label: 'Web', icon: 'Globe', component: 'WebTab' },
  { id: 'youtube', label: 'YouTube', icon: 'Youtube', component: 'YouTubeTab' },
  { id: 'preferences', label: 'Preferences', icon: 'Sliders', component: 'PreferencesTab' },
];

const iconMap = {
  FileText,
  Globe,
  Youtube,
  Sliders,
};

const SourceTabs: React.FC<SourceTabsProps> = ({ activeTab, onTabChange }) => {
  const renderTabContent = () => {
    switch (activeTab) {
      case 'myfiles':
        return <MyFilesTab />;
      case 'web':
        return <WebTab />;
      case 'youtube':
        return <YouTubeTab />;
      case 'preferences':
        return <PreferencesTab />;
      default:
        return null;
    }
  };

  return (
    <div className="border-b border-border bg-white">
      <div className="flex overflow-x-auto">
        {tabs.map((tab) => {
          const Icon = iconMap[tab.icon as keyof typeof iconMap];
          const isActive = activeTab === tab.id;

          return (
            <button
              key={tab.id}
              onClick={() => onTabChange(tab.id)}
              className={`flex items-center gap-2 px-6 py-3 border-b-2 transition-colors ${
                isActive
                  ? 'border-primary text-primary font-medium'
                  : 'border-transparent text-text_secondary hover:text-text_primary hover:border-border'
              }`}
              aria-selected={isActive}
              role="tab"
            >
              {Icon && <Icon className="w-5 h-5" />}
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>
      <div className="p-4" role="tabpanel">
        {renderTabContent()}
      </div>
    </div>
  );
};

export default SourceTabs;
