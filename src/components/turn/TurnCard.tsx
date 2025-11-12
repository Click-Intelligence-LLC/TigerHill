/**
 * TurnCard - Display a complete turn with request and response
 */

import { useState } from 'react';
import { Card, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { ChevronDown, Play, GitCompare } from 'lucide-react';

interface TurnCardProps {
  turnNumber: number;
  totalTokens?: number;
  durationMs?: number;
  isExpanded?: boolean;
  onToggle?: () => void;
  onReplay?: () => void;
  onCompare?: () => void;
  children?: React.ReactNode;
}

export function TurnCard({
  turnNumber,
  totalTokens,
  durationMs,
  isExpanded = true,
  onToggle,
  onReplay,
  onCompare,
  children,
}: TurnCardProps) {
  const [collapsed, setCollapsed] = useState(!isExpanded);

  const handleToggle = () => {
    setCollapsed(!collapsed);
    onToggle?.();
  };

  const formatDuration = (ms: number) => {
    if (ms < 1000) return `${ms}ms`;
    return `${(ms / 1000).toFixed(2)}s`;
  };

  return (
    <Card className="overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-gray-200 bg-gray-50 px-6 py-4">
        <div className="flex items-center gap-4">
          <button
            onClick={handleToggle}
            className="flex items-center gap-2 text-left transition-colors hover:text-blue-600"
          >
            {collapsed ? (
              <ChevronRight className="h-5 w-5" />
            ) : (
              <ChevronDown className="h-5 w-5" />
            )}
            <h2 className="text-lg font-semibold text-gray-900">
              Turn {turnNumber}
            </h2>
          </button>

          <div className="flex items-center gap-2">
            {totalTokens !== undefined && (
              <Badge variant="outline" className="font-mono">
                {totalTokens.toLocaleString()} tokens
              </Badge>
            )}
            {durationMs !== undefined && (
              <Badge variant="outline" className="font-mono">
                {formatDuration(durationMs)}
              </Badge>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2">
          {onReplay && (
            <Button
              size="sm"
              variant="outline"
              leftIcon={<Play className="h-4 w-4" />}
              onClick={(e) => {
                e.stopPropagation();
                onReplay();
              }}
            >
              Replay
            </Button>
          )}
          {onCompare && (
            <Button
              size="sm"
              variant="outline"
              leftIcon={<GitCompare className="h-4 w-4" />}
              onClick={(e) => {
                e.stopPropagation();
                onCompare();
              }}
            >
              Compare
            </Button>
          )}
        </div>
      </div>

      {/* Content */}
      {!collapsed && (
        <CardContent className="p-6">
          {children || (
            <div className="space-y-4">
              <div className="rounded-lg border-2 border-dashed border-gray-300 p-8 text-center">
                <p className="text-sm text-gray-400">
                  Request and Response sections will be rendered here
                </p>
              </div>
            </div>
          )}
        </CardContent>
      )}
    </Card>
  );
}

// Import fix for ChevronRight
import { ChevronRight } from 'lucide-react';
