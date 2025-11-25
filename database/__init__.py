"""
Copyright © Krypton 2019-Present - https://github.com/kkrypt0nn (https://krypton.ninja)
Description:
🐍 A simple template to start to code your own and personalized Discord bot in Python

Version: 6.3.0
"""

import asyncpg
import asyncio
from datetime import datetime, date, timedelta
from typing import Union, Optional
import logging


class DatabaseManager:
    def __init__(self, *, connection):
        """初始化数据库管理器
        
        Args:
            connection: asyncpg.Pool - PostgreSQL连接池
        """
        self.pool = connection
    
    async def get_pool_status(self) -> dict:
        """获取连接池状态信息"""
        return {
            "size": self.pool.get_size(),
            "idle": self.pool.get_idle_size(),
            "min_size": self.pool.get_min_size(),
            "max_size": self.pool.get_max_size(),
        }
    
    # 移除所有对_convert_to_postgres的调用
    # 确保所有查询都直接使用PostgreSQL语法
    
    async def execute_query(self, query: str, params: tuple = ()):
        """统一的查询执行方法，带重试机制"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                async with self.pool.acquire() as conn:
                    return await conn.fetch(query, *params)
            except (asyncpg.PostgresConnectionError, asyncpg.InterfaceError, asyncpg.InternalServerError) as e:
                if attempt == max_retries - 1:
                    logging.error(f"数据库连接失败，已重试{max_retries}次: {e}")
                    raise
                logging.warning(f"数据库连接失败，正在重试 {attempt + 1}/{max_retries}: {e}")
                await asyncio.sleep(0.1 * (2 ** attempt))  # 指数退避
            except Exception as e:
                # 对于其他类型的错误（如SQL语法错误），不重试
                logging.error(f"数据库查询错误: {e}")
                raise
    
    async def execute_single(self, query: str, params: tuple = ()):
        """执行单条查询，带重试机制"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                async with self.pool.acquire() as conn:
                    return await conn.fetchrow(query, *params)
            except (asyncpg.PostgresConnectionError, asyncpg.InterfaceError, asyncpg.InternalServerError) as e:
                if attempt == max_retries - 1:
                    logging.error(f"数据库连接失败，已重试{max_retries}次: {e}")
                    raise
                logging.warning(f"数据库连接失败，正在重试 {attempt + 1}/{max_retries}: {e}")
                await asyncio.sleep(0.1 * (2 ** attempt))
            except Exception as e:
                logging.error(f"数据库查询错误: {e}")
                raise
    
    async def execute_write(self, query: str, params: tuple = ()):
        """执行写入操作，带重试机制"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                async with self.pool.acquire() as conn:
                    await conn.execute(query, *params)
                return
            except (asyncpg.PostgresConnectionError, asyncpg.InterfaceError, asyncpg.InternalServerError) as e:
                if attempt == max_retries - 1:
                    logging.error(f"数据库连接失败，已重试{max_retries}次: {e}")
                    raise
                logging.warning(f"数据库连接失败，正在重试 {attempt + 1}/{max_retries}: {e}")
                await asyncio.sleep(0.1 * (2 ** attempt))
            except Exception as e:
                logging.error(f"数据库写入错误: {e}")
                raise

    async def add_warn(
        self, user_id: int, server_id: int, moderator_id: int, reason: str
    ) -> int:
        """
        This function will add a warn to the database.

        :param user_id: The ID of the user that should be warned.
        :param reason: The reason why the user should be warned.
        """
        result = await self.execute_single(
            "SELECT id FROM warns WHERE user_id=$1 AND server_id=$2 ORDER BY id DESC LIMIT 1",
            (user_id, server_id)
        )
        warn_id = result[0] + 1 if result is not None else 1
        await self.execute_write(
            "INSERT INTO warns(id, user_id, server_id, moderator_id, reason) VALUES ($1, $2, $3, $4, $5)",
            (warn_id, user_id, server_id, moderator_id, reason)
        )
        return warn_id

    async def remove_warn(self, warn_id: int, user_id: int, server_id: int) -> int:
        """
        This function will remove a warn from the database.

        :param warn_id: The ID of the warn.
        :param user_id: The ID of the user that was warned.
        :param server_id: The ID of the server where the user has been warned
        """
        await self.execute_write(
            "DELETE FROM warns WHERE id=$1 AND user_id=$2 AND server_id=$3",
            (warn_id, user_id, server_id)
        )
        return await self.get_warnings_count(user_id, server_id)

    async def get_warnings(self, user_id: int, server_id: int) -> list:
        """
        This function will get all the warnings of a user.

        :param user_id: The ID of the user that should be checked.
        :param server_id: The ID of the server that should be checked.
        :return: A list of all the warnings of the user.
        """
        results = await self.execute_query(
            "SELECT user_id, server_id, moderator_id, reason, EXTRACT(EPOCH FROM created_at) as created_at FROM warns WHERE user_id=$1 AND server_id=$2",
            (user_id, server_id)
        )
        return results

    async def get_warnings_count(self, user_id: int, server_id: int) -> int:
        """
        This function will get the number of warnings of a user.

        :param user_id: The ID of the user that should be checked.
        :param server_id: The ID of the server that should be checked.
        :return: The number of warnings of the user.
        """
        result = await self.execute_single(
            "SELECT COUNT(*) FROM warns WHERE user_id=$1 AND server_id=$2",
            (user_id, server_id)
        )
        return result[0] if result else 0

    async def get_user_points(self, user_id: int, server_id: int) -> dict:
        """
        获取用户的积分信息 - 简化版本，直接查询
        """
        import time
        start_time = time.time()
        
        try:
            conn_start = time.time()
            async with self.pool.acquire() as conn:
                conn_time = time.time() - conn_start
                logging.info(f"⏱️ [DB-PERF] 连接池获取连接耗时: {conn_time:.3f}s")
                
                query_start = time.time()
                result = await conn.fetchrow(
                    "SELECT COALESCE(points, 0) as points, COALESCE(total_checkins, 0) as total_checkins FROM user_points WHERE user_id=$1 AND server_id=$2",
                    str(user_id), str(server_id)
                )
                query_time = time.time() - query_start
                total_time = time.time() - start_time
                
                logging.info(f"⏱️ [DB-PERF] SQL查询耗时: {query_time:.3f}s")
                logging.info(f"⏱️ [DB-PERF] get_user_points总耗时: {total_time:.3f}s")
                
                if conn_time > 1.0:
                    logging.warning(f"🐌 [DB-SLOW] 连接池获取连接过慢: {conn_time:.3f}s")
                if query_time > 0.5:
                    logging.warning(f"🐌 [DB-SLOW] SQL查询过慢: {query_time:.3f}s")
                
                if result:
                    return {
                        "points": result[0],
                        "total_checkins": result[1]
                    }
                return {"points": 0, "total_checkins": 0}
                
        except Exception as e:
            error_time = time.time() - start_time
            logging.error(f"获取用户积分失败 (耗时{error_time:.3f}s): {e}")
            return {"points": 0, "total_checkins": 0}

    async def add_points(self, user_id: int, server_id: int, points: int) -> int:
        """
        为用户添加积分 - 使用事务保证原子性（优化版）
        """
        # 添加积分限制
        if abs(points) > 10000:  # 单次最多加减10000分
            raise ValueError("单次积分变更不能超过10000分")
        
        async with self.pool.acquire() as conn:
            # 简化版本：直接更新积分，不重新计算签到次数
            result = await conn.fetchrow(
                """INSERT INTO user_points (user_id, server_id, points, total_checkins) 
                   VALUES ($1, $2, $3, 0)
                   ON CONFLICT (user_id, server_id) 
                   DO UPDATE SET 
                       points = GREATEST(0, user_points.points + $3),  -- 不允许负积分
                       updated_at = NOW()
                   RETURNING points""",
                str(user_id), str(server_id), points
            )
            return result[0] if result else 0

    async def daily_checkin(self, user_id: int, server_id: int) -> dict:
        """
        执行每日签到 - 使用事务保证数据一致性
        """
        today = date.today()
        
        async with self.pool.acquire() as conn:
            # 首先检查今天是否已经签到（在事务外检查，避免锁定）
            existing_checkin = await conn.fetchrow(
                "SELECT points_earned, streak_count FROM daily_checkins WHERE user_id=$1 AND server_id=$2 AND checkin_date=$3",
                str(user_id), str(server_id), today
            )
            
            if existing_checkin:
                return {
                    "success": False,
                    "message": "Already checked in today!",
                    "points_earned": existing_checkin[0],
                    "streak": existing_checkin[1]
                }
            
            # 开始事务进行签到
            async with conn.transaction():
                yesterday = today - timedelta(days=1)
                
                # 获取昨天的streak信息，用于计算今天的streak
                yesterday_streak = await self._get_yesterday_streak(conn, user_id, server_id)
                new_streak = yesterday_streak + 1
                
                # 根据连续签到天数计算奖励积分
                base_points = 5
                weekly_bonus = 5 if new_streak % 7 == 0 else 0
                total_points = min(base_points + weekly_bonus, 100)  # 单次最大100分
                
                try:
                    # 尝试插入签到记录
                    await conn.execute(
                        "INSERT INTO daily_checkins (user_id, server_id, checkin_date, points_earned, streak_count) VALUES ($1, $2, $3, $4, $5)",
                        str(user_id), str(server_id), today, total_points, new_streak
                    )
                    
                    # 签到成功，更新用户积分
                    result = await conn.fetchrow(
                        """INSERT INTO user_points (user_id, server_id, points, total_checkins) 
                           VALUES ($1, $2, $3, 1)
                           ON CONFLICT (user_id, server_id) 
                           DO UPDATE SET 
                               points = user_points.points + $3,
                               total_checkins = user_points.total_checkins + 1,
                               updated_at = NOW()
                           RETURNING points""",
                        str(user_id), str(server_id), total_points
                    )
                    
                    new_total = result[0] if result else total_points
                    
                    return {
                        "success": True,
                        "message": "签到成功！",
                        "points_earned": total_points,
                        "streak": new_streak,
                        "total_points": new_total
                    }
                    
                except asyncpg.UniqueViolationError:
                    # 并发情况下，其他请求已经插入了记录
                    # 事务会自动回滚，我们需要重新查询
                    pass
            
            # 如果到这里，说明发生了并发冲突，重新查询今天的签到信息
            existing_checkin = await conn.fetchrow(
                "SELECT points_earned, streak_count FROM daily_checkins WHERE user_id=$1 AND server_id=$2 AND checkin_date=$3",
                str(user_id), str(server_id), today
            )
            
            return {
                "success": False,
                "message": "Already checked in today!",
                "points_earned": existing_checkin[0] if existing_checkin else 0,
                "streak": existing_checkin[1] if existing_checkin else 0
            }
    
    async def _calculate_streak(self, user_id: int, server_id: int) -> int:
        """
        计算用户的连续签到天数
        """
        results = await self.execute_query(
            "SELECT checkin_date FROM daily_checkins WHERE user_id=$1 AND server_id=$2 ORDER BY checkin_date DESC LIMIT 30",
            (str(user_id), str(server_id))
        )
        
        if not results:
            return 0
        
        streak = 0
        current_date = date.today()
        
        for row in results:
            checkin_date = row[0] if isinstance(row[0], date) else datetime.strptime(str(row[0]), "%Y-%m-%d").date()
            
            expected_date = current_date - timedelta(days=streak)
            
            if checkin_date == expected_date:
                streak += 1
            elif checkin_date == expected_date - timedelta(days=1):
                streak += 1
                current_date = checkin_date
            else:
                break
        
        return streak

    async def _get_yesterday_streak(self, conn, user_id: int, server_id: int) -> int:
        """
        获取昨天的签到连续天数，如果昨天没签到则返回0
        调用方需要根据情况决定是否+1
        """
        yesterday = date.today() - timedelta(days=1)
        
        # 检查昨天是否有签到记录
        yesterday_checkin = await conn.fetchrow(
            "SELECT streak_count FROM daily_checkins WHERE user_id=$1 AND server_id=$2 AND checkin_date=$3",
            str(user_id), str(server_id), yesterday
        )
        
        return yesterday_checkin[0] if yesterday_checkin else 0

    async def get_leaderboard(self, server_id: int, limit: int = 10) -> list:
        """
        获取服务器积分排行榜
        """
        results = await self.execute_query(
            "SELECT user_id, points, total_checkins FROM user_points WHERE server_id=$1 ORDER BY points DESC LIMIT $2",
            (str(server_id), limit)
        )
        
        leaderboard = []
        for i, row in enumerate(results, 1):
            leaderboard.append({
                "rank": i,
                "user_id": row[0],
                "points": row[1],
                "total_checkins": row[2]
            })
        return leaderboard

    async def record_message(self, user_id: str, server_id: str, message_time: datetime) -> None:
        """记录用户消息时间"""
        query = "INSERT INTO message_logs (user_id, server_id, message_time) VALUES ($1, $2, $3)"
        await self.execute_write(query, (user_id, server_id, message_time))
    
    async def count_messages_in_window(self, user_id: str, server_id: str, window_start: datetime, window_end: datetime) -> int:
        """统计时间窗口内的消息数量"""
        query = "SELECT COUNT(*) FROM message_logs WHERE user_id = $1 AND server_id = $2 AND message_time BETWEEN $3 AND $4"
        result = await self.execute_single(query, (user_id, server_id, window_start, window_end))
        return result[0] if result else 0
    
    async def has_daily_activity_reward(self, user_id: str, server_id: str, reward_date: date) -> bool:
        """检查用户今天是否已获得活跃奖励"""
        query = "SELECT 1 FROM daily_activity_rewards WHERE user_id = $1 AND server_id = $2 AND reward_date = $3"
        result = await self.execute_single(query, (user_id, server_id, reward_date))
        return result is not None
    
    async def give_daily_activity_reward(self, user_id: str, server_id: str, points: int, message_count: int, reward_time: datetime) -> None:
        """发放每日活跃奖励"""
        reward_date = reward_time.date()
        
        # 插入奖励记录
        reward_query = "INSERT INTO daily_activity_rewards (user_id, server_id, reward_date, points_earned, message_count_when_rewarded, reward_time) VALUES ($1, $2, $3, $4, $5, $6)"
        await self.execute_write(reward_query, (user_id, server_id, reward_date, points, message_count, reward_time))
        
        # 更新用户总积分
        points_query = "INSERT INTO user_points (user_id, server_id, points) VALUES ($1, $2, $3) ON CONFLICT (user_id, server_id) DO UPDATE SET points = user_points.points + EXCLUDED.points, updated_at = $4"
        await self.execute_write(points_query, (user_id, server_id, points, reward_time))
    
    
    async def cleanup_old_message_logs(self, days_to_keep: int = 7) -> int:
        """清理旧的消息记录（保留指定天数）"""
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        query = "DELETE FROM message_logs WHERE message_time < $1"
        result = await self.execute_write(query, (cutoff_date,))
        return result
    
    async def get_daily_message_stats(self, user_id: str, server_id: str, target_date: date) -> dict:
        """获取用户每日消息统计（重用daily_activity_rewards表）"""
        # 查找今天的记录，使用message_count_when_rewarded字段存储消息计数
        query = "SELECT message_count_when_rewarded, points_earned FROM daily_activity_rewards WHERE user_id = $1 AND server_id = $2 AND reward_date = $3"
        result = await self.execute_single(query, (user_id, server_id, target_date))
        
        if result:
            return {
                "message_count": result[0],
                "points_earned": result[1]
            }
        return {
            "message_count": 0,
            "points_earned": 0
        }
    
    async def record_daily_message_reward(self, user_id: str, server_id: str, points_earned: int, message_time: datetime) -> bool:
        """记录每日消息积分奖励（重用daily_activity_rewards表）"""
        reward_date = message_time.date()
        
        try:
            # 插入或更新今日记录
            activity_query = """
            INSERT INTO daily_activity_rewards (user_id, server_id, reward_date, message_count_when_rewarded, points_earned, reward_time) 
            VALUES ($1, $2, $3, 1, $4, $5)
            ON CONFLICT (user_id, server_id, reward_date) 
            DO UPDATE SET 
                message_count_when_rewarded = daily_activity_rewards.message_count_when_rewarded + 1,
                points_earned = daily_activity_rewards.points_earned + $4,
                reward_time = $5
            """
            await self.execute_write(activity_query, (user_id, server_id, reward_date, points_earned, message_time))
            
            # 给用户增加积分
            if points_earned > 0:
                await self.add_points(int(user_id), int(server_id), points_earned)
            
            return True
        except Exception as e:
            logging.error(f"记录每日消息奖励失败: {e}")
            return False
    
    async def should_give_daily_message_points(self, user_id: str, server_id: str, message_time: datetime) -> int:
        """检查是否应该给用户每日消息积分，返回应给的积分数量"""
        today = message_time.date()
        stats = await self.get_daily_message_stats(user_id, server_id, today)
        
        # 前三条消息每条给5积分
        messages_today = stats["message_count"]
        if messages_today < 3:
            return 5
        return 0
    
    async def get_user_activity_stats(self, user_id: str, server_id: str) -> dict:
        """获取用户活跃统计信息"""
        now = datetime.now()
        window_start = now - timedelta(hours=6)
        today = now.date()
        
        # 获取6小时内消息数量
        message_count = await self.count_messages_in_window(user_id, server_id, window_start, now)
        
        # 检查今天是否已获得奖励
        has_reward = await self.has_daily_activity_reward(user_id, server_id, today)
        
        # 获取今天的奖励记录
        reward_query = "SELECT points_earned, message_count_when_rewarded, reward_time FROM daily_activity_rewards WHERE user_id = $1 AND server_id = $2 AND reward_date = $3"
        reward_info = await self.execute_single(reward_query, (user_id, server_id, today))
        
        return {
            "message_count_6h": message_count,
            "has_daily_reward": has_reward,
            "reward_info": {
                "points_earned": reward_info[0] if reward_info else 0,
                "message_count_when_rewarded": reward_info[1] if reward_info else 0,
                "reward_time": reward_info[2] if reward_info else None
            } if reward_info else None
        }

    async def find_early_role_member(
        self, user_id: Union[int, str], guild_id: Union[int, str]
    ) -> Optional[dict]:
        """根据 user_id 和 guild_id 查询成员记录"""
        query = (
            "SELECT user_id, guild_id, wallet_address, "
            "created_at FROM early_role_members "
            "WHERE user_id = $1 AND guild_id = $2"
        )

        record = await self.execute_single(query, (str(user_id), str(guild_id)))
        if not record:
            return None
        return {
            "user_id": record[0],
            "guild_id": record[1],
            "wallet_address": record[2],
            "created_at": record[3],
        }

    async def create_early_role_member(
        self,
        *,
        guild_id: Union[int, str],
        user_id: Union[int, str],
        wallet_address: Optional[str] = None,
    ) -> None:
        """新增或更新early_role_members记录"""
        query = """
        INSERT INTO early_role_members (
            user_id,
            guild_id,
            wallet_address,
            created_at,
            updated_at
        )
        VALUES ($1, $2, $3, NOW(), NOW())
        ON CONFLICT (guild_id, user_id)
        DO UPDATE SET
            wallet_address = COALESCE(EXCLUDED.wallet_address, early_role_members.wallet_address),
            updated_at = NOW()
        """
        await self.execute_write(
            query,
            (
                str(user_id),
                str(guild_id),
                wallet_address,
            ),
        )

    async def update_early_role_member(
        self,
        user_id: Union[int, str],
        *,
        guild_id: Optional[Union[int, str]] = None,
        **fields,
    ) -> bool:
        """根据user_id（可选guild_id）更新early_role_members字段"""
        if not fields:
            return False

        allowed_fields = {
            "wallet_address",
        }
        set_clauses = []
        params = []
        idx = 1

        for key, value in fields.items():
            if key not in allowed_fields:
                continue
            set_clauses.append(f"{key} = ${idx}")
            params.append(value)
            idx += 1

        if not set_clauses:
            return False

        set_clause = ", ".join(set_clauses + ["updated_at = NOW()"])
        query = f"UPDATE early_role_members SET {set_clause} WHERE user_id = ${idx}"
        params.append(str(user_id))

        if guild_id is not None:
            idx += 1
            query += f" AND guild_id = ${idx}"
            params.append(str(guild_id))

        await self.execute_write(query, tuple(params))
        return True

    async def get_early_role_member(
        self,
        *,
        guild_id: Union[int, str],
        user_id: Union[int, str],
    ) -> Optional[dict]:
        """获取单个 early_role_members 记录"""
        query = (
            "SELECT user_id, guild_id, wallet_address, "
            "created_at, updated_at FROM early_role_members "
            "WHERE guild_id = $1 AND user_id = $2"
        )
        record = await self.execute_single(
            query, (str(guild_id), str(user_id))
        )
        if not record:
            return None
        return {
            "user_id": record[0],
            "guild_id": record[1],
            "wallet_address": record[2],
            "created_at": record[3],
            "updated_at": record[4],
        }

    # Twitter相关方法
    async def bind_twitter_account(self, discord_user_id: str, server_id: str, twitter_user_id: str, twitter_username: str, access_token: str = None, refresh_token: str = None, token_expires_at: datetime = None) -> dict:
        """绑定Twitter账户（支持OAuth tokens），返回绑定结果和奖励信息"""
        try:
            # 检查是否是首次绑定
            existing_query = "SELECT id FROM twitter_bindings WHERE user_id = $1 AND server_id = $2"
            existing_binding = await self.execute_single(existing_query, (discord_user_id, server_id))
            
            is_first_time = existing_binding is None
            
            query = """
            INSERT INTO twitter_bindings (user_id, server_id, twitter_username, twitter_user_id, access_token, refresh_token, token_expires_at, verified, created_at, updated_at) 
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            ON CONFLICT (user_id, server_id) 
            DO UPDATE SET twitter_username = $3, twitter_user_id = $4, access_token = $5, refresh_token = $6, token_expires_at = $7, verified = $8, updated_at = $10
            """
            
            await self.execute_write(query, (
                discord_user_id, server_id, twitter_username, twitter_user_id, 
                access_token, refresh_token, token_expires_at, True, 
                datetime.now(), datetime.now()
            ))
            
            # 如果是首次绑定，直接发放20积分奖励
            bonus_points = 0
            if is_first_time:
                bonus_points = 20
                # 使用全局积分系统
                await self.add_points(int(discord_user_id), 0, bonus_points)  # 使用server_id=0作为全局积分
                logging.info(f"用户 {discord_user_id} 首次绑定Twitter，获得 {bonus_points} 积分奖励")
            
            return {
                "success": True,
                "is_first_time": is_first_time,
                "bonus_points": bonus_points
            }
            
        except Exception as e:
            logging.error(f"绑定Twitter账户失败: {e}")
            return {
                "success": False,
                "is_first_time": False,
                "bonus_points": 0
            }
    
    async def get_twitter_binding(self, user_id: str, server_id: str) -> dict:
        """获取用户的Twitter绑定信息"""
        # 先查找服务器特定的绑定
        query = "SELECT twitter_username, twitter_user_id, verified, access_token, refresh_token, token_expires_at FROM twitter_bindings WHERE user_id = $1 AND server_id = $2"
        result = await self.execute_single(query, (user_id, server_id))
        
        # 如果没找到，查找全局绑定
        if not result:
            query = "SELECT twitter_username, twitter_user_id, verified, access_token, refresh_token, token_expires_at FROM twitter_bindings WHERE user_id = $1 AND server_id = 'global'"
            result = await self.execute_single(query, (user_id,))
        
        if result:
            return {
                "twitter_username": result[0],
                "twitter_user_id": result[1],
                "verified": result[2],
                "access_token": result[3],
                "refresh_token": result[4],
                "token_expires_at": result[5]
            }
        return None
    
    async def update_twitter_token(self, twitter_user_id: str, access_token: str, refresh_token: str, expires_at: datetime) -> bool:
        """更新Twitter token信息"""
        try:
            query = """
            UPDATE twitter_bindings 
            SET access_token = $1, refresh_token = $2, token_expires_at = $3, updated_at = $4
            WHERE twitter_user_id = $5
            """
            
            await self.execute_write(query, (
                access_token, refresh_token, expires_at, datetime.now(), twitter_user_id
            ))
            
            return True
        except Exception as e:
            logging.error(f"更新Twitter token失败: {e}")
            return False
    
    async def add_target_tweet(self, server_id: str, tweet_id: str, tweet_url: str, description: str = None, 
                              like_points: int = 5, retweet_points: int = 10, reply_points: int = 15, triple_bonus: int = 20) -> bool:
        """添加目标推文"""
        try:
            query = "INSERT INTO twitter_target_tweets (server_id, tweet_id, tweet_url, description, like_points, retweet_points, reply_points, triple_bonus_points) VALUES ($1, $2, $3, $4, $5, $6, $7, $8) ON CONFLICT (server_id, tweet_id) DO UPDATE SET tweet_url = $3, description = $4, like_points = $5, retweet_points = $6, reply_points = $7, triple_bonus_points = $8"
            
            await self.execute_write(query, (server_id, tweet_id, tweet_url, description, like_points, retweet_points, reply_points, triple_bonus, tweet_url, description, like_points, retweet_points, reply_points, triple_bonus))
            
            return True
        except Exception as e:
            print(f"添加目标推文失败: {e}")
            return False
    
    async def get_target_tweets(self, server_id: str) -> list:
        """获取服务器的目标推文列表"""
        query = "SELECT tweet_id, tweet_url, description, like_points, retweet_points, reply_points, triple_bonus_points FROM twitter_target_tweets WHERE server_id = $1 AND is_active = $2"
        results = await self.execute_query(query, (server_id, True))
        
        # 如果没找到，查找全局配置
        if not results:
            results = await self.execute_query(query, ("global", True))
        
        tweets = []
        for row in results:
            tweets.append({
                "tweet_id": row[0],
                "tweet_url": row[1],
                "description": row[2],
                "like_points": row[3],
                "retweet_points": row[4],
                "reply_points": row[5],
                "triple_bonus_points": row[6]
            })
        return tweets
    
    async def record_twitter_verification(self, user_id: str, server_id: str, twitter_username: str, 
                                        tweet_id: str, action_type: str, points_earned: int) -> bool:
        """记录Twitter验证结果"""
        try:
            query = "INSERT INTO twitter_verifications (user_id, server_id, twitter_username, tweet_id, action_type, points_earned) VALUES ($1, $2, $3, $4, $5, $6)"
            await self.execute_write(query, (user_id, server_id, twitter_username, tweet_id, action_type, points_earned))
            return True
        except Exception as e:
            # 如果是重复记录（已经验证过），返回False
            return False
    
    async def get_user_twitter_verifications(self, user_id: str, server_id: str) -> list:
        """获取用户的Twitter验证记录"""
        query = "SELECT tweet_id, action_type, points_earned, verified_at FROM twitter_verifications WHERE user_id = $1 AND server_id = $2 ORDER BY verified_at DESC"
        results = await self.execute_query(query, (user_id, server_id))
        
        # 如果没找到，查找全局记录
        if not results:
            results = await self.execute_query(query, (user_id, "global"))
        
        verifications = []
        for row in results:
            verifications.append({
                "tweet_id": row[0],
                "action_type": row[1],
                "points_earned": row[2],
                "verified_at": row[3]
            })
        return verifications
    
    async def check_triple_action(self, user_id: str, server_id: str, tweet_id: str) -> bool:
        """检查用户是否对某条推文完成了三连（点赞+转发+评论）"""
        query = "SELECT COUNT(DISTINCT action_type) FROM twitter_verifications WHERE user_id = $1 AND server_id = $2 AND tweet_id = $3 AND action_type IN ('like', 'retweet', 'reply')"
        result = await self.execute_single(query, (user_id, server_id, tweet_id))
        
        # 如果没找到或计数为0，查找全局记录
        if not result or result[0] == 0:
            result = await self.execute_single(query, (user_id, "global", tweet_id))
        
        return result[0] == 3 if result else False

    async def set_server_config(self, server_id: str, config_key: str, config_value: str) -> bool:
        """设置服务器配置"""
        try:
            query = "INSERT INTO server_config (server_id, config_key, config_value, updated_at) VALUES ($1, $2, $3, NOW()) ON CONFLICT (server_id, config_key) DO UPDATE SET config_value = $3, updated_at = NOW()"
            
            await self.execute_write(query, (server_id, config_key, config_value))
            return True
        except Exception as e:
            print(f"设置服务器配置失败: {e}")
            return False

    async def get_server_config(self, server_id: str, config_key: str) -> str:
        """获取服务器配置"""
        query = "SELECT config_value FROM server_config WHERE server_id = $1 AND config_key = $2"
        result = await self.execute_single(query, (server_id, config_key))
        return result[0] if result else None

    async def get_auto_detect_twitter_username(self, server_id: str) -> str:
        """获取自动检测的Twitter用户名"""
        result = await self.get_server_config(server_id, "auto_detect_twitter_username")
        
        # 如果没找到，查找全局配置
        if not result:
            result = await self.get_server_config("global", "auto_detect_twitter_username")
        
        return result

    async def get_auto_detect_twitter_user_id(self, server_id: str) -> str:
        """获取自动检测的Twitter用户ID"""
        result = await self.get_server_config(server_id, "auto_detect_twitter_user_id")
        
        # 如果没找到，查找全局配置
        if not result:
            result = await self.get_server_config("global", "auto_detect_twitter_user_id")
        
        return result

    # OAuth临时存储相关方法
    async def store_oauth_code_verifier(self, state: str, code_verifier: str, discord_user_id: str, expires_in_minutes: int = 10) -> bool:
        """存储OAuth code verifier"""
        try:
            expires_at = datetime.now() + timedelta(minutes=expires_in_minutes)
            query = """
            INSERT INTO oauth_temp_storage (state, code_verifier, discord_user_id, expires_at) 
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (state) 
            DO UPDATE SET code_verifier = $2, discord_user_id = $3, expires_at = $4
            """
            
            await self.execute_write(query, (state, code_verifier, discord_user_id, expires_at))
            return True
        except Exception as e:
            logging.error(f"存储OAuth code verifier失败: {e}")
            return False
    
    async def get_oauth_code_verifier(self, state: str) -> dict:
        """获取并删除OAuth code verifier"""
        try:
            # 首先获取code verifier
            query = "SELECT code_verifier, discord_user_id FROM oauth_temp_storage WHERE state = $1 AND expires_at > NOW()"
            result = await self.execute_single(query, (state,))
            
            if result:
                code_verifier, discord_user_id = result
                
                # 删除已使用的记录
                delete_query = "DELETE FROM oauth_temp_storage WHERE state = $1"
                await self.execute_write(delete_query, (state,))
                
                return {
                    "code_verifier": code_verifier,
                    "discord_user_id": discord_user_id
                }
            
            return None
        except Exception as e:
            logging.error(f"获取OAuth code verifier失败: {e}")
            return None
    
    async def cleanup_expired_oauth_verifiers(self) -> int:
        """清理过期的OAuth verifier记录"""
        try:
            # 在PostgreSQL中，execute_write应该返回受影响的行数
            # 或者我们可以先查询要删除的记录数
            count_query = "SELECT COUNT(*) FROM oauth_temp_storage WHERE expires_at <= NOW()"
            count_result = await self.execute_single(count_query, ())
            count = count_result[0] if count_result else 0
            
            # 执行删除操作
            query = "DELETE FROM oauth_temp_storage WHERE expires_at <= NOW()"
            await self.execute_write(query, ())
            
            return count
        except Exception as e:
            logging.error(f"清理过期OAuth verifier失败: {e}")
            return 0

    # 管理员操作审计日志方法
    async def log_admin_operation(self, operation_type: str, operator_id: int, operator_username: str,
                                target_user_id: int, target_username: str, server_id: int,
                                points_change: int, points_before: int, points_after: int, 
                                reason: str) -> bool:
        """记录管理员操作日志"""
        try:
            query = """
            INSERT INTO admin_audit_logs 
            (operation_type, operator_user_id, operator_username, target_user_id, 
             target_username, server_id, points_change, points_before, points_after, reason)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            """
            
            await self.execute_write(query, (
                operation_type, str(operator_id), operator_username, str(target_user_id),
                target_username, str(server_id), points_change, points_before, points_after, reason
            ))
            return True
        except Exception as e:
            logging.error(f"记录审计日志失败: {e}")
            return False

    async def get_admin_audit_logs(self, server_id: int, limit: int = 20, 
                                  operator_id: int = None, target_id: int = None) -> list:
        """获取管理员操作日志"""
        try:
            if operator_id and target_id:
                query = """
                SELECT operation_type, operator_username, target_username,
                       points_change, points_before, points_after, reason, operation_time
                FROM admin_audit_logs 
                WHERE server_id=$1 AND operator_user_id=$2 AND target_user_id=$3
                ORDER BY operation_time DESC LIMIT $4
                """
                params = (str(server_id), str(operator_id), str(target_id), limit)
            elif operator_id:
                query = """
                SELECT operation_type, operator_username, target_username,
                       points_change, points_before, points_after, reason, operation_time
                FROM admin_audit_logs 
                WHERE server_id=$1 AND operator_user_id=$2
                ORDER BY operation_time DESC LIMIT $3
                """
                params = (str(server_id), str(operator_id), limit)
            elif target_id:
                query = """
                SELECT operation_type, operator_username, target_username,
                       points_change, points_before, points_after, reason, operation_time
                FROM admin_audit_logs 
                WHERE server_id=$1 AND target_user_id=$2
                ORDER BY operation_time DESC LIMIT $3
                """
                params = (str(server_id), str(target_id), limit)
            else:
                query = """
                SELECT operation_type, operator_username, target_username,
                       points_change, points_before, points_after, reason, operation_time
                FROM admin_audit_logs 
                WHERE server_id=$1
                ORDER BY operation_time DESC LIMIT $2
                """
                params = (str(server_id), limit)
            
            return await self.execute_query(query, params)
        except Exception as e:
            logging.error(f"获取审计日志失败: {e}")
            return []
