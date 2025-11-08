"""
TraceStore module for storing and retrieving agent execution traces.

This module provides a flexible storage backend for TigerHill's tracing
and evaluation workflows, supporting in-memory, file-based, and structured
trace storage.
"""

import json
import os
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum


class EventType(str, Enum):
    """Types of trace events."""
    PROMPT = "prompt"
    MODEL_RESPONSE = "model_response"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    ERROR = "error"
    ASSERTION = "assertion"
    CUSTOM = "custom"


@dataclass
class TraceEvent:
    """Represents a single trace event."""
    event_id: str
    trace_id: str
    event_type: EventType
    timestamp: float
    data: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "event_id": self.event_id,
            "trace_id": self.trace_id,
            "event_type": self.event_type.value if isinstance(self.event_type, EventType) else self.event_type,
            "timestamp": self.timestamp,
            "data": self.data,
            "metadata": self.metadata or {}
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TraceEvent":
        """Create from dictionary."""
        return cls(
            event_id=data["event_id"],
            trace_id=data["trace_id"],
            event_type=EventType(data["event_type"]),
            timestamp=data["timestamp"],
            data=data["data"],
            metadata=data.get("metadata")
        )

    def to_db_dict(self, sequence_number: int) -> Dict[str, Any]:
        """Convert to database format (for events table).

        Args:
            sequence_number: The sequence number of this event in the trace

        Returns:
            Dictionary with fields matching the events table schema
        """
        # Combine data and metadata into a single JSON object for the data field
        event_data = {
            'event_id': self.event_id,
            'event_type': self.event_type.value if isinstance(self.event_type, EventType) else self.event_type,
            'data': self.data,
            'metadata': self.metadata or {}
        }

        return {
            'trace_id': self.trace_id,
            'event_type': self.event_type.value if isinstance(self.event_type, EventType) else self.event_type,
            'timestamp': self.timestamp,
            'sequence_number': sequence_number,
            'data': json.dumps(event_data)
        }

    @classmethod
    def from_db_dict(cls, db_data: Dict[str, Any]) -> "TraceEvent":
        """Create TraceEvent from database format.

        Args:
            db_data: Dictionary from events table (row data)

        Returns:
            TraceEvent object
        """
        # Parse the data field
        try:
            event_data = json.loads(db_data['data'])
        except (json.JSONDecodeError, TypeError):
            # Fallback if data is not JSON
            event_data = {
                'event_id': str(uuid.uuid4()),
                'event_type': db_data['event_type'],
                'data': {},
                'metadata': {}
            }

        return cls(
            event_id=event_data.get('event_id', str(uuid.uuid4())),
            trace_id=db_data['trace_id'],
            event_type=EventType(db_data['event_type']),
            timestamp=db_data['timestamp'],
            data=event_data.get('data', {}),
            metadata=event_data.get('metadata')
        )


