/**
 * WebSocket Hook for Real-time Communication
 *
 * Provides WebSocket connection management with auto-reconnect,
 * message handling, and connection state management.
 */

import { useEffect, useRef, useState, useCallback } from 'react';

export interface WebSocketMessage {
  type: string;
  [key: string]: any;
}

export interface WebSocketConfig {
  url: string;
  token?: string;
  autoConnect?: boolean;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
  heartbeatInterval?: number;
}

export interface WebSocketState {
  isConnected: boolean;
  isConnecting: boolean;
  error: Error | null;
  connectionId: string | null;
  reconnectAttempts: number;
}

export const useWebSocket = (config: WebSocketConfig) => {
  const {
    url,
    token,
    autoConnect = true,
    reconnectInterval = 3000,
    maxReconnectAttempts = 10,
    heartbeatInterval = 30000,
  } = config;

  const [state, setState] = useState<WebSocketState>({
    isConnected: false,
    isConnecting: false,
    error: null,
    connectionId: null,
    reconnectAttempts: 0,
  });

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const heartbeatIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const messageHandlersRef = useRef<Map<string, Set<(data: any) => void>>>(new Map());

  /**
   * Connect to WebSocket server
   */
  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      console.log('[WebSocket] Already connected');
      return;
    }

    setState(prev => ({ ...prev, isConnecting: true, error: null }));

    try {
      // Build WebSocket URL with token
      const wsUrl = token ? `${url}?token=${token}` : url;

      console.log('[WebSocket] Connecting to:', wsUrl);
      const ws = new WebSocket(wsUrl);

      // Connection opened
      ws.onopen = () => {
        console.log('[WebSocket] Connected');
        setState(prev => ({
          ...prev,
          isConnected: true,
          isConnecting: false,
          error: null,
          reconnectAttempts: 0,
        }));

        // Start heartbeat
        if (heartbeatInterval > 0) {
          heartbeatIntervalRef.current = setInterval(() => {
            if (ws.readyState === WebSocket.OPEN) {
              ws.send(JSON.stringify({ type: 'ping' }));
            }
          }, heartbeatInterval);
        }
      };

      // Message received
      ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          console.log('[WebSocket] Message received:', message.type);

          // Handle connection established
          if (message.type === 'connection.established') {
            setState(prev => ({
              ...prev,
              connectionId: message.connection_id,
            }));
          }

          // Call registered handlers for this message type
          const handlers = messageHandlersRef.current.get(message.type);
          if (handlers) {
            handlers.forEach(handler => handler(message));
          }

          // Call wildcard handlers
          const wildcardHandlers = messageHandlersRef.current.get('*');
          if (wildcardHandlers) {
            wildcardHandlers.forEach(handler => handler(message));
          }
        } catch (error) {
          console.error('[WebSocket] Failed to parse message:', error);
        }
      };

      // Connection closed
      ws.onclose = (event) => {
        console.log('[WebSocket] Disconnected:', event.code, event.reason);

        setState(prev => ({
          ...prev,
          isConnected: false,
          isConnecting: false,
          connectionId: null,
        }));

        // Clear heartbeat
        if (heartbeatIntervalRef.current) {
          clearInterval(heartbeatIntervalRef.current);
          heartbeatIntervalRef.current = null;
        }

        // Attempt reconnection
        if (!event.wasClean && state.reconnectAttempts < maxReconnectAttempts) {
          console.log(`[WebSocket] Reconnecting in ${reconnectInterval}ms...`);
          reconnectTimeoutRef.current = setTimeout(() => {
            setState(prev => ({
              ...prev,
              reconnectAttempts: prev.reconnectAttempts + 1,
            }));
            connect();
          }, reconnectInterval);
        }
      };

      // Error occurred
      ws.onerror = (error) => {
        console.error('[WebSocket] Error:', error);
        setState(prev => ({
          ...prev,
          error: new Error('WebSocket connection error'),
          isConnecting: false,
        }));
      };

      wsRef.current = ws;
    } catch (error) {
      console.error('[WebSocket] Failed to connect:', error);
      setState(prev => ({
        ...prev,
        error: error as Error,
        isConnecting: false,
      }));
    }
  }, [url, token, reconnectInterval, maxReconnectAttempts, heartbeatInterval]);

  /**
   * Disconnect from WebSocket server
   */
  const disconnect = useCallback(() => {
    console.log('[WebSocket] Disconnecting...');

    // Clear reconnection timeout
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    // Clear heartbeat
    if (heartbeatIntervalRef.current) {
      clearInterval(heartbeatIntervalRef.current);
      heartbeatIntervalRef.current = null;
    }

    // Close WebSocket
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    setState({
      isConnected: false,
      isConnecting: false,
      error: null,
      connectionId: null,
      reconnectAttempts: 0,
    });
  }, []);

  /**
   * Send message to server
   */
  const send = useCallback((message: WebSocketMessage) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      console.warn('[WebSocket] Not connected, cannot send message');
      return false;
    }

    try {
      wsRef.current.send(JSON.stringify(message));
      console.log('[WebSocket] Message sent:', message.type);
      return true;
    } catch (error) {
      console.error('[WebSocket] Failed to send message:', error);
      return false;
    }
  }, []);

  /**
   * Subscribe to messages of a specific type
   */
  const subscribe = useCallback((messageType: string, handler: (data: any) => void) => {
    if (!messageHandlersRef.current.has(messageType)) {
      messageHandlersRef.current.set(messageType, new Set());
    }

    messageHandlersRef.current.get(messageType)!.add(handler);

    // Return unsubscribe function
    return () => {
      const handlers = messageHandlersRef.current.get(messageType);
      if (handlers) {
        handlers.delete(handler);
        if (handlers.size === 0) {
          messageHandlersRef.current.delete(messageType);
        }
      }
    };
  }, []);

  /**
   * Auto-connect on mount if configured
   */
  useEffect(() => {
    if (autoConnect) {
      connect();
    }

    return () => {
      disconnect();
    };
  }, [autoConnect, connect, disconnect]);

  return {
    state,
    connect,
    disconnect,
    send,
    subscribe,
    isConnected: state.isConnected,
    isConnecting: state.isConnecting,
    error: state.error,
  };
};
