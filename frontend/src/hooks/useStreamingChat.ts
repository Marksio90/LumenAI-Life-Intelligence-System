/**
 * Streaming Chat Hook
 *
 * Handles real-time LLM streaming via WebSocket with message history,
 * typing indicators, and auto-scroll.
 */

import { useState, useCallback, useEffect, useRef } from 'react';
import { useWebSocket, WebSocketMessage } from './useWebSocket';

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
  isStreaming?: boolean;
  metadata?: Record<string, any>;
}

export interface StreamingChatConfig {
  wsUrl: string;
  token?: string;
  conversationId?: string;
  model?: string;
  provider?: 'openai' | 'anthropic';
  onMessageReceived?: (message: ChatMessage) => void;
  onStreamComplete?: (message: ChatMessage) => void;
  onError?: (error: Error) => void;
}

export const useStreamingChat = (config: StreamingChatConfig) => {
  const {
    wsUrl,
    token,
    conversationId,
    model = 'gpt-4-turbo-preview',
    provider = 'openai',
    onMessageReceived,
    onStreamComplete,
    onError,
  } = config;

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isTyping, setIsTyping] = useState(false);
  const [currentStreamId, setCurrentStreamId] = useState<string | null>(null);

  const streamingMessageRef = useRef<ChatMessage | null>(null);

  const { state, send, subscribe, isConnected } = useWebSocket({
    url: wsUrl,
    token,
    autoConnect: true,
    reconnectInterval: 3000,
    maxReconnectAttempts: 10,
  });

  /**
   * Handle LLM stream start
   */
  const handleStreamStart = useCallback((data: WebSocketMessage) => {
    console.log('[StreamingChat] Stream started:', data.stream_id);
    setCurrentStreamId(data.stream_id);
    setIsTyping(true);

    // Create new streaming message
    streamingMessageRef.current = {
      id: data.stream_id,
      role: 'assistant',
      content: '',
      timestamp: data.timestamp,
      isStreaming: true,
      metadata: {
        model: data.model,
        provider: data.provider,
      },
    };

    setMessages(prev => [...prev, streamingMessageRef.current!]);
  }, []);

  /**
   * Handle LLM stream chunk
   */
  const handleStreamChunk = useCallback((data: WebSocketMessage) => {
    if (data.stream_id !== currentStreamId) return;

    const chunk = data.content;

    // Update streaming message
    if (streamingMessageRef.current) {
      streamingMessageRef.current.content += chunk;

      // Update messages state
      setMessages(prev =>
        prev.map(msg =>
          msg.id === data.stream_id
            ? { ...msg, content: streamingMessageRef.current!.content }
            : msg
        )
      );
    }
  }, [currentStreamId]);

  /**
   * Handle LLM stream end
   */
  const handleStreamEnd = useCallback((data: WebSocketMessage) => {
    if (data.stream_id !== currentStreamId) return;

    console.log('[StreamingChat] Stream ended:', data.stream_id);
    setIsTyping(false);
    setCurrentStreamId(null);

    // Finalize streaming message
    if (streamingMessageRef.current) {
      streamingMessageRef.current.isStreaming = false;

      setMessages(prev =>
        prev.map(msg =>
          msg.id === data.stream_id
            ? { ...msg, isStreaming: false }
            : msg
        )
      );

      if (onStreamComplete) {
        onStreamComplete(streamingMessageRef.current);
      }

      streamingMessageRef.current = null;
    }
  }, [currentStreamId, onStreamComplete]);

  /**
   * Handle stream error
   */
  const handleStreamError = useCallback((data: WebSocketMessage) => {
    console.error('[StreamingChat] Stream error:', data.error);
    setIsTyping(false);
    setCurrentStreamId(null);

    if (onError) {
      onError(new Error(data.error));
    }

    // Mark streaming message as failed
    if (streamingMessageRef.current) {
      setMessages(prev =>
        prev.map(msg =>
          msg.id === data.stream_id
            ? { ...msg, isStreaming: false, metadata: { ...msg.metadata, error: data.error } }
            : msg
        )
      );
      streamingMessageRef.current = null;
    }
  }, [onError]);

  /**
   * Send chat message
   */
  const sendMessage = useCallback(
    (content: string, options?: { stream?: boolean; metadata?: Record<string, any> }) => {
      const { stream = true, metadata } = options || {};

      // Add user message to history
      const userMessage: ChatMessage = {
        id: `user_${Date.now()}`,
        role: 'user',
        content,
        timestamp: new Date().toISOString(),
        metadata,
      };

      setMessages(prev => [...prev, userMessage]);

      if (onMessageReceived) {
        onMessageReceived(userMessage);
      }

      // Send via WebSocket
      const success = send({
        type: 'chat.message',
        content,
        conversation_id: conversationId,
        stream,
        model,
        provider,
        metadata,
      });

      if (!success) {
        console.error('[StreamingChat] Failed to send message');
        if (onError) {
          onError(new Error('Failed to send message'));
        }
      }

      return success;
    },
    [send, conversationId, model, provider, onMessageReceived, onError]
  );

  /**
   * Clear chat history
   */
  const clearMessages = useCallback(() => {
    setMessages([]);
    streamingMessageRef.current = null;
    setCurrentStreamId(null);
    setIsTyping(false);
  }, []);

  /**
   * Subscribe to WebSocket events
   */
  useEffect(() => {
    const unsubscribers = [
      subscribe('llm.stream.start', handleStreamStart),
      subscribe('llm.stream.chunk', handleStreamChunk),
      subscribe('llm.stream.end', handleStreamEnd),
      subscribe('llm.stream.error', handleStreamError),
    ];

    return () => {
      unsubscribers.forEach(unsub => unsub());
    };
  }, [subscribe, handleStreamStart, handleStreamChunk, handleStreamEnd, handleStreamError]);

  return {
    messages,
    isConnected,
    isTyping,
    currentStreamId,
    sendMessage,
    clearMessages,
    connectionState: state,
  };
};
