#!/usr/bin/env python3
"""
TigerHill数据迁移工具
将JSONL格式的trace数据迁移到SQLite数据库

功能:
1. 从JSONL文件加载trace数据
2. 转换为数据库格式并写入SQLite
3. 支持增量迁移（跳过已存在的traces）
4. 显示进度和统计信息
5. 完整的错误处理和回滚机制
"""

import argparse
import json
import sys
from pathlib import Path
from typing import List, Dict, Any, Tuple
import logging

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tigerhill.storage.trace_store import Trace, TraceEvent
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


def load_trace_from_json(file_path: Path) -> Trace:
    """从JSON文件加载trace

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
        return Trace.from_dict(data)
    except Exception as e:
        raise ValueError(f"Failed to load trace from {file_path}: {e}")


def trace_exists(db: DatabaseManager, trace_id: str) -> bool:
    """检查trace是否已存在于数据库

    Args:
        db: 数据库管理器
        trace_id: Trace ID

    Returns:
        是否存在
    """
    result = db.fetch_one(
        "SELECT trace_id FROM traces WHERE trace_id = ?",
        (trace_id,)
    )
    return result is not None


def migrate_trace(db: DatabaseManager, trace: Trace) -> Tuple[bool, str]:
    """迁移单个trace到数据库

    Args:
        db: 数据库管理器
        trace: Trace对象

    Returns:
        (是否成功, 错误信息)
    """
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
    verbose: bool = False
) -> MigrationStats:
    """迁移整个目录的trace文件

    Args:
        source_dir: 源目录路径
        db_path: 目标数据库路径
        incremental: 是否增量迁移（跳过已存在的）
        verbose: 是否显示详细日志

    Returns:
        迁移统计信息
    """
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

    # 查找所有trace JSON文件
    json_files = list(source_dir.glob("trace_*.json"))
    stats.total_files = len(json_files)

    if stats.total_files == 0:
        logger.warning(f"No trace files found in {source_dir}")
        return stats

    logger.info(f"Found {stats.total_files} trace files")
    print(f"\n开始迁移 {stats.total_files} 个trace文件...\n")

    # 处理每个文件
    for idx, file_path in enumerate(json_files, 1):
        try:
            # 加载trace
            trace = load_trace_from_json(file_path)

            # 检查是否已存在
            if incremental and trace_exists(db, trace.trace_id):
                stats.skipped += 1
                if verbose:
                    logger.info(f"[{idx}/{stats.total_files}] Skipped (exists): {trace.trace_id}")
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
                        f"[{idx}/{stats.total_files}] Success: {trace.trace_id} "
                        f"({len(trace.events)} events)"
                    )
                else:
                    print(f"\r进度: {idx}/{stats.total_files} | 成功: {stats.processed} | 跳过: {stats.skipped} | 失败: {stats.failed}", end='')
            else:
                stats.failed += 1
                logger.error(f"[{idx}/{stats.total_files}] Failed: {file_path.name} - {error}")

        except Exception as e:
            stats.failed += 1
            logger.error(f"[{idx}/{stats.total_files}] Error processing {file_path.name}: {e}")

    print()  # 换行
    return stats


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='Migrate TigerHill trace data from JSONL to SQLite',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # 迁移默认目录到默认数据库
  python scripts/migrate_to_db.py

  # 指定源目录和目标数据库
  python scripts/migrate_to_db.py -s ./test_traces -d ./tigerhill_test.db

  # 完全重新迁移（覆盖已存在的）
  python scripts/migrate_to_db.py --no-incremental

  # 显示详细日志
  python scripts/migrate_to_db.py -v
        """
    )

    parser.add_argument(
        '-s', '--source',
        type=str,
        default='./test_traces',
        help='Source directory containing trace JSON files (default: ./test_traces)'
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
    print("TigerHill 数据迁移工具")
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
