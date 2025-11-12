/**
 * TurnDetail - 极简风格显示 Turn 详情
 */

import { useState } from 'react';
import { useTurnDetail } from '@/hooks/useTurnDetail';
import { useComponentEditor } from '@/hooks/useComponentEditor';
import { apiClient } from '@/lib/api';
import type { PromptComponent, ResponseSpan } from '@/types';

interface TurnDetailProps {
  turnNumber: number;
  requestInteraction?: any;
  responseInteraction?: any;
}

export function TurnDetail({
  turnNumber,
  requestInteraction,
  responseInteraction,
}: TurnDetailProps) {
  const { components, spans, isLoading, error } = useTurnDetail(
    requestInteraction?.id,
    responseInteraction?.id
  );

  // 编辑状态管理
  const editor = useComponentEditor();

  // Helper to format turn number for display
  const formatTurnNumber = (turn: number): string => {
    if (Number.isInteger(turn)) {
      return turn.toString();
    }
    return turn.toFixed(2).replace(/\.?0+$/, "");  // Show up to 2 decimals, remove trailing zeros
  };

  // 重放状态
  const [replayResult, setReplayResult] = useState<any>(null);
  const [isReplaying, setIsReplaying] = useState(false);
  const [replayError, setReplayError] = useState<string | null>(null);

  if (isLoading) {
    return <div className="text-gray-500">加载中...</div>;
  }

  // 容错：即使有错误也显示基本信息
  const hasDataError = error !== null;

  // 处理重放
  const handleReplay = async () => {
    if (!requestInteraction?.id) {
      setReplayError('缺少 request interaction ID');
      return;
    }

    setIsReplaying(true);
    setReplayError(null);

    try {
      const result = await apiClient.replayRequest(
        requestInteraction.id,
        editor.getAllEdits(),
        editor.editedConfig  // 传递配置修改
      );
      setReplayResult(result);
    } catch (err) {
      setReplayError(err instanceof Error ? err.message : '重放请求失败');
    } finally {
      setIsReplaying(false);
    }
  };

  // Check if this is a non-LLM interaction
  const isNonLLM = requestInteraction?.metadata?.is_llm_interaction === false ||
                   responseInteraction?.metadata?.is_llm_interaction === false;

  return (
    <div className="max-w-4xl space-y-8">
      {/* Turn 标题 */}
      <div>
        <h1 className="text-2xl font-medium text-gray-900">Turn {formatTurnNumber(turnNumber)}</h1>
        {requestInteraction?.request_id && (
          <div className="mt-2 text-xs text-gray-500">
            <span className="mr-2">Request ID:</span>
            <code className="rounded bg-gray-100 px-2 py-1 font-mono text-gray-700">
              {requestInteraction.request_id}
            </code>
          </div>
        )}
        {hasDataError && (
          <div className="mt-2 rounded border border-yellow-200 bg-yellow-50 px-3 py-2">
            <p className="text-sm text-yellow-800">
              ⚠ 详细数据加载失败，仅显示基本信息
            </p>
          </div>
        )}
        {isNonLLM && (
          <div className="mt-2 rounded border border-gray-200 bg-gray-50 px-3 py-2">
            <p className="text-sm text-gray-600">
              <span className="mr-1">⚙️</span>
              <strong>非 LLM 交互</strong> - 这是系统级别的内部请求（如 Code Assist 初始化），不是实际的大模型对话
            </p>
          </div>
        )}
      </div>

      {/* REQUEST 部分 */}
      <section>
        <h2 className="mb-4 border-b border-gray-300 pb-2 text-sm font-medium uppercase tracking-wide text-gray-500">
          Request
        </h2>

        {/* Parameters - Editable */}
        {requestInteraction && (
          <div className="mb-6 space-y-3 border-l-2 border-blue-200 bg-blue-50 pl-4 py-3 pr-4">
            <div className="text-xs font-medium uppercase tracking-wide text-gray-600">
              配置参数 <span className="text-gray-400">（可编辑）</span>
            </div>

            {/* Endpoint */}
            <div className="space-y-1">
              <label className="text-xs text-gray-600">Endpoint:</label>
              <input
                type="text"
                value={editor.getConfigValue('endpoint', requestInteraction.url || '')}
                onChange={(e) => editor.updateConfig('endpoint', e.target.value)}
                className="w-full rounded border border-gray-300 bg-white px-2 py-1 font-mono text-xs text-gray-900 focus:border-blue-400 focus:outline-none"
                placeholder="https://..."
              />
            </div>

            <div className="grid grid-cols-3 gap-3">
              {/* Model */}
              <div className="space-y-1">
                <label className="text-xs text-gray-600">Model:</label>
                <input
                  type="text"
                  value={editor.getConfigValue('model', requestInteraction.model || '')}
                  onChange={(e) => editor.updateConfig('model', e.target.value)}
                  className="w-full rounded border border-gray-300 bg-white px-2 py-1 font-mono text-xs text-gray-900 focus:border-blue-400 focus:outline-none"
                />
              </div>

              {/* Temperature */}
              <div className="space-y-1">
                <label className="text-xs text-gray-600">Temperature:</label>
                <input
                  type="number"
                  step="0.1"
                  min="0"
                  max="2"
                  value={editor.getConfigValue('temperature', requestInteraction.temperature ?? 0)}
                  onChange={(e) => editor.updateConfig('temperature', parseFloat(e.target.value))}
                  className="w-full rounded border border-gray-300 bg-white px-2 py-1 font-mono text-xs text-gray-900 focus:border-blue-400 focus:outline-none"
                />
              </div>

              {/* Max Tokens */}
              <div className="space-y-1">
                <label className="text-xs text-gray-600">Max Tokens:</label>
                <input
                  type="number"
                  value={editor.getConfigValue('max_tokens', requestInteraction.max_tokens || '')}
                  onChange={(e) => editor.updateConfig('max_tokens', parseInt(e.target.value) || undefined)}
                  className="w-full rounded border border-gray-300 bg-white px-2 py-1 font-mono text-xs text-gray-900 focus:border-blue-400 focus:outline-none"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              {/* Top P */}
              <div className="space-y-1">
                <label className="text-xs text-gray-600">Top P:</label>
                <input
                  type="number"
                  step="0.1"
                  min="0"
                  max="1"
                  value={editor.getConfigValue('top_p', requestInteraction.top_p ?? 1.0)}
                  onChange={(e) => editor.updateConfig('top_p', parseFloat(e.target.value))}
                  className="w-full rounded border border-gray-300 bg-white px-2 py-1 font-mono text-xs text-gray-900 focus:border-blue-400 focus:outline-none"
                />
              </div>

              {/* Top K */}
              <div className="space-y-1">
                <label className="text-xs text-gray-600">Top K:</label>
                <input
                  type="number"
                  value={editor.getConfigValue('top_k', requestInteraction.top_k ?? '')}
                  onChange={(e) => editor.updateConfig('top_k', e.target.value ? parseInt(e.target.value) : null)}
                  className="w-full rounded border border-gray-300 bg-white px-2 py-1 font-mono text-xs text-gray-900 focus:border-blue-400 focus:outline-none"
                  placeholder="(空)"
                />
              </div>
            </div>

            {editor.hasConfigEdits && (
              <div className="text-xs text-blue-600">
                ✓ 配置已修改，点击"重放"应用更改
              </div>
            )}
          </div>
        )}


        {/* Components */}
        <div className="space-y-4">
          {components.length === 0 ? (
            <div className="rounded border border-gray-200 bg-gray-50 px-4 py-6 text-center">
              <p className="text-sm text-gray-500">
                {hasDataError ? '数据加载失败' : '暂无 prompt 组件数据'}
              </p>
              {!hasDataError && requestInteraction && (
                <p className="mt-1 text-xs text-gray-400">
                  这可能是因为数据尚未被解析和导入
                </p>
              )}
            </div>
          ) : (
            components
              .sort((a, b) => (a.order_index || 0) - (b.order_index || 0))
              .map((component) => {
                try {
                  return (
                    <ComponentItem
                      key={component.id}
                      component={component}
                      editor={editor}
                    />
                  );
                } catch (err) {
                  console.error('Error rendering component:', component, err);
                  return (
                    <div key={component.id} className="rounded border border-red-200 bg-red-50 p-3 text-sm text-red-700">
                      ✗ 组件渲染错误: {err instanceof Error ? err.message : String(err)}
                    </div>
                  );
                }
              })
          )}
        </div>

        {/* 操作按钮 */}
        {(components.length > 0 || requestInteraction) && (
          <div className="mt-6 flex items-center gap-3">
            <button
              onClick={handleReplay}
              disabled={!editor.hasAnyEdits || isReplaying}
              className="border border-blue-300 bg-blue-50 px-4 py-2 text-sm text-blue-700 hover:bg-blue-100 disabled:border-gray-200 disabled:bg-gray-50 disabled:text-gray-400"
            >
              {isReplaying ? '重放中...' : '重放'}
            </button>
            <button
              onClick={editor.resetAll}
              disabled={!editor.hasAnyEdits || isReplaying}
              className="border border-gray-300 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 disabled:border-gray-200 disabled:text-gray-400"
            >
              重置修改
            </button>
            {editor.hasAnyEdits && (
              <span className="text-sm text-gray-500">
                {editor.hasConfigEdits && `已修改配置参数`}
                {editor.hasConfigEdits && editor.getAllEdits().length > 0 && `, `}
                {editor.getAllEdits().length > 0 && `已修改 ${editor.getAllEdits().length} 个组件`}
              </span>
            )}
            {replayError && (
              <span className="text-sm text-red-600">
                ✗ {replayError}
              </span>
            )}
          </div>
        )}
      </section>

      {/* RESPONSE 部分 */}
      <section>
        <h2 className="mb-4 border-b border-gray-300 pb-2 text-sm font-medium uppercase tracking-wide text-gray-500">
          Response
        </h2>

        {/* 重放结果显示 */}
        {replayResult && (
          <div className="mb-6 rounded border-2 border-green-300 bg-green-50 p-4">
            <div className="mb-2 flex items-center gap-2">
              <span className="text-lg">✓</span>
              <h3 className="font-medium text-green-900">重放成功</h3>
              {replayResult.is_mock && (
                <span className="rounded bg-yellow-100 px-2 py-0.5 text-xs text-yellow-800">
                  Mock数据
                </span>
              )}
            </div>
            <div className="space-y-2 text-sm text-green-800">
              <p>{replayResult.message}</p>
              {replayResult.mock_response_data && (
                <div className="mt-3 rounded border border-green-200 bg-white p-3">
                  <div className="text-xs text-gray-500 mb-1">模拟响应内容：</div>
                  <pre className="whitespace-pre-wrap font-mono text-sm text-gray-700">
                    {replayResult.mock_response_data.content}
                  </pre>
                  <div className="mt-2 flex gap-4 text-xs text-gray-500">
                    <span>Tokens: {replayResult.mock_response_data.total_tokens}</span>
                    <span>Duration: {replayResult.mock_response_data.duration_ms}ms</span>
                  </div>
                </div>
              )}
            </div>
            <button
              onClick={() => setReplayResult(null)}
              className="mt-3 text-xs text-green-700 hover:underline"
            >
              关闭
            </button>
          </div>
        )}

        {/* Metrics */}
        {responseInteraction && (
          <div className="mb-6 flex items-center gap-6 border-l-2 border-gray-200 pl-4 text-sm">
            <div>
              <span className={responseInteraction.is_success === false ? 'text-red-600' : 'text-green-600'}>
                {responseInteraction.is_success === false ? '✗ Error' : '✓ Success'}
              </span>
            </div>
            {responseInteraction.duration_ms && (
              <div>
                <span className="text-gray-500">Duration:</span>{' '}
                <span className="font-mono">{(responseInteraction.duration_ms / 1000).toFixed(2)}s</span>
              </div>
            )}
            {responseInteraction.total_tokens && (
              <div>
                <span className="text-gray-500">Tokens:</span>{' '}
                <span className="font-mono">{responseInteraction.total_tokens.toLocaleString()}</span>
              </div>
            )}
            {responseInteraction.estimated_cost_usd !== undefined && (
              <div>
                <span className="text-gray-500">Cost:</span>{' '}
                <span className="font-mono">${responseInteraction.estimated_cost_usd.toFixed(4)}</span>
              </div>
            )}
          </div>
        )}

        {/* Error Message */}
        {responseInteraction?.is_success === false && responseInteraction.error_message && (
          <div className="mb-6 border-l-4 border-red-500 bg-red-50 p-4">
            <div className="font-medium text-red-900">{responseInteraction.error_type || 'Error'}</div>
            <div className="mt-1 text-sm text-red-700">{responseInteraction.error_message}</div>
          </div>
        )}

        {/* Spans */}
        <div className="space-y-4">
          {spans.length === 0 ? (
            <div className="rounded border border-gray-200 bg-gray-50 px-4 py-6 text-center">
              <p className="text-sm text-gray-500">
                {hasDataError ? '数据加载失败' : '暂无 response span 数据'}
              </p>
              {!hasDataError && responseInteraction && (
                <p className="mt-1 text-xs text-gray-400">
                  这可能是因为数据尚未被解析和导入
                </p>
              )}
            </div>
          ) : (
            spans
              .sort((a, b) => (a.order_index || 0) - (b.order_index || 0))
              .map((span, index) => {
                try {
                  return <SpanItem key={span.id} span={span} index={index} />;
                } catch (err) {
                  console.error('Error rendering span:', span, err);
                  return (
                    <div key={span.id} className="rounded border border-red-200 bg-red-50 p-3 text-sm text-red-700">
                      ✗ Span渲染错误: {err instanceof Error ? err.message : String(err)}
                    </div>
                  );
                }
              })
          )}
        </div>
      </section>
    </div>
  );
}

