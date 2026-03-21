import React, { useState, useRef, useEffect } from 'react';
import { useChat } from '../contexts/ChatContext';
import ChatInput from '../components/chat/ChatInput';
import ChatMessage from '../components/chat/ChatMessage';
import { SourceTabBar, SourcePanel } from '../components/chat/SourceTabs';
import { MessageSquare } from 'lucide-react';

const suggestions = [
  'Summarize my uploaded documents',
  'What are the key findings?',
  'Explain the methodology used',
  'Compare the main arguments',
];

const ChatPage: React.FC = () => {
  const { messages, sendMessage, isLoading } = useChat();
  const scrollRef = useRef<HTMLDivElement>(null);
  const [activeTab, setActiveTab] = useState('files');
  const [isPanelOpen, setIsPanelOpen] = useState(false);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' });
  }, [messages]);

  const handleTogglePanel = (tab: string) => {
    if (isPanelOpen && activeTab === tab) { setIsPanelOpen(false); return; }
    setActiveTab(tab); setIsPanelOpen(true);
  };

  return (
    <div className="flex h-full overflow-hidden">
      <div className={`flex-1 flex flex-col min-w-0 transition-all duration-normal ${isPanelOpen ? 'lg:mr-panel' : ''}`}>
        {/* Toolbar */}
        <div
          className="px-3 sm:px-4 flex items-center justify-between flex-shrink-0"
          style={{
            height: '44px',
            background: 'var(--glass-surface)',
            borderBottom: '1px solid var(--border-subtle)',
          }}
        >
          <div className="flex items-center gap-2 flex-shrink-0">
            <MessageSquare className="w-3.5 h-3.5 text-text_muted" />
            <span className="text-xs font-medium text-text_secondary">Chat</span>
          </div>
          <div className="overflow-x-auto">
            <SourceTabBar
              activeTab={activeTab}
              isPanelOpen={isPanelOpen}
              onTogglePanel={handleTogglePanel}
            />
          </div>
        </div>

        {/* Messages */}
        <div ref={scrollRef} className="flex-1 overflow-y-auto scroll-smooth" style={{ background: 'var(--bg-primary)' }}>
          <div className="max-w-2xl mx-auto px-4 py-5 space-y-3">
            {messages.length === 0 ? (
              <div className="flex flex-col items-center justify-center min-h-[340px] gap-6 px-2">
                <div className="text-center">
                  <div
                    className="w-10 h-10 rounded-glass-sm flex items-center justify-center mx-auto mb-4"
                    style={{ background: 'var(--glass-elevated)', border: '1px solid var(--border-subtle)' }}
                  >
                    <MessageSquare className="w-4 h-4 text-text_muted" />
                  </div>
                  <h2 className="heading-md mb-1">Start a conversation</h2>
                  <p className="text-xs text-text_muted max-w-xs leading-relaxed mx-auto">
                    Ask questions about your documents, or explore topics with AI-powered retrieval.
                  </p>
                </div>

                {/* Suggestion chips */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 w-full max-w-md">
                  {suggestions.map((s) => (
                    <button
                      key={s}
                      onClick={() => sendMessage(s)}
                      className="text-left card-compact group hover:border-accent_primary transition-colors duration-fast"
                      style={{ minHeight: '44px' }}
                    >
                      <span className="text-xs text-text_secondary group-hover:text-text_primary transition-colors duration-fast">{s}</span>
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              messages.map((msg, i) => (
                <ChatMessage key={msg.id || i} message={msg} />
              ))
            )}

            {isLoading && (
              <div className="flex gap-1 items-center pl-1 py-2">
                <div className="w-2 h-2 rounded-full bg-text_muted animate-liquid-dot-1" />
                <div className="w-2 h-2 rounded-full bg-text_muted animate-liquid-dot-2" />
                <div className="w-2 h-2 rounded-full bg-text_muted animate-liquid-dot-3" />
              </div>
            )}
          </div>
        </div>

        {/* Input */}
        <div
          className="px-4 py-3 pb-safe flex-shrink-0"
          style={{ background: 'var(--glass-surface)', borderTop: '1px solid var(--border-subtle)' }}
        >
          <div className="max-w-2xl mx-auto">
            <ChatInput onSendMessage={sendMessage} isLoading={isLoading} />
          </div>
        </div>
      </div>

      <SourcePanel activeTab={activeTab} isOpen={isPanelOpen} onClose={() => setIsPanelOpen(false)} />
    </div>
  );
};

export default ChatPage;
