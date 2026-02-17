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
  <div className="flex items-center gap-1" role="tablist" aria-label="Source tabs">
    {tabs.map(({ id, icon: Icon, label }) => {
      const isActive = isPanelOpen && activeTab === id;
      return (
        <button
          key={id}
          onClick={() => onTogglePanel(id)}
          className={`flex items-center gap-1.5 rounded-glass-sm text-xs font-medium
            transition-all duration-fast active:scale-[0.96] flex-shrink-0 whitespace-nowrap
            ${isActive ? 'text-primary' : 'text-text_muted hover:text-text_secondary'}`}
          style={{
            padding: '8px 12px',
            minHeight: '36px',
            ...(isActive ? {
              background: 'var(--hover-glow)',
              border: '1px solid var(--focus-ring)',
              boxShadow: '0 0 12px var(--hover-glow)',
            } : {
              background: 'transparent',
              border: '1px solid transparent',
            }),
          }}
          onMouseEnter={(e) => { if (!isActive) e.currentTarget.style.background = 'var(--hover-glow)'; }}
          onMouseLeave={(e) => { if (!isActive) e.currentTarget.style.background = isActive ? 'var(--hover-glow)' : 'transparent'; }}
          role="tab"
          aria-selected={isActive}
          aria-label={`Open ${label} panel`}
        >
          <Icon className="w-4 h-4 flex-shrink-0" />
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
        style={{ background: 'rgba(0,0,0,0.12)', backdropFilter: 'blur(3px)' }}
        onClick={onClose}
        aria-hidden="true"
      />
      <div
        className="fixed right-0 top-0 h-full z-50 overflow-y-auto animate-slide-in-right liquid-glass-elevated"
        style={{
          width: 'min(380px, 85vw)',
          padding: '16px',
          borderLeft: '1px solid var(--border-subtle)',
          boxShadow: '-8px 0 40px var(--glass-shadow-lg)',
        }}
        role="tabpanel"
        aria-label={`${activeTab} panel`}
      >
        <div className="flex items-center justify-between mb-4 z-content relative">
          <h3 className="text-sm font-semibold text-text_secondary capitalize">{activeTab}</h3>
          <button
            onClick={onClose}
            className="flex items-center justify-center rounded-glass-sm transition-all duration-fast active:scale-[0.92] flex-shrink-0"
            style={{
              width: '36px', height: '36px',
              background: 'transparent',
              color: 'var(--text-muted)',
            }}
            onMouseEnter={(e) => { e.currentTarget.style.background = 'var(--hover-glow)'; }}
            onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; }}
            aria-label="Close panel"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        <div className="z-content relative">{panelContent[activeTab]}</div>
      </div>
    </>
  );
};
