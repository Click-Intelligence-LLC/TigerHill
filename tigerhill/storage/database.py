"""
数据库管理器 - 提供SQLite数据库连接和基本操作

提供功能:
1. 数据库连接管理（单例模式）
2. 连接池管理
3. 基本CRUD操作
4. 事务管理
5. 数据库初始化和迁移
"""

import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class DatabaseManager:
    """SQLite数据库管理器（单例模式）"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, db_path: str = None):
        """实现单例模式"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, db_path: str = None):
        """初始化数据库管理器

        Args:
            db_path: 数据库文件路径，默认为 ./tigerhill.db
        """
        # 避免重复初始化
        if hasattr(self, '_initialized') and self._initialized:
            return

        self.db_path = db_path or str(Path.cwd() / "tigerhill.db")
        self._local = threading.local()  # 线程本地存储
        self._initialized = True
        self._in_transaction = False  # 事务状态标志

        logger.info(f"DatabaseManager initialized with db_path: {self.db_path}")

    def get_connection(self) -> sqlite3.Connection:
        """获取当前线程的数据库连接

        每个线程维护自己的连接，避免线程安全问题
        """
        if not hasattr(self._local, 'connection') or self._local.connection is None:
            self._local.connection = self._create_connection()
        return self._local.connection

    def _create_connection(self) -> sqlite3.Connection:
        """创建新的数据库连接"""
        conn = sqlite3.connect(
            self.db_path,
            check_same_thread=False,
            isolation_level='DEFERRED'  # 使用DEFERRED模式支持显式事务
        )

        # 启用外键约束
        conn.execute("PRAGMA foreign_keys = ON")

        # 启用WAL模式提高并发性能
        conn.execute("PRAGMA journal_mode = WAL")

        # 设置Row Factory，使查询结果可以像字典一样访问
        conn.row_factory = sqlite3.Row

        logger.debug(f"Created new database connection for thread {threading.current_thread().name}")
        return conn

    def close_connection(self):
        """关闭当前线程的数据库连接"""
        if hasattr(self._local, 'connection') and self._local.connection:
            self._local.connection.close()
            self._local.connection = None
            logger.debug(f"Closed database connection for thread {threading.current_thread().name}")

    @contextmanager
    def transaction(self):
        """事务上下文管理器

        使用示例:
            with db.transaction():
                db.execute("INSERT INTO ...")
                db.execute("UPDATE ...")
        """
        conn = self.get_connection()
        self._in_transaction = True
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Transaction rolled back: {e}")
            raise
        finally:
            self._in_transaction = False

    def execute(self, sql: str, params: Tuple = None) -> sqlite3.Cursor:
        """执行SQL语句

        Args:
            sql: SQL语句
            params: 参数元组

        Returns:
            游标对象
        """
        conn = self.get_connection()
        try:
            if params:
                cursor = conn.execute(sql, params)
            else:
                cursor = conn.execute(sql)
            # 只有在非事务模式下才自动提交
            if not self._in_transaction:
                conn.commit()
            return cursor
        except sqlite3.Error as e:
            logger.error(f"SQL execution error: {e}")
            logger.error(f"SQL: {sql}")
            logger.error(f"Params: {params}")
            raise

    def execute_many(self, sql: str, params_list: List[Tuple]) -> None:
        """批量执行SQL语句

        Args:
            sql: SQL语句
            params_list: 参数列表
        """
        conn = self.get_connection()
        try:
            conn.executemany(sql, params_list)
            # 只有在非事务模式下才自动提交
            if not self._in_transaction:
                conn.commit()
        except sqlite3.Error as e:
            logger.error(f"SQL batch execution error: {e}")
            raise

    def fetch_one(self, sql: str, params: Tuple = None) -> Optional[Dict[str, Any]]:
        """查询单条记录

        Args:
            sql: SQL查询语句
            params: 参数元组

        Returns:
            字典形式的记录，如果不存在则返回None
        """
        conn = self.get_connection()
        try:
            if params:
                cursor = conn.execute(sql, params)
            else:
                cursor = conn.execute(sql)
            row = cursor.fetchone()
            return dict(row) if row else None
        except sqlite3.Error as e:
            logger.error(f"SQL query error: {e}")
            raise

    def fetch_all(self, sql: str, params: Tuple = None) -> List[Dict[str, Any]]:
        """查询多条记录

        Args:
            sql: SQL查询语句
            params: 参数元组

        Returns:
            字典列表
        """
        conn = self.get_connection()
        try:
            if params:
                cursor = conn.execute(sql, params)
            else:
                cursor = conn.execute(sql)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except sqlite3.Error as e:
            logger.error(f"SQL query error: {e}")
            raise

    def insert(self, table: str, data: Dict[str, Any]) -> int:
        """插入记录

        Args:
            table: 表名
            data: 字段字典

        Returns:
            插入记录的ID
        """
        fields = ', '.join(data.keys())
        placeholders = ', '.join(['?'] * len(data))
        sql = f"INSERT INTO {table} ({fields}) VALUES ({placeholders})"

        cursor = self.execute(sql, tuple(data.values()))
        return cursor.lastrowid

    def update(self, table: str, data: Dict[str, Any], where: str, where_params: Tuple = None) -> int:
        """更新记录

        Args:
            table: 表名
            data: 要更新的字段字典
            where: WHERE条件
            where_params: WHERE条件参数

        Returns:
            受影响的行数
        """
        set_clause = ', '.join([f"{k} = ?" for k in data.keys()])
        sql = f"UPDATE {table} SET {set_clause} WHERE {where}"

        params = tuple(data.values()) + (where_params or ())
        cursor = self.execute(sql, params)
        return cursor.rowcount

    def delete(self, table: str, where: str, where_params: Tuple = None) -> int:
        """删除记录

        Args:
            table: 表名
            where: WHERE条件
            where_params: WHERE条件参数

        Returns:
            受影响的行数
        """
        sql = f"DELETE FROM {table} WHERE {where}"
        cursor = self.execute(sql, where_params)
        return cursor.rowcount

    def table_exists(self, table_name: str) -> bool:
        """检查表是否存在

        Args:
            table_name: 表名

        Returns:
            表是否存在
        """
        sql = "SELECT name FROM sqlite_master WHERE type='table' AND name=?"
        result = self.fetch_one(sql, (table_name,))
        return result is not None

    def get_schema_version(self) -> Optional[int]:
        """获取当前数据库Schema版本

        Returns:
            版本号，如果表不存在返回None
        """
        if not self.table_exists('schema_version'):
            return None

        sql = "SELECT MAX(version) as version FROM schema_version"
        result = self.fetch_one(sql)
        return result['version'] if result else None

    def initialize_database(self, schema_sql_path: str = None):
        """初始化数据库

        Args:
            schema_sql_path: Schema SQL文件路径，默认使用内置的v1 schema
        """
        # 如果数据库已存在且有schema_version表，则不重新初始化
        if self.table_exists('schema_version'):
            version = self.get_schema_version()
            logger.info(f"Database already initialized with schema version {version}")
            return

        # 读取并执行SQL脚本
        if schema_sql_path is None:
            # 使用默认的v1 schema
            schema_sql_path = str(Path(__file__).parent.parent.parent / "scripts" / "migrations" / "v1_initial_schema.sql")

        schema_sql_path = Path(schema_sql_path)
        if not schema_sql_path.exists():
            raise FileNotFoundError(f"Schema SQL file not found: {schema_sql_path}")

        with open(schema_sql_path, 'r', encoding='utf-8') as f:
            schema_sql = f.read()

        # 执行Schema创建脚本
        conn = self.get_connection()
        try:
            conn.executescript(schema_sql)
            conn.commit()
            logger.info(f"Database initialized successfully from {schema_sql_path}")
        except sqlite3.Error as e:
            logger.error(f"Failed to initialize database: {e}")
            raise

    def __del__(self):
        """析构函数，确保连接被关闭"""
        self.close_connection()


# 全局数据库管理器实例
_db_manager: Optional[DatabaseManager] = None


def get_db_manager(db_path: str = None) -> DatabaseManager:
    """获取全局数据库管理器实例

    Args:
        db_path: 数据库文件路径

    Returns:
        DatabaseManager实例
    """
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager(db_path)
    return _db_manager