@dataclass
class Trace:
    """Represents a complete trace (collection of events)."""
    trace_id: str
    agent_name: str
    task_id: Optional[str]
    start_time: float
    end_time: Optional[float]
    events: List[TraceEvent]
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "trace_id": self.trace_id,
            "agent_name": self.agent_name,
            "task_id": self.task_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "events": [e.to_dict() for e in self.events],
            "metadata": self.metadata or {}
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Trace":
        """Create from dictionary."""
        return cls(
            trace_id=data["trace_id"],
            agent_name=data["agent_name"],
            task_id=data.get("task_id"),
            start_time=data["start_time"],
            end_time=data.get("end_time"),
            events=[TraceEvent.from_dict(e) for e in data.get("events", [])],
            metadata=data.get("metadata")
        )

    def to_db_dict(self) -> Dict[str, Any]:
        """Convert to database format (for traces table).

        Returns:
            Dictionary with fields matching the traces table schema
        """
        # Calculate duration
        duration_seconds = None
        if self.end_time:
            duration_seconds = self.end_time - self.start_time

        # Determine status
        if self.end_time is None:
            status = 'running'
        else:
            # Check for error events
            has_error = any(e.event_type == EventType.ERROR for e in self.events)
            status = 'failed' if has_error else 'completed'

        # Calculate statistics from events
        total_events = len(self.events)
        llm_calls_count = sum(
            1 for e in self.events
            if e.event_type in (EventType.PROMPT, EventType.MODEL_RESPONSE)
        )

        # Extract LLM stats from events
        total_tokens = 0
        total_cost_usd = 0.0
        for event in self.events:
            if event.event_type in (EventType.PROMPT, EventType.MODEL_RESPONSE):
                # Try to extract token and cost info from event data
                total_tokens += event.data.get('total_tokens', 0)
                total_cost_usd += event.data.get('cost_usd', 0.0)

        # Extract tags and quality metrics from metadata
        tags = None
        quality_score = None
        cost_efficiency = None

        if self.metadata:
            if 'tags' in self.metadata:
                tags = json.dumps(self.metadata['tags'])
            if 'quality_score' in self.metadata:
                quality_score = self.metadata['quality_score']
            if 'cost_efficiency' in self.metadata:
                cost_efficiency = self.metadata['cost_efficiency']

        # Serialize metadata (excluding tags which are stored separately)
        metadata_dict = dict(self.metadata) if self.metadata else {}
        metadata_dict.pop('tags', None)  # Remove tags from metadata
        metadata_json = json.dumps(metadata_dict) if metadata_dict else None

        return {
            'trace_id': self.trace_id,
            'agent_name': self.agent_name,
            'task_id': self.task_id,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'duration_seconds': duration_seconds,
            'status': status,
            'total_events': total_events,
            'llm_calls_count': llm_calls_count,
            'total_tokens': total_tokens,
            'total_cost_usd': total_cost_usd,
            'quality_score': quality_score,
            'cost_efficiency': cost_efficiency,
            'tags': tags,
            'metadata': metadata_json
        }

    @classmethod
    def from_db_dict(cls, db_data: Dict[str, Any], events: Optional[List[TraceEvent]] = None) -> "Trace":
        """Create Trace from database format.

        Args:
            db_data: Dictionary from traces table (row data)
            events: Optional list of TraceEvent objects (loaded separately from events table)

        Returns:
            Trace object
        """
        # Parse metadata
        metadata = {}
        if db_data.get('metadata'):
            try:
                metadata = json.loads(db_data['metadata'])
            except (json.JSONDecodeError, TypeError):
                pass

        # Add tags back to metadata
        if db_data.get('tags'):
            try:
                metadata['tags'] = json.loads(db_data['tags'])
            except (json.JSONDecodeError, TypeError):
                pass

        # Add quality metrics to metadata
        if db_data.get('quality_score') is not None:
            metadata['quality_score'] = db_data['quality_score']
        if db_data.get('cost_efficiency') is not None:
            metadata['cost_efficiency'] = db_data['cost_efficiency']

        # Add database-specific fields to metadata for reference
        metadata['_db_status'] = db_data.get('status')
        metadata['_db_total_events'] = db_data.get('total_events')
        metadata['_db_llm_calls_count'] = db_data.get('llm_calls_count')
        metadata['_db_total_tokens'] = db_data.get('total_tokens')
        metadata['_db_total_cost_usd'] = db_data.get('total_cost_usd')

        return cls(
            trace_id=db_data['trace_id'],
            agent_name=db_data['agent_name'],
            task_id=db_data.get('task_id'),
            start_time=db_data['start_time'],
            end_time=db_data.get('end_time'),
            events=events or [],
            metadata=metadata if metadata else None
        )


