/**
 * React hooks for V3 Unified Interaction Model
 */

import { useQuery, UseQueryOptions } from '@tanstack/react-query';
import { apiClient } from '@/lib/api';
import type {
  SessionV3,
  SessionInteractionsResponse,
  TurnInteractionsResponse,
  SessionStatsResponse,
  RequestInteraction,
  ResponseInteraction,
} from '@/types';

/**
 * Fetch session detail with V3 stats
 */
export function useSessionV3(
  sessionId: string | undefined,
  options?: Omit<UseQueryOptions<SessionV3>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: ['session-v3', sessionId],
    queryFn: () => apiClient.getSessionV3(sessionId!),
    enabled: !!sessionId,
    staleTime: 5 * 60 * 1000, // 5 minutes
    ...options,
  });
}

/**
 * Fetch all interactions for a session
 */
export function useSessionInteractions(
  sessionId: string | undefined,
  params?: { limit?: number; offset?: number },
  options?: Omit<UseQueryOptions<SessionInteractionsResponse>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: ['session-interactions', sessionId, params],
    queryFn: () => apiClient.getSessionInteractions(sessionId!, params),
    enabled: !!sessionId,
    staleTime: 5 * 60 * 1000,
    ...options,
  });
}

/**
 * Fetch interactions for a specific turn
 */
export function useTurnInteractions(
  sessionId: string | undefined,
  turnNumber: number | undefined,
  options?: Omit<UseQueryOptions<TurnInteractionsResponse>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: ['turn-interactions', sessionId, turnNumber],
    queryFn: () => apiClient.getTurnInteractions(sessionId!, turnNumber!),
    enabled: !!sessionId && turnNumber !== undefined,
    staleTime: 5 * 60 * 1000,
    ...options,
  });
}

/**
 * Fetch interaction detail with components/spans
 */
export function useInteractionDetail(
  interactionId: string | undefined,
  options?: Omit<
    UseQueryOptions<RequestInteraction | ResponseInteraction>,
    'queryKey' | 'queryFn'
  >
) {
  return useQuery({
    queryKey: ['interaction-detail', interactionId],
    queryFn: () => apiClient.getInteractionDetail(interactionId!),
    enabled: !!interactionId,
    staleTime: 10 * 60 * 1000, // Detail data rarely changes
    ...options,
  });
}

/**
 * Fetch session statistics
 */
export function useSessionStats(
  sessionId: string | undefined,
  options?: Omit<UseQueryOptions<SessionStatsResponse>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: ['session-stats', sessionId],
    queryFn: () => apiClient.getSessionStats(sessionId!),
    enabled: !!sessionId,
    staleTime: 5 * 60 * 1000,
    ...options,
  });
}

/**
 * Fetch list of all sessions
 */
export function useSessionsV3(
  params?: { limit?: number; offset?: number },
  options?: Omit<UseQueryOptions<any>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey: ['sessions-v3', params],
    queryFn: () => apiClient.getSessionsV3(params),
    staleTime: 1 * 60 * 1000, // 1 minute (list data changes more frequently)
    ...options,
  });
}
