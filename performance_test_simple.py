#!/usr/bin/env python3
"""
简单性能测试 - 测试签到和查询积分的响应时间
"""

import asyncio
import time
import os
from dotenv import load_dotenv
load_dotenv()

import sys

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.config import DatabaseConfig, DatabaseConnection
from database import DatabaseManager


async def test_performance():
    """测试签到和查询积分的性能"""
    print("🔧 初始化数据库连接...")
    
    try:
        # 初始化数据库连接
        config = DatabaseConfig()
        db_connection = DatabaseConnection(config)
        pool = await db_connection.connect()
        db_manager = DatabaseManager(connection=pool)
        
        print("✅ 数据库连接成功")
        
        # 获取连接池状态
        pool_status = await db_manager.get_pool_status()
        print(f"📊 连接池状态: {pool_status}")
        
        test_user_id = 999999  # 使用一个测试用户ID
        test_server_id = 0
        
        # 测试1: 签到性能
        print(f"\n🏃‍♂️ 测试签到性能...")
        start_time = time.time()
        checkin_result = await db_manager.daily_checkin(test_user_id, test_server_id)
        checkin_time = time.time() - start_time
        
        print(f"   签到结果: {checkin_result}")
        print(f"   签到耗时: {checkin_time:.3f}秒")
        
        # 测试2: 查询积分性能
        print(f"\n📊 测试查询积分性能...")
        start_time = time.time()
        points_result = await db_manager.get_user_points(test_user_id, test_server_id)
        points_time = time.time() - start_time
        
        print(f"   积分结果: {points_result}")
        print(f"   查询耗时: {points_time:.3f}秒")
        
        # 测试3: 再次签到（应该失败，但测试性能）
        print(f"\n🔄 测试重复签到性能...")
        start_time = time.time()
        duplicate_checkin = await db_manager.daily_checkin(test_user_id, test_server_id)
        duplicate_time = time.time() - start_time
        
        print(f"   重复签到结果: {duplicate_checkin}")
        print(f"   重复签到耗时: {duplicate_time:.3f}秒")
        
        # 测试4: 添加积分性能
        print(f"\n💰 测试添加积分性能...")
        start_time = time.time()
        new_total = await db_manager.add_points(test_user_id, test_server_id, 10)
        add_points_time = time.time() - start_time
        
        print(f"   添加积分后总数: {new_total}")
        print(f"   添加积分耗时: {add_points_time:.3f}秒")
        
        # 测试5: 并发签到测试（新用户）
        print(f"\n🔀 测试并发签到安全性...")
        test_user_concurrent = 888888  # 新的测试用户
        
        # 创建5个并发签到任务
        async def concurrent_checkin():
            return await db_manager.daily_checkin(test_user_concurrent, test_server_id)
        
        start_time = time.time()
        concurrent_results = await asyncio.gather(
            concurrent_checkin(), concurrent_checkin(), concurrent_checkin(),
            concurrent_checkin(), concurrent_checkin(),
            return_exceptions=True
        )
        concurrent_time = time.time() - start_time
        
        # 统计结果
        successful_checkins = [r for r in concurrent_results if isinstance(r, dict) and r.get('success')]
        failed_checkins = [r for r in concurrent_results if isinstance(r, dict) and not r.get('success')]
        exceptions = [r for r in concurrent_results if isinstance(r, Exception)]
        
        print(f"   并发签到总耗时: {concurrent_time:.3f}秒")
        print(f"   成功签到次数: {len(successful_checkins)}")
        print(f"   失败签到次数: {len(failed_checkins)}")
        print(f"   异常次数: {len(exceptions)}")
        
        if len(successful_checkins) == 1 and len(failed_checkins) == 4:
            print(f"   ✅ 并发安全性测试通过：只有一次签到成功")
        else:
            print(f"   ❌ 并发安全性测试失败：可能存在重复签到")
            for i, result in enumerate(concurrent_results):
                print(f"      任务{i+1}: {result}")
        
        # 性能评估
        print(f"\n📈 性能评估:")
        
        if checkin_time < 0.1:
            print(f"   ✅ 签到性能优秀: {checkin_time:.3f}秒")
        elif checkin_time < 0.5:
            print(f"   ⚠️  签到性能一般: {checkin_time:.3f}秒")
        else:
            print(f"   ❌ 签到性能较差: {checkin_time:.3f}秒")
        
        if points_time < 0.05:
            print(f"   ✅ 查询性能优秀: {points_time:.3f}秒")
        elif points_time < 0.2:
            print(f"   ⚠️  查询性能一般: {points_time:.3f}秒")
        else:
            print(f"   ❌ 查询性能较差: {points_time:.3f}秒")
        
        if duplicate_time < 0.05:
            print(f"   ✅ 重复签到检查优秀: {duplicate_time:.3f}秒")
        elif duplicate_time < 0.2:
            print(f"   ⚠️  重复签到检查一般: {duplicate_time:.3f}秒")
        else:
            print(f"   ❌ 重复签到检查较差: {duplicate_time:.3f}秒")
        
        # 最终连接池状态
        final_pool_status = await db_manager.get_pool_status()
        print(f"\n📊 测试后连接池状态: {final_pool_status}")
        
        await db_connection.close()
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("🧪 egoscale_api 数据层性能测试")
    print("📝 测试签到和积分查询的响应时间")
    
    asyncio.run(test_performance())
