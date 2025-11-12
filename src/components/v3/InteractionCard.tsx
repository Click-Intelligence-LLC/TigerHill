/**
 * InteractionCard - Display a single interaction (request or response)
 */

import { useMemo } from 'react';
import { Card, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import type { Interaction } from '@/types';
import {
  getInteractionIcon,
  getInteractionColorClass,
  formatTokens,
  formatDuration,
} from '@/utils/interactionHelpers';
import { Clock, Coins, CheckCircle, XCircle, AlertCircle } from 'lucide-react';

interface InteractionCardProps {
  interaction: Interaction;
  isExpanded?: boolean;
  onToggle?: () => void;
}

export function InteractionCard({
  interaction,
  isExpanded = false,
  onToggle,
}: InteractionCardProps) {
  const icon = getInteractionIcon(interaction.type);
  const colorClass = getInteractionColorClass(interaction.type);

  const statusIcon = useMemo(() => {
    if (interaction.type === 'response') {
      if (interaction.is_success) {
        return <CheckCircle className="h-4 w-4 text-green-600" />;
      }
      if (interaction.error_message) {
        return <XCircle className="h-4 w-4 text-red-600" />;
      }
    }
    return null;
  }, [interaction]);

  return (
    <Card
      className={`transition-all ${colorClass} border-l-4 cursor-pointer hover:shadow-md`}
      onClick={onToggle}
    >
      <CardContent className="p-4 space-y-3">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-lg">{icon}</span>
            <span className="font-semibold capitalize">{interaction.type}</span>
            <Badge variant="outline" className="text-xs">
              Seq {interaction.sequence}
            </Badge>
            {statusIcon}
          </div>
          <span className="text-xs text-gray-500">
            {new Date(interaction.timestamp * 1000).toLocaleTimeString()}
          </span>
        </div>

        {/* Request-specific info */}
        {interaction.type === 'request' && (
          <div className="space-y-2 text-sm">
            {interaction.user_input && (
              <div className="bg-white dark:bg-gray-800 p-3 rounded border">
                <p className="font-mono text-xs line-clamp-3">{interaction.user_input}</p>
              </div>
            )}
            <div className="flex gap-4 text-xs text-gray-600">
              {interaction.model && <span>Model: {interaction.model}</span>}
              {interaction.temperature !== null && interaction.temperature !== undefined && (
                <span>Temp: {interaction.temperature}</span>
              )}
              {interaction.max_tokens && <span>Max: {interaction.max_tokens}</span>}
            </div>
          </div>
        )}

        {/* Response-specific info */}
        {interaction.type === 'response' && (
          <div className="space-y-2">
            <div className="flex flex-wrap gap-2">
              {interaction.duration_ms !== null && interaction.duration_ms !== undefined && (
                <Badge variant="outline" className="text-xs flex items-center gap-1">
                  <Clock className="h-3 w-3" />
                  {formatDuration(interaction.duration_ms)}
                </Badge>
              )}
              {interaction.total_tokens && (
                <Badge variant="outline" className="text-xs flex items-center gap-1">
                  <Coins className="h-3 w-3" />
                  {formatTokens(interaction.total_tokens)} tokens
                </Badge>
              )}
              {interaction.status_code && (
                <Badge
                  variant={interaction.is_success ? 'success' : 'danger'}
                  className="text-xs"
                >
                  {interaction.status_code}
                </Badge>
              )}
            </div>

            {interaction.input_tokens !== null && interaction.input_tokens !== undefined && (
              <div className="text-xs text-gray-600 flex gap-3">
                <span>In: {formatTokens(interaction.input_tokens)}</span>
                <span>Out: {formatTokens(interaction.output_tokens)}</span>
              </div>
            )}

            {interaction.error_message && (
              <div className="bg-red-50 dark:bg-red-950 p-2 rounded text-xs text-red-700 dark:text-red-300 flex items-start gap-2">
                <AlertCircle className="h-4 w-4 flex-shrink-0 mt-0.5" />
                <span>{interaction.error_message}</span>
              </div>
            )}
          </div>
        )}

        {/* Expandable details */}
        {isExpanded && (
          <div className="pt-3 border-t space-y-2">
            <div className="text-xs space-y-1">
              <p>
                <span className="font-semibold">ID:</span>{' '}
                <span className="font-mono">{interaction.id.slice(0, 8)}...</span>
              </p>
              {interaction.request_id && (
                <p>
                  <span className="font-semibold">Request ID:</span>{' '}
                  <span className="font-mono">{interaction.request_id.slice(0, 8)}...</span>
                </p>
              )}
              {interaction.provider && (
                <p>
                  <span className="font-semibold">Provider:</span> {interaction.provider}
                </p>
              )}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
