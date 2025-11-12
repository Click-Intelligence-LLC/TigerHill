/**
 * SessionDetailV3 - Session detail page using V3 Unified Interaction Model
 */

import { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { toast } from 'sonner';
import { Card, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Spinner } from '@/components/ui/Spinner';
import { Badge } from '@/components/ui/Badge';
import { Breadcrumbs } from '@/components/navigation/Breadcrumbs';
import { InteractionTimeline } from '@/components/v3/InteractionTimeline';
import { SessionStatsCard } from '@/components/v3/SessionStatsCard';
import {
  useSessionV3,
  useSessionInteractions,
  useSessionStats,
} from '@/hooks/useSessionV3';
import { formatDuration } from '@/utils';
import { ArrowLeft } from 'lucide-react';

export default function SessionDetailV3Page() {
  const { id } = useParams<{ id: string }>();
  const [showStats, setShowStats] = useState(false);

  // Fetch session detail
  const sessionQuery = useSessionV3(id);

  // Fetch all interactions
  const interactionsQuery = useSessionInteractions(id, { limit: 500 });

  // Fetch stats (only when showStats is true)
  const statsQuery = useSessionStats(id, { enabled: showStats });

  if (sessionQuery.isLoading || interactionsQuery.isLoading) {
    return (
      <div className="flex h-80 items-center justify-center">
        <Spinner />
      </div>
    );
  }

  if (sessionQuery.error || !sessionQuery.data) {
    toast.error('Failed to load session details');
    return (
      <Card>
        <CardContent className="py-10 text-center text-sm text-gray-500">
          Unable to load session. Please try again later.
        </CardContent>
      </Card>
    );
  }

  const session = sessionQuery.data;
  const interactions = interactionsQuery.data?.interactions || [];

  return (
    <div className="space-y-6">
      {/* Breadcrumbs */}
      <Breadcrumbs
        items={[
          { label: 'Dashboard', href: '/' },
          { label: 'Sessions', href: '/session' },
          { label: session.title ?? 'Session Details (V3)' },
        ]}
      />

      {/* Header with actions */}
      <div className="flex items-center justify-between">
        <Link to="/session">
          <Button variant="ghost" leftIcon={<ArrowLeft className="h-4 w-4" />}>
            Back to Sessions
          </Button>
        </Link>
        <div className="flex items-center gap-3">
          <Badge variant="info">V3 Unified Model</Badge>
          {session.duration_seconds && (
            <Badge variant="outline">Duration: {formatDuration(session.duration_seconds)}</Badge>
          )}
        </div>
      </div>

      {/* Session Header */}
      <Card>
        <CardContent className="pt-6 space-y-4">
          <div>
            <h1 className="text-2xl font-bold">{session.title}</h1>
            <p className="text-sm text-gray-600 mt-1">
              Session ID: <span className="font-mono">{session.id}</span>
            </p>
          </div>

          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            <div>
              <p className="text-sm text-gray-600">Status</p>
              <Badge variant={session.status === 'success' ? 'success' : 'danger'}>
                {session.status}
              </Badge>
            </div>
            <div>
              <p className="text-sm text-gray-600">Total Turns</p>
              <p className="text-xl font-bold">{session.total_turns}</p>
            </div>
            <div>
              <p className="text-sm text-gray-600">Total Interactions</p>
              <p className="text-xl font-bold">{session.total_interactions || 'N/A'}</p>
            </div>
            {session.stats && (
              <div>
                <p className="text-sm text-gray-600">Request / Response</p>
                <p className="text-xl font-bold">
                  {session.stats.request_count} / {session.stats.response_count}
                </p>
              </div>
            )}
          </div>

          {session.primary_provider && (
            <div className="flex gap-2">
              <Badge variant="outline">{session.primary_provider}</Badge>
              {session.primary_model && <Badge variant="outline">{session.primary_model}</Badge>}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Interaction Timeline */}
      <InteractionTimeline
        interactions={interactions}
        isLoading={interactionsQuery.isLoading}
        showStats={showStats}
        onToggleStats={() => setShowStats(!showStats)}
      />

      {/* Session Stats (conditional) */}
      {showStats && (
        <>
          {statsQuery.isLoading && (
            <Card>
              <CardContent className="py-10 flex justify-center">
                <Spinner />
              </CardContent>
            </Card>
          )}
          {statsQuery.data && <SessionStatsCard stats={statsQuery.data} />}
          {statsQuery.error && (
            <Card>
              <CardContent className="py-10 text-center text-sm text-red-600">
                Failed to load statistics
              </CardContent>
            </Card>
          )}
        </>
      )}

      {/* Footer Info */}
      <Card>
        <CardContent className="py-4 text-xs text-gray-500">
          <p>
            💡 This page uses the V3 Unified Interaction Model. Interactions are displayed by turn
            with no duplication. The turn boundary is automatically detected based on the request-response pattern.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
