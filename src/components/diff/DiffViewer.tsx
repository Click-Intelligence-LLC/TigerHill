import { useMemo, useState } from "react";
import { Button } from "@/components/ui/Button";
import { DiffLegend } from "./DiffLegend";
import { cn } from "@/lib/utils";

interface DiffViewerProps {
  diffLines: string[];
}

type Mode = "unified" | "split";

interface HighlightSegment {
  text: string;
  changed: boolean;
}

interface DiffLine {
  prefix: string;
  content: string;
  highlights?: HighlightSegment[];
  variant: "added" | "removed" | "context" | "meta";
}

type DiffEntry =
  | { kind: "line"; line: DiffLine }
  | { kind: "pair"; removed: DiffLine; added: DiffLine };

const tokenize = (text: string) => text.match(/[\p{L}\p{N}_-]+|\s+|[^\s\p{L}\p{N}_-]+/gu) ?? [text];

const buildHighlights = (removed: string, added: string) => {
  const sourceTokens = tokenize(removed);
  const targetTokens = tokenize(added);
  const rows = sourceTokens.length;
  const cols = targetTokens.length;
  const dp = Array.from({ length: rows + 1 }, () => Array(cols + 1).fill(0));

  for (let i = rows - 1; i >= 0; i -= 1) {
    for (let j = cols - 1; j >= 0; j -= 1) {
      if (sourceTokens[i] === targetTokens[j]) {
        dp[i][j] = dp[i + 1][j + 1] + 1;
      } else {
        dp[i][j] = Math.max(dp[i + 1][j], dp[i][j + 1]);
      }
    }
  }

  let i = 0;
  let j = 0;
  const matches: Array<{ a: number; b: number }> = [];
  while (i < rows && j < cols) {
    if (sourceTokens[i] === targetTokens[j]) {
      matches.push({ a: i, b: j });
      i += 1;
      j += 1;
    } else if (dp[i + 1][j] >= dp[i][j + 1]) {
      i += 1;
    } else {
      j += 1;
    }
  }

  const buildSegments = (tokens: string[], matchedIndices: number[]) => {
    const segments: HighlightSegment[] = [];
    let cursor = 0;

    matchedIndices.forEach((matchIndex) => {
      if (matchIndex > cursor) {
        segments.push({
          text: tokens.slice(cursor, matchIndex).join(""),
          changed: true,
        });
      }
      segments.push({ text: tokens[matchIndex], changed: false });
      cursor = matchIndex + 1;
    });

    if (cursor < tokens.length) {
      segments.push({
        text: tokens.slice(cursor).join(""),
        changed: true,
      });
    }

    return segments.filter((segment) => segment.text.length > 0);
  };

  const removedSegments = buildSegments(
    sourceTokens,
    matches.map((match) => match.a),
  );
  const addedSegments = buildSegments(
    targetTokens,
    matches.map((match) => match.b),
  );

  return { removedSegments, addedSegments };
};

const parseDiffEntries = (diffLines: string[]): DiffEntry[] => {
  const entries: DiffEntry[] = [];
  for (let index = 0; index < diffLines.length; index += 1) {
    const line = diffLines[index];
    if (line.startsWith("-") && diffLines[index + 1]?.startsWith("+")) {
      const removed = line.slice(1);
      const added = diffLines[index + 1].slice(1);
      const { removedSegments, addedSegments } = buildHighlights(removed, added);
      entries.push({
        kind: "pair",
        removed: {
          prefix: "-",
          content: removed,
          highlights: removedSegments,
          variant: "removed",
        },
        added: {
          prefix: "+",
          content: added,
          highlights: addedSegments,
          variant: "added",
        },
      });
      index += 1;
      continue;
    }

    if (line.startsWith("-") || line.startsWith("+") || line.startsWith(" ")) {
      entries.push({
        kind: "line",
        line: {
          prefix: line.slice(0, 1),
          content: line.slice(1),
          variant: line.startsWith("+")
            ? "added"
            : line.startsWith("-")
              ? "removed"
              : "context",
        },
      });
      continue;
    }

    entries.push({
      kind: "line",
      line: {
        prefix: "@",
        content: line,
        variant: "meta",
      },
    });
  }
  return entries;
};

