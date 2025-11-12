import { IntentAnalysis, IntentUnit, IntentFlowAnalysis } from '@/types';
import { Brain, Target, TrendingUp, Hash } from 'lucide-react';

interface IntentAnalysisProps {
  analysis: IntentAnalysis;
}

interface IntentFlowAnalysisProps {
  flowAnalysis: IntentFlowAnalysis;
}

interface IntentUnitCardProps {
  unit: IntentUnit;
}

function IntentUnitCard({ unit }: IntentUnitCardProps) {
  const getIntentColor = (intentType: string) => {
    const colors: Record<string, string> = {
      'information_seeking': 'bg-blue-100 text-blue-800',
      'task_completion': 'bg-green-100 text-green-800',
      'creative_writing': 'bg-purple-100 text-purple-800',
      'analysis': 'bg-orange-100 text-orange-800',
      'clarification': 'bg-yellow-100 text-yellow-800',
      'default': 'bg-gray-100 text-gray-800'
    };
    return colors[intentType] || colors['default'];
  };

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow">
      <div className="flex items-center justify-between mb-2">
        <span className={`px-2 py-1 rounded-full text-xs font-medium ${getIntentColor(unit.intent_type)}`}>
          {unit.intent_type}
        </span>
        <div className="flex items-center text-sm text-gray-500">
          <Target className="h-3 w-3 mr-1" />
          {(unit.confidence * 100).toFixed(1)}%
        </div>
      </div>
      
      <div className="space-y-2">
        <div className="flex items-center justify-between text-sm">
          <span className="text-gray-600">复杂度:</span>
          <span className="font-medium">{unit.complexity_score.toFixed(2)}</span>
        </div>
        
        <div className="flex items-center justify-between text-sm">
          <span className="text-gray-600">Token数:</span>
          <span className="font-medium">{unit.tokens}</span>
        </div>
        
        <div className="flex items-center justify-between text-sm">
          <span className="text-gray-600">位置:</span>
          <span className="font-medium">{unit.start_pos}-{unit.end_pos}</span>
        </div>
      </div>
      
      {unit.metadata && Object.keys(unit.metadata).length > 0 && (
        <details className="mt-3">
          <summary className="text-xs text-gray-500 cursor-pointer hover:text-gray-700">
            元数据
          </summary>
          <pre className="mt-1 text-xs bg-gray-50 p-2 rounded overflow-x-auto">
            {JSON.stringify(unit.metadata, null, 2)}
          </pre>
        </details>
      )}
    </div>
  );
}

