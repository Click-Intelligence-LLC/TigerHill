import * as React from "react";
import { cn } from "@/lib/utils";
import { colorTokens } from "@/styles/design-tokens";

export interface TokenData {
  turnNumber: number;
  inputTokens: {
    total: number;
    system?: number;
    history?: number;
    context?: number;
    toolCall?: number;
    user?: number;
  };
  outputTokens: number;
}

export interface TokenBreakdownChartProps {
  data: TokenData[];
  className?: string;
  maxHeight?: number; // in pixels
}

/**
 * Token Breakdown Chart matching stitch "模型交互可视化" design
 * Shows stacked bar chart with color-coded prompt components
 */
export const TokenBreakdownChart: React.FC<TokenBreakdownChartProps> = ({
  data,
  className,
  maxHeight = 192, // 12rem = 192px
}) => {
  if (!data || data.length === 0) {
    return null;
  }

  // Find max total tokens for scaling
  const maxTotal = Math.max(
    ...data.map((d) => d.inputTokens.total + d.outputTokens),
  );

  return (
    <div className={cn("flex flex-col gap-4", className)}>
      {/* Chart Container */}
      <div
        className="grid items-end gap-x-4"
        style={{
          gridTemplateColumns: `repeat(${data.length}, 1fr)`,
          gridTemplateRows: `${maxHeight}px auto`,
          minHeight: `${maxHeight + 32}px`,
        }}
      >
        {/* Bars */}
        {data.map((turn) => {
          const totalTokens = turn.inputTokens.total + turn.outputTokens;
          const heightPercent = (totalTokens / maxTotal) * 100;

          // Calculate heights for input token segments
          const inputTotal = turn.inputTokens.total;
          const systemHeight = ((turn.inputTokens.system || 0) / inputTotal) * 100;
          const historyHeight = ((turn.inputTokens.history || 0) / inputTotal) * 100;
          const contextHeight = ((turn.inputTokens.context || 0) / inputTotal) * 100;
          const toolCallHeight = ((turn.inputTokens.toolCall || 0) / inputTotal) * 100;
          const userHeight = ((turn.inputTokens.user || 0) / inputTotal) * 100;

          // Calculate heights relative to total bar
          const inputPercent = (inputTotal / totalTokens) * 100;
          const outputPercent = (turn.outputTokens / totalTokens) * 100;

          return (
            <React.Fragment key={turn.turnNumber}>
              {/* Stacked Bar */}
              <div
                className="flex flex-col overflow-hidden rounded-t-lg"
                style={{ height: `${heightPercent}%` }}
              >
                {/* Input Tokens (stacked segments) */}
                <div
                  className="flex flex-col"
                  style={{ height: `${inputPercent}%` }}
                >
                  {turn.inputTokens.system ? (
                    <div
                      className="w-full"
                      style={{
                        height: `${systemHeight}%`,
                        backgroundColor: colorTokens.prompt.system,
                      }}
                      title={`System: ${turn.inputTokens.system} tokens`}
                    />
                  ) : null}
                  {turn.inputTokens.history ? (
                    <div
                      className="w-full"
                      style={{
                        height: `${historyHeight}%`,
                        backgroundColor: colorTokens.prompt.history,
                      }}
                      title={`History: ${turn.inputTokens.history} tokens`}
                    />
                  ) : null}
                  {turn.inputTokens.context ? (
                    <div
                      className="w-full"
                      style={{
                        height: `${contextHeight}%`,
                        backgroundColor: colorTokens.prompt.context,
                      }}
                      title={`Context: ${turn.inputTokens.context} tokens`}
                    />
                  ) : null}
                  {turn.inputTokens.toolCall ? (
                    <div
                      className="w-full"
                      style={{
                        height: `${toolCallHeight}%`,
                        backgroundColor: colorTokens.prompt.toolCall,
                      }}
                      title={`Tool Call: ${turn.inputTokens.toolCall} tokens`}
                    />
                  ) : null}
                  {turn.inputTokens.user ? (
                    <div
                      className="w-full"
                      style={{
                        height: `${userHeight}%`,
                        backgroundColor: colorTokens.prompt.user,
                      }}
                      title={`User: ${turn.inputTokens.user} tokens`}
                    />
                  ) : null}
                </div>

                {/* Output Tokens */}
                <div
                  className="w-full"
                  style={{
                    height: `${outputPercent}%`,
                    backgroundColor: colorTokens.token.output,
                  }}
                  title={`Response: ${turn.outputTokens} tokens`}
                />
              </div>

              {/* Turn Label */}
              <p className="text-center text-xs font-medium text-gray-500 dark:text-gray-400">
                Turn {turn.turnNumber}
              </p>
            </React.Fragment>
          );
        })}
      </div>

      {/* Legend */}
      <div className="flex flex-col gap-3 pt-2">
        {/* Response */}
        <div className="flex items-center gap-2">
          <div
            className="h-3 w-3 rounded-sm"
            style={{ backgroundColor: colorTokens.token.output }}
          />
          <p className="text-sm text-gray-600 dark:text-gray-300">Response</p>
        </div>

        {/* Prompt Breakdown */}
        <div className="text-sm text-gray-600 dark:text-gray-300">
          Prompt Breakdown:
        </div>
        <div className="grid grid-cols-2 gap-x-4 gap-y-2 pl-5">
          <div className="flex items-center gap-2">
            <div
              className="h-3 w-3 rounded-sm"
              style={{ backgroundColor: colorTokens.prompt.system }}
            />
            <p className="text-sm text-gray-600 dark:text-gray-300">
              System Instruction
            </p>
          </div>
          <div className="flex items-center gap-2">
            <div
              className="h-3 w-3 rounded-sm"
              style={{ backgroundColor: colorTokens.prompt.history }}
            />
            <p className="text-sm text-gray-600 dark:text-gray-300">History</p>
          </div>
          <div className="flex items-center gap-2">
            <div
              className="h-3 w-3 rounded-sm"
              style={{ backgroundColor: colorTokens.prompt.context }}
            />
            <p className="text-sm text-gray-600 dark:text-gray-300">Context</p>
          </div>
          <div className="flex items-center gap-2">
            <div
              className="h-3 w-3 rounded-sm"
              style={{ backgroundColor: colorTokens.prompt.toolCall }}
            />
            <p className="text-sm text-gray-600 dark:text-gray-300">
              Tool Call
            </p>
          </div>
          <div className="flex items-center gap-2">
            <div
              className="h-3 w-3 rounded-sm"
              style={{ backgroundColor: colorTokens.prompt.user }}
            />
            <p className="text-sm text-gray-600 dark:text-gray-300">
              User Instruction
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

TokenBreakdownChart.displayName = "TokenBreakdownChart";

export default TokenBreakdownChart;
