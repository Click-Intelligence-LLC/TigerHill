/**
 * AgentDebugger - 极简风格的 Agent 调试界面
 */

import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useSessionV3, useSessionInteractions } from '@/hooks/useSessionV3';
import { TurnDetail } from '@/components/debugger/TurnDetail';

export default function AgentDebuggerPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [selectedTurn, setSelectedTurn] = useState<number>(0);

  // 获取 session 和 interactions
  const sessionQuery = useSessionV3(id);
  const interactionsQuery = useSessionInteractions(id, { limit: 500 });

  if (sessionQuery.isLoading || interactionsQuery.isLoading) {
    return (
      <div className="flex h-screen items-center justify-center bg-white">
        <div className="text-gray-500">加载中...</div>
      </div>
    );
  }

  // 容错处理：即使没有完整数据也尝试显示
  const session = sessionQuery.data || {
    id: id || 'unknown',
    title: '未知 Session',
    start_time: null,
    end_time: null,
    status: 'unknown',
  };
  const interactions = interactionsQuery.data?.interactions || [];

  // 显示错误信息但不阻止页面渲染
  const hasError = sessionQuery.error || interactionsQuery.error;

  // 按 turn 分组
  const turnMap = new Map<number, { request: any; response: any }>();
  interactions.forEach((interaction) => {
    const turn = interaction.turn_number;
    if (!turnMap.has(turn)) {
      turnMap.set(turn, { request: null, response: null });
    }
    const turnData = turnMap.get(turn)!;
    if (interaction.type === 'request') {
      turnData.request = interaction;
    } else if (interaction.type === 'response') {
      turnData.response = interaction;
    }
  });

  const turns = Array.from(turnMap.entries())
    .sort(([a], [b]) => a - b)  // Numeric sort works for both integers and floats
    .map(([turnNumber, turnData]) => ({ turnNumber, ...turnData }));

  // Helper to format turn number for display
  const formatTurnNumber = (turn: number): string => {
    // Check if it's a whole number
    if (Number.isInteger(turn)) {
      return turn.toString();
    }
    // It's a fractional turn (e.g., 13.01 → "13.1", 13.10 → "13.10")
    // Show up to 2 decimal places, removing trailing zeros unless needed
    const formatted = turn.toFixed(2);
    const parts = formatted.split('.');
    const decimal = parts[1].replace(/0+$/, '');  // Remove trailing zeros
    return decimal ? `${parts[0]}.${decimal}` : parts[0];
  };

  return (
    <div className="flex h-screen bg-white font-sans">
      {/* 顶部栏 */}
      <div className="fixed left-0 right-0 top-0 z-10 border-b border-gray-200 bg-white">
        <div className="flex items-center justify-between px-6 py-3">
          <div className="flex items-center gap-4">
            <h1 className="text-lg font-medium text-gray-900">TigerHill Agent Debugger</h1>
            <span className="text-sm text-gray-500">
              Session: {session.title || session.id.slice(0, 12)}...
            </span>
          </div>
          <button
            onClick={() => navigate('/session')}
            className="text-sm text-gray-500 hover:text-gray-900"
          >
            ✕
          </button>
        </div>
        {/* 错误提示条 */}
        {hasError && (
          <div className="border-t border-yellow-200 bg-yellow-50 px-6 py-2">
            <p className="text-sm text-yellow-800">
              ⚠ 数据加载出现问题，显示可能不完整
              {sessionQuery.error && ` (Session: ${sessionQuery.error.message})`}
              {interactionsQuery.error && ` (Interactions: ${interactionsQuery.error.message})`}
            </p>
          </div>
        )}
      </div>

      {/* 主内容区 */}
      <div className={`flex w-full ${hasError ? 'mt-24' : 'mt-14'}`}>
        {/* 左侧 Turn 列表 */}
        <aside className="w-48 flex-shrink-0 border-r border-gray-200 bg-white overflow-y-auto">
          <div className="p-4">
            <h2 className="mb-3 text-xs font-medium uppercase tracking-wide text-gray-500">
              Turns ({turns.length})
            </h2>
            <div className="space-y-1">
              {turns.map(({ turnNumber, request, response }) => {
                // Check if this is a non-LLM interaction
                const isNonLLM = request?.metadata?.is_llm_interaction === false ||
                                 response?.metadata?.is_llm_interaction === false;

                return (
                  <button
                    key={turnNumber}
                    onClick={() => setSelectedTurn(turnNumber)}
                    className={`
                      block w-full px-3 py-2 text-left text-sm transition-colors
                      ${
                        selectedTurn === turnNumber
                          ? 'bg-blue-50 font-medium text-blue-900'
                          : isNonLLM
                          ? 'text-gray-400 hover:bg-gray-50'
                          : 'text-gray-700 hover:bg-gray-50'
                      }
                    `}
                  >
                    <div className="flex items-center gap-1">
                      <span>Turn {formatTurnNumber(turnNumber)}</span>
                      {isNonLLM && (
                        <span className="text-xs text-gray-400" title="Non-LLM system request">⚙️</span>
                      )}
                    </div>
                    {request?.request_id && (
                      <div className="mt-1 text-xs text-gray-400 font-mono" title={request.request_id}>
                        {request.request_id.slice(0, 8)}...
                      </div>
                    )}
                    {response?.total_tokens && (
                      <div className="mt-1 text-xs text-gray-500">
                        {response.total_tokens.toLocaleString()} tokens
                      </div>
                    )}
                  </button>
                );
              })}
            </div>
          </div>
        </aside>

        {/* 右侧 Turn 详情 */}
        <main className="flex-1 overflow-y-auto bg-white p-8">
          {turns.length === 0 ? (
            <div className="py-20 text-center text-gray-500">
              暂无数据
            </div>
          ) : (
            <TurnDetail
              key={selectedTurn}
              turnNumber={selectedTurn}
              requestInteraction={
                turns.find((t) => t.turnNumber === selectedTurn)?.request
              }
              responseInteraction={
                turns.find((t) => t.turnNumber === selectedTurn)?.response
              }
            />
          )}
        </main>
      </div>
    </div>
  );
}