class TraceStore:
    """
    Storage backend for agent execution traces.

    Supports in-memory storage with optional file-based persistence.
    Each trace represents a single agent run and contains multiple events.
    """

    def __init__(self, storage_path: Optional[str] = None, auto_save: bool = True):
        """
        Initialize TraceStore.

        Args:
            storage_path: Optional path to store traces. If None, uses traces/ directory.
            auto_save: If True, automatically save traces to disk after writing events.
        """
        self.storage_path = Path(storage_path) if storage_path else Path("traces")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.auto_save = auto_save

        # In-memory storage
        self._traces: Dict[str, Trace] = {}  # trace_id -> Trace
        self._current_trace_id: Optional[str] = None

        # Load existing traces if available
        self._load_traces()

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
        trace = Trace(
            trace_id=trace_id,
            agent_name=agent_name,
            task_id=task_id,
            start_time=time.time(),
            end_time=None,
            events=[],
            metadata=metadata
        )

        self._traces[trace_id] = trace
        self._current_trace_id = trace_id

        return trace_id

    def end_trace(self, trace_id: Optional[str] = None) -> None:
        """
        End a trace.

        Args:
            trace_id: The trace to end. If None, uses current trace.
        """
        tid = trace_id or self._current_trace_id
        if tid and tid in self._traces:
            self._traces[tid].end_time = time.time()

            if self.auto_save:
                self._save_trace(tid)

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
        if not tid or tid not in self._traces:
            raise ValueError("No active trace. Call start_trace() first.")

        # Infer event type if not provided
        if event_type is None:
            event_type = self._infer_event_type(event_data)

        event = TraceEvent(
            event_id=str(uuid.uuid4()),
            trace_id=tid,
            event_type=event_type,
            timestamp=time.time(),
            data=event_data,
            metadata=metadata
        )

        self._traces[tid].events.append(event)

        return event.event_id

    def get_trace(self, trace_id: str) -> Optional[Trace]:
        """
        Retrieve a trace by ID.

        Args:
            trace_id: The trace ID to retrieve.

        Returns:
            The Trace object, or None if not found.
        """
        return self._traces.get(trace_id)

    def get_all_traces(self) -> List[Trace]:
        """
        Retrieve all traces.

        Returns:
            List of all Trace objects.
        """
        return list(self._traces.values())

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
        trace = self.get_trace(trace_id)
        if not trace:
            return []

        events = trace.events
        if event_type:
            events = [e for e in events if e.event_type == event_type]

        return events

    def query_traces(
        self,
        agent_name: Optional[str] = None,
        task_id: Optional[str] = None,
        start_after: Optional[float] = None,
        end_before: Optional[float] = None
    ) -> List[Trace]:
        """
        Query traces with filters.

        Args:
            agent_name: Filter by agent name.
            task_id: Filter by task ID.
            start_after: Filter traces that started after this timestamp.
            end_before: Filter traces that ended before this timestamp.

        Returns:
            List of matching Trace objects.
        """
        results = list(self._traces.values())

        if agent_name:
            results = [t for t in results if t.agent_name == agent_name]

        if task_id:
            results = [t for t in results if t.task_id == task_id]

        if start_after:
            results = [t for t in results if t.start_time >= start_after]

        if end_before:
            results = [t for t in results if t.end_time and t.end_time <= end_before]

        return results

    def clear(self) -> None:
        """Clear all traces from memory."""
        self._traces.clear()
        self._current_trace_id = None

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

    def _save_trace(self, trace_id: str) -> None:
        """Save a trace to disk."""
        trace = self._traces.get(trace_id)
        if not trace:
            return

        filename = f"trace_{trace_id}_{int(trace.start_time)}.json"
        filepath = self.storage_path / filename

        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(trace.to_dict(), f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Warning: Failed to save trace {trace_id}: {e}")

    def _load_traces(self) -> None:
        """Load traces from disk."""
        if not self.storage_path.exists():
            return

        for filepath in self.storage_path.glob("trace_*.json"):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    trace = Trace.from_dict(data)
                    self._traces[trace.trace_id] = trace
            except Exception as e:
                print(f"Warning: Failed to load trace from {filepath}: {e}")

    def save_all(self) -> int:
        """
        Save all traces to disk.

        Returns:
            Number of traces saved.
        """
        count = 0
        for trace_id in self._traces:
            self._save_trace(trace_id)
            count += 1
        return count

    def export_trace(self, trace_id: str, output_path: str) -> bool:
        """
        Export a specific trace to a file.

        Args:
            trace_id: The trace ID to export.
            output_path: Path to save the trace.

        Returns:
            True if successful, False otherwise.
        """
        trace = self.get_trace(trace_id)
        if not trace:
            return False

        try:
            output = Path(output_path)
            output.parent.mkdir(parents=True, exist_ok=True)

            with open(output, 'w', encoding='utf-8') as f:
                json.dump(trace.to_dict(), f, indent=2, ensure_ascii=False)

            return True
        except Exception as e:
            print(f"Failed to export trace {trace_id}: {e}")
            return False

    def get_summary(self, trace_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a summary of a trace.

        Args:
            trace_id: The trace ID.

        Returns:
            Dictionary containing trace summary statistics.
        """
        trace = self.get_trace(trace_id)
        if not trace:
            return None

        event_counts = {}
        for event in trace.events:
            event_type = event.event_type.value
            event_counts[event_type] = event_counts.get(event_type, 0) + 1

        duration = None
        if trace.end_time:
            duration = trace.end_time - trace.start_time

        return {
            "trace_id": trace_id,
            "agent_name": trace.agent_name,
            "task_id": trace.task_id,
            "start_time": datetime.fromtimestamp(trace.start_time).isoformat(),
            "end_time": datetime.fromtimestamp(trace.end_time).isoformat() if trace.end_time else None,
            "duration_seconds": duration,
            "total_events": len(trace.events),
            "event_counts": event_counts,
            "metadata": trace.metadata
        }


__all__ = ["TraceStore", "TraceEvent", "Trace", "EventType"]
