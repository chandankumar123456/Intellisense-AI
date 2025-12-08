import React, { useState, useMemo } from 'react';
import { Clock, Trash2, MessageSquare, Search } from 'lucide-react';
import { useChat } from '../contexts/ChatContext';
import { Storage } from '../utils/storage';
import Button from '../components/common/Button';
import Input from '../components/common/Input';
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

  // Load conversations from storage
  React.useEffect(() => {
    const saved = Storage.getConversationHistory();
    if (saved) {
      setConversations(saved);
    } else if (messages.length > 0) {
      // Create conversation from current messages
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

  // Filter conversations by search query
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
    
    if (selectedConversation === id) {
      setSelectedConversation(null);
    }
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
    <div className="p-8 h-full flex flex-col">
      <div className="max-w-7xl mx-auto w-full flex-1 flex gap-6">
        {/* Conversations List */}
        <div className="w-80 flex-shrink-0 flex flex-col">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-3">
              <Clock className="w-6 h-6 text-primary" />
              <h1 className="text-2xl font-bold text-text_primary">History</h1>
            </div>
            {conversations.length > 0 && (
              <Button
                variant="danger"
                size="sm"
                onClick={handleClearAll}
                aria-label="Clear all history"
              >
                <Trash2 className="w-4 h-4" />
              </Button>
            )}
          </div>

          {/* Search */}
          <div className="mb-4">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-text_secondary" />
              <Input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search conversations..."
                className="pl-10"
              />
            </div>
          </div>

          {/* Conversations */}
          <div className="flex-1 overflow-y-auto space-y-2">
            {filteredConversations.length === 0 ? (
              <div className="text-center py-8 text-text_secondary">
                <MessageSquare className="w-12 h-12 mx-auto mb-4 text-text_secondary/50" />
                <p>No conversations found</p>
                {searchQuery && (
                  <p className="text-sm mt-2">Try a different search term</p>
                )}
              </div>
            ) : (
              filteredConversations.map((conversation) => (
                <div
                  key={conversation.id}
                  className={`
                    p-4 rounded-lg border cursor-pointer transition-colors
                    ${
                      selectedConversation === conversation.id
                        ? 'border-primary bg-blue-50'
                        : 'border-border hover:border-primary/50'
                    }
                  `}
                  onClick={() => setSelectedConversation(conversation.id)}
                >
                  <div className="flex items-start justify-between mb-2">
                    <h3 className="font-medium text-text_primary line-clamp-2">
                      {conversation.title}
                    </h3>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDeleteConversation(conversation.id);
                      }}
                      className="ml-2 p-1 text-error hover:bg-error/10 rounded"
                      aria-label="Delete conversation"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                  <p className="text-xs text-text_secondary">
                    {conversation.messages.length} messages
                  </p>
                  <p className="text-xs text-text_secondary mt-1">
                    {new Date(conversation.updatedAt).toLocaleDateString()}
                  </p>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Messages View */}
        <div className="flex-1 flex flex-col">
          {selectedMessages ? (
            <>
              <div className="mb-4 pb-4 border-b border-border">
                <h2 className="text-xl font-semibold text-text_primary">
                  {conversations.find((c) => c.id === selectedConversation)?.title}
                </h2>
              </div>
              <div className="flex-1 overflow-y-auto space-y-4">
                {selectedMessages.map((message) => (
                  <div key={message.id}>
                    <ChatMessage message={message} />
                  </div>
                ))}
              </div>
            </>
          ) : (
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center">
                <MessageSquare className="w-16 h-16 mx-auto mb-4 text-text_secondary/50" />
                <h2 className="text-xl font-semibold text-text_primary mb-2">
                  Select a conversation
                </h2>
                <p className="text-text_secondary">
                  Choose a conversation from the list to view its messages
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default HistoryPage;