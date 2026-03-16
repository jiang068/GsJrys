import json
import random
from pathlib import Path
from typing import Dict, Any, List, Tuple
from datetime import datetime, timedelta

from .config import jrys_config, STATIC_DIR, USER_DATA_DIR

USER_DATA_DIR.mkdir(parents=True, exist_ok=True)

def load_fortune_texts() -> Dict[str, List[Dict]]:
    data_file = STATIC_DIR / 'jrys.json'
    if data_file.exists():
        try:
            with open(data_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def get_fortune_level_config() -> List[Dict]:
    levels_config = jrys_config.get_config('fortune_levels').data
    level_list = []
    
    if isinstance(levels_config, list):
        for item in levels_config:
            try:
                item_str = str(item).replace('：', ':').strip()
                parts = item_str.split(':')
                if len(parts) >= 3:
                    level_list.append({
                        'name': parts[0].strip(),
                        'stars': parts[1].strip(),
                        'probability': float(parts[2].strip())
                    })
            except Exception:
                continue
    elif isinstance(levels_config, str):
        try:
            import ast
            parsed = ast.literal_eval(levels_config)
            if isinstance(parsed, list):
                for item in parsed:
                    item_str = str(item).replace('：', ':').strip()
                    parts = item_str.split(':')
                    if len(parts) >= 3:
                        level_list.append({
                            'name': parts[0].strip(),
                            'stars': parts[1].strip(),
                            'probability': float(parts[2].strip())
                        })
        except Exception:
            pass
            
    if not level_list:
        level_list = [
            {'name': '大凶', 'stars': '☆☆☆☆☆☆☆', 'probability': 3.0},
            {'name': '小凶', 'stars': '★☆☆☆☆☆☆', 'probability': 5.0},
            {'name': '凶', 'stars': '★★☆☆☆☆☆', 'probability': 7.0},
            {'name': '末吉', 'stars': '★★★☆☆☆☆', 'probability': 10.0},
            {'name': '吉', 'stars': '★★★★☆☆☆', 'probability': 20.0},
            {'name': '小吉', 'stars': '★★★★★☆☆', 'probability': 25.0},
            {'name': '中吉', 'stars': '★★★★★★☆', 'probability': 20.0},
            {'name': '大吉', 'stars': '★★★★★★★', 'probability': 10.0}
        ]
    return level_list

def validate_probabilities() -> Tuple[bool, float]:
    lvls = get_fortune_level_config()
    total = sum(l['probability'] for l in lvls)
    return abs(total - 100.0) < 0.01, total

def get_random_background() -> str:
    bg_folder = STATIC_DIR / 'backgroundFolder'
    if not bg_folder.exists():
        bg_folder.mkdir(parents=True)
        return ""
        
    all_bgs = []
    for file in bg_folder.rglob('*'):
        if file.suffix.lower() == '.txt':
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    all_bgs.extend([line.strip() for line in f if line.strip() and not line.startswith('#')])
            except Exception:
                pass
        elif file.suffix.lower() in ['.jpg', '.jpeg', '.png', '.webp', '.bmp']:
            all_bgs.append(str(file))
            
    return random.choice(all_bgs) if all_bgs else ""

def get_fortune_data() -> Dict[str, Any]:
    levels = get_fortune_level_config()
    is_valid, total_prob = validate_probabilities()
    
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
    
    texts = load_fortune_texts()
    matches = []
    
    target_name = selected_lv['name']
    target_stars = selected_lv['stars']
    
    for entries in texts.values():
        for e in entries:
            json_name = e.get('fortuneSummary', '')
            json_stars = e.get('luckyStar', '')
            if target_name in json_name or target_stars == json_stars:
                matches.append(e)
                
    if matches:
        pick = random.choice(matches)
        if pick.get('fortuneSummary'):
            fortune_item['fortuneSummary'] = pick['fortuneSummary']
        fortune_item['signText'] = pick.get('signText', '运势平稳，诸事顺心')
        fortune_item['unsignText'] = pick.get('unsignText', '今日运势较佳，保持积极的心态。')
    else:
        default_texts = {
            '大吉': ('鸿运当头，万事亨通', '今日运势极佳，是非常适合做重要决定和开始新事业的日子。'),
            '中吉': ('吉星照耀，诸事顺遂', '今日运势很好，工作上容易得到贵人帮助，稳步前行即可。'),
            '小吉': ('小有收获，步步为营', '今日运势不错，稳中求进，会有意想不到的收获。'),
            '吉': ('运势平稳，诸事顺心', '今日生活工作顺心，没有特别大的惊喜，也不会遇到阻碍。'),
            '末吉': ('谨慎行事，量力而为', '建议保持谨慎，专注手头工作，不宜冒进。'),
            '凶': ('诸事不顺，小心谨慎', '今日运势偏差，建议保持低调，避免与他人发生冲突。'),
            '小凶': ('运势欠佳，凡事小心', '容易遇到小的挫折，建议推迟重要决定，保持耐心。'),
            '大凶': ('运势低迷，宜静不宜动', '今日运势较差，建议尽量减少外出和重要活动，谨言慎行。')
        }
        dt = default_texts.get(target_name, ('运势未明，顺其自然', '保持平常心，今天也是充实的一天。'))
        fortune_item['signText'] = dt[0]
        fortune_item['unsignText'] = dt[1]
        
    return fortune_item

def get_date_json_path(date: str) -> Path:
    return USER_DATA_DIR / f"{date}.json"

async def save_fortune_record(user_id: str, date: str, fortune_data: Dict, bot_id: str, redraw_count: int = 0):
    json_file = get_date_json_path(date)
    data = {}
    
    if json_file.exists():
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception:
            pass
            
    data[str(user_id)] = {
        'fortune_data': fortune_data,
        'bot_id': bot_id,
        'redraw_count': redraw_count,
        'created_at': datetime.now().isoformat()
    }
    
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

async def get_fortune_record(user_id: str, date: str) -> dict:
    json_file = get_date_json_path(date)
    if json_file.exists():
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                return json.load(f).get(str(user_id))
        except Exception:
            return None
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
    now = datetime.now()
    weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
    return f"{now.strftime('%Y年%m月%d日')} {weekdays[now.weekday()]}"