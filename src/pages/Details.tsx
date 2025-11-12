import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Spinner } from "@/components/ui/Spinner";
import { RequestSummary } from "@/components/details/RequestSummary";
import { HeadersTable } from "@/components/details/HeadersTable";
import { PayloadViewer } from "@/components/details/PayloadViewer";
import type { SessionDetailsResponse } from "@/types";
import { Breadcrumbs } from "@/components/navigation/Breadcrumbs";
import { Shield, AlertTriangle } from "lucide-react";

export default function DetailsPage() {
  const { id } = useParams<{ id: string }>();
  const [currentIndex, setCurrentIndex] = useState(0);
  const [showSensitive, setShowSensitive] = useState(false);
  const [showHeaders, setShowHeaders] = useState(true);

  const detailsQuery = useQuery<SessionDetailsResponse>({
    queryKey: ["session-details", id],
    queryFn: () => apiClient.getSessionDetails(id!),
    enabled: !!id,
  });

  const session = detailsQuery.data?.session;
  const requests = detailsQuery.data?.request_responses ?? [];

  useEffect(() => {
    if (currentIndex >= requests.length && requests.length > 0) {
      setCurrentIndex(0);
    }
  }, [currentIndex, requests.length]);

  const currentRequest = requests[currentIndex];

  const stats = useMemo(() => {
    if (!requests.length) {
      return {
        successCount: 0,
        averageLatency: 0,
        tokenUsage: { input: 0, output: 0 },
      };
    }

    const successCount = requests.filter(
      (request) => request.status_code && request.status_code < 400,
    ).length;
    const averageLatency = (() => {
      const latencies = requests.filter((item) => item.response_time_ms);
      if (!latencies.length) return 0;
      return (
        latencies.reduce((sum, item) => sum + (item.response_time_ms || 0), 0) /
        latencies.length
      );
    })();
    const tokenUsage = requests.reduce(
      (sum, request) => ({
        input: sum.input + (request.response?.input_tokens ?? 0),
        output: sum.output + (request.response?.output_tokens ?? 0),
      }),
      { input: 0, output: 0 },
    );
    return { successCount, averageLatency, tokenUsage };
  }, [requests]);

  if (detailsQuery.isLoading) {
    return (
      <div className="flex h-80 items-center justify-center">
        <Spinner />
      </div>
    );
  }

  if (!session || !requests.length || !currentRequest) {
    return (
      <Card>
        <CardContent className="py-10 text-center text-sm text-text-muted">
          暂无请求/响应数据
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <Breadcrumbs
        items={[
          { label: "Dashboard", href: "/" },
          { label: "会话总览", href: "/session" },
          { label: "请求详情" },
        ]}
      />

      <Card>
        <CardHeader>
          <CardTitle>概要</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-4">
          <SummaryTile label="总请求数" value={requests.length} />
          <SummaryTile label="成功请求" value={stats.successCount} accent="text-status-success" />
          <SummaryTile
            label="平均响应时间"
            value={`${Math.round(stats.averageLatency)}ms`}
            accent="text-status-warning"
          />
          <SummaryTile
            label="Token 使用"
            value={`输入 ${stats.tokenUsage.input} / 输出 ${stats.tokenUsage.output}`}
          />
        </CardContent>
      </Card>

      <div className="grid gap-4 lg:grid-cols-[280px,1fr]">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">请求列表</CardTitle>
          </CardHeader>
          <CardContent className="max-h-[32rem] space-y-2 overflow-auto">
            {requests.map((request, idx) => (
              <button
                key={request.id}
                className={`w-full rounded-2xl border px-3 py-2 text-left text-sm transition hover:border-brand ${
                  idx === currentIndex ? "border-brand bg-brand/5" : "border-border"
                }`}
                onClick={() => setCurrentIndex(idx)}
              >
                <div className="flex items-center justify-between text-xs text-text-muted">
                  <span>
                    #{idx + 1} {request.method}
                  </span>
                  <span>{request.status_code ?? "—"}</span>
                </div>
                <p className="truncate text-sm text-text">{request.url}</p>
              </button>
            ))}
          </CardContent>
        </Card>

        <div className="space-y-4">
          <RequestSummary
            request={currentRequest}
            index={currentIndex}
            total={requests.length}
            onPrev={() => setCurrentIndex((idx) => Math.max(0, idx - 1))}
            onNext={() => setCurrentIndex((idx) => Math.min(requests.length - 1, idx + 1))}
          />

          <Card>
            <CardHeader>
              <CardTitle className="text-sm">响应指标</CardTitle>
            </CardHeader>
            <CardContent className="grid gap-4 md:grid-cols-3">
              <Metric label="状态码" value={currentRequest.status_code ?? "—"} />
              <Metric label="响应时间" value={`${currentRequest.response_time_ms ?? 0}ms`} />
              <Metric
                label="Token 使用"
                value={`in ${currentRequest.response?.input_tokens ?? 0} / out ${
                  currentRequest.response?.output_tokens ?? 0
                }`}
              />
            </CardContent>
          </Card>

          <div className="rounded-2xl border border-status-warning/40 bg-status-warning/5 p-4 text-sm text-text">
            <div className="flex items-center gap-2">
              <Shield className="h-4 w-4 text-status-warning" />
              <span>敏感信息默认隐藏。启用后请注意不要泄露凭证。</span>
              <Button
                variant={showSensitive ? "destructive" : "outline"}
                size="sm"
                onClick={() => setShowSensitive((prev) => !prev)}
              >
                {showSensitive ? "隐藏敏感信息" : "显示敏感信息"}
              </Button>
            </div>
          </div>

          <div className="space-y-4">
            <Card>
              <CardHeader className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
                <CardTitle className="text-sm">请求/响应头</CardTitle>
                <Button variant="ghost" size="sm" onClick={() => setShowHeaders((prev) => !prev)}>
                  {showHeaders ? "收起" : "展开"}
                </Button>
              </CardHeader>
              {showHeaders && (
                <CardContent>
                  <HeadersTable request={currentRequest} showSensitive={showSensitive} />
                </CardContent>
              )}
            </Card>

            <PayloadViewer
              label="请求体"
              content={
                typeof currentRequest.request_body === "string"
                  ? currentRequest.request_body
                  : JSON.stringify(currentRequest.request_body ?? {}, null, 2)
              }
              filename={`request-${currentRequest.id}.json`}
            />
            <PayloadViewer
              label="响应体"
              content={
                typeof currentRequest.response_body === "string"
                  ? currentRequest.response_body
                  : JSON.stringify(currentRequest.response_body ?? {}, null, 2)
              }
              filename={`response-${currentRequest.id}.json`}
            />
          </div>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-sm text-status-warning">
            <AlertTriangle className="h-4 w-4" />
            大型负载提醒
          </CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-text-muted">
          超过 10K 字符的 payload 会自动截断，点击“展开更多”即可查看完整内容。
        </CardContent>
      </Card>
    </div>
  );
}

const SummaryTile = ({
  label,
  value,
  accent,
}: {
  label: string;
  value: string | number;
  accent?: string;
}) => (
  <div className="rounded-2xl border border-border bg-background-subtle/50 p-4">
    <p className="text-xs uppercase tracking-wide text-text-muted">{label}</p>
    <p className={`text-2xl font-semibold ${accent ?? "text-text"}`}>{value}</p>
  </div>
);

const Metric = ({
  label,
  value,
}: {
  label: string;
  value: string | number;
}) => (
  <div className="rounded-2xl border border-border bg-surface p-3">
    <p className="text-xs uppercase tracking-wide text-text-muted">{label}</p>
    <p className="text-lg font-semibold text-text">{value}</p>
  </div>
);
