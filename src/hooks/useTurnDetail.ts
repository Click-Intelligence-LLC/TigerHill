/**
 * useTurnDetail - 获取 Turn 的完整数据（components + spans）
 */

import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api';
import type { PromptComponent, ResponseSpan } from '@/types';

interface UseTurnDetailResult {
  components: PromptComponent[];
  spans: ResponseSpan[];
  isLoading: boolean;
  error: Error | null;
}

export function useTurnDetail(
  requestId?: string,
  responseId?: string
): UseTurnDetailResult {
  // 获取 request components
  const componentsQuery = useQuery({
    queryKey: ['interaction-components', requestId],
    queryFn: () => apiClient.getInteractionComponents(requestId!),
    enabled: !!requestId,
  });

  // 获取 response spans
  const spansQuery = useQuery({
    queryKey: ['interaction-spans', responseId],
    queryFn: () => apiClient.getInteractionSpans(responseId!),
    enabled: !!responseId,
  });

  return {
    components: componentsQuery.data || [],
    spans: spansQuery.data || [],
    isLoading: componentsQuery.isLoading || spansQuery.isLoading,
    error: (componentsQuery.error || spansQuery.error) as Error | null,
  };
}
