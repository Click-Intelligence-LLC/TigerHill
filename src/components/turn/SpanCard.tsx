/**
 * SpanCard - Display a single response span with type-specific rendering
 */

import { useState } from 'react';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { ChevronDown, ChevronRight, Copy, Check } from 'lucide-react';
import type { ResponseSpan } from '@/types';

interface SpanCardProps {
  span: ResponseSpan;
  index: number;
  initiallyCollapsed?: boolean;
}

// Icon mapping for span types
const SPAN_ICONS: Record<string, string> = {
  text: '📝',
  thinking: '🧠',
  tool_call: '🔧',
  code_block: '💻',
  image: '🖼️',
  default: '📄',
};

// Label mapping for span types
const SPAN_LABELS: Record<string, string> = {
  text: 'Text',
  thinking: 'Thinking',
  tool_call: 'Tool Call',
  code_block: 'Code Block',
  image: 'Image',
};

export function SpanCard({ span, index, initiallyCollapsed = false }: SpanCardProps) {
  const [collapsed, setCollapsed] = useState(initiallyCollapsed);
  const [copied, setCopied] = useState(false);

  const icon = SPAN_ICONS[span.span_type] || SPAN_ICONS.default;
  const label = SPAN_LABELS[span.span_type] || span.span_type;

  const handleCopy = () => {
    const content = span.content || JSON.stringify(span.content_json, null, 2);
    navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // Render content based on span type
  const renderContent = () => {
    if (span.span_type === 'thinking' && span.content_json) {
      return (
        <pre className="overflow-x-auto rounded bg-gray-900 p-4 text-sm text-gray-100">
          {JSON.stringify(span.content_json, null, 2)}
        </pre>
      );
    }

    if (span.span_type === 'tool_call') {
      return (
        <div className="space-y-3">
          {span.tool_name && (
            <div className="flex items-center gap-2">
              <Badge variant="info" className="font-mono">
                {span.tool_name}
              </Badge>
            </div>
          )}

          {span.tool_input && (
            <div>
              <h4 className="mb-2 text-xs font-semibold uppercase tracking-wider text-gray-500">
                Input
              </h4>
              <pre className="overflow-x-auto rounded bg-gray-50 p-3 text-xs text-gray-700">
                {JSON.stringify(span.tool_input, null, 2)}
              </pre>
            </div>
          )}

          {span.tool_output && (
            <div>
              <h4 className="mb-2 text-xs font-semibold uppercase tracking-wider text-gray-500">
                Output
              </h4>
              <pre className="overflow-x-auto rounded bg-gray-50 p-3 text-xs text-gray-700">
                {JSON.stringify(span.tool_output, null, 2)}
              </pre>
            </div>
          )}
        </div>
      );
    }

    if (span.span_type === 'code_block' && span.language) {
      return (
        <div>
          <div className="mb-2 flex items-center justify-between rounded-t bg-gray-800 px-3 py-1">
            <Badge variant="outline" className="border-gray-600 text-gray-300">
              {span.language}
            </Badge>
          </div>
          <pre className="overflow-x-auto rounded-b bg-gray-900 p-4 text-sm text-gray-100 font-mono">
            {span.content}
          </pre>
        </div>
      );
    }

    // Default text rendering
    return (
      <div className="prose prose-sm max-w-none">
        <div className="whitespace-pre-wrap text-sm text-gray-700">{span.content}</div>
      </div>
    );
  };

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
          <span className="font-medium text-gray-900">
            {label} #{index + 1}
          </span>
        </button>

        <div className="flex items-center gap-2">
          {span.token_count !== undefined && (
            <Badge variant="outline" className="font-mono text-xs">
              {span.token_count.toLocaleString()} tokens
            </Badge>
          )}
          <Button
            size="sm"
            variant="ghost"
            leftIcon={copied ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
            onClick={(e) => {
              e.stopPropagation();
              handleCopy();
            }}
            className="text-gray-500 hover:text-gray-700"
          >
            {copied ? 'Copied' : 'Copy'}
          </Button>
        </div>
      </div>

      {/* Content */}
      {!collapsed && (
        <div className="px-4 py-3">
          {renderContent()}

          {span.metadata && Object.keys(span.metadata).length > 0 && (
            <details className="mt-3">
              <summary className="cursor-pointer text-xs text-gray-500">
                Metadata
              </summary>
              <pre className="mt-2 overflow-x-auto rounded bg-gray-50 p-2 text-xs text-gray-600">
                {JSON.stringify(span.metadata, null, 2)}
              </pre>
            </details>
          )}
        </div>
      )}
    </div>
  );
}
