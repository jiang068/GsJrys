"""
每日运势插件 - Daily Fortune Plugin
根据用户请求生成今日运势卡片
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any

from gsuid_core.sv import SV
from gsuid_core.bot import Bot  
from gsuid_core.models import Event

from .config import jrys_config
from .utils import (
    get_fortune_data, 
    get_random_background,
    save_fortune_record,
    get_fortune_record,
    cleanup_old_fortune_files,
    get_user_fortune_history
)
from .draw import draw_fortune_card

# 创建服务
jrys_sv = SV('每日运势')

# 获取插件目录路径
PLUGIN_PATH = Path(__file__).parent
DATA_PATH = PLUGIN_PATH / 'data'
USERJRYS_PATH = PLUGIN_PATH / 'userjrys'

# 确保目录存在
USERJRYS_PATH.mkdir(exist_ok=True)


# 动态获取命令配置
def get_commands():
    """获取运势命令配置"""
    try:
        commands = jrys_config.get_config('commands').data
        return tuple(commands) if commands else ('运势', 'jrys')
    except:
        return ('运势', 'jrys')


# 创建装饰器函数  
def create_fortune_command():
    commands = get_commands()
    return jrys_sv.on_command(commands, block=True)


@create_fortune_command()
async def get_fortune(bot: Bot, ev: Event):
    """获取今日运势"""
    user_id = ev.user_id
    today = datetime.now().strftime('%Y-%m-%d')
    
    try:
        # 检查今日是否已经抽过运势
        existing_record = await get_fortune_record(user_id, today)
        
        if existing_record:
            # 已经抽过，使用已有记录
            fortune_data = existing_record['fortune_data']
        else:
            # 今日首次抽取运势
            fortune_data = get_fortune_data()
            
            # 保存记录到JSON文件
            await save_fortune_record(
                user_id=user_id,
                date=today,
                fortune_data=fortune_data,
                background_image=fortune_data.get('backgroundImage', ''),
                bot_id=ev.bot_id
            )
        
        # 获取用户名称
        user_name = getattr(ev, 'sender', {}).get('nickname', f'用户{user_id}')
        
        # 生成运势卡片
        img_bytes = await draw_fortune_card(
            user_name=user_name,
            fortune_data=fortune_data
        )
        
        # 发送图片 - 直接发送图片字节数据
        await bot.send(img_bytes)
        
        # 如果开启自动清理，定期清理过期文件
        if jrys_config.get_config('enable_auto_cleanup').data:
            import asyncio
            asyncio.create_task(auto_cleanup_if_needed())
        
    except Exception as e:
        await bot.send(f'运势获取失败：{str(e)}')


@jrys_sv.on_command('清理运势记录', block=True)  
async def clean_fortune_records(bot: Bot, ev: Event):
    """清理过期的运势记录"""
    try:
        # 获取保存天数配置
        keep_days = jrys_config.get_config('keep_days').data
        
        # 清理JSON文件
        deleted_count = await cleanup_old_fortune_files(keep_days)
        
        await bot.send(f'已清理 {keep_days} 天前的运势文件，共删除 {deleted_count} 个文件')
        
    except Exception as e:
        await bot.send(f'清理运势记录失败：{str(e)}')


@jrys_sv.on_command('查看运势等级', block=True)
async def view_fortune_levels(bot: Bot, ev: Event):
    """查看当前运势等级配置"""
    try:
        from .utils import get_fortune_level_config, validate_probabilities
        level_config = get_fortune_level_config()
        
        # 验证概率总和
        is_valid, total_prob = validate_probabilities()
        
        # 构建消息
        message_lines = ["当前运势等级配置："]
        for level in level_config:
            probability = level['probability']
            message_lines.append(f"{level['stars']} {level['name']} - {probability}%")
        
        message_lines.append(f"\n概率总和: {total_prob:.1f}%")
        if not is_valid:
            message_lines.append("⚠️ 警告：概率总和不等于100%，系统将自动归一化处理")
        else:
            message_lines.append("✅ 概率配置正常")
        
        message = "\n".join(message_lines)
        await bot.send(message)
        
    except Exception as e:
        await bot.send(f'查看运势等级配置失败：{str(e)}')


@jrys_sv.on_command(('测试运势等级', '测试运势'), block=True)
async def test_fortune_level(bot: Bot, ev: Event):
    """测试运势等级配置"""
    try:
        text = ev.text.strip()
        
        if not text:
            # 如果没有参数，就模拟抽取一次运势
            from .utils import weighted_random_choice_from_levels
            selected_level = weighted_random_choice_from_levels()
            message = f"模拟抽取结果:\n{selected_level['stars']} {selected_level['name']} (概率: {selected_level['probability']}%)"
            await bot.send(message)
            return
        
        # 如果有参数，查找对应的运势等级
        from .utils import get_fortune_level_config
        level_config = get_fortune_level_config()
        
        found_level = None
        for level in level_config:
            if level['name'] == text or text in level['name']:
                found_level = level
                break
        
        if found_level:
            message = f"运势等级 '{found_level['name']}':\n{found_level['stars']}\n概率: {found_level['probability']}%"
        else:
            available_levels = [level['name'] for level in level_config]
            message = f"未找到运势等级 '{text}'。\n可用等级: {', '.join(available_levels)}"
        
        await bot.send(message)
        
    except Exception as e:
        await bot.send(f'测试运势等级失败：{str(e)}')


# 自动清理相关功能
_last_cleanup_date = None

async def auto_cleanup_if_needed():
    """如果需要，自动清理过期文件"""
    global _last_cleanup_date
    
    today = datetime.now().strftime('%Y-%m-%d')
    
    # 如果今天已经清理过，则跳过
    if _last_cleanup_date == today:
        return
        
    try:
        keep_days = jrys_config.get_config('keep_days').data
        deleted_count = await cleanup_old_fortune_files(keep_days)
        
        if deleted_count > 0:
            print(f"自动清理完成，删除了 {deleted_count} 个过期文件")
            
        _last_cleanup_date = today
        
    except Exception as e:
        print(f"自动清理失败：{e}")