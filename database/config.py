"""
Author: SpaceDandy13 liudonglin301@gmail.com
FilePath: \egoscale_api\database\config.py
Description: PostgreSQL数据库配置模块
"""

import os
import asyncpg
from urllib.parse import urlparse


class DatabaseConfig:
    def __init__(self):
        self.database_url = os.getenv("DATABASE_URL")
        if not self.database_url:
            raise ValueError("DATABASE_URL environment variable is required")
        
    def get_postgres_config(self) -> dict:
        """获取PostgreSQL连接配置"""
        if not self.database_url.startswith(("postgresql://", "postgres://")):
            raise ValueError("DATABASE_URL must be a PostgreSQL connection string")
        
        parsed = urlparse(self.database_url)
        return {
            "host": parsed.hostname,
            "port": parsed.port or 5432,
            "user": parsed.username,
            "password": parsed.password,
            "database": parsed.path[1:] if parsed.path else "postgres"
        }


class DatabaseConnection:
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self.pool = None
    
    async def connect(self):
        """连接到PostgreSQL数据库"""
        postgres_config = self.config.get_postgres_config()
        
        # 针对1000-10000用户规模优化的连接池配置
        pool_config = {
            **postgres_config,
            "min_size": 5,                    # 最小连接数，保证基本可用性
            "max_size": 18,                   # 最大连接数，留2个给Railway系统使用
            "max_queries": 5000,              # 每个连接最多执行5000次查询后回收
            "max_inactive_connection_lifetime": 300,  # 连接空闲5分钟后回收
            "command_timeout": 30            # 单个命令最大执行时间30秒
        }

        self.pool = await asyncpg.create_pool(**pool_config)
        return self.pool

    async def close(self):
        """关闭数据库连接池"""
        if self.pool:
            await self.pool.close()
    
    def get_connection(self):
        """获取连接池"""
        return self.pool
