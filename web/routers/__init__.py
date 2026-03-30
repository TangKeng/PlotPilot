"""
路由模块：处理HTTP请求和响应
"""

from web.routers.stats import create_stats_router

__all__ = [
    "create_stats_router"
]
