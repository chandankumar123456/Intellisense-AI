import React from 'react';

const MessageSkeleton: React.FC = () => {
  return (
    <div className="flex justify-start mb-4 animate-pulse">
      <div className="message-assistant max-w-[80%]">
        <div className="space-y-2">
          <div className="h-4 bg-gray-200 rounded w-3/4" />
          <div className="h-4 bg-gray-200 rounded w-1/2" />
          <div className="h-4 bg-gray-200 rounded w-5/6" />
        </div>
      </div>
    </div>
  );
};

export default MessageSkeleton;
