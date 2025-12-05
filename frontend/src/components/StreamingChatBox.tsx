/**
 * Streaming Chat Box Component
 *
 * Real-time chat interface with LLM streaming, typing indicators,
 * and auto-scroll functionality.
 */

import React, { useEffect, useRef, useState } from 'react';
import { useStreamingChat } from '../hooks/useStreamingChat';

interface StreamingChatBoxProps {
  wsUrl?: string;
  token?: string;
  conversationId?: string;
  model?: string;
  provider?: 'openai' | 'anthropic';
  className?: string;
  placeholder?: string;
  autoFocus?: boolean;
}

export const StreamingChatBox: React.FC<StreamingChatBoxProps> = ({
  wsUrl = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws/chat`,
  token,
  conversationId,
  model = 'gpt-4-turbo-preview',
  provider = 'openai',
  className = '',
  placeholder = 'Type your message...',
  autoFocus = true,
}) => {
  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const {
    messages,
    isConnected,
    isTyping,
    sendMessage,
    clearMessages,
    connectionState,
  } = useStreamingChat({
    wsUrl,
    token,
    conversationId,
    model,
    provider,
    onError: (error) => {
      console.error('[ChatBox] Error:', error);
    },
  });

  /**
   * Auto-scroll to bottom when new messages arrive
   */
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  /**
   * Auto-focus input on mount
   */
  useEffect(() => {
    if (autoFocus && inputRef.current) {
      inputRef.current.focus();
    }
  }, [autoFocus]);

  /**
   * Handle form submission
   */
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    if (!input.trim() || !isConnected) {
      return;
    }

    sendMessage(input.trim());
    setInput('');

    // Refocus input
    setTimeout(() => inputRef.current?.focus(), 0);
  };

  /**
   * Handle keyboard shortcuts
   */
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // Submit on Enter (without Shift)
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  /**
   * Format timestamp
   */
  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  return (
    <div className={`streaming-chat-box ${className}`}>
      {/* Connection Status */}
      <div className="chat-header">
        <div className="connection-status">
          {isConnected ? (
            <span className="status-connected">● Connected</span>
          ) : connectionState.isConnecting ? (
            <span className="status-connecting">○ Connecting...</span>
          ) : (
            <span className="status-disconnected">○ Disconnected</span>
          )}
        </div>
        <div className="chat-actions">
          <button
            type="button"
            onClick={clearMessages}
            className="btn-clear"
            disabled={messages.length === 0}
          >
            Clear
          </button>
        </div>
      </div>

      {/* Messages */}
      <div className="chat-messages">
        {messages.length === 0 ? (
          <div className="empty-state">
            <p>Start a conversation!</p>
          </div>
        ) : (
          messages.map((message) => (
            <div
              key={message.id}
              className={`message message-${message.role} ${
                message.isStreaming ? 'message-streaming' : ''
              }`}
            >
              <div className="message-header">
                <span className="message-role">
                  {message.role === 'user' ? 'You' : 'Assistant'}
                </span>
                <span className="message-time">{formatTime(message.timestamp)}</span>
              </div>
              <div className="message-content">
                {message.content}
                {message.isStreaming && <span className="streaming-cursor">▊</span>}
              </div>
              {message.metadata?.error && (
                <div className="message-error">Error: {message.metadata.error}</div>
              )}
            </div>
          ))
        )}

        {/* Typing Indicator */}
        {isTyping && !messages[messages.length - 1]?.isStreaming && (
          <div className="message message-assistant message-typing">
            <div className="message-header">
              <span className="message-role">Assistant</span>
            </div>
            <div className="message-content">
              <span className="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
              </span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Form */}
      <form onSubmit={handleSubmit} className="chat-input-form">
        <textarea
          ref={inputRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={isConnected ? placeholder : 'Connecting...'}
          disabled={!isConnected}
          className="chat-input"
          rows={1}
        />
        <button
          type="submit"
          disabled={!isConnected || !input.trim()}
          className="btn-send"
        >
          Send
        </button>
      </form>

      {/* Error Display */}
      {connectionState.error && (
        <div className="chat-error">
          Connection error: {connectionState.error.message}
        </div>
      )}
    </div>
  );
};

export default StreamingChatBox;
