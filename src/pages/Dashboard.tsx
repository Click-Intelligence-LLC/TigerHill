import { useEffect, useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { apiClient } from "@/lib/api";
import StatsCards from "@/components/StatsCards";
import SessionsTable from "@/components/SessionsTable";
import TrendChart from "@/components/TrendChart";
import ModelChart from "@/components/ModelChart";
import { ErrorBreakdownChart } from "@/components/ErrorBreakdownChart";
import DataImport from "@/components/DataImport";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Card, CardContent } from "@/components/ui/Card";
import { Spinner } from "@/components/ui/Spinner";
import { RefreshCw, Search, Upload } from "lucide-react";
import { useSessionStore } from "@/stores/sessionStore";
import { useFilterStore } from "@/stores/filterStore";
import type { SessionSort, SessionsResponse } from "@/types";

const statusOptions = [
  { label: "All Status", value: "" },
  { label: "Success", value: "success" },
  { label: "Error", value: "error" },
  { label: "Timeout", value: "timeout" },
  { label: "Cancelled", value: "cancelled" },
];

const providerOptions = [
  { label: "All Providers", value: "" },
  { label: "OpenAI", value: "openai" },
  { label: "Anthropic", value: "anthropic" },
  { label: "Gemini", value: "gemini" },
  { label: "Vertex", value: "vertex" },
  { label: "Azure", value: "azure" },
];

const sortOptions = [
  { label: "Newest First", value: "newest" },
  { label: "Oldest First", value: "oldest" },
  { label: "Longest Duration", value: "longest" },
  { label: "Shortest Duration", value: "shortest" },
];

