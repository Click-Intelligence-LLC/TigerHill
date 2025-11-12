/**
 * ComponentCard - Display a single prompt component
 */

import { useState } from 'react';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { ChevronDown, ChevronRight, Edit2 } from 'lucide-react';
import type { PromptComponent } from '@/types';

interface ComponentCardProps {
  component: PromptComponent;
  onEdit?: (component: PromptComponent) => void;
  initiallyCollapsed?: boolean;
}

// Icon mapping for component types
const COMPONENT_ICONS: Record<string, string> = {
  environment: '🌍',
  conversation_history: '💬',
  user: '👤',
  system: '⚙️',
  tool_definition: '🔧',
  context: '📋',
  instruction: '📝',
  default: '📄',
};

// Label mapping for component types
const COMPONENT_LABELS: Record<string, string> = {
  environment: 'Environment',
  conversation_history: 'Conversation History',
  user: 'User Input',
  system: 'System Instruction',
  tool_definition: 'Tool Definition',
  context: 'Context',
  instruction: 'Instruction',
};

export function ComponentCard({
  component,
  onEdit,
  initiallyCollapsed = true,
}: ComponentCardProps) {
  const [collapsed, setCollapsed] = useState(initiallyCollapsed);

  const icon = COMPONENT_ICONS[component.component_type] || COMPONENT_ICONS.default;
  const label = COMPONENT_LABELS[component.component_type] || component.component_type;

  // For long content, show only first few lines when collapsed
  const contentPreview = component.content
    ? component.content.split('\n').slice(0, 3).join('\n')
    : '';
  const hasMoreContent = component.content && component.content.split('\n').length > 3;

  return (
    <div className="rounded-lg border border-gray-200 bg-white shadow-sm">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-gray-100 px-4 py-3">
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="flex items-center gap-3 flex-1 text-left transition-colors hover:text-blue-600"
        >
          {collapsed ? (
            <ChevronRight className="h-4 w-4 flex-shrink-0" />
          ) : (
            <ChevronDown className="h-4 w-4 flex-shrink-0" />
          )}
          <span className="text-lg">{icon}</span>
          <span className="font-medium text-gray-900">{label}</span>
        </button>

        <div className="flex items-center gap-2">
          {component.token_count !== undefined && (
            <Badge variant="outline" className="font-mono text-xs">
              {component.token_count.toLocaleString()} tokens
            </Badge>
          )}
          {onEdit && (
            <Button
              size="sm"
              variant="ghost"
              leftIcon={<Edit2 className="h-3 w-3" />}
              onClick={(e) => {
                e.stopPropagation();
                onEdit(component);
              }}
              className="text-gray-500 hover:text-gray-700"
            >
              Edit
            </Button>
          )}
        </div>
      </div>

      {/* Content */}
      {!collapsed && (
        <div className="px-4 py-3">
          {component.content_json ? (
            <pre className="overflow-x-auto rounded bg-gray-50 p-3 text-xs text-gray-700">
              {JSON.stringify(component.content_json, null, 2)}
            </pre>
          ) : component.content ? (
            <div className="prose prose-sm max-w-none">
              <pre className="whitespace-pre-wrap text-sm text-gray-700 font-mono">
                {component.content}
              </pre>
            </div>
          ) : (
            <p className="text-sm italic text-gray-400">No content</p>
          )}

          {component.metadata && Object.keys(component.metadata).length > 0 && (
            <details className="mt-3">
              <summary className="cursor-pointer text-xs text-gray-500">
                Metadata
              </summary>
              <pre className="mt-2 overflow-x-auto rounded bg-gray-50 p-2 text-xs text-gray-600">
                {JSON.stringify(component.metadata, null, 2)}
              </pre>
            </details>
          )}
        </div>
      )}

      {/* Collapsed Preview */}
      {collapsed && hasMoreContent && (
        <div className="px-4 py-2 bg-gray-50 border-t border-gray-100">
          <p className="text-xs text-gray-500 line-clamp-2 font-mono">
            {contentPreview}...
          </p>
        </div>
      )}
    </div>
  );
}
