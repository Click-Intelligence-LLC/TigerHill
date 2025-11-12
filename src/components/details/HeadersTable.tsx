import type { RequestResponse } from "@/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";

interface HeadersTableProps {
  request: RequestResponse;
  showSensitive: boolean;
}

const SENSITIVE_KEYS = ["authorization", "api-key", "x-api-key"];

export const HeadersTable = ({ request, showSensitive }: HeadersTableProps) => {
  const headers = request.request_headers || {};
  const responseHeaders = request.response_headers || {};

  const mask = (key: string, value: any) => {
    if (showSensitive) return value;
    return SENSITIVE_KEYS.includes(key.toLowerCase()) ? "•••• (已隐藏)" : value;
  };

  const renderRows = (entries: Record<string, any>) =>
    Object.entries(entries).map(([key, value]) => (
      <tr key={key} className="border-b border-border">
        <td className="px-3 py-2 font-mono text-xs text-text-muted">{key}</td>
        <td className="px-3 py-2 text-sm text-text">{mask(key, value)}</td>
      </tr>
    ));

  return (
    <div className="grid gap-4 md:grid-cols-2">
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">请求头</CardTitle>
        </CardHeader>
        <CardContent className="max-h-72 overflow-auto p-0">
          <table className="w-full text-left">
            <tbody>{renderRows(headers)}</tbody>
          </table>
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">响应头</CardTitle>
        </CardHeader>
        <CardContent className="max-h-72 overflow-auto p-0">
          <table className="w-full text-left">
            <tbody>{renderRows(responseHeaders)}</tbody>
          </table>
        </CardContent>
      </Card>
    </div>
  );
};
