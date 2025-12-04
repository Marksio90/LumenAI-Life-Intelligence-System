/**
 * API Client with Automatic Token Refresh
 *
 * Features:
 * - Automatic access token attachment to requests
 * - Automatic token refresh on 401 errors
 * - Request queuing during token refresh
 * - Centralized error handling
 */

import axios, { AxiosInstance, AxiosError, InternalAxiosRequestConfig } from 'axios';
import { useAuthStore } from '@/store/authStore';

// API Base URL
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Create axios instance
const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Flag to prevent multiple refresh attempts
let isRefreshing = false;
let refreshSubscribers: ((token: string) => void)[] = [];

/**
 * Subscribe to token refresh
 */
const subscribeTokenRefresh = (cb: (token: string) => void) => {
  refreshSubscribers.push(cb);
};

/**
 * Notify all subscribers when token is refreshed
 */
const onTokenRefreshed = (token: string) => {
  refreshSubscribers.forEach((cb) => cb(token));
  refreshSubscribers = [];
};

/**
 * Request interceptor - Add access token to headers
 */
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const { accessToken } = useAuthStore.getState();

    if (accessToken && config.headers) {
      config.headers.Authorization = `Bearer ${accessToken}`;
    }

    return config;
  },
  (error: AxiosError) => {
    return Promise.reject(error);
  }
);

/**
 * Response interceptor - Handle 401 errors and refresh tokens
 */
apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean };

    // Handle 401 Unauthorized errors
    if (error.response?.status === 401 && !originalRequest._retry) {
      // Mark this request as retried to prevent infinite loops
      originalRequest._retry = true;

      const { refreshToken, refreshAccessToken, logout } = useAuthStore.getState();

      if (!refreshToken) {
        // No refresh token available, logout
        logout();
        return Promise.reject(error);
      }

      // If already refreshing, queue this request
      if (isRefreshing) {
        return new Promise((resolve) => {
          subscribeTokenRefresh((token: string) => {
            if (originalRequest.headers) {
              originalRequest.headers.Authorization = `Bearer ${token}`;
            }
            resolve(apiClient(originalRequest));
          });
        });
      }

      // Start refresh process
      isRefreshing = true;

      try {
        // Attempt to refresh the token
        const newAccessToken = await refreshAccessToken();

        if (newAccessToken) {
          // Update the original request with new token
          if (originalRequest.headers) {
            originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;
          }

          // Notify all queued requests
          onTokenRefreshed(newAccessToken);

          // Retry the original request
          return apiClient(originalRequest);
        } else {
          // Refresh failed, logout
          logout();
          return Promise.reject(error);
        }
      } catch (refreshError) {
        // Refresh failed, logout
        logout();
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }

    // Handle other errors
    return Promise.reject(error);
  }
);

/**
 * API Helper Functions
 */
export const api = {
  // Authentication
  auth: {
    login: (email: string, password: string) =>
      apiClient.post('/api/v1/auth/login', { email, password }),

    register: (email: string, password: string, username: string, full_name: string) =>
      apiClient.post('/api/v1/auth/register', { email, password, username, full_name }),

    refreshToken: (refreshToken: string) =>
      apiClient.post('/api/v1/auth/refresh', { refresh_token: refreshToken }),

    logout: () =>
      apiClient.post('/api/v1/auth/logout'),

    getProfile: () =>
      apiClient.get('/api/v1/auth/me'),

    updateProfile: (data: any) =>
      apiClient.put('/api/v1/auth/me', data),

    changePassword: (oldPassword: string, newPassword: string) =>
      apiClient.post('/api/v1/auth/change-password', {
        old_password: oldPassword,
        new_password: newPassword,
      }),
  },

  // Chat
  chat: {
    send: (message: string, agentName: string = 'orchestrator', conversationId?: string) =>
      apiClient.post('/api/v1/chat', {
        message,
        agent_name: agentName,
        conversation_id: conversationId,
      }),

    stream: (message: string, agentName: string = 'orchestrator', conversationId?: string) => {
      const { accessToken } = useAuthStore.getState();
      const params = new URLSearchParams({
        message,
        agent_name: agentName,
        ...(conversationId && { conversation_id: conversationId }),
      });

      return new EventSource(
        `${API_BASE_URL}/api/v1/chat/stream?${params.toString()}`,
        {
          headers: {
            Authorization: `Bearer ${accessToken}`,
          } as any,
        }
      );
    },
  },

  // Memory
  memory: {
    getContext: (userId: string) =>
      apiClient.get(`/api/v1/memory/${userId}`),

    saveMemory: (userId: string, data: any) =>
      apiClient.post(`/api/v1/memory/${userId}`, data),
  },

  // Health
  health: {
    check: () =>
      apiClient.get('/health'),

    metrics: () =>
      apiClient.get('/metrics'),
  },
};

export default apiClient;
