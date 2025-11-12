/**
 * ParametersCard - Display model configuration parameters
 */

import { Settings } from 'lucide-react';

interface ParametersCardProps {
  parameters: {
    model?: string;
    temperature?: number;
    max_tokens?: number;
    top_p?: number;
    top_k?: number;
    [key: string]: any;
  };
}

export function ParametersCard({ parameters }: ParametersCardProps) {
  const displayParams = [
    { key: 'model', label: 'Model', value: parameters.model },
    { key: 'temperature', label: 'Temperature', value: parameters.temperature },
    { key: 'max_tokens', label: 'Max Tokens', value: parameters.max_tokens },
    { key: 'top_p', label: 'Top P', value: parameters.top_p },
    { key: 'top_k', label: 'Top K', value: parameters.top_k },
  ].filter((p) => p.value !== undefined && p.value !== null);

  if (displayParams.length === 0) {
    return null;
  }

  return (
    <div className="rounded-lg border border-gray-200 bg-white shadow-sm">
      {/* Header */}
      <div className="flex items-center gap-2 border-b border-gray-100 px-4 py-3">
        <Settings className="h-4 w-4 text-gray-500" />
        <span className="font-medium text-gray-900">Parameters</span>
      </div>

      {/* Parameter Grid */}
      <div className="grid grid-cols-2 gap-3 p-4 sm:grid-cols-3 lg:grid-cols-5">
        {displayParams.map(({ key, label, value }) => (
          <div key={key} className="space-y-1">
            <dt className="text-xs font-medium text-gray-500">{label}</dt>
            <dd className="text-sm font-mono text-gray-900">
              {typeof value === 'number' ? value.toString() : value}
            </dd>
          </div>
        ))}
      </div>

      {/* Additional parameters */}
      {Object.keys(parameters).length > 5 && (
        <details className="border-t border-gray-100 px-4 py-2">
          <summary className="cursor-pointer text-xs text-gray-500">
            {Object.keys(parameters).length - 5} more parameters
          </summary>
          <pre className="mt-2 overflow-x-auto rounded bg-gray-50 p-2 text-xs text-gray-600">
            {JSON.stringify(
              Object.fromEntries(
                Object.entries(parameters).filter(
                  ([key]) => !['model', 'temperature', 'max_tokens', 'top_p', 'top_k'].includes(key)
                )
              ),
              null,
              2
            )}
          </pre>
        </details>
      )}
    </div>
  );
}
