import React, { useMemo } from 'react';
import ChatMessage from './ChatMessage';
import RetrievalTracePanel from './RetrievalTracePanel';
import MessageSkeleton from './MessageSkeleton';
import { Message } from '../../types/chat.types';

interface VirtualizedMessageListProps {
  messages: Message[];
  isLoading: boolean;
}

interface MessageItem {
  message: Message;
  hasTrace: boolean;
}

const VirtualizedMessageList: React.FC<VirtualizedMessageListProps> = ({
  messages,
  isLoading,
}) => {
  // Transform messages into items with metadata
  const items = useMemo<MessageItem[]>(() => {
    return messages.map((message) => ({
      message,
      hasTrace:
        message.role === 'assistant' &&
        !!message.metadata?.retrieval_trace,
    }));
  }, [messages]);


  if (messages.length === 0 && !isLoading) {
    return (
      <div className="text-center py-12">
        <h2 className="text-2xl font-semibold text-text_primary mb-2">
          Start a conversation
        </h2>
        <p className="text-text_secondary">
          Ask a question or search your knowledge base to get started
        </p>
      </div>
    );
  }

  // For small lists, use regular rendering
  if (messages.length < 20) {
    return (
      <div className="space-y-4">
        {items.map((item, index) => (
          <div key={item.message.id}>
            <ChatMessage message={item.message} />
            {item.hasTrace && item.message.metadata?.retrieval_trace && (
              <RetrievalTracePanel
                trace={item.message.metadata.retrieval_trace}
                confidence={item.message.metadata.confidence}
                latency={item.message.metadata.latency_ms}
              />
            )}
          </div>
        ))}
        {isLoading && <MessageSkeleton />}
      </div>
    );
  }

  // For now, use regular rendering with performance optimizations
  // Full virtualization can be added later if needed for very large lists (1000+ messages)
  return (
    <div className="space-y-4">
      {items.map((item) => (
        <div key={item.message.id}>
          <ChatMessage message={item.message} />
          {item.hasTrace && item.message.metadata?.retrieval_trace && (
            <RetrievalTracePanel
              trace={item.message.metadata.retrieval_trace}
              confidence={item.message.metadata.confidence}
              latency={item.message.metadata.latency_ms}
            />
          )}
        </div>
      ))}
      {isLoading && <MessageSkeleton />}
    </div>
  );
};

export default VirtualizedMessageList;
