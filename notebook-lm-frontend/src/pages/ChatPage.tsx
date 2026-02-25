import React, { useState, useRef, useEffect, useCallback } from 'react';
import { useChat } from '../contexts/ChatContext';
import ChatInput from '../components/chat/ChatInput';
import ChatMessage from '../components/chat/ChatMessage';
import { SourceTabBar, SourcePanel } from '../components/chat/SourceTabs';
import { MessageSquare, Sparkles, ArrowDown } from 'lucide-react';

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
  const [showScrollBtn, setShowScrollBtn] = useState(false);

  const scrollToBottom = useCallback(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    const handleScroll = () => {
      const distanceFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
      setShowScrollBtn(distanceFromBottom > 150);
    };
    el.addEventListener('scroll', handleScroll, { passive: true });
    return () => el.removeEventListener('scroll', handleScroll);
  }, []);

  const handleTogglePanel = (tab: string) => {
    if (isPanelOpen && activeTab === tab) { setIsPanelOpen(false); return; }
    setActiveTab(tab); setIsPanelOpen(true);
  };

  return (
    <div className="flex h-full overflow-hidden">
      <div className={`flex-1 flex flex-col min-w-0 transition-all duration-normal ${isPanelOpen ? 'lg:mr-panel' : ''}`}>
        {/* Toolbar — liquid glass, responsive padding */}
        <div
          className="px-3 sm:px-5 flex items-center justify-between liquid-glass-header flex-shrink-0"
          style={{ minHeight: '48px' }}
        >
          <div className="flex items-center gap-2 flex-shrink-0">
            <MessageSquare className="w-4 h-4 text-primary" />
            <span className="text-sm font-medium text-text_secondary z-content">Chat</span>
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
        <div className="flex-1 overflow-hidden relative">
          <div ref={scrollRef} className="h-full overflow-y-auto p-3 sm:p-5 scroll-smooth">
            <div className="max-w-3xl mx-auto space-y-4 sm:space-y-5">
              {messages.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full min-h-[300px] sm:min-h-[400px] gap-5 sm:gap-6 px-2">
                {/* Liquid glass orb */}
                <div
                  className="w-16 h-16 sm:w-20 sm:h-20 rounded-full flex items-center justify-center animate-float liquid-glass"
                  style={{
                    background: 'linear-gradient(135deg, var(--hover-glow), var(--active-glow))',
                    boxShadow: '0 12px 48px var(--hover-glow)',
                  }}
                >
                  <Sparkles className="w-6 h-6 sm:w-8 sm:h-8 text-primary z-content" />
                </div>
                <div className="text-center">
                  <h2 className="text-lg sm:text-xl font-semibold text-text_primary mb-2">Start a conversation</h2>
                  <p className="text-xs sm:text-sm text-text_muted max-w-md leading-relaxed">
                    Ask questions about your documents, or explore topics with AI-powered retrieval.
                  </p>
                </div>

                {/* Suggestion chips — liquid glass cards */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 w-full max-w-lg mt-2">
                  {suggestions.map((s) => (
                    <button
                      key={s}
                      onClick={() => sendMessage(s)}
                      className="text-left card group relative z-content"
                      style={{ minHeight: '48px' }}
                    >
                      <span className="text-sm text-text_secondary group-hover:text-text_primary transition-colors duration-fast z-content relative">{s}</span>
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
              <div className="flex gap-1.5 items-center pl-2 py-2">
                <div className="w-2.5 h-2.5 rounded-full bg-primary animate-liquid-dot-1" />
                <div className="w-2.5 h-2.5 rounded-full bg-secondary animate-liquid-dot-2" />
                <div className="w-2.5 h-2.5 rounded-full bg-primary animate-liquid-dot-3" />
              </div>
            )}
          </div>
          </div>

          {/* Scroll to bottom button */}
          {showScrollBtn && messages.length > 0 && (
            <button
              onClick={scrollToBottom}
              className="absolute bottom-4 left-1/2 -translate-x-1/2 liquid-glass rounded-full transition-all duration-fast hover:scale-105 active:scale-95 flex items-center gap-1.5 px-3 py-2 z-10"
              style={{
                boxShadow: '0 4px 20px var(--glass-shadow-lg)',
                color: 'var(--text-secondary)',
              }}
              aria-label="Scroll to bottom"
            >
              <ArrowDown className="w-4 h-4" />
              <span className="text-xs font-medium z-content relative">Back to bottom</span>
            </button>
          )}
        </div>

        {/* Input — responsive bottom padding */}
        <div className="px-3 sm:px-5 pb-3 sm:pb-5 pb-safe flex-shrink-0">
          <div className="max-w-3xl mx-auto">
            <ChatInput onSendMessage={sendMessage} isLoading={isLoading} />
          </div>
        </div>
      </div>

      <SourcePanel activeTab={activeTab} isOpen={isPanelOpen} onClose={() => setIsPanelOpen(false)} />
    </div>
  );
};

export default ChatPage;
