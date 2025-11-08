"""Data loader for dashboard"""

import json
import time
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path

from tigerhill.web.dashboard.models.trace_metadata import TraceMetadata
from tigerhill.web.dashboard.models.analysis_result import AnalysisResult
from tigerhill.storage.trace_store import Trace, TraceEvent, EventType


class DataLoader:
    """数据加载器 - 从TraceStore或SQLite加载数据"""

    def __init__(
        self,
        storage_path: str = "./test_traces",
        use_database: bool = False,
        db_path: Optional[str] = None
    ):
        """初始化数据加载器

        Args:
            storage_path: TraceStore数据存储目录（JSONL文件）
            use_database: 是否使用SQLite数据库
            db_path: 数据库文件路径（如果use_database=True）
        """
        self.storage_path = Path(storage_path).expanduser()
        self.use_database = use_database
        self.db_path = db_path or "./tigerhill.db"
        self._trace_store = None
        self._single_trace_cache: Optional[Trace] = None
        self.is_file_source = self.storage_path.is_file() and not self.use_database

    @property
    def trace_store(self):
        """延迟加载TraceStore或SQLiteTraceStore"""
        if self._trace_store is None:
            try:
                if self.use_database:
                    # 使用SQLite数据库
                    from tigerhill.storage.sqlite_trace_store import SQLiteTraceStore
                    self._trace_store = SQLiteTraceStore(
                        db_path=self.db_path,
                        auto_init=False  # 不自动初始化，假设数据库已存在
                    )
                elif not self.is_file_source:
                    # 使用JSONL文件
                    from tigerhill.storage.trace_store import TraceStore
                    self._trace_store = TraceStore(storage_path=str(self.storage_path))
                else:
                    self._trace_store = None
            except Exception as e:
                print(f"Warning: Failed to load TraceStore: {e}")
                import traceback
                traceback.print_exc()
                self._trace_store = None
        return self._trace_store

    @property
    def data_source_type(self) -> str:
        """获取数据源类型"""
        if self.use_database:
            return "SQLite Database"
        if self.is_file_source:
            return "Trace File"
        return "JSONL Files"

    def load_traces(self, limit: int = 1000) -> List[TraceMetadata]:
        """加载trace元数据列表

        Args:
            limit: 最大加载数量

        Returns:
            TraceMetadata列表
        """
        try:
            if self.use_database:
                if self.trace_store is None:
                    return []
                traces = self.trace_store.query_traces()
                traces = traces[:limit] if limit > 0 else traces
                return [self._trace_to_metadata(t) for t in traces]

            if self.is_file_source:
                trace = self._load_single_trace()
                return [self._trace_to_metadata(trace)] if trace else []

            if self.trace_store is None:
                return []

            traces = self.trace_store.query_traces()
            traces = traces[:limit] if limit > 0 else traces
            return [self._trace_to_metadata(t) for t in traces]
        except Exception as e:
            print(f"Error loading traces: {e}")
            return []

    def load_trace_detail(self, trace_id: str) -> Optional[Dict[str, Any]]:
        """加载完整trace数据

        Args:
            trace_id: 追踪ID

        Returns:
            完整trace数据字典
        """
        try:
            if self.use_database:
                if self.trace_store is None:
                    return None
                return self.trace_store.get_trace(trace_id)

            if self.is_file_source:
                trace = self._load_single_trace()
                if not trace:
                    return None
                if trace.trace_id != trace_id:
                    # 即使ID不同，也返回唯一trace
                    return trace.to_dict()
                return trace.to_dict()

            if self.trace_store is None:
                return None
            return self.trace_store.get_trace(trace_id)
        except Exception as e:
            print(f"Error loading trace detail: {e}")
            return None

    def load_analysis(self, trace_id: str) -> Optional[AnalysisResult]:
        """加载分析结果

        Args:
            trace_id: 追踪ID

        Returns:
            分析结果对象
        """
        # TODO: 实现从缓存或文件加载分析结果
        # 暂时返回None，需要用户触发分析
        return None

    def _trace_to_metadata(self, trace_obj) -> TraceMetadata:
        """将trace对象转换为TraceMetadata

        Args:
            trace_obj: TraceStore返回的Trace对象或字典

        Returns:
            TraceMetadata对象
        """
        # 如果是Trace对象，转换为字典
        if hasattr(trace_obj, 'to_dict'):
            trace_dict = trace_obj.to_dict()
        else:
            trace_dict = trace_obj

        # 解析时间
        start_time = trace_dict.get("start_time")
        if isinstance(start_time, str):
            start_time = datetime.fromisoformat(start_time)
        elif isinstance(start_time, (int, float)):
            start_time = datetime.fromtimestamp(start_time)

        end_time = trace_dict.get("end_time")
        if end_time:
            if isinstance(end_time, str):
                end_time = datetime.fromisoformat(end_time)
            elif isinstance(end_time, (int, float)):
                end_time = datetime.fromtimestamp(end_time)

        # 计算时长
        duration = 0.0
        if start_time and end_time:
            duration = (end_time - start_time).total_seconds()
        elif "duration" in trace_dict:
            duration = trace_dict["duration"]

        # 优先从metadata中的数据库字段获取统计信息
        metadata = trace_dict.get("metadata", {})
        llm_calls_count = metadata.get("_db_llm_calls_count", 0)
        total_tokens = metadata.get("_db_total_tokens", 0)
        total_cost = metadata.get("_db_total_cost_usd", 0.0)
        total_events = metadata.get("_db_total_events", 0)
        status = metadata.get("_db_status", "unknown")

        # 如果没有数据库字段，使用传统方式从events计算
        events = trace_dict.get("events", [])
        if llm_calls_count == 0 and total_tokens == 0 and len(events) > 0:
            for event in events:
                event_type = event.get("type", "")
                if "llm" in event_type.lower() or "prompt" in event_type.lower():
                    llm_calls_count += 1

                    # 提取token信息
                    data = event.get("data", {})
                    if isinstance(data, dict):
                        total_tokens += data.get("total_tokens", 0)
                        total_cost += data.get("cost_usd", 0.0)

        # 从summary中获取统计信息（如果有）
        summary = trace_dict.get("summary", {})
        if summary:
            llm_calls_count = summary.get("llm_calls_count", llm_calls_count)
            total_tokens = summary.get("total_tokens", total_tokens)
            total_cost = summary.get("total_cost_usd", total_cost)

        # 如果还是没有status，根据end_time推断
        if status == "unknown":
            if end_time:
                status = "completed"
            else:
                status = "running"

        # 如果没有从数据库获取total_events，使用events长度
        if total_events == 0:
            total_events = len(events)

        # 提取tags（可能在metadata中）
        tags = metadata.get("tags", trace_dict.get("tags", []))

        # 提取quality_score和cost_efficiency（可能在metadata中）
        quality_score = metadata.get("quality_score", trace_dict.get("quality_score"))
        cost_efficiency = metadata.get("cost_efficiency", trace_dict.get("cost_efficiency"))

        return TraceMetadata(
            trace_id=trace_dict.get("trace_id", "unknown"),
            agent_name=trace_dict.get("agent_name", "unknown"),
            start_time=start_time or datetime.now(),
            end_time=end_time,
            duration_seconds=duration,
            status=status,
            total_events=total_events,
            llm_calls_count=llm_calls_count,
            total_tokens=total_tokens,
            total_cost_usd=total_cost,
            quality_score=quality_score,
            cost_efficiency=cost_efficiency,
            tags=tags,
            metadata=metadata
        )

    def _load_single_trace(self) -> Optional[Trace]:
        """从单个文件加载trace或capture"""
        if self._single_trace_cache is not None:
            return self._single_trace_cache

        if not self.storage_path.exists():
            raise FileNotFoundError(f"Trace file does not exist: {self.storage_path}")

        suffix = self.storage_path.suffix.lower()
        if suffix == ".jsonl":
            with open(self.storage_path, "r", encoding="utf-8") as f:
                first_line = f.readline().strip()
                content = first_line or "{}"
                data = json.loads(content)
        else:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                data = json.load(f)

        if isinstance(data, list):
            # 兼容JSONL解析成列表的情况，取第一项
            data = data[0] if data else {}

        if "trace_id" in data:
            trace = Trace.from_dict(data)
            source_type = "trace_file"
        elif "capture_id" in data:
            trace = self._convert_capture_to_trace(data)
            source_type = "capture_file"
        else:
            raise ValueError("Unsupported file format. Expecting trace_*.json or capture_*.json structure.")

        if trace.metadata is None:
            trace.metadata = {}
        trace.metadata.setdefault("source_path", str(self.storage_path))
        trace.metadata.setdefault("source_type", source_type)

        if not trace.end_time and trace.events:
            trace.end_time = trace.events[-1].timestamp

        self._single_trace_cache = trace
        return trace

    def _convert_capture_to_trace(self, capture: Dict[str, Any]) -> Trace:
        """将PromptCapture格式转换为Trace"""
        trace = Trace(
            trace_id=capture.get("capture_id", str(uuid.uuid4())),
            agent_name=capture.get("agent_name", "unknown"),
            task_id=capture.get("metadata", {}).get("task"),
            start_time=capture.get("start_time", time.time()),
            end_time=capture.get("end_time"),
            events=[],
            metadata=capture.get("metadata", {}).copy()
        )

        requests = capture.get("requests", [])
        responses = capture.get("responses", [])
        tool_calls = capture.get("tool_calls", [])

        for idx, request in enumerate(requests):
            req_timestamp = request.get("timestamp", trace.start_time)
            trace.events.append(
                TraceEvent(
                    event_id=str(uuid.uuid4()),
                    trace_id=trace.trace_id,
                    event_type=EventType.PROMPT,
                    timestamp=req_timestamp,
                    data=request
                )
            )

            if idx < len(responses):
                response = responses[idx]
                resp_timestamp = response.get("timestamp", req_timestamp)
                trace.events.append(
                    TraceEvent(
                        event_id=str(uuid.uuid4()),
                        trace_id=trace.trace_id,
                        event_type=EventType.MODEL_RESPONSE,
                        timestamp=resp_timestamp,
                        data=response
                    )
                )

        for tool_call in tool_calls:
            tool_timestamp = tool_call.get("timestamp", trace.start_time)
            trace.events.append(
                TraceEvent(
                    event_id=str(uuid.uuid4()),
                    trace_id=trace.trace_id,
                    event_type=EventType.TOOL_CALL,
                    timestamp=tool_timestamp,
                    data=tool_call
                )
            )

        statistics = capture.get("statistics", {})
        trace.metadata.setdefault("_db_total_tokens", statistics.get("total_tokens", 0))

        if not trace.end_time and trace.events:
            trace.end_time = trace.events[-1].timestamp

        return trace

    def get_unique_agent_names(self, traces: List[TraceMetadata]) -> List[str]:
        """获取所有唯一的agent名称

        Args:
            traces: TraceMetadata列表

        Returns:
            唯一的agent名称列表
        """
        return sorted(list(set(t.agent_name for t in traces)))

    def get_all_tags(self, traces: List[TraceMetadata]) -> List[str]:
        """获取所有标签

        Args:
            traces: TraceMetadata列表

        Returns:
            所有标签列表
        """
        all_tags = set()
        for trace in traces:
            all_tags.update(trace.tags)
        return sorted(list(all_tags))
