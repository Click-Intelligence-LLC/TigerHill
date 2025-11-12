/**
 * ResponseSection - Container for response spans and metrics
 */

import { Badge } from '@/components/ui/Badge';
import { SpanCard } from './SpanCard';
import { MetricsCard } from './MetricsCard';
import { CheckCircle, XCircle, Clock } from 'lucide-react';
import type { ResponseSpan } from '@/types';

interface ResponseSectionProps {
  spans: ResponseSpan[];
  metrics?: {
    input_tokens?: number;
    output_tokens?: number;
    total_tokens?: number;
    duration_ms?: number;
    estimated_cost_usd?: number;
    is_success?: boolean;
    error_type?: string;
    error_message?: string;
    status_code?: number;
  };
}

export function ResponseSection({ spans, metrics }: ResponseSectionProps) {
  const isSuccess = metrics?.is_success !== false;

  return (
    <div className="space-y-4">
      {/* Section Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h3 className="text-sm font-semibold uppercase tracking-wider text-gray-600">
            Response
          </h3>

          {/* Status Badge */}
          {metrics?.is_success !== undefined && (
            <Badge
              variant={isSuccess ? 'default' : 'destructive'}
              className={`flex items-center gap-1 ${isSuccess ? 'bg-green-100 text-green-800 border-green-200' : 'bg-red-100 text-red-800 border-red-200'}`}
            >
              {isSuccess ? (
                <>
                  <CheckCircle className="h-3 w-3" />
                  <span>Success</span>
                </>
              ) : (
                <>
                  <XCircle className="h-3 w-3" />
                  <span>Error</span>
                </>
              )}
            </Badge>
          )}

          {/* Duration */}
          {metrics?.duration_ms !== undefined && (
            <Badge variant="outline" className="flex items-center gap-1 font-mono">
              <Clock className="h-3 w-3" />
              <span>{(metrics.duration_ms / 1000).toFixed(2)}s</span>
            </Badge>
          )}
        </div>
      </div>

      {/* Error Message */}
      {!isSuccess && metrics?.error_message && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4">
          <div className="flex items-start gap-3">
            <XCircle className="h-5 w-5 flex-shrink-0 text-red-600" />
            <div className="flex-1">
              <h4 className="font-medium text-red-900">
                {metrics.error_type || 'Error'}
              </h4>
              <p className="mt-1 text-sm text-red-700">{metrics.error_message}</p>
              {metrics.status_code && (
                <p className="mt-1 text-xs text-red-600">
                  Status Code: {metrics.status_code}
                </p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Metrics Card */}
      {metrics && <MetricsCard metrics={metrics} />}

      {/* Spans */}
      <div className="space-y-3">
        {spans.length === 0 ? (
          <div className="rounded-lg border-2 border-dashed border-gray-300 p-6 text-center">
            <p className="text-sm text-gray-400">No response spans</p>
          </div>
        ) : (
          spans
            .sort((a, b) => a.order_index - b.order_index)
            .map((span, index) => (
              <SpanCard
                key={span.id}
                span={span}
                index={index}
                initiallyCollapsed={span.span_type === 'thinking'}
              />
            ))
        )}
      </div>
    </div>
  );
}