export function IntentAnalysisComponent({ analysis }: IntentAnalysisProps) {
  return (
    <div className="bg-white shadow rounded-lg">
      <div className="px-4 py-5 sm:p-6">
        <div className="flex items-center mb-4">
          <Brain className="h-6 w-6 text-blue-600 mr-2" />
          <h3 className="text-lg font-medium text-gray-900">意图分析</h3>
        </div>
        
        {/* 概览统计 */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <div className="text-center p-3 bg-blue-50 rounded-lg">
            <div className="flex items-center justify-center mb-1">
              <Target className="h-4 w-4 text-blue-600" />
            </div>
            <div className="text-lg font-bold text-blue-900">
              {analysis.primary_intent}
            </div>
            <div className="text-xs text-blue-700">主要意图</div>
          </div>
          
          <div className="text-center p-3 bg-green-50 rounded-lg">
            <div className="flex items-center justify-center mb-1">
              <TrendingUp className="h-4 w-4 text-green-600" />
            </div>
            <div className="text-lg font-bold text-green-900">
              {(analysis.confidence * 100).toFixed(1)}%
            </div>
            <div className="text-xs text-green-700">置信度</div>
          </div>
          
          <div className="text-center p-3 bg-orange-50 rounded-lg">
            <div className="text-lg font-bold text-orange-900">
              {analysis.complexity_score.toFixed(2)}
            </div>
            <div className="text-xs text-orange-700">复杂度</div>
          </div>
          
          <div className="text-center p-3 bg-purple-50 rounded-lg">
            <div className="flex items-center justify-center mb-1">
              <Hash className="h-4 w-4 text-purple-600" />
            </div>
            <div className="text-lg font-bold text-purple-900">
              {analysis.intent_units.length}
            </div>
            <div className="text-xs text-purple-700">意图单元数</div>
          </div>
        </div>
        
        {/* 意图单元列表 */}
        <div>
          <h4 className="text-md font-medium text-gray-900 mb-3">
            意图单元 ({analysis.intent_units.length})
          </h4>
          
          {analysis.intent_units.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {analysis.intent_units.map((unit, index) => (
                <IntentUnitCard key={unit.id || index} unit={unit} />
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-gray-500">
              <Brain className="h-12 w-12 mx-auto mb-2 text-gray-300" />
              <p>暂无意图单元数据</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export function IntentFlowAnalysisComponent({ flowAnalysis }: IntentFlowAnalysisProps) {
  const getTopTransitions = () => {
    const transitions: Array<{from: string, to: string, count: number}> = [];
    
    Object.entries(flowAnalysis.transition_matrix).forEach(([from_intent, to_intents]) => {
      Object.entries(to_intents).forEach(([to_intent, count]) => {
        if (count > 0) {
          transitions.push({ from: from_intent, to: to_intent, count });
        }
      });
    });
    
    return transitions.sort((a, b) => b.count - a.count).slice(0, 10);
  };

  const topTransitions = getTopTransitions();
  const totalTransitions = Object.values(flowAnalysis.transition_matrix)
    .flatMap(row => Object.values(row))
    .reduce((sum, count) => sum + count, 0);

  return (
    <div className="bg-white shadow rounded-lg">
      <div className="px-4 py-5 sm:p-6">
        <div className="flex items-center mb-4">
          <TrendingUp className="h-6 w-6 text-green-600 mr-2" />
          <h3 className="text-lg font-medium text-gray-900">意图流转分析</h3>
        </div>
        
        {/* 统计信息 */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          <div className="text-center p-3 bg-blue-50 rounded-lg">
            <div className="text-lg font-bold text-blue-900">
              {Object.keys(flowAnalysis.intent_distribution).length}
            </div>
            <div className="text-xs text-blue-700">意图类型数</div>
          </div>
          
          <div className="text-center p-3 bg-green-50 rounded-lg">
            <div className="text-lg font-bold text-green-900">
              {totalTransitions}
            </div>
            <div className="text-xs text-green-700">总流转次数</div>
          </div>
          
          <div className="text-center p-3 bg-purple-50 rounded-lg">
            <div className="text-lg font-bold text-purple-900">
              {flowAnalysis.transition_patterns.length}
            </div>
            <div className="text-xs text-purple-700">流转模式数</div>
          </div>
        </div>
        
        {/* 流转矩阵 */}
        <div className="mb-6">
          <h4 className="text-md font-medium text-gray-900 mb-3">意图流转矩阵</h4>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    从 \ 到
                  </th>
                  {Object.keys(flowAnalysis.transition_matrix).map(intent => (
                    <th key={intent} className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      {intent.slice(0, 8)}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {Object.entries(flowAnalysis.transition_matrix).map(([from_intent, to_intents]) => (
                  <tr key={from_intent}>
                    <td className="px-3 py-2 whitespace-nowrap text-sm font-medium text-gray-900">
                      {from_intent.slice(0, 8)}
                    </td>
                    {Object.entries(to_intents).map(([to_intent, count]) => (
                      <td key={to_intent} className="px-3 py-2 whitespace-nowrap text-sm text-gray-900 text-center">
                        <span className={`inline-block px-2 py-1 rounded text-xs ${
                          count > 5 ? 'bg-red-100 text-red-800' :
                          count > 2 ? 'bg-yellow-100 text-yellow-800' :
                          count > 0 ? 'bg-green-100 text-green-800' :
                          'bg-gray-100 text-gray-500'
                        }`}>
                          {count}
                        </span>
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
        
        {/* 热门流转 */}
        <div>
          <h4 className="text-md font-medium text-gray-900 mb-3">
            热门流转模式 (Top {topTransitions.length})
          </h4>
          <div className="space-y-2">
            {topTransitions.map((transition, index) => (
              <div key={`${transition.from}-${transition.to}`} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                <div className="flex items-center space-x-2">
                  <span className="text-sm font-medium text-gray-500">#{index + 1}</span>
                  <div className="flex items-center space-x-1">
                    <span className="px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded">
                      {transition.from}
                    </span>
                    <span className="text-gray-400">→</span>
                    <span className="px-2 py-1 bg-green-100 text-green-800 text-xs rounded">
                      {transition.to}
                    </span>
                  </div>
                </div>
                <div className="text-sm font-medium text-gray-900">
                  {transition.count} 次
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}