// Component Item - 极简显示单个 component
function ComponentItem({
  component,
  editor,
}: {
  component: PromptComponent;
  editor: ReturnType<typeof useComponentEditor>;
}) {
  const [isEditing, setIsEditing] = useState(false);
  const [editValue, setEditValue] = useState('');

  const typeLabels: Record<string, string> = {
    environment: 'Environment',
    conversation_history: 'Conversation History',
    user: 'User Input',
    system: 'System Instruction',
    assistant: 'Assistant Message',
    tool_definition: 'Tool Definition',
    tool_definitions: 'Tool Definitions',
    tool_result: 'Tool Result',
    tool_call: 'Tool Call',
    example: 'Example',
    context: 'Context',
    instruction: 'Instruction',
    function: 'Function',
    functions: 'Functions',
  };

  const label = typeLabels[component.component_type] || component.component_type;
  const currentValue = editor.getComponentValue(component);
  const isModified = editor.isEdited(component.id);

  const handleEdit = () => {
    // 进入编辑模式，初始化编辑值
    const initialValue = component.content_json
      ? JSON.stringify(component.content_json, null, 2)
      : component.content || '';
    setEditValue(initialValue);
    setIsEditing(true);
  };

  const handleSave = () => {
    // 保存编辑
    if (component.content_json) {
      try {
        const parsed = JSON.parse(editValue);
        editor.saveEdit(component.id, null, parsed);
      } catch (e) {
        alert('JSON 格式错误，请检查');
        return;
      }
    } else {
      editor.saveEdit(component.id, editValue, null);
    }
    setIsEditing(false);
  };

  const handleCancel = () => {
    setIsEditing(false);
    setEditValue('');
  };

  return (
    <div className={`border-l-2 pl-4 ${isModified ? 'border-blue-400' : 'border-gray-200'}`}>
      <div className="mb-2 flex items-baseline justify-between">
        <div className="flex items-center gap-2">
          <h3 className="font-medium text-gray-900">{label}</h3>
          {isModified && (
            <span className="rounded bg-blue-100 px-2 py-0.5 text-xs text-blue-700">
              已修改
            </span>
          )}
        </div>
        {component.token_count != null && (
          <span className="text-xs text-gray-500">{component.token_count.toLocaleString()} tokens</span>
        )}
      </div>

      {isEditing ? (
        // 编辑模式
        <div className="space-y-2">
          <textarea
            value={editValue}
            onChange={(e) => setEditValue(e.target.value)}
            className="w-full rounded border border-gray-300 p-3 font-mono text-sm text-gray-700 focus:border-blue-400 focus:outline-none"
            rows={component.content_json ? 10 : 5}
            placeholder="输入内容..."
          />
          <div className="flex gap-2">
            <button
              onClick={handleSave}
              className="border border-blue-300 bg-blue-50 px-3 py-1 text-sm text-blue-700 hover:bg-blue-100"
            >
              保存
            </button>
            <button
              onClick={handleCancel}
              className="border border-gray-300 px-3 py-1 text-sm text-gray-700 hover:bg-gray-50"
            >
              取消
            </button>
          </div>
        </div>
      ) : (
        // 显示模式
        <>
          {/* Conversation History 特殊显示 */}
          {component.component_type === 'conversation_history' && currentValue.content_json && Array.isArray(currentValue.content_json) ? (
            <div className="space-y-2">
              {currentValue.content_json.map((item: any, idx: number) => (
                <div key={idx} className="rounded border border-gray-200 bg-gray-50 p-3">
                  <div className="mb-1 text-xs font-medium text-gray-500">
                    {item.role === 'assistant' ? '🤖 Assistant' : '👤 User'}
                  </div>
                  {item.type === 'text' ? (
                    <div className="text-sm text-gray-700">
                      {typeof item.content === 'string' ? item.content : JSON.stringify(item.content)}
                    </div>
                  ) : item.type === 'function_call' ? (
                    <div className="text-xs font-mono text-gray-600">
                      🔧 Function Call: {item.content?.name || 'unknown'}
                    </div>
                  ) : (
                    <pre className="text-xs font-mono text-gray-600">
                      {JSON.stringify(item.content, null, 2)}
                    </pre>
                  )}
                </div>
              ))}
              <div className="text-xs text-gray-500">
                {currentValue.content_json.length} message(s) in history
              </div>
            </div>
          ) : currentValue.content_json ? (
            <pre className="overflow-x-auto bg-gray-50 p-3 text-xs font-mono text-gray-700">
              {JSON.stringify(currentValue.content_json, null, 2)}
            </pre>
          ) : currentValue.content ? (
            <div className="whitespace-pre-wrap text-sm text-gray-700">
              {currentValue.content.length > 500
                ? currentValue.content.slice(0, 500) + '...'
                : currentValue.content}
            </div>
          ) : (
            <div className="text-sm italic text-gray-400">无内容</div>
          )}

          <div className="mt-2">
            <button
              onClick={handleEdit}
              className="text-xs text-blue-600 hover:underline"
            >
              编辑
            </button>
          </div>
        </>
      )}
    </div>
  );
}

