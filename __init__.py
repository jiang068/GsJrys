import asyncio
import httpx
from pathlib import Path
from datetime import datetime
from gsuid_core.sv import SV
from gsuid_core.bot import Bot
from gsuid_core.models import Event

from .config import jrys_config
from .utils import (
    get_fortune_data, save_fortune_record, get_fortune_record,
    cleanup_old_fortune_files, get_fortune_level_config, validate_probabilities
)
from .draw import draw_fortune_card

jrys_sv = SV('每日运势')
_last_cleanup_date = None

def has_reply(ev: Event) -> bool:
    """检查事件中是否包含引用回复"""
    if getattr(ev, 'reply', None): return True
    if hasattr(ev, 'content'):
        for msg in ev.content:
            if getattr(msg, 'type', '') == 'reply':
                return True
    return False

@jrys_sv.on_fullmatch(('运势', 'jrys', '今日运势', '抽签'), block=True)
async def get_fortune(bot: Bot, ev: Event):
    """获取今日运势"""
    user_id = ev.user_id
    today = datetime.now().strftime('%Y-%m-%d')
    
    try:
        global _last_cleanup_date
        if jrys_config.get_config('enable_auto_cleanup').data and _last_cleanup_date != today:
            asyncio.create_task(cleanup_old_fortune_files())
            _last_cleanup_date = today

        record = await get_fortune_record(user_id, today)
        if record:
            fortune_data = record['fortune_data']
        else:
            fortune_data = get_fortune_data()
            await save_fortune_record(user_id, today, fortune_data, ev.bot_id)
            
        img_bytes = await draw_fortune_card(user_id, fortune_data)
        await bot.send(img_bytes)
            
    except Exception as e:
        await bot.send(f'运势获取失败，服务器开了个小差：{e}')

@jrys_sv.on_fullmatch(('毁签', '悔签', '重抽'), block=True)
async def redraw_fortune(bot: Bot, ev: Event):
    """销毁当前运势，重新抽取"""
    user_id = ev.user_id
    today = datetime.now().strftime('%Y-%m-%d')
    
    try:
        limit = jrys_config.get_config('redraw_limit').data
        empty_msg = jrys_config.get_config('redraw_empty_message').data
        
        if limit <= 0:
            return await bot.send(empty_msg)
            
        record = await get_fortune_record(user_id, today)
        if not record:
            return await bot.send("你今天还没抽过运势呢！请先发送【运势】。")
            
        current_redraws = record.get('redraw_count', 0)
        if current_redraws >= limit:
            return await bot.send(empty_msg)
            
        new_fortune_data = get_fortune_data()
        await save_fortune_record(user_id, today, new_fortune_data, ev.bot_id, redraw_count=current_redraws + 1)
        
        img_bytes = await draw_fortune_card(user_id, new_fortune_data)
        await bot.send(img_bytes)
            
    except Exception as e:
        await bot.send(f'毁签过程出现了小故障：{e}')

@jrys_sv.on_fullmatch('运势背景图', block=True)
async def send_fortune_bg(bot: Bot, ev: Event):
    """获取运势底图（支持 @别人，或直接获取自己的）"""
    today = datetime.now().strftime('%Y-%m-%d')
    
    try:
        # 如果检测到群友使用了引用回复，委婉提示 GsCore 的限制
        if has_reply(ev):
            return await bot.send("由于 GsCore 底层限制，目前无法通过引用卡片来找图哦！\n👉 请直接输入【运势背景图 @对方】来获取别人的神仙底图~")
            
        # 按照 @ 或本人查询
        target_id = ev.user_id
        if getattr(ev, 'at_list', None) and len(ev.at_list) > 0:
            target_id = ev.at_list[0]
        elif getattr(ev, 'at', None):
            target_id = ev.at
            
        record = await get_fortune_record(target_id, today)
        
        if not record:
            if str(target_id) != str(ev.user_id):
                return await bot.send("这位群友今天还没有抽取运势呢！")
            else:
                return await bot.send("你今天还没有抽取运势呢！请先发送【运势】。")

        bg_path = record['fortune_data'].get('backgroundImage', '')
        if not bg_path:
            return await bot.send("未能找到对应的背景图数据！")
            
        # 发送原底图
        if bg_path.startswith('http'):
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(bg_path)
                resp.raise_for_status()
                await bot.send(resp.content)
        else:
            path_obj = Path(bg_path)
            if path_obj.exists():
                await bot.send(path_obj.read_bytes())
            else:
                await bot.send("底图文件在本地已丢失或被移除！")
                
    except Exception as e:
        await bot.send(f"获取背景图失败：{e}")

@jrys_sv.on_fullmatch('清理运势记录', block=True)
async def clean_fortune_records(bot: Bot, ev: Event):
    if ev.user_pm > 2:
        return await bot.send("仅限管理员可用。")
    count = await cleanup_old_fortune_files()
    await bot.send(f'清理完成，共删除 {count} 个过期文件。')

@jrys_sv.on_fullmatch('查看运势等级', block=True)
async def view_fortune_levels(bot: Bot, ev: Event):
    if ev.user_pm > 2: return
    level_config = get_fortune_level_config()
    is_valid, total_prob = validate_probabilities()
    
    msg = ["📊 当前运势星级与概率配置："]
    for lv in level_config:
        lvl_num = int(lv['level'])
        stars_str = '★' * lvl_num + '☆' * (7 - lvl_num)
        msg.append(f"{stars_str} ({lv['level']}星) - {lv['probability']}%")
        
    msg.append(f"\n概率总和: {total_prob:.1f}%")
    msg.append("✅ 配置正常" if is_valid else "⚠️ 警告：总和非100%，系统已自动按比例分配。")
    await bot.send("\n".join(msg))