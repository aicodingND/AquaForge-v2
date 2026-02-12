'use client';

// TODO: port dependency — `@/lib/queries` does not exist on Mac. Create `frontend/src/lib/queries.ts` with a `useHealthCheck` hook using @tanstack/react-query.
import { useHealthCheck } from '@/lib/queries';

/**
 * Health indicator component that shows API connection status.
 * Uses TanStack Query for automatic refresh and caching.
 */
export default function HealthIndicator() {
    const { data, isLoading, isError, error } = useHealthCheck();

    if (isLoading) {
        return (
            <div className="flex items-center gap-2 text-xs text-white/40">
                <div className="w-2 h-2 rounded-full bg-yellow-500 animate-pulse" />
                <span>Connecting...</span>
            </div>
        );
    }

    if (isError) {
        return (
            <div className="flex items-center gap-2 text-xs text-red-400" title={error?.message}>
                <div className="w-2 h-2 rounded-full bg-red-500" />
                <span>API Offline</span>
            </div>
        );
    }

    return (
        <div className="flex items-center gap-2 text-xs text-green-400" title={`Status: ${data?.status}`}>
            <div className="w-2 h-2 rounded-full bg-green-500" />
            <span>Connected</span>
        </div>
    );
}
