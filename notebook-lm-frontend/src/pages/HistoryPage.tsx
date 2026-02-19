import React, { useState, useMemo } from 'react';
import { Clock, Trash2, MessageSquare, Search } from 'lucide-react';
import { useChat } from '../contexts/ChatContext';
import { Storage } from '../utils/storage';
import ChatMessage from '../components/chat/ChatMessage';
import { Message } from '../types/chat.types';

interface Conversation {
  id: string;
  title: string;
  messages: Message[];
  createdAt: Date;
  updatedAt: Date;
}

const HistoryPage: React.FC = () => {
  const { messages, clearHistory } = useChat();
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [selectedConversation, setSelectedConversation] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');

  React.useEffect(() => {
    const saved = Storage.getConversationHistory();
    if (saved) {
      setConversations(saved);
    } else if (messages.length > 0) {
      const conversation: Conversation = {
        id: `conv-${Date.now()}`,
        title: messages[0]?.content.substring(0, 50) || 'New Conversation',
        messages,
        createdAt: new Date(),
        updatedAt: new Date(),
      };
      setConversations([conversation]);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const filteredConversations = useMemo(() => {
    if (!searchQuery.trim()) return conversations;
    return conversations.filter((conv) =>
      conv.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      conv.messages.some((msg) =>
        msg.content.toLowerCase().includes(searchQuery.toLowerCase())
      )
    );
  }, [conversations, searchQuery]);

  const handleDeleteConversation = (id: string) => {
    const updated = conversations.filter((conv) => conv.id !== id);
    setConversations(updated);
    Storage.setConversationHistory(updated);
    if (selectedConversation === id) setSelectedConversation(null);
  };

  const handleClearAll = () => {
    if (window.confirm('Are you sure you want to clear all conversation history?')) {
      setConversations([]);
      setSelectedConversation(null);
      Storage.removeConversationHistory();
      clearHistory();
    }
  };

  const selectedMessages = useMemo(() => {
    if (!selectedConversation) return null;
    return conversations.find((conv) => conv.id === selectedConversation)?.messages || null;
  }, [selectedConversation, conversations]);

  return (
    <div className="p-4 sm:p-6 lg:p-8 h-full flex flex-col" style={{ background: 'var(--bg-primary)' }}>
      <div className="max-w-7xl mx-auto w-full flex-1 flex flex-col lg:flex-row gap-4 sm:gap-6 min-h-0">
        {/* Conversations List */}
        <div className="w-full lg:w-80 lg:flex-shrink-0 flex flex-col min-h-0">
          <div className="flex items-center justify-between mb-4 sm:mb-6">
            <div className="flex items-center gap-2.5">
              <div
                className="w-9 h-9 sm:w-10 sm:h-10 rounded-glass-sm flex items-center justify-center flex-shrink-0"
                style={{ background: 'var(--hover-glow)', border: '1px solid var(--focus-ring)' }}
              >
                <Clock className="w-4 h-4 sm:w-5 sm:h-5" style={{ color: 'var(--accent-primary)' }} />
              </div>
              <h1 className="text-lg sm:text-xl font-semibold text-text_primary tracking-tight">History</h1>
            </div>
            {conversations.length > 0 && (
              <button
                onClick={handleClearAll}
                className="btn-liquid flex-shrink-0"
                style={{
                  minHeight: '36px', padding: '6px 14px', fontSize: '12px',
                  background: 'rgba(239,68,68,0.06)', borderColor: 'rgba(239,68,68,0.12)',
                  color: '#EF4444',
                }}
                aria-label="Clear all history"
              >
                <Trash2 className="w-3.5 h-3.5 z-content relative" />
                <span className="z-content relative hidden sm:inline">Clear</span>
              </button>
            )}
          </div>

          {/* Search */}
          <div className="mb-3 sm:mb-4 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4" style={{ color: 'var(--text-muted)' }} />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search conversations..."
              className="input-field pl-10"
              style={{ minHeight: '42px', fontSize: '13px' }}
            />
          </div>

          {/* Conversations */}
          <div className="flex-1 overflow-y-auto space-y-2 min-h-0">
            {filteredConversations.length === 0 ? (
              <div className="text-center py-8">
                <MessageSquare className="w-10 h-10 mx-auto mb-3" style={{ color: 'var(--text-muted)', opacity: 0.5 }} />
                <p className="text-sm text-text_secondary">No conversations found</p>
                {searchQuery && <p className="text-xs text-text_muted mt-1.5">Try a different search term</p>}
              </div>
            ) : (
              filteredConversations.map((conversation) => {
                const isSelected = selectedConversation === conversation.id;
                return (
                  <div
                    key={conversation.id}
                    className="rounded-glass-sm cursor-pointer group transition-all duration-fast"
                    onClick={() => setSelectedConversation(conversation.id)}
                    style={{
                      padding: '12px 14px',
                      minHeight: '48px',
                      background: isSelected ? 'var(--hover-glow)' : 'var(--glass-surface)',
                      border: `1px solid ${isSelected ? 'var(--focus-ring)' : 'var(--border-subtle)'}`,
                      boxShadow: isSelected ? '0 2px 12px var(--hover-glow)' : 'none',
                    }}
                    onMouseEnter={(e) => { if (!isSelected) e.currentTarget.style.background = 'var(--glass-elevated)'; }}
                    onMouseLeave={(e) => { if (!isSelected) e.currentTarget.style.background = 'var(--glass-surface)'; }}
                    role="listitem"
                  >
                    <div className="flex items-start justify-between gap-2 mb-1">
                      <h3 className="font-medium text-sm text-text_primary line-clamp-2 leading-snug">{conversation.title}</h3>
                      <button
                        onClick={(e) => { e.stopPropagation(); handleDeleteConversation(conversation.id); }}
                        className="flex items-center justify-center rounded-glass-sm transition-all duration-fast flex-shrink-0 opacity-0 group-hover:opacity-100 active:scale-[0.9]"
                        style={{ width: '28px', height: '28px', background: 'transparent', color: 'var(--text-muted)' }}
                        onMouseEnter={(e) => { e.currentTarget.style.background = 'rgba(239,68,68,0.08)'; e.currentTarget.style.color = '#EF4444'; }}
                        onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'var(--text-muted)'; }}
                        aria-label="Delete conversation"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                    <div className="flex items-center gap-3">
                      <p className="text-[11px] text-text_muted">{conversation.messages.length} messages</p>
                      <p className="text-[11px] text-text_muted">{new Date(conversation.updatedAt).toLocaleDateString()}</p>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Messages View */}
        <div className="flex-1 flex flex-col min-h-0">
          {selectedMessages ? (
            <>
              <div
                className="mb-3 sm:mb-4 pb-3 sm:pb-4 flex-shrink-0"
                style={{ borderBottom: '1px solid var(--border-subtle)' }}
              >
                <h2 className="text-base sm:text-lg font-semibold text-text_primary">
                  {conversations.find((c) => c.id === selectedConversation)?.title}
                </h2>
              </div>
              <div className="flex-1 overflow-y-auto space-y-4">
                {selectedMessages.map((message) => (
                  <div key={message.id}><ChatMessage message={message} /></div>
                ))}
              </div>
            </>
          ) : (
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center px-4">
                <MessageSquare className="w-12 h-12 sm:w-14 sm:h-14 mx-auto mb-3 sm:mb-4" style={{ color: 'var(--text-muted)', opacity: 0.3 }} />
                <h2 className="text-base sm:text-lg font-semibold text-text_primary mb-1.5">Select a conversation</h2>
                <p className="text-xs sm:text-sm text-text_muted">Choose a conversation from the list to view its messages</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default HistoryPage;