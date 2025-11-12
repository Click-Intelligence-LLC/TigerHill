/**
 * MetricsCard - Display response metrics (tokens, duration, cost)
 */

import { Coins, Clock, Hash, DollarSign } from 'lucide-react';

interface MetricsCardProps {
  metrics: {
    input_tokens?: number;
    output_tokens?: number;
    total_tokens?: number;
    duration_ms?: number;
    estimated_cost_usd?: number;
    is_success?: boolean;
  };
}

export function MetricsCard({ metrics }: MetricsCardProps) {
  const formatCost = (cost: number) => {
    if (cost < 0.001) return `$${(cost * 1000).toFixed(4)}`;
    return `$${cost.toFixed(4)}`;
  };

  const formatDuration = (ms: number) => {
    if (ms < 1000) return `${ms}ms`;
    if (ms < 60000) return `${(ms / 1000).toFixed(2)}s`;
    return `${(ms / 60000).toFixed(2)}m`;
  };

  const metricsData = [
    {
      icon: Hash,
      label: 'Input Tokens',
      value: metrics.input_tokens?.toLocaleString(),
      show: metrics.input_tokens !== undefined,
    },
    {
      icon: Hash,
      label: 'Output Tokens',
      value: metrics.output_tokens?.toLocaleString(),
      show: metrics.output_tokens !== undefined,
    },
    {
      icon: Coins,
      label: 'Total Tokens',
      value: metrics.total_tokens?.toLocaleString(),
      show: metrics.total_tokens !== undefined,
      highlight: true,
    },
    {
      icon: Clock,
      label: 'Duration',
      value: metrics.duration_ms !== undefined ? formatDuration(metrics.duration_ms) : undefined,
      show: metrics.duration_ms !== undefined,
    },
    {
      icon: DollarSign,
      label: 'Estimated Cost',
      value: metrics.estimated_cost_usd !== undefined ? formatCost(metrics.estimated_cost_usd) : undefined,
      show: metrics.estimated_cost_usd !== undefined,
    },
  ].filter((m) => m.show);

  if (metricsData.length === 0) {
    return null;
  }

  return (
    <div className="rounded-lg border border-gray-200 bg-gradient-to-br from-gray-50 to-white shadow-sm">
      <div className="grid grid-cols-2 gap-4 p-4 sm:grid-cols-3 lg:grid-cols-5">
        {metricsData.map(({ icon: Icon, label, value, highlight }) => (
          <div
            key={label}
            className={`space-y-2 ${highlight ? 'rounded-lg bg-blue-50/50 p-3 -m-1' : ''}`}
          >
            <div className="flex items-center gap-2">
              <Icon className={`h-4 w-4 ${highlight ? 'text-blue-600' : 'text-gray-400'}`} />
              <dt className="text-xs font-medium text-gray-600">{label}</dt>
            </div>
            <dd
              className={`text-base font-mono font-semibold ${
                highlight ? 'text-blue-900' : 'text-gray-900'
              }`}
            >
              {value}
            </dd>
          </div>
        ))}
      </div>
    </div>
  );
}
