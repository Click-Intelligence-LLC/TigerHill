#!/usr/bin/env python3
"""
TigerHill Capture数据迁移工具
将capture_*.json格式的数据迁移到SQLite数据库

支持两种文件格式:
1. capture_*.json - PromptCapture生成的格式
2. trace_*.json - TraceStore生成的格式
"""

import argparse
import json
import sys
from pathlib import Path
from typing import List, Dict, Any, Tuple
import logging
from datetime import datetime

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tigerhill.storage.trace_store import Trace, TraceEvent, EventType
from tigerhill.storage.database import DatabaseManager

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MigrationStats:
    """迁移统计信息"""
    def __init__(self):
        self.total_files = 0
        self.processed = 0
        self.skipped = 0
        self.failed = 0
        self.traces_inserted = 0
        self.events_inserted = 0

    def __str__(self):
        return f"""
迁移统计:
  总文件数: {self.total_files}
  处理成功: {self.processed}
  已存在跳过: {self.skipped}
  处理失败: {self.failed}
  插入traces: {self.traces_inserted}
  插入events: {self.events_inserted}
"""


def convert_session_to_trace(session_data: Dict[str, Any]) -> Trace:
    """将gemini session格式转换为Trace格式

    Session格式来自gemini_session_interceptor.cjs，包含turns数组

    Args:
        session_data: session_*.json的数据

    Returns:
        Trace对象
    """
    import uuid

    # 创建Trace对象
    trace = Trace(
        trace_id=session_data.get('session_id', 'unknown'),
        agent_name=session_data.get('agent_name', 'gemini-cli'),
        task_id='gemini-cli-session',
        start_time=session_data.get('start_time', 0),
        end_time=session_data.get('end_time'),
        events=[],
        metadata=session_data.get('metadata', {})
    )

    # 处理conversation_history（如果存在Phase 1增强的结构）
    conv_history = session_data.get('conversation_history', {})
    if conv_history and 'system_prompt' in conv_history:
        trace.metadata['system_prompt'] = conv_history.get('system_prompt')

    # 遍历所有turns
    turns = session_data.get('turns', [])
    for turn in turns:
        turn_number = turn.get('turn_number', 0)
        requests = turn.get('requests', [])
        responses = turn.get('responses', [])  # 注意是复数

        # 找到generateContent或streamGenerateContent请求（通常是最后一个request）
        gen_request = None
        for req in requests:
            url = req.get('url', '')
            if 'generateContent' in url or 'streamGenerateContent' in url:
                gen_request = req
                break

        if not gen_request:
            continue

        # 提取用户输入内容
        user_content = ""
        contents = gen_request.get('contents', [])
        if contents and isinstance(contents, list):
            # 从contents数组中提取text
            for content_item in contents:
                if content_item.get('role') == 'user':
                    parts = content_item.get('parts', [])
                    for part in parts:
                        if isinstance(part, dict) and 'text' in part:
                            user_content += part['text']

        # 如果没有从contents提取到，尝试user_input字段
        if not user_content:
            user_content = gen_request.get('user_input', '')

        # 创建prompt event
        prompt_event = TraceEvent(
            event_id=str(uuid.uuid4()),
            trace_id=trace.trace_id,
            event_type=EventType.PROMPT,
            timestamp=gen_request.get('timestamp', trace.start_time),
            data={
                'type': 'prompt',
                'content': user_content,
                'model': gen_request.get('model', ''),
                'request_id': gen_request.get('request_id', ''),
                'generation_config': gen_request.get('generation_config'),
                'safety_settings': gen_request.get('safety_settings'),
                'tools': gen_request.get('tools'),
                'system_prompt': gen_request.get('system_prompt') or gen_request.get('system_instruction'),
                'turn_number': turn_number,
            }
        )
        trace.events.append(prompt_event)

        # 处理responses（可能有多个response，取generateContent的响应）
        if responses:
            # 找到generateContent的响应（通常是最后一个）
            gen_response = None
            for resp in responses:
                if resp.get('text'):  # 有文本内容的响应
                    gen_response = resp
                    break

            if gen_response:
                # 提取响应文本（interceptor已经提取好了）
                response_text = gen_response.get('text', '')

                # 如果text为空，尝试从raw_response中提取
                if not response_text and 'raw_response' in gen_response:
                    raw_resp = gen_response['raw_response']
                    candidates = raw_resp.get('candidates', [])
                    if candidates:
                        first_candidate = candidates[0]
                        content = first_candidate.get('content', {})
                        parts = content.get('parts', [])
                        for part in parts:
                            if isinstance(part, dict) and 'text' in part:
                                response_text += part['text']

                # 提取usage信息
                usage_metadata = gen_response.get('usage', {})

                response_event = TraceEvent(
                    event_id=str(uuid.uuid4()),
                    trace_id=trace.trace_id,
                    event_type=EventType.MODEL_RESPONSE,
                    timestamp=gen_response.get('timestamp', prompt_event.timestamp + 0.1),
                    data={
                        'type': 'model_response',
                        'content': response_text,
                        'response_id': gen_response.get('request_id', str(uuid.uuid4())),
                        'full_response': response_text,
                        'usage_metadata': usage_metadata,
                        'turn_number': turn_number,
                        'finish_reason': gen_response.get('finish_reason'),
                    }
                )
                trace.events.append(response_event)

    # 设置结束时间
    if trace.end_time is None:
        if len(trace.events) > 0:
            trace.end_time = trace.events[-1].timestamp
        else:
            trace.end_time = trace.start_time

    return trace


