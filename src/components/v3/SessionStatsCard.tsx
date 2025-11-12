/**
 * SessionStatsCard - Display session statistics from V3 API
 */

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import type { SessionStatsResponse } from '@/types';
import { formatTokens } from '@/utils/interactionHelpers';
import { BarChart3, MessageSquare, ArrowRightLeft, Coins } from 'lucide-react';

interface SessionStatsCardProps {
  stats: SessionStatsResponse;
}

export function SessionStatsCard({ stats }: SessionStatsCardProps) {
  const { overall, per_turn } = stats;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <BarChart3 className="h-5 w-5" />
          Session Statistics
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Overall Stats */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-sm text-gray-600">
              <MessageSquare className="h-4 w-4" />
              <span>Total Turns</span>
            </div>
            <p className="text-2xl font-bold">{overall.total_turns}</p>
          </div>

          <div className="space-y-2">
            <div className="flex items-center gap-2 text-sm text-gray-600">
              <ArrowRightLeft className="h-4 w-4" />
              <span>Total Interactions</span>
            </div>
            <p className="text-2xl font-bold">{overall.total_interactions}</p>
          </div>

          <div className="space-y-2">
            <div className="flex items-center gap-2 text-sm text-gray-600">
              <Coins className="h-4 w-4 text-blue-600" />
              <span>Input Tokens</span>
            </div>
            <p className="text-2xl font-bold text-blue-600">
              {formatTokens(overall.total_input_tokens)}
            </p>
          </div>

          <div className="space-y-2">
            <div className="flex items-center gap-2 text-sm text-gray-600">
              <Coins className="h-4 w-4 text-orange-600" />
              <span>Output Tokens</span>
            </div>
            <p className="text-2xl font-bold text-orange-600">
              {formatTokens(overall.total_output_tokens)}
            </p>
          </div>
        </div>

        {/* Per-Turn Stats Table */}
        <div>
          <h4 className="text-sm font-semibold mb-3">Per-Turn Breakdown</h4>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 dark:bg-gray-800">
                <tr>
                  <th className="px-4 py-2 text-left">Turn</th>
                  <th className="px-4 py-2 text-center">Interactions</th>
                  <th className="px-4 py-2 text-center">Requests</th>
                  <th className="px-4 py-2 text-center">Responses</th>
                  <th className="px-4 py-2 text-right">Input Tokens</th>
                  <th className="px-4 py-2 text-right">Output Tokens</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {per_turn.slice(0, 10).map((turn) => (
                  <tr
                    key={turn.turn_number}
                    className="hover:bg-gray-50 dark:hover:bg-gray-800"
                  >
                    <td className="px-4 py-2">
                      <Badge variant="outline">Turn {turn.turn_number}</Badge>
                    </td>
                    <td className="px-4 py-2 text-center">{turn.interaction_count}</td>
                    <td className="px-4 py-2 text-center">{turn.request_count}</td>
                    <td className="px-4 py-2 text-center">{turn.response_count}</td>
                    <td className="px-4 py-2 text-right text-blue-600">
                      {formatTokens(turn.total_input_tokens)}
                    </td>
                    <td className="px-4 py-2 text-right text-orange-600">
                      {formatTokens(turn.total_output_tokens)}
                    </td>
                  </tr>
                ))}
                {per_turn.length > 10 && (
                  <tr>
                    <td colSpan={6} className="px-4 py-2 text-center text-gray-500">
                      ... and {per_turn.length - 10} more turns
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