export default function Dashboard() {
  const queryClient = useQueryClient();
  const [showImport, setShowImport] = useState(false);
  const sessions = useSessionStore((state) => state.sessions);
  const total = useSessionStore((state) => state.total);
  const page = useSessionStore((state) => state.page);
  const limit = useSessionStore((state) => state.limit);
  const sort = useSessionStore((state) => state.sort);
  const isLoading = useSessionStore((state) => state.isLoading);
  const error = useSessionStore((state) => state.error);
  const setSessions = useSessionStore((state) => state.setSessions);
  const setError = useSessionStore((state) => state.setError);
  const setLoading = useSessionStore((state) => state.setLoading);
  const setPage = useSessionStore((state) => state.setPage);
  const setLimit = useSessionStore((state) => state.setLimit);
  const setSort = useSessionStore((state) => state.setSort);

  const modelFilter = useFilterStore((state) => state.model);
  const statusFilter = useFilterStore((state) => state.status);
  const providerFilter = useFilterStore((state) => state.provider);
  const searchFilter = useFilterStore((state) => state.search);
  const startDate = useFilterStore((state) => state.startDate);
  const endDate = useFilterStore((state) => state.endDate);
  const setFilter = useFilterStore((state) => state.setFilter);
  const resetFilters = useFilterStore((state) => state.resetFilters);

  const [searchInput, setSearchInput] = useState(searchFilter);

  useEffect(() => {
    setSearchInput(searchFilter);
  }, [searchFilter]);

  const sessionQueryParams = useMemo(() => {
    const params: Parameters<typeof apiClient.getSessions>[0] = {
      sort,
      limit,
      page,
    };
    if (modelFilter) params.model = modelFilter;
    if (statusFilter) params.status = statusFilter;
    if (providerFilter) params.provider = providerFilter;
    if (searchFilter) params.search = searchFilter;
    if (startDate) params.start_date = startDate;
    if (endDate) params.end_date = endDate;
    return params;
  }, [
    sort,
    limit,
    page,
    modelFilter,
    statusFilter,
    providerFilter,
    searchFilter,
    startDate,
    endDate,
  ]);

  const sessionsQuery = useQuery<SessionsResponse>({
    queryKey: ["sessions", sessionQueryParams],
    queryFn: () => apiClient.getSessions(sessionQueryParams),
  });

  const statsQuery = useQuery({
    queryKey: ["stats-overview"],
    queryFn: () => apiClient.getStatsOverview(),
  });

  const trendQuery = useQuery({
    queryKey: ["stats-trends"],
    queryFn: () => apiClient.getStatsTrends({ days: 7 }),
  });

  const modelStatsQuery = useQuery({
    queryKey: ["model-stats"],
    queryFn: () => apiClient.getModelStats(),
  });

  useEffect(() => {
    if (sessionsQuery.data) {
      const data = sessionsQuery.data;
      setSessions({
        sessions: data.sessions,
        total: data.total,
        nextCursor: data.next_cursor ?? null,
      });
      setError(null);
    }
  }, [sessionsQuery.data, setSessions, setError]);

  useEffect(() => {
    if (sessionsQuery.error) {
      const message =
        sessionsQuery.error instanceof Error
          ? sessionsQuery.error.message
          : "Failed to load session data";
      setError(message);
      toast.error(message);
    }
  }, [sessionsQuery.error, setError]);

  useEffect(() => {
    setLoading(sessionsQuery.isFetching);
  }, [sessionsQuery.isFetching, setLoading]);

  useEffect(() => {
    const debounce = setTimeout(() => {
      setFilter("search", searchInput);
      setPage(1);
    }, 400);
    return () => clearTimeout(debounce);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchInput]);

  const handleFilterChange = (
    key: Parameters<typeof setFilter>[0],
    value: string,
  ) => {
    setFilter(key, value);
    setPage(1);
  };

  const handleImportComplete = () => {
    setShowImport(false);
    queryClient.invalidateQueries({ queryKey: ["sessions"] });
    toast.success("Import completed, data refreshed");
  };

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-[rgb(var(--text))]">Dashboard</h1>
          <p className="mt-1 text-sm text-[rgb(var(--text-muted))]">
            Monitor sessions, model performance, and import status
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            leftIcon={<RefreshCw className="h-4 w-4" />}
            onClick={() => queryClient.invalidateQueries()}
          >
            Refresh
          </Button>
          <Button
            variant="primary"
            leftIcon={<Upload className="h-4 w-4" />}
            onClick={() => setShowImport((prev) => !prev)}
          >
            Import Data
          </Button>
        </div>
      </div>

      {showImport && (
        <Card>
          <CardContent className="pt-6">
            <DataImport onImportComplete={handleImportComplete} />
          </CardContent>
        </Card>
      )}

      {/* Stats Cards Section */}
      <StatsCards stats={statsQuery.data} isLoading={statsQuery.isLoading} />

      {/* Sessions Section */}
      <div className="space-y-4">
        {/* Section Header */}
        <div>
          <h2 className="text-lg font-semibold text-[rgb(var(--text))]">Sessions</h2>
          <p className="mt-1 text-sm text-[rgb(var(--text-muted))]">
            Filter and browse all session records
          </p>
        </div>

        {/* Filters */}
        <Card>
          <CardContent className="flex flex-col gap-4 p-4">
            <div className="flex flex-wrap items-center gap-3">
              <Input
                leadingIcon={<Search className="h-4 w-4" />}
                placeholder="Search by title, ID, or content..."
                value={searchInput}
                onChange={(event) => setSearchInput(event.target.value)}
              />
            <Select
              label="Status"
              value={statusFilter}
              onChange={(event) => handleFilterChange("status", event.target.value)}
            >
              {statusOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </Select>
            <Select
              label="Provider"
              value={providerFilter}
              onChange={(event) =>
                handleFilterChange("provider", event.target.value)
              }
            >
              {providerOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </Select>
            <Select
              label="Sort"
              value={sort}
              onChange={(event) =>
                setSort(event.target.value as SessionSort)
              }
            >
              {sortOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </Select>
          </div>
          <div className="flex flex-wrap gap-3">
            <label className="text-xs font-medium text-[rgb(var(--text-muted))]">
              Start Date
              <input
                type="date"
                value={startDate}
                onChange={(event) =>
                  handleFilterChange("startDate", event.target.value)
                }
                className="mt-1 rounded-md border border-border bg-transparent px-3 py-2 text-sm text-[rgb(var(--text))] dark:border-[rgb(var(--border-dark))]"
              />
            </label>
            <label className="text-xs font-medium text-[rgb(var(--text-muted))]">
              End Date
              <input
                type="date"
                value={endDate}
                onChange={(event) =>
                  handleFilterChange("endDate", event.target.value)
                }
                className="mt-1 rounded-md border border-border bg-transparent px-3 py-2 text-sm text-[rgb(var(--text))] dark:border-[rgb(var(--border-dark))]"
              />
            </label>
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                resetFilters();
                setSearchInput("");
                setPage(1);
              }}
            >
              Clear Filters
            </Button>
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-4 lg:grid-cols-2 xl:grid-cols-3">
        <Card>
          <CardContent className="pt-6">
            <TrendChart data={trendQuery.data?.trends ?? []} />
          </CardContent>
        </Card>
        <ModelChart data={modelStatsQuery.data?.model_stats ?? []} />
        <ErrorBreakdownChart data={statsQuery.data?.error_breakdown ?? {}} />
      </div>

      {error && (
        <Card className="border-status-danger/40 bg-status-danger/5 text-status-danger">
          <CardContent className="flex items-center gap-3 pt-6">
            <Spinner className="text-status-danger" />
            <p>{error}</p>
          </CardContent>
        </Card>
      )}

        <SessionsTable
          sessions={sessions}
          total={total}
          page={page}
          limit={limit}
          isLoading={isLoading}
          onPageChange={setPage}
          onLimitChange={(value) => {
            setLimit(value);
            setPage(1);
          }}
        />
      </div>
    </div>
  );
}
