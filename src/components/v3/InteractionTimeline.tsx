/**
 * InteractionTimeline - Main timeline component for V3 interactions
 */

import { useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Spinner } from '@/components/ui/Spinner';
import { TurnBlock } from './TurnBlock';
import type { Interaction } from '@/types';
import { groupInteractionsByTurn } from '@/utils/interactionHelpers';
import { List, BarChart3 } from 'lucide-react';

interface InteractionTimelineProps {
  interactions: Interaction[];
  isLoading?: boolean;
  showStats?: boolean;
  onToggleStats?: () => void;
}

export function InteractionTimeline({
  interactions,
  isLoading = false,
  showStats = false,
  onToggleStats,
}: InteractionTimelineProps) {
  const turnGroups = useMemo(
    () => groupInteractionsByTurn(interactions),
    [interactions]
  );

  if (isLoading) {
    return (
      <Card>
        <CardContent className="py-10 flex justify-center">
          <Spinner />
        </CardContent>
      </Card>
    );
  }

  if (!interactions.length) {
    return (
      <Card>
        <CardContent className="py-10 text-center text-sm text-gray-500">
          No interactions found
        </CardContent>
      </Card>
    );
  }

  const scrollToTurn = (turnNumber: number) => {
    const element = document.querySelector(`[data-turn="${turnNumber}"]`);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  };

  return (
    <Card>
      <CardHeader className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex items-center gap-2">
          <List className="h-5 w-5" />
          <CardTitle>Interaction Timeline</CardTitle>
          <span className="text-sm text-gray-500">
            ({turnGroups.length} turns, {interactions.length} interactions)
          </span>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {onToggleStats && (
            <Button
              variant={showStats ? 'primary' : 'outline'}
              size="sm"
              leftIcon={<BarChart3 className="h-4 w-4" />}
              onClick={onToggleStats}
            >
              {showStats ? 'Hide Stats' : 'Show Stats'}
            </Button>
          )}
          <div className="flex flex-wrap gap-2">
            {turnGroups.slice(0, 6).map((turn) => (
              <Button
                key={turn.turn_number}
                variant="outline"
                size="sm"
                onClick={() => scrollToTurn(turn.turn_number)}
              >
                Turn {turn.turn_number}
              </Button>
            ))}
            {turnGroups.length > 6 && (
              <span className="text-xs text-gray-500 self-center">
                +{turnGroups.length - 6} more
              </span>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {turnGroups.map((turnGroup, index) => (
          <div key={turnGroup.turn_number} data-turn={turnGroup.turn_number}>
            <TurnBlock turnGroup={turnGroup} index={index} />
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
