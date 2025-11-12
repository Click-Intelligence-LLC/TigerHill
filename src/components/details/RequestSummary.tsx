import { Card, CardContent } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import type { RequestResponse } from "@/types";
import { ClipboardCopy } from "lucide-react";
import { toast } from "sonner";

interface RequestSummaryProps {
  request: RequestResponse;
  index: number;
  total: number;
  onPrev: () => void;
  onNext: () => void;
}

export const RequestSummary = ({
  request,
  index,
  total,
  onPrev,
  onNext,
}: RequestSummaryProps) => {
  const handleCopy = async () => {
    await navigator.clipboard.writeText(request.id);
    toast.success("Request ID 已复制");
  };

  return (
    <Card>
      <CardContent className="flex flex-wrap items-center justify-between gap-4 pt-6">
        <div className="flex flex-col gap-1">
          <p className="text-xs uppercase tracking-wide text-text-muted">请求 ID</p>
          <div className="flex items-center gap-2 font-mono text-sm text-text">
            {request.id}
            <Button variant="ghost" size="icon" onClick={handleCopy}>
              <ClipboardCopy className="h-4 w-4" />
            </Button>
          </div>
        </div>
        <div className="flex flex-col gap-1">
          <p className="text-xs uppercase tracking-wide text-text-muted">方法 & URL</p>
          <Badge variant="outline">
            {request.method} {request.url}
          </Badge>
        </div>
        <div className="flex flex-col gap-1">
          <p className="text-xs uppercase tracking-wide text-text-muted">状态码</p>
          <Badge variant={request.status_code && request.status_code >= 400 ? "danger" : "success"}>
            {request.status_code ?? "—"}
          </Badge>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={onPrev} disabled={index === 0}>
            上一条
          </Button>
          <Badge variant="outline">
            {index + 1}/{total}
          </Badge>
          <Button
            variant="outline"
            size="sm"
            onClick={onNext}
            disabled={index >= total - 1}
          >
            下一条
          </Button>
        </div>
      </CardContent>
    </Card>
  );
};
