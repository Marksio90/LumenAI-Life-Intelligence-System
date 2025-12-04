/**
 * Protected Route Component
 *
 * Wrapper component that ensures user is authenticated before rendering children.
 * Redirects to login page if not authenticated.
 *
 * Usage:
 * <ProtectedRoute>
 *   <YourProtectedComponent />
 * </ProtectedRoute>
 */

'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/store/authStore';

interface ProtectedRouteProps {
  children: React.ReactNode;
  requireVerified?: boolean; // Require email verification
  requireSuperuser?: boolean; // Require superuser role
  fallback?: React.ReactNode; // Component to show while loading
  redirectTo?: string; // Custom redirect path
}

export default function ProtectedRoute({
  children,
  requireVerified = false,
  requireSuperuser = false,
  fallback = <LoadingSpinner />,
  redirectTo = '/login',
}: ProtectedRouteProps) {
  const router = useRouter();
  const { isAuthenticated, user, checkAuth } = useAuthStore();
  const [isChecking, setIsChecking] = useState(true);

  useEffect(() => {
    const verifyAuth = async () => {
      setIsChecking(true);

      // Check if user is authenticated
      const authenticated = await checkAuth();

      if (!authenticated) {
        // Not authenticated, redirect to login
        router.push(redirectTo);
        return;
      }

      // Check additional requirements
      if (requireVerified && !user?.is_email_verified) {
        // Email verification required but not verified
        router.push('/verify-email');
        return;
      }

      if (requireSuperuser && !user?.is_superuser) {
        // Superuser required but user is not superuser
        router.push('/unauthorized');
        return;
      }

      setIsChecking(false);
    };

    verifyAuth();
  }, [isAuthenticated, user, requireVerified, requireSuperuser, router, redirectTo, checkAuth]);

  // Show loading state while checking authentication
  if (isChecking) {
    return <>{fallback}</>;
  }

  // User is authenticated and meets requirements
  return <>{children}</>;
}

/**
 * Default Loading Spinner
 */
function LoadingSpinner() {
  return (
    <div className="flex items-center justify-center min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
      <div className="text-center">
        <div className="inline-block animate-spin rounded-full h-16 w-16 border-t-2 border-b-2 border-purple-500"></div>
        <p className="mt-4 text-gray-300 text-lg">Weryfikacja...</p>
      </div>
    </div>
  );
}

/**
 * Higher-Order Component version for class components or alternative usage
 */
export function withAuth<P extends object>(
  Component: React.ComponentType<P>,
  options?: Omit<ProtectedRouteProps, 'children'>
) {
  return function WithAuthComponent(props: P) {
    return (
      <ProtectedRoute {...options}>
        <Component {...props} />
      </ProtectedRoute>
    );
  };
}
