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
    
    # 【完美解析】：直接读取新版的字典配置结构 Dict[str, List]
    if isinstance(levels_config, dict):
        for name, data_list in levels_config.items():
            if isinstance(data_list, list) and len(data_list) >= 2:
                try:
                    level_list.append({
                        'name': str(name).strip(),
                        'stars': str(data_list[0]).strip(),
                        'probability': float(data_list[1])
                    })
                except Exception:
                    continue
                    
    # 【历史包袱兼容】：如果用户的旧配置文件没删，依然用旧的字符串分割法保底
    elif isinstance(levels_config, list) or isinstance(levels_config, str):
        if isinstance(levels_config, str):
            try:
                import ast
                levels_config = ast.literal_eval(levels_config)
            except Exception:
                levels_config = levels_config.split(',')
                
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
                
    # 终极兜底：如果用户把配置彻底删烂了，自动恢复完美比例
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
    for entries in texts.values():
        for e in entries:
            if selected_lv['name'] in e.get('fortuneSummary', '') or selected_lv['stars'] == e.get('luckyStar', ''):
                matches.append(e)
                
    if matches:
        pick = random.choice(matches)
        fortune_item['signText'] = pick.get('signText', '运势平稳，诸事顺心')
        fortune_item['unsignText'] = pick.get('unsignText', '今日运势较佳，保持积极的心态。')
    else:
        default_texts = {
            '大吉': ('鸿运当头，万事亨通', '今日运势极佳，是非常适合做重要决定和开始新事业的日子。'),
            '中吉': ('吉星照耀，诸事顺遂', '今日运势很好，工作上容易得到贵人帮助，稳步前行即可。'),
            '大凶': ('运势低迷，宜静不宜动', '今日运势较差，建议尽量减少外出和重要活动，谨言慎行。')
        }
        dt = default_texts.get(selected_lv['name'], ('运势未明，顺其自然', '保持平常心，今天也是充实的一天。'))
        fortune_item['signText'] = dt[0]
        fortune_item['unsignText'] = dt[1]
        
    return fortune_item

def get_date_json_path(date: str) -> Path:
    return USER_DATA_DIR / f"{date}.json"

async def save_fortune_record(user_id: str, date: str, fortune_data: Dict, bot_id: str):
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
    """获取参考图风格的格式化日期，例如：2026年03月11日 星期三"""
    now = datetime.now()
    weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
    return f"{now.strftime('%Y年%m月%d日')} {weekdays[now.weekday()]}"