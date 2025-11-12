/**
 * SessionList - 极简的 Session 列表页面（作为应用首页）
 */

import { useNavigate } from 'react-router-dom';
import { useSessionsV3 } from '@/hooks/useSessionV3';

export default function SessionListPage() {
  const navigate = useNavigate();
  const { data, isLoading, error } = useSessionsV3({ limit: 50 });

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center bg-white">
        <div className="text-gray-500">加载中...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex h-screen items-center justify-center bg-white">
        <div className="text-red-600">
          加载失败: {error instanceof Error ? error.message : '未知错误'}
        </div>
      </div>
    );
  }

  const sessions = data?.sessions || [];

  return (
    <div className="min-h-screen bg-white font-sans">
      {/* 顶部栏 */}
      <div className="border-b border-gray-200 bg-white">
        <div className="mx-auto max-w-6xl px-6 py-4">
          <h1 className="text-xl font-medium text-gray-900">TigerHill Agent Debugger</h1>
          <p className="mt-1 text-sm text-gray-500">
            检查和编辑 LLM 交互的捕获数据
          </p>
        </div>
      </div>

      {/* 主内容 */}
      <div className="mx-auto max-w-6xl px-6 py-8">
        {sessions.length === 0 ? (
          <div className="rounded-lg border-2 border-dashed border-gray-300 bg-gray-50 px-6 py-12 text-center">
            <div className="text-lg text-gray-600">暂无 Session 数据</div>
            <p className="mt-2 text-sm text-gray-500">
              请使用 Import 脚本导入捕获的 JSON 文件
            </p>
            <div className="mt-4 rounded bg-blue-50 px-4 py-3 text-left text-xs text-gray-700">
              <strong>使用方法：</strong>
              <pre className="mt-2 font-mono">
                POST /api/import/v3/json-files
              </pre>
              <p className="mt-2">
                或运行导入脚本处理本地 JSON 文件
              </p>
            </div>
          </div>
        ) : (
          <div>
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-lg font-medium text-gray-900">
                Sessions ({sessions.length})
              </h2>
            </div>

            {/* Session 列表 */}
            <div className="space-y-3">
              {sessions.map((session) => (
                <button
                  key={session.id}
                  onClick={() => navigate(`/debugger/${session.id}`)}
                  className="block w-full rounded-lg border border-gray-200 bg-white px-6 py-4 text-left transition-all hover:border-blue-300 hover:bg-blue-50 hover:shadow-sm"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <h3 className="font-medium text-gray-900">
                        {session.title || session.id.slice(0, 12) + '...'}
                      </h3>
                      <div className="mt-2 flex items-center gap-4 text-sm text-gray-600">
                        <span>
                          <strong className="text-gray-700">Turns:</strong> {session.total_turns}
                        </span>
                        <span>
                          <strong className="text-gray-700">Interactions:</strong>{' '}
                          {session.total_interactions}
                        </span>
                        {session.primary_model && (
                          <span>
                            <strong className="text-gray-700">Model:</strong> {session.primary_model}
                          </span>
                        )}
                      </div>
                      <div className="mt-1 text-xs text-gray-500">
                        {new Date(session.start_time).toLocaleString('zh-CN', {
                          year: 'numeric',
                          month: '2-digit',
                          day: '2-digit',
                          hour: '2-digit',
                          minute: '2-digit',
                          second: '2-digit',
                        })}
                      </div>
                    </div>
                    <div className="ml-4 text-sm text-blue-600">→</div>
                  </div>
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
