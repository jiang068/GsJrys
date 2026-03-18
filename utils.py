import json
import random
from pathlib import Path
from typing import Dict, Any, List, Tuple
from datetime import datetime, timedelta

from gsuid_core.logger import logger

from .config import jrys_config, STATIC_DIR, USER_DATA_DIR

USER_DATA_DIR.mkdir(parents=True, exist_ok=True)

def load_fortune_texts() -> Dict[str, List[Dict]]:
    custom_path_str = jrys_config.get_config('custom_json_path').data
    data_file = STATIC_DIR / 'jrys.json'
    
    if custom_path_str:
        cleaned_path_str = custom_path_str.strip(' "\'')
        
        if cleaned_path_str:
            custom_path = Path(cleaned_path_str)
            
            if not custom_path.is_absolute():
                plugin_root = Path(__file__).parent
                custom_path = (plugin_root / custom_path).resolve()
            else:
                custom_path = custom_path.resolve()
                
            if custom_path.exists() and custom_path.is_file():
                data_file = custom_path
            else:
                logger.warning(f"[GsJrys] 自定义文件不存在，已回退默认！实际寻找的绝对路径是: {custom_path}")
            
    if data_file.exists():
        try:
            with open(data_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"[GsJrys] 运势 JSON 解析失败: {e}")
            return {}
    return {}

def get_fortune_level_config() -> List[Dict]:
    levels_config = jrys_config.get_config('fortune_levels').data
    level_list = []
    
    def parse_items(items):
        for item in items:
            try:
                item_str = str(item).replace('：', ':').strip()
                parts = item_str.split(':')
                if len(parts) >= 2:
                    lvl = int(parts[0].strip())
                    prob = float(parts[1].strip())
                    if 0 <= lvl <= 7:  # 确保只有 0-7 级
                        level_list.append({'level': str(lvl), 'probability': prob})
            except Exception:
                continue

    if isinstance(levels_config, list):
        parse_items(levels_config)
    elif isinstance(levels_config, str):
        try:
            import ast
            parsed = ast.literal_eval(levels_config)
            if isinstance(parsed, list):
                parse_items(parsed)
        except Exception:
            pass
            
    # 如果用户乱填导致配置为空，启用极致精简的保底概率
    if not level_list:
        level_list = [
            {'level': '0', 'probability': 3.0},
            {'level': '1', 'probability': 5.0},
            {'level': '2', 'probability': 7.0},
            {'level': '3', 'probability': 10.0},
            {'level': '4', 'probability': 20.0},
            {'level': '5', 'probability': 25.0},
            {'level': '6', 'probability': 20.0},
            {'level': '7', 'probability': 10.0}
        ]
    return level_list

def validate_probabilities() -> Tuple[bool, float]:
    lvls = get_fortune_level_config()
    total = sum(l['probability'] for l in lvls)
    return abs(total - 100.0) < 0.01, total

def get_random_background() -> str:
    custom_bg_str = jrys_config.get_config('custom_bg_path').data
    bg_folder = STATIC_DIR / 'backgroundFolder'
    
    if custom_bg_str:
        cleaned_path_str = custom_bg_str.strip(' "\'')
        
        if cleaned_path_str:
            custom_path = Path(cleaned_path_str)
            
            if not custom_path.is_absolute():
                plugin_root = Path(__file__).parent
                custom_path = (plugin_root / custom_path).resolve()
            else:
                custom_path = custom_path.resolve()
                
            if custom_path.exists() and custom_path.is_dir():
                bg_folder = custom_path
            else:
                logger.warning(f"[GsJrys] 自定义背景图目录不存在或不是文件夹，已回退默认！实际寻找的路径是: {custom_path}")
                
    if not bg_folder.exists():
        bg_folder.mkdir(parents=True, exist_ok=True)
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
    
    # 按概率抽取星级
    for lv in levels:
        current += lv['probability']
        if r <= current:
            selected_lv = lv
            break
            
    target_level = selected_lv['level']
    stars_count = int(target_level)
    
    # 动态生成星星字符串，不用再写死在配置和 JSON 里
    lucky_star = '★' * stars_count + '☆' * (7 - stars_count)
            
    fortune_item = {
        'luckyStar': lucky_star,
        'luckValue': int(selected_lv['probability']),
        'backgroundImage': get_random_background()
    }
    
    texts = load_fortune_texts()
    
    # 直接根据数字键值（如 "7", "6"）去 JSON 里取数组
    level_texts = texts.get(target_level, [])
    
    if level_texts:
        pick = random.choice(level_texts)
        # 只要 JSON 里有的内容，直接塞进去，高度自由
        fortune_item['fortuneSummary'] = pick.get('fortuneSummary', '神秘运势')
        fortune_item['signText'] = pick.get('signText', '……')
        fortune_item['unsignText'] = pick.get('unsignText', '……')
    else:
        # 如果对应的星级在 JSON 里完全没写，给个极简防报错提示
        fortune_item['fortuneSummary'] = '未知'
        fortune_item['signText'] = '运势迷失在了时空裂隙中...'
        fortune_item['unsignText'] = f'请检查 jrys.json 中是否正确配置了 {target_level} 星级的数据。'
        
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