def convert_capture_to_trace(capture_data: Dict[str, Any]) -> Trace:
    """将capture格式转换为Trace格式

    Args:
        capture_data: capture_*.json的数据

    Returns:
        Trace对象
    """
    # 准备events列表
    events = []

    # 创建Trace对象
    trace = Trace(
        trace_id=capture_data.get('capture_id', 'unknown'),
        agent_name=capture_data.get('agent_name', 'unknown'),
        task_id=capture_data.get('metadata', {}).get('task', 'unknown'),
        start_time=capture_data.get('start_time', 0),
        end_time=capture_data.get('end_time'),
        events=events,  # 先传入空列表
        metadata=capture_data.get('metadata', {})
    )

    # 转换requests为prompt events
    import uuid
    requests = capture_data.get('requests', [])
    responses = capture_data.get('responses', [])

    # 创建request-response配对
    for i, request in enumerate(requests):
        # 添加prompt event
        prompt_event = TraceEvent(
            event_id=str(uuid.uuid4()),
            trace_id=trace.trace_id,
            event_type=EventType.PROMPT,
            timestamp=request.get('timestamp', trace.start_time),
            data={
                'type': 'prompt',
                'content': request.get('prompt', ''),
                'model': request.get('model', ''),
                'request_id': request.get('request_id', ''),
                'generation_config': request.get('generation_config'),
                'safety_settings': request.get('safety_settings'),
                'tools': request.get('tools'),
            }
        )
        trace.events.append(prompt_event)

        # 如果有对应的response，添加response event
        if i < len(responses):
            response = responses[i]

            # 尝试提取响应文本和token信息
            response_text = response.get('text', '')

            # 尝试从response中提取usage信息
            usage_metadata = {}
            if 'usage_metadata' in str(response_text):
                # 简单提取（实际应该解析完整的response结构）
                try:
                    # 这里简化处理，实际可能需要更复杂的解析
                    usage_metadata = {}
                except:
                    pass

            response_event = TraceEvent(
                event_id=str(uuid.uuid4()),
                trace_id=trace.trace_id,
                event_type=EventType.MODEL_RESPONSE,
                timestamp=response.get('timestamp', prompt_event.timestamp + 0.1),
                data={
                    'type': 'model_response',
                    'content': response_text[:1000] if len(response_text) > 1000 else response_text,  # 限制长度
                    'response_id': response.get('response_id', ''),
                    'full_response': response_text,
                }
            )
            trace.events.append(response_event)

    # 添加tool_calls
    for tool_call in capture_data.get('tool_calls', []):
        tool_event = TraceEvent(
            event_id=str(uuid.uuid4()),
            trace_id=trace.trace_id,
            event_type=EventType.TOOL_CALL,
            timestamp=tool_call.get('timestamp', trace.start_time),
            data={
                'type': 'tool_call',
                'tool_name': tool_call.get('tool_name', ''),
                'arguments': tool_call.get('arguments', {}),
            }
        )
        trace.events.append(tool_event)

    # 设置结束时间
    if trace.end_time is None and len(trace.events) > 0:
        trace.end_time = trace.events[-1].timestamp

    return trace


