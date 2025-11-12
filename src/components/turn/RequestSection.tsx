/**
 * RequestSection - Container for request components and parameters
 */

import { Badge } from '@/components/ui/Badge';
import { ComponentCard } from './ComponentCard';
import { ParametersCard } from './ParametersCard';
import type { PromptComponent } from '@/types';

interface RequestSectionProps {
  components: PromptComponent[];
  parameters?: {
    model?: string;
    temperature?: number;
    max_tokens?: number;
    top_p?: number;
    top_k?: number;
  };
  totalTokens?: number;
  onEditComponent?: (component: PromptComponent) => void;
}

export function RequestSection({
  components,
  parameters,
  totalTokens,
  onEditComponent,
}: RequestSectionProps) {
  return (
    <div className="space-y-4">
      {/* Section Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold uppercase tracking-wider text-gray-600">
          Request
        </h3>
        {totalTokens !== undefined && (
          <Badge variant="outline" className="font-mono">
            Total: {totalTokens.toLocaleString()} tokens
          </Badge>
        )}
      </div>

      {/* Parameters Card */}
      {parameters && <ParametersCard parameters={parameters} />}

      {/* Components */}
      <div className="space-y-3">
        {components.length === 0 ? (
          <div className="rounded-lg border-2 border-dashed border-gray-300 p-6 text-center">
            <p className="text-sm text-gray-400">No request components</p>
          </div>
        ) : (
          components
            .sort((a, b) => a.order_index - b.order_index)
            .map((component) => (
              <ComponentCard
                key={component.id}
                component={component}
                onEdit={onEditComponent}
                initiallyCollapsed={component.component_type !== 'user'}
              />
            ))
        )}
      </div>
    </div>
  );
}
