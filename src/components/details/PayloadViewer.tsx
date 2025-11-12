import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { ClipboardCopy, Download, Search } from "lucide-react";
import { toast } from "sonner";

interface PayloadViewerProps {
  label: string;
  content?: string | null;
  filename: string;
}

export const PayloadViewer = ({ label, content, filename }: PayloadViewerProps) => {
  const [expanded, setExpanded] = useState(false);
  const [filter, setFilter] = useState("");

  const text = content ?? "（无内容）";
  const display = expanded ? text : text.slice(0, 2000);
  const filtered = filter
    ? display.replace(new RegExp(filter, "gi"), (match) => `<<${match}>>`)
    : display;

  const handleCopy = async () => {
    await navigator.clipboard.writeText(text);
    toast.success(`${label} 已复制`);
  };

  const handleDownload = () => {
    const blob = new Blob([text], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <Card>
      <CardHeader className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <CardTitle className="text-sm">{label}</CardTitle>
        <div className="flex flex-wrap gap-2">
          <div className="flex items-center gap-1 rounded-xl border border-border bg-surface px-2 py-1 text-xs">
            <Search className="h-4 w-4 text-text-muted" />
            <input
              value={filter}
              onChange={(event) => setFilter(event.target.value)}
              placeholder="搜索内容"
              className="bg-transparent text-sm focus:outline-none"
            />
          </div>
          <Button variant="outline" size="sm" onClick={handleCopy} leftIcon={<ClipboardCopy className="h-4 w-4" />}>
            复制
          </Button>
          <Button variant="outline" size="sm" onClick={handleDownload} leftIcon={<Download className="h-4 w-4" />}>
            下载
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        <pre className="max-h-80 overflow-auto rounded-2xl bg-background-subtle/70 p-4 text-xs text-text">
          {filtered}
        </pre>
        {text.length > 2000 && (
          <Button variant="ghost" size="sm" onClick={() => setExpanded((prev) => !prev)}>
            {expanded ? "收起" : "展开更多"}
          </Button>
        )}
      </CardContent>
    </Card>
  );
};
