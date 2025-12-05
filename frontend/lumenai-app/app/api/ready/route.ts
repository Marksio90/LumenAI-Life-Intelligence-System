/**
 * Readiness Check Endpoint for Kubernetes Readiness Probe
 *
 * This endpoint is used by Kubernetes to determine if the container is ready to accept traffic.
 * If this endpoint fails, Kubernetes will not route traffic to this pod.
 *
 * Checks:
 * - Application is running
 * - Backend API is accessible (optional check)
 *
 * Returns 200 OK if the application is ready to serve traffic.
 */

import { NextResponse } from 'next/server';

export async function GET() {
  try {
    // Check if environment variables are configured
    const apiUrl = process.env.NEXT_PUBLIC_API_URL;
    const wsUrl = process.env.NEXT_PUBLIC_WS_URL;

    const checks = {
      app: true,
      envVars: !!(apiUrl && wsUrl),
    };

    // Optional: Check backend API connectivity
    // Uncomment if you want strict readiness checking
    /*
    if (apiUrl) {
      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 2000); // 2s timeout

        const response = await fetch(`${apiUrl}/health`, {
          signal: controller.signal,
          cache: 'no-store'
        });

        clearTimeout(timeoutId);
        checks.backendApi = response.ok;
      } catch (error) {
        checks.backendApi = false;
      }
    }
    */

    // Determine if ready
    const isReady = checks.app && checks.envVars;

    if (isReady) {
      return NextResponse.json(
        {
          status: 'ready',
          timestamp: new Date().toISOString(),
          service: 'lumenai-frontend',
          checks,
        },
        { status: 200 }
      );
    } else {
      return NextResponse.json(
        {
          status: 'not ready',
          timestamp: new Date().toISOString(),
          checks,
        },
        { status: 503 }
      );
    }
  } catch (error) {
    return NextResponse.json(
      {
        status: 'error',
        error: error instanceof Error ? error.message : 'Unknown error',
        timestamp: new Date().toISOString(),
      },
      { status: 503 }
    );
  }
}

// Disable caching for readiness checks
export const dynamic = 'force-dynamic';
export const revalidate = 0;