// Span Item - 极简显示单个 span
function SpanItem({ span, index }: { span: ResponseSpan; index: number }) {
  const typeLabels: Record<string, string> = {
    text: 'Text',
    thinking: 'Thinking',
    tool_call: 'Tool Call',
    code_block: 'Code Block',
    usage_metadata: 'Usage & Cost',
    safety_rating: 'Safety Rating',
    function_call: 'Function Call',
    function_response: 'Function Response',
    error: 'Error',
  };

  const label = typeLabels[span.span_type] || span.span_type;

  return (
    <div className="border-l-2 border-gray-200 pl-4">
      <div className="mb-2 flex items-baseline justify-between">
        <h3 className="font-medium text-gray-900">
          {label} #{index + 1}
        </h3>
        {span.token_count != null && (
          <span className="text-xs text-gray-500">{span.token_count.toLocaleString()} tokens</span>
        )}
      </div>

      {/* Tool Call 特殊显示 */}
      {span.span_type === 'tool_call' && (
        <div className="space-y-3">
          {span.tool_name && (
            <div className="text-sm">
              <span className="text-gray-500">Tool:</span>{' '}
              <span className="font-mono">{span.tool_name}</span>
            </div>
          )}
          {span.tool_input && (
            <div>
              <div className="mb-1 text-xs text-gray-500">Input</div>
              <pre className="overflow-x-auto bg-gray-50 p-3 text-xs font-mono text-gray-700">
                {JSON.stringify(span.tool_input, null, 2)}
              </pre>
            </div>
          )}
          {span.tool_output && (
            <div>
              <div className="mb-1 text-xs text-gray-500">Output</div>
              <pre className="overflow-x-auto bg-gray-50 p-3 text-xs font-mono text-gray-700">
                {JSON.stringify(span.tool_output, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}

      {/* Usage Metadata 特殊显示 */}
      {span.span_type === 'usage_metadata' && span.content_json && (
        <div className="rounded border border-blue-200 bg-blue-50 p-3">
          <div className="grid grid-cols-3 gap-4 text-sm">
            {span.content_json.prompt_tokens != null && (
              <div>
                <div className="text-xs text-blue-600">Prompt Tokens</div>
                <div className="font-mono font-medium text-blue-900">
                  {span.content_json.prompt_tokens.toLocaleString()}
                </div>
              </div>
            )}
            {span.content_json.completion_tokens != null && (
              <div>
                <div className="text-xs text-blue-600">Completion Tokens</div>
                <div className="font-mono font-medium text-blue-900">
                  {span.content_json.completion_tokens.toLocaleString()}
                </div>
              </div>
            )}
            {span.content_json.total_tokens != null && (
              <div>
                <div className="text-xs text-blue-600">Total Tokens</div>
                <div className="font-mono font-medium text-blue-900">
                  {span.content_json.total_tokens.toLocaleString()}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Safety Rating 特殊显示 */}
      {span.span_type === 'safety_rating' && span.content_json && (
        <div className="rounded border border-yellow-200 bg-yellow-50 p-3">
          <div className="space-y-1 text-sm">
            {span.content_json.category && (
              <div>
                <span className="text-yellow-600">Category:</span>{' '}
                <span className="font-mono text-yellow-900">
                  {span.content_json.category}
                </span>
              </div>
            )}
            {span.content_json.probability && (
              <div>
                <span className="text-yellow-600">Probability:</span>{' '}
                <span className="font-mono font-medium text-yellow-900">
                  {span.content_json.probability}
                </span>
              </div>
            )}
            {span.content_json.blocked && (
              <div className="mt-2 rounded bg-red-100 px-2 py-1 text-xs font-medium text-red-800">
                ⚠ Content Blocked
              </div>
            )}
          </div>
        </div>
      )}

      {/* Thinking 显示为 JSON */}
      {span.span_type === 'thinking' && span.content_json && (
        <pre className="overflow-x-auto bg-gray-900 p-3 text-xs font-mono text-gray-100">
          {JSON.stringify(span.content_json, null, 2)}
        </pre>
      )}

      {/* Code Block */}
      {span.span_type === 'code_block' && (
        <div>
          {span.language && (
            <div className="mb-1 bg-gray-800 px-2 py-1 text-xs text-gray-300">
              {span.language}
            </div>
          )}
          <pre className="overflow-x-auto bg-gray-900 p-3 text-sm font-mono text-gray-100">
            {span.content}
          </pre>
        </div>
      )}

      {/* 普通文本 */}
      {span.span_type === 'text' && span.content && (
        <div className="whitespace-pre-wrap text-sm text-gray-700">
          {span.content}
        </div>
      )}

      {/* 其他类型或无内容 */}
      {!['tool_call', 'usage_metadata', 'safety_rating', 'thinking', 'code_block', 'text'].includes(span.span_type) && (
        <div>
          {span.content_json ? (
            <pre className="overflow-x-auto bg-gray-50 p-3 text-xs font-mono text-gray-700">
              {JSON.stringify(span.content_json, null, 2)}
            </pre>
          ) : span.content ? (
            <div className="whitespace-pre-wrap text-sm text-gray-700">
              {span.content}
            </div>
          ) : (
            <div className="text-sm italic text-gray-400">无内容</div>
          )}
        </div>
      )}

      <div className="mt-2">
        <button className="text-xs text-blue-600 hover:underline">复制</button>
      </div>
    </div>
  );
}
