/**
 * TanStack Query hooks for AquaForge API
 * Provides cached, auto-refreshing data fetching
 */

import { useQuery } from '@tanstack/react-query';
import { api } from './api';

/**
 * Poll backend health endpoint every 30s.
 * Used by HealthIndicator to show API connection status.
 */
export function useHealthCheck() {
  return useQuery({
    queryKey: ['health'],
    queryFn: () => api.health(),
    refetchInterval: 30_000,
    retry: 1,
    staleTime: 10_000,
  });
}

/**
 * Fetch available optimization backends.
 * Cached for 5 minutes since backends rarely change at runtime.
 */
export function useBackends() {
  return useQuery({
    queryKey: ['backends'],
    queryFn: () => api.listBackends(),
    staleTime: 5 * 60_000,
  });
}

/**
 * Fetch available championship strategies.
 * Cached for 5 minutes.
 */
export function useStrategies() {
  return useQuery({
    queryKey: ['strategies'],
    queryFn: () => api.getStrategies(),
    staleTime: 5 * 60_000,
  });
}
