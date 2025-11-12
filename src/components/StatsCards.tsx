import { Card } from "@/components/ui/Card";
import { Spinner } from "@/components/ui/Spinner";
import { StatsCard } from "@/components/StatsCard";
import { StatsOverview } from "@/types";

interface StatsCardsProps {
  stats?: StatsOverview;
  isLoading?: boolean;
}

const skeletonCards = Array.from({ length: 4 });

export default function StatsCards({ stats, isLoading }: StatsCardsProps) {
  if (isLoading && !stats) {
    return (
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        {skeletonCards.map((_, idx) => (
          <div
            key={idx}
            className="flex flex-col gap-2 rounded-xl border border-gray-200/80 bg-white p-4 dark:border-white/10 dark:bg-black/20 animate-pulse"
          >
            <div className="h-4 w-24 rounded bg-gray-200 dark:bg-gray-700" />
            <div className="h-7 w-32 rounded bg-gray-200 dark:bg-gray-700" />
          </div>
        ))}
      </div>
    );
  }

  if (!stats) {
    return (
      <Card className="flex items-center gap-3 p-4">
        <Spinner />
        <p className="text-sm text-gray-600 dark:text-gray-400">
          正在加载统计数据...
        </p>
      </Card>
    );
  }

  const delta = stats.session_volume_change ?? 0;

  return (
    <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
      {/* Total Sessions */}
      <StatsCard
        label="Total Sessions"
        value={stats.total_sessions.toLocaleString()}
      />

      {/* Top Model */}
      <StatsCard
        label="Top Model"
        value={stats.top_model || "N/A"}
      />

      {/* Success Rate with Trend */}
      <StatsCard
        label="Success Rate"
        value={`${stats.success_rate}%`}
        trend={{
          value: delta,
          isPositive: delta >= 0,
        }}
      />

      {/* Average Duration */}
      <StatsCard label="Avg Duration" value={stats.avg_duration || "N/A"} />
    </div>
  );
}