def load_file(file_path: Path) -> Trace:
    """从JSON文件加载trace或capture数据

    Args:
        file_path: JSON文件路径

    Returns:
        Trace对象

    Raises:
        ValueError: 如果文件格式无效
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 判断文件类型
        if 'session_id' in data:
            # session格式（gemini_session_interceptor.cjs）
            logger.debug(f"Detected session format: {file_path.name}")
            return convert_session_to_trace(data)
        elif 'capture_id' in data:
            # capture格式
            logger.debug(f"Detected capture format: {file_path.name}")
            return convert_capture_to_trace(data)
        elif 'trace_id' in data:
            # trace格式
            logger.debug(f"Detected trace format: {file_path.name}")
            return Trace.from_dict(data)
        else:
            raise ValueError(f"Unknown file format (no session_id, capture_id or trace_id)")

    except Exception as e:
        raise ValueError(f"Failed to load file {file_path}: {e}")


def trace_exists(db: DatabaseManager, trace_id: str) -> bool:
    """检查trace是否已存在于数据库"""
    result = db.fetch_one(
        "SELECT trace_id FROM traces WHERE trace_id = ?",
        (trace_id,)
    )
    return result is not None


def migrate_trace(db: DatabaseManager, trace: Trace) -> Tuple[bool, str]:
    """迁移单个trace到数据库"""
    try:
        with db.transaction():
            # 1. 插入trace主记录
            trace_dict = trace.to_db_dict()
            db.insert('traces', trace_dict)

            # 2. 插入所有events
            for idx, event in enumerate(trace.events):
                event_dict = event.to_db_dict(sequence_number=idx)
                db.insert('events', event_dict)

        return True, ""
    except Exception as e:
        return False, str(e)


def migrate_directory(
    source_dir: Path,
    db_path: str,
    incremental: bool = True,
    verbose: bool = False,
    file_pattern: str = "*.json"
) -> MigrationStats:
    """迁移整个目录的文件"""
    stats = MigrationStats()

    # 初始化数据库
    logger.info(f"Initializing database: {db_path}")
    db = DatabaseManager(db_path)

    # 确保数据库schema已创建
    if not db.table_exists('traces'):
        logger.info("Database schema not found, initializing...")
        schema_path = project_root / "scripts" / "migrations" / "v1_initial_schema.sql"
        db.initialize_database(str(schema_path))
        logger.info("Database schema initialized")

    # 查找所有JSON文件
    json_files = []

    # 支持多种文件模式
    patterns = [
        "capture_*.json",  # PromptCapture格式
        "trace_*.json",    # TraceStore格式
        "session_*.json",  # Gemini session格式 (gemini_session_interceptor.cjs)
    ]

    for pattern in patterns:
        json_files.extend(list(source_dir.glob(pattern)))

    # 去重
    json_files = list(set(json_files))
    stats.total_files = len(json_files)

    if stats.total_files == 0:
        logger.warning(f"No capture or trace files found in {source_dir}")
        logger.info(f"Looking for patterns: {patterns}")
        return stats

    logger.info(f"Found {stats.total_files} files")
    print(f"\n开始迁移 {stats.total_files} 个文件...\n")

    # 处理每个文件
    for idx, file_path in enumerate(sorted(json_files), 1):
        try:
            # 加载文件
            trace = load_file(file_path)

            # 检查是否已存在
            if incremental and trace_exists(db, trace.trace_id):
                stats.skipped += 1
                if verbose:
                    logger.info(f"[{idx}/{stats.total_files}] Skipped (exists): {trace.trace_id[:16]}... from {file_path.name}")
                else:
                    print(f"\r进度: {idx}/{stats.total_files} | 成功: {stats.processed} | 跳过: {stats.skipped} | 失败: {stats.failed}", end='')
                continue

            # 迁移trace
            success, error = migrate_trace(db, trace)

            if success:
                stats.processed += 1
                stats.traces_inserted += 1
                stats.events_inserted += len(trace.events)
                if verbose:
                    logger.info(
                        f"[{idx}/{stats.total_files}] Success: {trace.trace_id[:16]}... "
                        f"({len(trace.events)} events) from {file_path.name}"
                    )
                else:
                    print(f"\r进度: {idx}/{stats.total_files} | 成功: {stats.processed} | 跳过: {stats.skipped} | 失败: {stats.failed}", end='')
            else:
                stats.failed += 1
                logger.error(f"[{idx}/{stats.total_files}] Failed: {file_path.name} - {error}")

        except Exception as e:
            stats.failed += 1
            logger.error(f"[{idx}/{stats.total_files}] Error processing {file_path.name}: {e}")
            if verbose:
                import traceback
                traceback.print_exc()

    print()  # 换行
    return stats


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='Migrate TigerHill capture/trace data to SQLite',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # 迁移capture目录到数据库
  python scripts/migrate_captures_to_db.py -s ./prompt_captures -d ./tigerhill.db

  # 迁移swarm_agent目录
  python scripts/migrate_captures_to_db.py -s ./prompt_captures/swarm_agent -d ./swarm.db

  # 显示详细日志
  python scripts/migrate_captures_to_db.py -s ./prompt_captures -d ./tigerhill.db -v

  # 覆盖已存在的traces
  python scripts/migrate_captures_to_db.py -s ./prompt_captures -d ./tigerhill.db --no-incremental
        """
    )

    parser.add_argument(
        '-s', '--source',
        type=str,
        default='./prompt_captures',
        help='Source directory containing capture/trace JSON files (default: ./prompt_captures)'
    )

    parser.add_argument(
        '-d', '--database',
        type=str,
        default='./tigerhill.db',
        help='Target SQLite database path (default: ./tigerhill.db)'
    )

    parser.add_argument(
        '--no-incremental',
        action='store_true',
        help='Disable incremental migration (re-insert existing traces)'
    )

    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )

    args = parser.parse_args()

    # 验证源目录
    source_dir = Path(args.source)
    if not source_dir.exists():
        logger.error(f"Source directory does not exist: {source_dir}")
        sys.exit(1)

    if not source_dir.is_dir():
        logger.error(f"Source path is not a directory: {source_dir}")
        sys.exit(1)

    # 显示配置
    print("=" * 60)
    print("TigerHill Capture数据迁移工具")
    print("=" * 60)
    print(f"源目录: {source_dir.absolute()}")
    print(f"目标数据库: {Path(args.database).absolute()}")
    print(f"增量迁移: {'是' if not args.no_incremental else '否'}")
    print(f"详细日志: {'是' if args.verbose else '否'}")
    print("=" * 60)
    print()

    # 执行迁移
    try:
        stats = migrate_directory(
            source_dir=source_dir,
            db_path=args.database,
            incremental=not args.no_incremental,
            verbose=args.verbose
        )

        # 显示统计信息
        print("\n" + "=" * 60)
        print(stats)
        print("=" * 60)

        # 返回状态码
        if stats.failed > 0:
            logger.warning(f"Migration completed with {stats.failed} failures")
            sys.exit(1)
        else:
            logger.info("Migration completed successfully!")
            sys.exit(0)

    except KeyboardInterrupt:
        print("\n\nMigration interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Migration failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
