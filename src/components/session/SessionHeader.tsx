import { Card, CardContent } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import type { Session } from "@/types";
import { formatDate, formatDuration } from "@/utils";
import { ClipboardCopy } from "lucide-react";
import { toast } from "sonner";

interface SessionHeaderProps {
  session: Session;
}

export const SessionHeader = ({ session }: SessionHeaderProps) => {
  const handleCopy = async () => {
    await navigator.clipboard.writeText(session.id);
    toast.success("Session ID 已复制");
  };

  return (
    <Card>
      <CardContent className="grid gap-6 pt-6 md:grid-cols-4">
        <div className="space-y-1">
          <p className="text-xs uppercase tracking-wide text-text-muted">
            Session ID
          </p>
          <div className="flex items-center gap-2">
            <span className="font-mono text-sm text-text">{session.id}</span>
            <Button
              variant="ghost"
              size="icon"
              aria-label="Copy session id"
              onClick={handleCopy}
            >
              <ClipboardCopy className="h-4 w-4" />
            </Button>
          </div>
        </div>
        <div className="space-y-1">
          <p className="text-xs uppercase tracking-wide text-text-muted">
            模型 / Provider
          </p>
          <div className="flex items-center gap-2">
            <Badge variant="outline">{session.model ?? "未知模型"}</Badge>
            {session.primary_provider && (
              <Badge variant="outline" className="text-text-muted">
                {session.primary_provider}
              </Badge>
            )}
          </div>
        </div>
        <div className="space-y-1">
          <p className="text-xs uppercase tracking-wide text-text-muted">
            状态 / 轮数
          </p>
          <div className="flex items-center gap-2 text-sm">
            <Badge variant="outline">{session.status}</Badge>
            <span className="text-text-muted">
              {session.total_turns} turns
            </span>
          </div>
        </div>
        <div className="space-y-1">
          <p className="text-xs uppercase tracking-wide text-text-muted">
            时间
          </p>
          <div className="text-sm text-text">
            {formatDate(session.start_time)}
            {session.duration_seconds ? (
              <span className="text-text-muted">
                {" "}
                · {formatDuration(session.duration_seconds)}
              </span>
            ) : null}
          </div>
        </div>
      </CardContent>
    </Card>
  );
};
