import { Session } from "@/types";
import { Select } from "@/components/ui/Select";
import { Card, CardContent } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { formatDate } from "@/utils";

interface SessionSelectorProps {
  label: string;
  sessions: Session[];
  selectedSessionId: string;
  onSessionChange: (sessionId: string) => void;
}

export default function SessionSelector({
  label,
  sessions,
  selectedSessionId,
  onSessionChange,
}: SessionSelectorProps) {
  const selectedSession = sessions.find((session) => session.id === selectedSessionId);

  return (
    <Card className="border-border bg-surface">
      <CardContent className="space-y-4 pt-6">
        <Select
          label={label}
          value={selectedSessionId}
          onChange={(event) => onSessionChange(event.target.value)}
        >
          <option value="">请选择会话...</option>
          {sessions.map((session) => (
            <option key={session.id} value={session.id}>
              {session.title} · {session.model} ·{" "}
              {new Date(session.start_time).toLocaleString()}
            </option>
          ))}
        </Select>

        {selectedSession && (
          <div className="rounded-2xl border border-border bg-background-subtle/60 p-4">
            <div className="flex flex-col gap-1">
              <div className="flex items-center justify-between">
                <span className="text-base font-semibold text-text">
                  {selectedSession.title}
                </span>
                <Badge variant="outline">{selectedSession.model}</Badge>
              </div>
              <p className="text-sm text-text-muted">
                开始时间：{formatDate(selectedSession.start_time)}
              </p>
              <div className="text-sm text-text-muted">
                状态：{selectedSession.status} · 轮数：{selectedSession.total_turns}
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
