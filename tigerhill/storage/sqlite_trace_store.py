"""
SQLite-backed TraceStore implementation

Provides persistent storage for traces using SQLite database,
with full compatibility with the original TraceStore interface.
"""

import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from tigerhill.storage.trace_store import Trace, TraceEvent, EventType
from tigerhill.storage.database import DatabaseManager


class SQLiteTraceStore:
    """
    SQLite-backed storage for agent execution traces.

    Compatible with TraceStore interface but uses SQLite for persistence.
    Supports advanced querying, filtering, sorting, and pagination.
    """

    def __init__(self, db_path: Optional[str] = None, auto_init: bool = True):
        """
        Initialize SQLiteTraceStore.

        Args:
            db_path: Path to SQLite database. If None, uses ./tigerhill.db
            auto_init: If True, automatically initialize database schema
        """
        self.db_path = db_path or "./tigerhill.db"
        self.db = DatabaseManager(self.db_path)
        self._current_trace_id: Optional[str] = None

        # Initialize database schema if needed
        if auto_init and not self.db.table_exists('traces'):
            schema_path = Path(__file__).parent.parent.parent / "scripts" / "migrations" / "v1_initial_schema.sql"
            self.db.initialize_database(str(schema_path))

    def start_trace(
        self,
        agent_name: str,
        task_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Start a new trace.

        Args:
            agent_name: Name of the agent.
            task_id: Optional task identifier.
            metadata: Optional metadata for the trace.

        Returns:
            The trace_id of the newly created trace.
        """
        trace_id = str(uuid.uuid4())

        # Create trace object
        trace = Trace(
            trace_id=trace_id,
            agent_name=agent_name,
            task_id=task_id,
            start_time=time.time(),
            end_time=None,
            events=[],
            metadata=metadata
        )

        # Insert into database
        trace_dict = trace.to_db_dict()
        self.db.insert('traces', trace_dict)

        self._current_trace_id = trace_id
        return trace_id

    def end_trace(self, trace_id: Optional[str] = None) -> None:
        """
        End a trace.

        Args:
            trace_id: The trace to end. If None, uses current trace.
        """
        tid = trace_id or self._current_trace_id
        if not tid:
            return

        # Update end_time and recalculate status
        end_time = time.time()

        # Get trace with all events to recalculate stats
        trace = self.get_trace(tid, include_events=True)
        if not trace:
            return

        trace.end_time = end_time

        # Recalculate all fields (including tokens, cost)
        trace_dict = trace.to_db_dict()

        # Update database with all recalculated fields
        self.db.update(
            'traces',
            {
                'end_time': trace_dict['end_time'],
                'duration_seconds': trace_dict['duration_seconds'],
                'status': trace_dict['status'],
                'total_tokens': trace_dict['total_tokens'],
                'total_cost_usd': trace_dict['total_cost_usd'],
                'llm_calls_count': trace_dict['llm_calls_count']
            },
            'trace_id = ?',
            (tid,)
        )

        if tid == self._current_trace_id:
            self._current_trace_id = None

    def write_event(
        self,
        event_data: Dict[str, Any],
        trace_id: Optional[str] = None,
        event_type: Optional[EventType] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Write a trace event.

        Args:
            event_data: The event data to store.
            trace_id: Optional trace ID. If None, uses current trace.
            event_type: Type of event. If None, inferred from event_data.
            metadata: Optional event metadata.

        Returns:
            The event_id of the created event.

        Raises:
            ValueError: If no trace is active.
        """
        tid = trace_id or self._current_trace_id
        if not tid:
            raise ValueError("No active trace. Call start_trace() first.")

        # Verify trace exists
        if not self.db.fetch_one("SELECT trace_id FROM traces WHERE trace_id = ?", (tid,)):
            raise ValueError(f"Trace {tid} does not exist.")

        # Infer event type if not provided
        if event_type is None:
            event_type = self._infer_event_type(event_data)

        # Create event
        event = TraceEvent(
            event_id=str(uuid.uuid4()),
            trace_id=tid,
            event_type=event_type,
            timestamp=time.time(),
            data=event_data,
            metadata=metadata
        )

        # Get current event count to determine sequence number
        result = self.db.fetch_one(
            "SELECT COUNT(*) as count FROM events WHERE trace_id = ?",
            (tid,)
        )
        sequence_number = result['count'] if result else 0

        # Insert event
        event_dict = event.to_db_dict(sequence_number)
        self.db.insert('events', event_dict)

        return event.event_id

    def get_trace(self, trace_id: str, include_events: bool = True) -> Optional[Trace]:
        """
        Retrieve a trace by ID.

        Args:
            trace_id: The trace ID to retrieve.
            include_events: If True, load all events for the trace.

        Returns:
            The Trace object, or None if not found.
        """
        # Load trace from database
        trace_data = self.db.fetch_one(
            "SELECT * FROM traces WHERE trace_id = ?",
            (trace_id,)
        )

        if not trace_data:
            return None

        # Load events if requested
        events = []
        if include_events:
            events_data = self.db.fetch_all(
                "SELECT * FROM events WHERE trace_id = ? ORDER BY sequence_number",
                (trace_id,)
            )
            events = [TraceEvent.from_db_dict(e) for e in events_data]

        # Create Trace object
        return Trace.from_db_dict(trace_data, events=events)

    def get_all_traces(self, include_events: bool = False) -> List[Trace]:
        """
        Retrieve all traces.

        Args:
            include_events: If True, load events for all traces.

        Returns:
            List of all Trace objects.
        """
        traces_data = self.db.fetch_all(
            "SELECT * FROM traces ORDER BY start_time DESC"
        )

        traces = []
        for trace_data in traces_data:
            if include_events:
                trace = self.get_trace(trace_data['trace_id'], include_events=True)
            else:
                trace = Trace.from_db_dict(trace_data, events=[])

            if trace:
                traces.append(trace)

        return traces

    def get_events(
        self,
        trace_id: str,
        event_type: Optional[EventType] = None
    ) -> List[TraceEvent]:
        """
        Get events for a specific trace, optionally filtered by type.

        Args:
            trace_id: The trace ID.
            event_type: Optional event type to filter by.

        Returns:
            List of TraceEvent objects.
        """
        if event_type:
            events_data = self.db.fetch_all(
                "SELECT * FROM events WHERE trace_id = ? AND event_type = ? ORDER BY sequence_number",
                (trace_id, event_type.value)
            )
        else:
            events_data = self.db.fetch_all(
                "SELECT * FROM events WHERE trace_id = ? ORDER BY sequence_number",
                (trace_id,)
            )

        return [TraceEvent.from_db_dict(e) for e in events_data]

    def query_traces(
        self,
        agent_name: Optional[str] = None,
        task_id: Optional[str] = None,
        start_after: Optional[float] = None,
        end_before: Optional[float] = None,
        status: Optional[str] = None,
        min_cost: Optional[float] = None,
        max_cost: Optional[float] = None,
        tags: Optional[List[str]] = None,
        order_by: str = 'start_time',
        order_desc: bool = True,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[Trace]:
        """
        Query traces with filters and pagination.

        Args:
            agent_name: Filter by agent name.
            task_id: Filter by task ID.
            start_after: Filter traces that started after this timestamp.
            end_before: Filter traces that ended before this timestamp.
            status: Filter by status (running/completed/failed).
            min_cost: Minimum cost filter.
            max_cost: Maximum cost filter.
            tags: Filter by tags (must contain all specified tags).
            order_by: Field to order by (start_time/total_cost_usd/total_tokens).
            order_desc: If True, order descending.
            limit: Maximum number of results.
            offset: Number of results to skip.

        Returns:
            List of matching Trace objects.
        """
        # Build query
        sql = "SELECT * FROM traces WHERE 1=1"
        params = []

        if agent_name:
            sql += " AND agent_name = ?"
            params.append(agent_name)

        if task_id:
            sql += " AND task_id = ?"
            params.append(task_id)

        if start_after:
            sql += " AND start_time >= ?"
            params.append(start_after)

        if end_before:
            sql += " AND end_time <= ?"
            params.append(end_before)

        if status:
            sql += " AND status = ?"
            params.append(status)

        if min_cost is not None:
            sql += " AND total_cost_usd >= ?"
            params.append(min_cost)

        if max_cost is not None:
            sql += " AND total_cost_usd <= ?"
            params.append(max_cost)

        if tags:
            # Simple tag filtering - check if JSON contains the tag
            for tag in tags:
                sql += " AND tags LIKE ?"
                params.append(f'%"{tag}"%')

        # Order by
        valid_order_fields = ['start_time', 'total_cost_usd', 'total_tokens', 'quality_score']
        if order_by in valid_order_fields:
            sql += f" ORDER BY {order_by}"
            sql += " DESC" if order_desc else " ASC"
        else:
            sql += " ORDER BY start_time DESC"

        # Pagination
        if limit:
            sql += " LIMIT ?"
            params.append(limit)

        if offset:
            sql += " OFFSET ?"
            params.append(offset)

        # Execute query
        traces_data = self.db.fetch_all(sql, tuple(params))

        # Convert to Trace objects (without events for performance)
        return [Trace.from_db_dict(t, events=[]) for t in traces_data]

    def clear(self) -> None:
        """Clear all traces from database."""
        self.db.execute("DELETE FROM events")
        self.db.execute("DELETE FROM traces")
        self._current_trace_id = None

    def delete_trace(self, trace_id: str) -> bool:
        """
        Delete a specific trace.

        Args:
            trace_id: The trace ID to delete.

        Returns:
            True if deleted, False if not found.
        """
        rows = self.db.delete('traces', 'trace_id = ?', (trace_id,))
        return rows > 0

    def get_summary(self, trace_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a summary of a trace.

        Args:
            trace_id: The trace ID.

        Returns:
            Dictionary containing trace summary statistics.
        """
        trace = self.get_trace(trace_id, include_events=False)
        if not trace:
            return None

        # Get database stats
        trace_data = self.db.fetch_one(
            "SELECT * FROM traces WHERE trace_id = ?",
            (trace_id,)
        )

        if not trace_data:
            return None

        # Count events by type
        event_counts_data = self.db.fetch_all(
            "SELECT event_type, COUNT(*) as count FROM events WHERE trace_id = ? GROUP BY event_type",
            (trace_id,)
        )
        event_counts = {row['event_type']: row['count'] for row in event_counts_data}

        return {
            "trace_id": trace_id,
            "agent_name": trace_data['agent_name'],
            "task_id": trace_data['task_id'],
            "start_time": datetime.fromtimestamp(trace_data['start_time']).isoformat(),
            "end_time": datetime.fromtimestamp(trace_data['end_time']).isoformat() if trace_data['end_time'] else None,
            "duration_seconds": trace_data['duration_seconds'],
            "status": trace_data['status'],
            "total_events": trace_data['total_events'],
            "llm_calls_count": trace_data['llm_calls_count'],
            "total_tokens": trace_data['total_tokens'],
            "total_cost_usd": trace_data['total_cost_usd'],
            "quality_score": trace_data['quality_score'],
            "event_counts": event_counts,
            "metadata": trace.metadata
        }

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get overall statistics across all traces.

        Returns:
            Dictionary with aggregate statistics.
        """
        stats = self.db.fetch_one("""
            SELECT
                COUNT(*) as total_traces,
                SUM(total_events) as total_events,
                SUM(llm_calls_count) as total_llm_calls,
                SUM(total_tokens) as total_tokens,
                SUM(total_cost_usd) as total_cost,
                AVG(quality_score) as avg_quality_score,
                MIN(start_time) as first_trace_time,
                MAX(start_time) as last_trace_time
            FROM traces
        """)

        status_counts = self.db.fetch_all("""
            SELECT status, COUNT(*) as count
            FROM traces
            GROUP BY status
        """)

        return {
            "total_traces": stats['total_traces'] or 0,
            "total_events": stats['total_events'] or 0,
            "total_llm_calls": stats['total_llm_calls'] or 0,
            "total_tokens": stats['total_tokens'] or 0,
            "total_cost_usd": stats['total_cost'] or 0.0,
            "avg_quality_score": stats['avg_quality_score'],
            "first_trace_time": datetime.fromtimestamp(stats['first_trace_time']).isoformat() if stats['first_trace_time'] else None,
            "last_trace_time": datetime.fromtimestamp(stats['last_trace_time']).isoformat() if stats['last_trace_time'] else None,
            "status_counts": {row['status']: row['count'] for row in status_counts}
        }

    def _infer_event_type(self, event_data: Dict[str, Any]) -> EventType:
        """Infer event type from event data."""
        event_type_str = event_data.get("type", "")

        type_mapping = {
            "prompt": EventType.PROMPT,
            "model_response": EventType.MODEL_RESPONSE,
            "tool_call": EventType.TOOL_CALL,
            "tool_result": EventType.TOOL_RESULT,
            "error": EventType.ERROR,
            "assertion": EventType.ASSERTION,
        }

        return type_mapping.get(event_type_str, EventType.CUSTOM)


__all__ = ["SQLiteTraceStore"]
