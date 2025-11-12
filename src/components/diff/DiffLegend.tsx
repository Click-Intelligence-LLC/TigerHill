export const DiffLegend = () => (
  <div className="flex flex-wrap items-center gap-4 text-xs text-text-muted">
    <span className="inline-flex items-center gap-1">
      <span className="h-3 w-3 rounded bg-status-success/30" />
      新增
    </span>
    <span className="inline-flex items-center gap-1">
      <span className="h-3 w-3 rounded bg-status-danger/30" />
      删除
    </span>
    <span className="inline-flex items-center gap-1">
      <span className="h-3 w-3 rounded bg-border" />
      未变化
    </span>
  </div>
);
