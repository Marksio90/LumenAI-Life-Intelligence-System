/**
 * Health Check Endpoint for Kubernetes Liveness Probe
 *
 * This endpoint is used by Kubernetes to determine if the container is alive.
 * If this endpoint fails, Kubernetes will restart the container.
 *
 * Returns 200 OK if the application is running.
 */

import { NextResponse } from 'next/server';

export async function GET() {
  try {
    // Basic health check - if this code executes, the app is alive
    return NextResponse.json(
      {
        status: 'healthy',
        timestamp: new Date().toISOString(),
        service: 'lumenai-frontend',
        uptime: process.uptime(),
      },
      { status: 200 }
    );
  } catch (error) {
    // If there's an error, the app is unhealthy
    return NextResponse.json(
      {
        status: 'unhealthy',
        error: error instanceof Error ? error.message : 'Unknown error',
        timestamp: new Date().toISOString(),
      },
      { status: 503 }
    );
  }
}

// Disable caching for health checks
export const dynamic = 'force-dynamic';
export const revalidate = 0;
