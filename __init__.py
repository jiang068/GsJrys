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
    cleanup_old_fortune_files, get_fortune_level_config, validate_probabilities,
    update_fortune_msg_id, get_fortune_record_by_msg_id
)
from .draw import draw_fortune_card

# 创建服务
jrys_sv = SV('每日运势')
_last_cleanup_date = None

def _extract_msg_id(resp) -> str:
    """【强化】从Bot发消息的响应中提取出准确的msg_id，适配各种平台嵌套结构"""
    if not resp:
        return ""
    if isinstance(resp, list) and len(resp) > 0:
        resp = resp[0]
    
    # 1. 字典提取 (完美适配 OneBot/AstrBot 等返回的嵌套字典)
    if isinstance(resp, dict):
        mid = resp.get('message_id') or resp.get('msg_id')
        if mid:
            return str(mid)
        # 如果嵌套在 data 里
        data = resp.get('data')
        if isinstance(data, dict):
            mid = data.get('message_id') or data.get('msg_id')
            if mid:
                return str(mid)
                
    # 2. 对象属性提取 (适配其他面向对象设计的平台)
    if hasattr(resp, 'message_id') and getattr(resp, 'message_id'):
        return str(getattr(resp, 'message_id'))
    if hasattr(resp, 'msg_id') and getattr(resp, 'msg_id'):
        return str(getattr(resp, 'msg_id'))
        
    return ""


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
        resp = await bot.send(img_bytes)
        
        # 【修复点】：使用强化的 msg_id 提取器，确保一定能存入数据库
        msg_id = _extract_msg_id(resp)
        if msg_id:
            await update_fortune_msg_id(user_id, today, msg_id)
            
    except Exception as e:
        await bot.send(f'运势获取失败，服务器开了个小差：{e}')


@jrys_sv.on_fullmatch('毁签', block=True)
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
        resp = await bot.send(img_bytes)
        
        # 【修复点】：毁签后同样需要准确存档新图片的 msg_id
        msg_id = _extract_msg_id(resp)
        if msg_id:
            await update_fortune_msg_id(user_id, today, msg_id)
            
    except Exception as e:
        await bot.send(f'毁签过程出现了小故障：{e}')


@jrys_sv.on_fullmatch('运势背景图', block=True)
async def send_fortune_bg(bot: Bot, ev: Event):
    """获取运势底图（支持引用卡片、@别人、或直接获取自己的）"""
    today = datetime.now().strftime('%Y-%m-%d')
    record = None
    
    try:
        # 1. 优先判定：是否对着某张具体的运势卡片进行了“回复”
        if getattr(ev, 'reply', None):
            record = await get_fortune_record_by_msg_id(today, str(ev.reply))
            # 【修复点】：切断错误兜底。如果引用了图片但是找不到记录，立刻报错停止，绝不发自己的图凑数！
            if not record:
                return await bot.send("未能识别此卡片。由于机器人刚刚重启或这并不是今天的运势卡，找不到原底图记录啦！")
        else:
            # 2. 如果没回复，则按 @ 某人或本人查询
            target_id = ev.user_id
            if getattr(ev, 'at_list', None) and len(ev.at_list) > 0:
                target_id = ev.at_list[0]
            elif getattr(ev, 'at', None):
                target_id = ev.at
                
            record = await get_fortune_record(target_id, today)
            
            if not record:
                if target_id != ev.user_id:
                    return await bot.send("这位群友今天还没有抽取运势呢！")
                else:
                    return await bot.send("你今天还没有抽取运势呢！请先发送【运势】。")

        bg_path = record['fortune_data'].get('backgroundImage', '')
        if not bg_path:
            return await bot.send("未能找到对应的背景图数据！")
            
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
    
    msg = ["📊 当前运势等级与概率配置："]
    for lv in level_config:
        msg.append(f"{lv['stars']} {lv['name']} - {lv['probability']}%")
        
    msg.append(f"\n概率总和: {total_prob:.1f}%")
    msg.append("✅ 配置正常" if is_valid else "⚠️ 警告：总和非100%，系统已自动按比例分配。")
    await bot.send("\n".join(msg))