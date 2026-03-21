import React from 'react';
import { FolderOpen, Globe, Youtube, Settings, X } from 'lucide-react';
import MyFilesTab from './tabs/MyFilesTab';
import WebTab from './tabs/WebTab';
import YouTubeTab from './tabs/YouTubeTab';
import PreferencesTab from './tabs/PreferencesTab';

interface SourceTabBarProps {
  activeTab: string;
  isPanelOpen: boolean;
  onTogglePanel: (tabId: string) => void;
}

const tabs = [
  { id: 'files', icon: FolderOpen, label: 'Files' },
  { id: 'web', icon: Globe, label: 'Web' },
  { id: 'youtube', icon: Youtube, label: 'YouTube' },
  { id: 'preferences', icon: Settings, label: 'Prefs' },
];

export const SourceTabBar: React.FC<SourceTabBarProps> = ({ activeTab, isPanelOpen, onTogglePanel }) => (
  <div className="flex items-center gap-0.5" role="tablist" aria-label="Source tabs">
    {tabs.map(({ id, icon: Icon, label }) => {
      const isActive = isPanelOpen && activeTab === id;
      return (
        <button
          key={id}
          onClick={() => onTogglePanel(id)}
          className={`flex items-center gap-1.5 text-xs font-medium
            transition-all duration-fast active:scale-[0.96] flex-shrink-0 whitespace-nowrap
            rounded-glass-sm
            ${isActive ? 'text-text_primary' : 'text-text_muted hover:text-text_secondary'}`}
          style={{
            padding: '6px 10px',
            minHeight: '32px',
            background: isActive ? 'var(--glass-elevated)' : 'transparent',
            border: isActive ? '1px solid var(--border-subtle)' : '1px solid transparent',
          }}
          onMouseEnter={(e) => { if (!isActive) e.currentTarget.style.background = 'var(--hover-glow)'; }}
          onMouseLeave={(e) => { if (!isActive) e.currentTarget.style.background = 'transparent'; }}
          role="tab"
          aria-selected={isActive}
          aria-label={`Open ${label} panel`}
        >
          <Icon className="w-3.5 h-3.5 flex-shrink-0" />
          <span className="hidden sm:inline">{label}</span>
        </button>
      );
    })}
  </div>
);

interface SourcePanelProps {
  activeTab: string;
  isOpen: boolean;
  onClose: () => void;
}

export const SourcePanel: React.FC<SourcePanelProps> = ({ activeTab, isOpen, onClose }) => {
  if (!isOpen) return null;

  const panelContent: Record<string, React.ReactNode> = {
    files: <MyFilesTab />,
    web: <WebTab />,
    youtube: <YouTubeTab />,
    preferences: <PreferencesTab />,
  };

  return (
    <>
      <div
        className="lg:hidden fixed inset-0 z-40 animate-fade-in"
        style={{ background: 'rgba(0,0,0,0.2)' }}
        onClick={onClose}
        aria-hidden="true"
      />
      <div
        className="fixed right-0 top-0 h-full z-50 overflow-y-auto animate-slide-in-right"
        style={{
          width: 'min(360px, 82vw)',
          padding: '16px',
          background: 'var(--bg-secondary)',
          borderLeft: '1px solid var(--border-subtle)',
          boxShadow: '-4px 0 16px var(--glass-shadow)',
        }}
        role="tabpanel"
        aria-label={`${activeTab} panel`}
      >
        {/* Panel header — clearly secondary */}
        <div className="flex items-center justify-between mb-5">
          <div>
            <span className="label-sm block">{activeTab}</span>
            <span className="text-xs text-text_muted mt-0.5 block">Source configuration</span>
          </div>
          <button
            onClick={onClose}
            className="flex items-center justify-center rounded-glass-sm transition-all duration-fast active:scale-[0.92]"
            style={{
              width: '32px', height: '32px',
              background: 'transparent',
              color: 'var(--text-muted)',
              border: '1px solid transparent',
            }}
            onMouseEnter={(e) => { e.currentTarget.style.background = 'var(--glass-elevated)'; e.currentTarget.style.borderColor = 'var(--border-subtle)'; }}
            onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.borderColor = 'transparent'; }}
            aria-label="Close panel"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
        <div>{panelContent[activeTab]}</div>
      </div>
    </>
  );
};