const renderContent = (line: DiffLine) => {
  if (!line.highlights) return line.content || " ";
  return line.highlights.map((segment, index) => (
    <span
      key={`${segment.text}-${index}`}
      className={segment.changed ? "bg-status-warning/20 text-status-warning" : undefined}
    >
      {segment.text}
    </span>
  ));
};

const lineClass = (variant: DiffLine["variant"]) => {
  if (variant === "added") {
    return "bg-status-success/15 text-status-success";
  }
  if (variant === "removed") {
    return "bg-status-danger/15 text-status-danger";
  }
  if (variant === "meta") {
    return "text-status-warning";
  }
  return "text-text";
};

export const DiffViewer = ({ diffLines }: DiffViewerProps) => {
  const [mode, setMode] = useState<Mode>("unified");
  const entries = useMemo(() => parseDiffEntries(diffLines), [diffLines]);

  if (!entries.length) {
    return <div className="text-sm text-text-muted">没有更多差异。</div>;
  }

  const splitRows = entries;

  const unifiedView = (
    <div className="max-h-[32rem] overflow-auto rounded-2xl bg-background-subtle/70 p-4 font-mono text-sm">
      {entries.map((entry, idx) => {
        if (entry.kind === "pair") {
          return (
            <div key={`pair-${idx}`} className="space-y-1">
              {["removed", "added"].map((key) => {
                const line = entry[key as "removed" | "added"];
                return (
                  <div
                    key={`${key}-${idx}`}
                    className={cn(
                      "flex gap-2 rounded-xl px-3 py-1",
                      lineClass(line.variant),
                    )}
                  >
                    <span className="select-none text-text-muted">{line.prefix}</span>
                    <span className="flex-1 whitespace-pre-wrap">{renderContent(line)}</span>
                  </div>
                );
              })}
            </div>
          );
        }

        return (
          <div
            key={`${entry.line.prefix}-${idx}`}
            className={cn(
              "flex gap-2 rounded-xl px-3 py-1",
              lineClass(entry.line.variant),
            )}
          >
            <span className="select-none text-text-muted">{entry.line.prefix}</span>
            <span className="flex-1 whitespace-pre-wrap">{renderContent(entry.line)}</span>
          </div>
        );
      })}
    </div>
  );

  const splitView = (
    <div className="grid max-h-[32rem] grid-cols-2 gap-3 overflow-auto rounded-2xl bg-background-subtle/70 p-4 text-sm">
      {splitRows.map((entry, idx) => {
        if (entry.kind === "line") {
          return (
            <div key={`single-${idx}`} className="col-span-2">
              <div
                className={cn(
                  "flex gap-2 rounded-xl px-3 py-1 font-mono",
                  lineClass(entry.line.variant),
                )}
              >
                <span className="select-none text-text-muted">{entry.line.prefix}</span>
                <span className="flex-1 whitespace-pre-wrap">{renderContent(entry.line)}</span>
              </div>
            </div>
          );
        }

        return (
          <div key={`pair-${idx}`} className="contents font-mono">
            <div
              className={cn(
                "rounded-xl px-3 py-1",
                lineClass(entry.removed.variant),
              )}
            >
              <span className="select-none text-text-muted">{entry.removed.prefix}</span>{" "}
              <span className="whitespace-pre-wrap">{renderContent(entry.removed)}</span>
            </div>
            <div
              className={cn(
                "rounded-xl px-3 py-1",
                lineClass(entry.added.variant),
              )}
            >
              <span className="select-none text-text-muted">{entry.added.prefix}</span>{" "}
              <span className="whitespace-pre-wrap">{renderContent(entry.added)}</span>
            </div>
          </div>
        );
      })}
    </div>
  );

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <DiffLegend />
        <div className="flex gap-2">
          <Button
            variant={mode === "unified" ? "primary" : "outline"}
            size="sm"
            onClick={() => setMode("unified")}
          >
            合并视图
          </Button>
          <Button
            variant={mode === "split" ? "primary" : "outline"}
            size="sm"
            onClick={() => setMode("split")}
          >
            对照视图
          </Button>
        </div>
      </div>
      {mode === "unified" ? unifiedView : splitView}
    </div>
  );
};
