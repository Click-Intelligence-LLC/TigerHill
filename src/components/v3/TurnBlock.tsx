/**
 * TurnBlock - Display all interactions within a single turn
 */

import { useState } from 'react';
import { Card, CardContent, CardHeader } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { InteractionCard } from './InteractionCard';
import type { TurnGroup } from '@/types';
import {
  getTurnSummary,
  isStreamingTurn,
  isFunctionCallingTurn,
} from '@/utils/interactionHelpers';
import { ChevronDown, ChevronUp, Zap, FunctionSquare } from 'lucide-react';

interface TurnBlockProps {
  turnGroup: TurnGroup;
  index: number;
}

export function TurnBlock({ turnGroup, index }: TurnBlockProps) {
  const [isExpanded, setIsExpanded] = useState(index < 3); // First 3 turns expanded by default
  const [expandedInteractions, setExpandedInteractions] = useState<Set<string>>(new Set());

  const isStreaming = isStreamingTurn(turnGroup);
  const isFunctionCalling = isFunctionCallingTurn(turnGroup);
  const summary = getTurnSummary(turnGroup);

  const toggleInteraction = (id: string) => {
    const newSet = new Set(expandedInteractions);
    if (newSet.has(id)) {
      newSet.delete(id);
    } else {
      newSet.add(id);
    }
    setExpandedInteractions(newSet);
  };

  return (
    <Card className="overflow-hidden">
      <CardHeader
        className="cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-lg font-bold text-blue-600">Turn {turnGroup.turn_number}</span>
            <Badge variant="outline" className="text-xs">
              {turnGroup.interactions.length} interactions
            </Badge>
            {isStreaming && (
              <Badge variant="default" className="text-xs flex items-center gap-1">
                <Zap className="h-3 w-3" />
                Streaming
              </Badge>
            )}
            {isFunctionCalling && (
              <Badge variant="default" className="text-xs flex items-center gap-1">
                <FunctionSquare className="h-3 w-3" />
                Function Call
              </Badge>
            )}
          </div>
          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-600">{summary}</span>
            <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
              {isExpanded ? (
                <ChevronUp className="h-4 w-4" />
              ) : (
                <ChevronDown className="h-4 w-4" />
              )}
            </Button>
          </div>
        </div>
      </CardHeader>

      {isExpanded && (
        <CardContent className="space-y-3 pt-4">
          {turnGroup.interactions.map((interaction) => (
            <InteractionCard
              key={interaction.id}
              interaction={interaction}
              isExpanded={expandedInteractions.has(interaction.id)}
              onToggle={() => toggleInteraction(interaction.id)}
            />
          ))}
        </CardContent>
      )}
    </Card>
  );
}
