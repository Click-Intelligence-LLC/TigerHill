/**
 * Helper utilities for working with V3 Interaction model
 */

import type { Interaction, TurnGroup } from '@/types';

/**
 * Group interactions by turn number
 */
export function groupInteractionsByTurn(interactions: Interaction[]): TurnGroup[] {
  const turnMap = new Map<number, Interaction[]>();

  // Group by turn_number
  interactions.forEach((interaction) => {
    const existing = turnMap.get(interaction.turn_number) || [];
    existing.push(interaction);
    turnMap.set(interaction.turn_number, existing);
  });

  // Convert to TurnGroup array and sort
  const turnGroups: TurnGroup[] = Array.from(turnMap.entries())
    .map(([turn_number, interactions]) => {
      // Sort interactions within turn by sequence
      const sortedInteractions = interactions.sort((a, b) => a.sequence - b.sequence);

      return {
        turn_number,
        interactions: sortedInteractions,
        request_count: sortedInteractions.filter((i) => i.type === 'request').length,
        response_count: sortedInteractions.filter((i) => i.type === 'response').length,
      };
    })
    .sort((a, b) => a.turn_number - b.turn_number);

  return turnGroups;
}

/**
 * Find request interaction by request_id
 */
export function findRequestByRequestId(
  interactions: Interaction[],
  requestId: string
): Interaction | undefined {
  return interactions.find((i) => i.type === 'request' && i.request_id === requestId);
}

/**
 * Find all responses for a request_id
 */
export function findResponsesForRequest(
  interactions: Interaction[],
  requestId: string
): Interaction[] {
  return interactions.filter(
    (i) => i.type === 'response' && i.request_id === requestId
  );
}

/**
 * Get turn summary text
 */
export function getTurnSummary(turnGroup: TurnGroup): string {
  const { request_count, response_count } = turnGroup;

  if (request_count === 1 && response_count === 1) {
    return 'Single request-response';
  }

  if (request_count === 1 && response_count > 1) {
    return `Streaming (${response_count} chunks)`;
  }

  if (request_count > 1 && response_count > 1) {
    return `Function calling (${request_count} req, ${response_count} resp)`;
  }

  return `${request_count} request(s), ${response_count} response(s)`;
}

/**
 * Check if turn is a streaming response
 */
export function isStreamingTurn(turnGroup: TurnGroup): boolean {
  return turnGroup.request_count === 1 && turnGroup.response_count > 1;
}

/**
 * Check if turn is function calling
 */
export function isFunctionCallingTurn(turnGroup: TurnGroup): boolean {
  return turnGroup.request_count > 1;
}

/**
 * Get interaction type icon
 */
export function getInteractionIcon(type: 'request' | 'response'): string {
  return type === 'request' ? '📤' : '📥';
}

/**
 * Get interaction type color class
 */
export function getInteractionColorClass(type: 'request' | 'response'): string {
  return type === 'request'
    ? 'border-blue-500 bg-blue-50 dark:bg-blue-950'
    : 'border-orange-500 bg-orange-50 dark:bg-orange-950';
}

/**
 * Format token count
 */
export function formatTokens(tokens: number | null | undefined): string {
  if (tokens === null || tokens === undefined) return 'N/A';
  return tokens.toLocaleString();
}

/**
 * Format duration
 */
export function formatDuration(ms: number | null | undefined): string {
  if (ms === null || ms === undefined) return 'N/A';
  if (ms < 1000) return `${Math.round(ms)}ms`;
  return `${(ms / 1000).toFixed(2)}s`;
}
