import React from 'react';
import { Settings as SettingsIcon, Palette, Bell, Shield } from 'lucide-react';

const SettingsPage: React.FC = () => {
  return (
    <div className="p-4 sm:p-6 lg:p-8 overflow-y-auto h-full" style={{ background: 'var(--bg-primary)' }}>
      <div className="max-w-4xl mx-auto">
        <div className="flex items-center gap-2.5 mb-6 sm:mb-8">
          <div
            className="w-9 h-9 sm:w-10 sm:h-10 rounded-glass-sm flex items-center justify-center flex-shrink-0"
            style={{ background: 'var(--hover-glow)', border: '1px solid var(--focus-ring)' }}
          >
            <SettingsIcon className="w-4 h-4 sm:w-5 sm:h-5" style={{ color: 'var(--accent-primary)' }} />
          </div>
          <h1 className="text-lg sm:text-xl font-semibold text-text_primary tracking-tight">Settings</h1>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 sm:gap-4 mb-6">
          {[
            { icon: Palette, title: 'Appearance', desc: 'Theme, fonts, and display options' },
            { icon: Bell, title: 'Notifications', desc: 'Alerts and notification preferences' },
            { icon: Shield, title: 'Privacy', desc: 'Data and privacy controls' },
          ].map(({ icon: Icon, title, desc }) => (
            <div key={title} className="card group cursor-default" style={{ opacity: 0.6 }}>
              <div
                className="w-10 h-10 rounded-glass-sm flex items-center justify-center mb-3 z-content relative"
                style={{ background: 'var(--hover-glow)', border: '1px solid var(--focus-ring)' }}
              >
                <Icon className="w-5 h-5" style={{ color: 'var(--accent-primary)' }} />
              </div>
              <h3 className="text-sm font-semibold text-text_primary mb-1 z-content relative">{title}</h3>
              <p className="text-xs text-text_secondary z-content relative">{desc}</p>
              <span
                className="inline-block mt-3 text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-pill z-content relative"
                style={{ background: 'var(--hover-glow)', color: 'var(--accent-primary)' }}
              >
                Coming Soon
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default SettingsPage;
