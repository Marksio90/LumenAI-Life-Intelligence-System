import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { api } from '@/lib/apiClient';

interface User {
  user_id: string;
  email: string;
  username: string;
  full_name?: string;
  avatar_url?: string;
  is_active: boolean;
  is_email_verified: boolean;
  is_superuser: boolean;
  created_at: string;
}

interface AuthState {
  user: User | null;
  accessToken: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;

  // Actions
  login: (email: string, password: string) => Promise<void>;
  register: (data: {
    email: string;
    username: string;
    password: string;
    full_name?: string;
  }) => Promise<void>;
  logout: () => void;
  refreshAccessToken: () => Promise<string | null>;
  setUser: (user: User) => void;
  setTokens: (accessToken: string, refreshToken: string) => void;
  checkAuth: () => Promise<boolean>;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,
      isLoading: false,

      // Login
      login: async (email: string, password: string) => {
        set({ isLoading: true });

        try {
          const response = await api.auth.login(email, password);
          const data = response.data;

          set({
            user: data.user,
            accessToken: data.token.access_token,
            refreshToken: data.token.refresh_token,
            isAuthenticated: true,
            isLoading: false,
          });
        } catch (error: any) {
          set({ isLoading: false });
          throw new Error(error.response?.data?.message || 'Login failed');
        }
      },

      // Register
      register: async (data) => {
        set({ isLoading: true });

        try {
          const response = await api.auth.register(
            data.email,
            data.password,
            data.username,
            data.full_name || ''
          );
          const result = response.data;

          set({
            user: result.user,
            accessToken: result.token.access_token,
            refreshToken: result.token.refresh_token,
            isAuthenticated: true,
            isLoading: false,
          });
        } catch (error: any) {
          set({ isLoading: false });
          throw new Error(error.response?.data?.message || 'Registration failed');
        }
      },

      // Logout
      logout: () => {
        // Call logout API (optional - token will be invalidated on server)
        try {
          api.auth.logout();
        } catch (error) {
          // Ignore errors - clear local state anyway
        }

        set({
          user: null,
          accessToken: null,
          refreshToken: null,
          isAuthenticated: false,
        });
      },

      // Refresh access token
      refreshAccessToken: async () => {
        const { refreshToken } = get();

        if (!refreshToken) {
          return null;
        }

        try {
          const response = await api.auth.refreshToken(refreshToken);
          const data = response.data;

          const newAccessToken = data.access_token;

          set({
            accessToken: newAccessToken,
          });

          return newAccessToken;
        } catch (error) {
          get().logout();
          return null;
        }
      },

      // Set user
      setUser: (user: User) => {
        set({ user, isAuthenticated: true });
      },

      // Set tokens
      setTokens: (accessToken: string, refreshToken: string) => {
        set({ accessToken, refreshToken, isAuthenticated: true });
      },

      // Check authentication status with backend verification
      checkAuth: async () => {
        const { accessToken, user } = get();

        if (!accessToken || !user) {
          set({ isAuthenticated: false });
          return false;
        }

        try {
          // Verify token with backend
          const response = await api.auth.getProfile();
          const userData = response.data;

          set({
            user: userData,
            isAuthenticated: true,
          });

          return true;
        } catch (error) {
          // Token invalid or expired, try to refresh
          const newToken = await get().refreshAccessToken();

          if (newToken) {
            // Refresh successful, try again
            try {
              const response = await api.auth.getProfile();
              const userData = response.data;

              set({
                user: userData,
                isAuthenticated: true,
              });

              return true;
            } catch (error) {
              get().logout();
              return false;
            }
          } else {
            get().logout();
            return false;
          }
        }
      },
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        user: state.user,
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
      }),
    }
  )
);

// Initialize auth check on module load
if (typeof window !== 'undefined') {
  useAuthStore.getState().checkAuth();
}
