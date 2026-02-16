import React, { useRef, useEffect, useMemo } from 'react';
import { useChat } from '../contexts/ChatContext';
import ChatMessage from '../components/chat/ChatMessage';
import ChatInput from '../components/chat/ChatInput';
import RetrievalTracePanel from '../components/chat/RetrievalTracePanel';
import SourceTabs from '../components/chat/SourceTabs';
import { Search } from 'lucide-react';
import Input from '../components/common/Input';
import { useDebounce } from '../hooks/useDebounce';

const ChatPage: React.FC = () => {
  const {
    messages,
    currentQuery,
    isLoading,
    activeTab,
    sendMessage,
    setActiveTab,
    setCurrentQuery,
  } = useChat();

  const messagesEndRef = useRef<HTMLDivElement>(null);
  // Debounced query for future search functionality
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const debouncedQuery = useDebounce(currentQuery, 300);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Memoize message list to prevent unnecessary re-renders
  const memoizedMessages = useMemo(() => messages, [messages]);

  const handleSend = async (query: string) => {
    await sendMessage(query);
  };

  return (
    <div className="flex flex-col h-full bg-background">
      {/* Search bar */}
      <div className="border-b border-border bg-white p-4">
        <div className="max-w-4xl mx-auto">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-text_secondary" />
            <Input
              type="text"
              value={currentQuery}
              onChange={(e) => setCurrentQuery(e.target.value)}
              placeholder="Search your knowledge base..."
              className="pl-10"
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  handleSend(currentQuery);
                }
              }}
            />
          </div>
        </div>
      </div>

      {/* Source tabs */}
      <SourceTabs activeTab={activeTab} onTabChange={setActiveTab} />

      {/* Messages */}
      <div className="flex-1 overflow-hidden p-4">
        <div className="max-w-4xl mx-auto h-full">
          {messages.length === 0 && !isLoading ? (
            <div className="text-center py-12">
              <h2 className="text-2xl font-semibold text-text_primary mb-2">
                Start a conversation
              </h2>
              <p className="text-text_secondary">
                Ask a question or search your knowledge base to get started
              </p>
            </div>
          ) : (
            <div className="h-full overflow-y-auto px-2">
              {memoizedMessages.map((message) => (
                <div key={message.id} className="mb-4">
                  <ChatMessage message={message} />
                  {message.role === 'assistant' && message.metadata?.retrieval_trace && (
                    <RetrievalTracePanel
                      trace={message.metadata.retrieval_trace}
                      confidence={message.metadata.confidence}
                      latency={message.metadata.latency_ms}
                    />
                  )}
                </div>
              ))}
              {isLoading && (
                <div className="flex justify-start mb-4">
                  <div className="message-assistant">
                    <div className="flex items-center gap-2">
                      <div className="w-2 h-2 bg-text_secondary rounded-full animate-pulse" />
                      <div className="w-2 h-2 bg-text_secondary rounded-full animate-pulse delay-75" />
                      <div className="w-2 h-2 bg-text_secondary rounded-full animate-pulse delay-150" />
                    </div>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>
      </div>

      {/* Input */}
      <ChatInput onSend={handleSend} isLoading={isLoading} />
    </div>
  );
};

export default ChatPage;
