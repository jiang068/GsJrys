import json
import random
from pathlib import Path
from typing import Dict, Any, List, Tuple
from datetime import datetime, timedelta

from .config import jrys_config, STATIC_DIR, USER_DATA_DIR

# 确保动态数据目录存在
USER_DATA_DIR.mkdir(parents=True, exist_ok=True)

def load_fortune_texts() -> Dict[str, List[Dict]]:
    """加载运势签文数据"""
    data_file = STATIC_DIR / 'jrys.json'
    if data_file.exists():
        with open(data_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def get_fortune_level_config() -> List[Dict]:
    levels_config = jrys_config.get_config('fortune_levels').data
    level_list = []
    
    for item in levels_config:
        try:
            name, stars, prob = item.split(':')
            level_list.append({
                'name': name.strip(),
                'stars': stars.strip(),
                'probability': float(prob.strip())
            })
        except Exception:
            continue
            
    # 兜底默认值
    if not level_list:
        level_list = [{'name': '吉', 'stars': '★★★★☆☆☆', 'probability': 100.0}]
    return level_list

def validate_probabilities() -> Tuple[bool, float]:
    lvls = get_fortune_level_config()
    total = sum(l['probability'] for l in lvls)
    return abs(total - 100.0) < 0.01, total

def get_random_background() -> str:
    """全自动扫描背景图目录，支持本地图片和 txt 网络链接库"""
    bg_folder = STATIC_DIR / 'backgroundFolder'
    if not bg_folder.exists():
        bg_folder.mkdir(parents=True)
        return ""
        
    all_bgs = []
    for file in bg_folder.rglob('*'):
        # 处理纯文本 URL 库
        if file.suffix.lower() == '.txt':
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    all_bgs.extend([line.strip() for line in f if line.strip() and not line.startswith('#')])
            except Exception:
                pass
        # 处理本地图片
        elif file.suffix.lower() in ['.jpg', '.jpeg', '.png', '.webp', '.bmp']:
            all_bgs.append(str(file))
            
    return random.choice(all_bgs) if all_bgs else ""

def get_fortune_data() -> Dict[str, Any]:
    levels = get_fortune_level_config()
    is_valid, total_prob = validate_probabilities()
    
    # 按权重随机抽选等级
    r = random.uniform(0, total_prob if not is_valid else 100.0)
    current = 0
    selected_lv = levels[-1]
    
    for lv in levels:
        current += lv['probability']
        if r <= current:
            selected_lv = lv
            break
            
    fortune_item = {
        'fortuneSummary': selected_lv['name'],
        'luckyStar': selected_lv['stars'],
        'luckValue': int(selected_lv['probability']),
        'backgroundImage': get_random_background()
    }
    
    # 匹配签文
    texts = load_fortune_texts()
    matches = []
    for entries in texts.values():
        for e in entries:
            if e.get('fortuneSummary') == selected_lv['name'] or e.get('luckyStar') == selected_lv['stars']:
                matches.append(e)
                
    if matches:
        pick = random.choice(matches)
        fortune_item['signText'] = pick.get('signText', '运势平稳')
        fortune_item['unsignText'] = pick.get('unsignText', '顺其自然。')
    else:
        fortune_item['signText'] = '运势未明，顺其自然'
        fortune_item['unsignText'] = '保持平常心，今天也是充实的一天。'
        
    return fortune_item

def get_date_json_path(date: str) -> Path:
    return USER_DATA_DIR / f"{date}.json"

async def save_fortune_record(user_id: str, date: str, fortune_data: Dict, bot_id: str):
    json_file = get_date_json_path(date)
    data = {}
    if json_file.exists():
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
    data[str(user_id)] = {
        'fortune_data': fortune_data,
        'bot_id': bot_id,
        'created_at': datetime.now().isoformat()
    }
    
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

async def get_fortune_record(user_id: str, date: str) -> dict:
    json_file = get_date_json_path(date)
    if json_file.exists():
        with open(json_file, 'r', encoding='utf-8') as f:
            return json.load(f).get(str(user_id))
    return None

async def cleanup_old_fortune_files() -> int:
    keep_days = jrys_config.get_config('keep_days').data
    cutoff = datetime.now() - timedelta(days=keep_days)
    count = 0
    
    for file in USER_DATA_DIR.glob('*.json'):
        if file.name == 'config.json': continue
        try:
            file_date = datetime.strptime(file.stem, '%Y-%m-%d')
            if file_date < cutoff:
                file.unlink()
                count += 1
        except Exception:
            pass
    return count

def get_formatted_date() -> str:
    """获取参考图风格的格式化日期，例如：2026年03月11日 星期三"""
    now = datetime.now()
    weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
    return f"{now.strftime('%Y年%m月%d日')} {weekdays[now.weekday()]}"