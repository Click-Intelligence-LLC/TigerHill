"""Formatting utilities for dashboard"""

from datetime import datetime
from typing import Any


def format_number(num: float, precision: int = 2) -> str:
    """格式化数字，添加千分位分隔符

    Args:
        num: 数字
        precision: 小数位数

    Returns:
        格式化后的字符串
    """
    if num >= 1_000_000:
        return f"{num / 1_000_000:.{precision}f}M"
    elif num >= 1_000:
        return f"{num / 1_000:.{precision}f}K"
    else:
        return f"{num:.{precision}f}"


def format_currency(amount: float) -> str:
    """格式化货币

    Args:
        amount: 金额

    Returns:
        格式化后的美元字符串
    """
    return f"${amount:.4f}"


def format_duration(seconds: float) -> str:
    """格式化时长

    Args:
        seconds: 秒数

    Returns:
        格式化后的时长字符串
    """
    if seconds < 60:
        return f"{seconds:.1f}秒"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}分钟"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}小时"


def format_datetime(dt: datetime) -> str:
    """格式化日期时间

    Args:
        dt: datetime对象

    Returns:
        格式化后的日期时间字符串
    """
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def format_date(dt: datetime) -> str:
    """格式化日期

    Args:
        dt: datetime对象

    Returns:
        格式化后的日期字符串
    """
    return dt.strftime("%Y-%m-%d")


def format_percentage(value: float) -> str:
    """格式化百分比

    Args:
        value: 数值（0-100）

    Returns:
        格式化后的百分比字符串
    """
    return f"{value:.1f}%"


def truncate_text(text: str, max_length: int = 100) -> str:
    """截断文本

    Args:
        text: 原始文本
        max_length: 最大长度

    Returns:
        截断后的文本
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."
