"""
运势业务逻辑工具
"""

import json
import random
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
from urllib.parse import urlparse
import asyncio
from datetime import datetime

from .config import jrys_config


def load_fortune_data() -> Dict[str, List[Dict[str, Any]]]:
    """加载运势数据"""
    data_file = Path(__file__).parent / 'data' / 'jrys.json'
    
    if not data_file.exists():
        # 如果文件不存在，返回默认数据
        return {
            "70": [{
                "fortuneSummary": "吉",
                "luckyStar": "★★★★★☆☆",
                "signText": "运势平稳，诸事顺心",
                "unsignText": "今日运势较佳，工作和生活都比较顺利，保持积极的心态。",
                "luckValue": 70
            }]
        }
    
    with open(data_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_fortune_level_config() -> List[Dict[str, Any]]:
    """获取运势等级配置"""
    try:
        levels_config = jrys_config.get_config('fortune_levels').data
        
        # 确保配置是列表格式
        if not isinstance(levels_config, list):
            print(f"配置格式错误: {type(levels_config)}, {levels_config}")
            raise ValueError("配置应该是列表格式")
            
        level_list = []
        
        for config_item in levels_config:
            try:
                # 解析格式: 等级名称:星级字符串:概率(%)
                name_part, star_part, probability_part = config_item.split(':')
                level_list.append({
                    'name': name_part.strip(),
                    'stars': star_part.strip(),
                    'probability': float(probability_part.strip())  # 直接使用百分比
                })
            except (ValueError, IndexError):
                print(f"跳过无效配置项: {config_item}")
                continue
    except Exception as e:
        print(f"读取运势等级配置失败: {e}")
        level_list = []
    
    # 如果配置为空或解析失败，使用默认配置
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
    """验证概率配置是否有效"""
    level_config = get_fortune_level_config()
    total_probability = sum(level['probability'] for level in level_config)
    
    # 允许一定的浮点误差
    is_valid = abs(total_probability - 100.0) < 0.01
    return is_valid, total_probability


def weighted_random_choice_from_levels() -> Dict[str, Any]:
    """直接从运势等级配置中随机选择"""
    level_config = get_fortune_level_config()
    
    if not level_config:
        # 回退到默认
        return {'name': '吉', 'stars': '★★★★☆☆☆', 'probability': 20.0}
    
    # 验证概率总和
    is_valid, total_prob = validate_probabilities()
    if not is_valid:
        # 如果概率总和不是100%，进行归一化处理
        for level in level_config:
            level['probability'] = (level['probability'] / total_prob) * 100.0
    
    # 使用概率随机选择
    r = random.uniform(0, 100)
    current_prob = 0
    
    for level in level_config:
        current_prob += level['probability']
        if r <= current_prob:
            return level
    
    return level_config[-1]  # 兜底返回最后一个


def get_fortune_data() -> Dict[str, Any]:
    """获取随机运势数据"""
    fortune_json = load_fortune_data()
    
    # 使用新的运势等级配置
    selected_level = weighted_random_choice_from_levels()
    
    # 构建运势数据
    fortune_item = {
        'fortuneSummary': selected_level['name'],
        'luckyStar': selected_level['stars'],
        'luckValue': int(selected_level.get('probability', 50))  # 使用概率作为数值
    }
    
    # 尝试从JSON数据中获取对应的签文
    # 首先尝试找到匹配的等级
    matching_entries = []
    for level_key, entries in fortune_json.items():
        for entry in entries:
            if (entry.get('fortuneSummary', '').strip() == selected_level['name'] or
                entry.get('luckyStar', '').strip() == selected_level['stars']):
                matching_entries.append(entry)
    
    if matching_entries:
        # 如果找到匹配的条目，随机选择一个并使用其签文
        selected_entry = random.choice(matching_entries)
        fortune_item.update({
            'signText': selected_entry.get('signText', '运势平稳，诸事顺心'),
            'unsignText': selected_entry.get('unsignText', '今日运势较佳，保持积极心态。')
        })
    else:
        # 如果没有找到匹配的，使用默认签文
        default_texts = get_default_fortune_texts(selected_level['name'])
        fortune_item.update(default_texts)
    
    # 获取随机背景图片
    background_image = get_random_background()
    fortune_item['backgroundImage'] = background_image
    
    return fortune_item


def get_default_fortune_texts(level_name: str) -> Dict[str, str]:
    """根据等级获取默认的签文"""
    fortune_texts = {
        '大吉': {
            'signText': '鸿运当头，万事亨通，财源广进，吉星高照',
            'unsignText': '今日运势极佳，是非常适合做重要决定和开始新事业的日子。财运、事业运、感情运都非常旺盛，把握机会，必有所成。'
        },
        '中吉': {
            'signText': '吉星照耀，诸事顺遂，贵人相助，前程似锦',
            'unsignText': '今日运势很好，各方面都比较顺利。工作上容易得到贵人帮助，感情生活也较为和谐，适合进行重要的交流和协商。'
        },
        '小吉': {
            'signText': '小有收获，步步为营，稳中求进，渐入佳境',
            'unsignText': '今日运势不错，虽然不会有大的突破，但各方面都在稳步发展。保持现有的节奏，持续努力，会有不错的收获。'
        },
        '吉': {
            'signText': '运势平稳，诸事顺心，心想事成，平安顺遂',
            'unsignText': '今日运势良好，生活工作都比较顺心。虽然没有特别大的惊喜，但也不会遇到什么困难，是平稳发展的一天。'
        },
        '末吉': {
            'signText': '谨慎行事，量力而为，守成为宜，不宜冒进',
            'unsignText': '今日运势一般，建议保持谨慎的态度。不适合做重大决定或冒险行为，专注于完成手头的工作，维持现状为宜。'
        },
        '凶': {
            'signText': '诸事不顺，小心谨慎，避免冲突，以退为进',
            'unsignText': '今日运势偏差，可能会遇到一些小的困难和阻碍。建议保持低调，避免与他人发生冲突，专注于调整心态。'
        },
        '小凶': {
            'signText': '运势欠佳，凡事小心，避免决策，静待时机',
            'unsignText': '今日运势不太理想，容易遇到小的挫折和困难。建议推迟重要决定，保持耐心，等待更好的时机。'
        },
        '大凶': {
            'signText': '运势低迷，宜静不宜动，修身养性，等待转机',
            'unsignText': '今日运势较差，建议尽量减少外出和重要活动。适合在家休息、反思总结，或进行一些修身养性的活动，等待运势好转。'
        }
    }
    
    return fortune_texts.get(level_name, {
        'signText': '运势未明，保持平常心，顺其自然',
        'unsignText': '今日运势情况不明，建议保持平常心态，顺其自然地处理各种事务。'
    })


def get_random_background() -> str:
    """获取随机背景图片路径"""
    try:
        background_paths = jrys_config.get_config('background_images').data
        
        if not background_paths:
            # 使用默认备用图片
            fallback_path = Path(__file__).parent / 'data' / 'backgroundFolder' / 'miao.jpg'
            return str(fallback_path) if fallback_path.exists() else ''
        
        # 展开所有可能的背景图片路径
        all_backgrounds = []
        
        for path_str in background_paths:
            path = Path(path_str)
            
            if path.suffix.lower() == '.txt':
                # 读取txt文件中的URL列表
                if path.exists():
                    try:
                        with open(path, 'r', encoding='utf-8') as f:
                            urls = [line.strip() for line in f if line.strip() and not line.strip().startswith('#')]
                            all_backgrounds.extend(urls)
                    except Exception as e:
                        print(f"读取txt文件失败 {path}: {e}")
                        continue
            elif path.is_dir():
                # 扫描目录中的图片文件和txt文件
                for item in path.rglob('*'):
                    if item.suffix.lower() == '.txt':
                        # 读取txt文件
                        try:
                            with open(item, 'r', encoding='utf-8') as f:
                                urls = [line.strip() for line in f if line.strip() and not line.strip().startswith('#')]
                                all_backgrounds.extend(urls)
                        except Exception as e:
                            print(f"读取txt文件失败 {item}: {e}")
                            continue
                    elif item.suffix.lower() in ['.jpg', '.jpeg', '.png', '.webp', '.bmp']:
                        all_backgrounds.append(str(item))
            elif path.is_file():
                # 直接添加图片文件
                if path.suffix.lower() in ['.jpg', '.jpeg', '.png', '.webp', '.bmp']:
                    all_backgrounds.append(str(path))
            else:
                # 可能是URL
                if is_url(path_str):
                    all_backgrounds.append(path_str)
        
        if not all_backgrounds:
            # 如果没有找到任何背景，使用默认备用图片
            fallback_path = Path(__file__).parent / 'data' / 'backgroundFolder' / 'miao.jpg'
            return str(fallback_path) if fallback_path.exists() else ''
        
        selected = random.choice(all_backgrounds)
        print(f"选中的背景图: {selected}")
        return selected
    
    except Exception as e:
        print(f"获取背景图片失败: {e}")
        # 出错时使用默认备用图片
        fallback_path = Path(__file__).parent / 'data' / 'backgroundFolder' / 'miao.jpg'
        return str(fallback_path) if fallback_path.exists() else ''


def is_url(string: str) -> bool:
    """判断字符串是否为URL"""
    try:
        result = urlparse(string)
        return all([result.scheme, result.netloc])
    except ValueError:
        return False


async def download_image(url: str, save_path: str = None) -> str:
    """下载网络图片（如果需要的话）"""
    if not is_url(url):
        return url
    
    # 如果提供了保存路径，尝试下载图片到本地
    if save_path:
        try:
            try:
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as response:
                        if response.status == 200:
                            content = await response.read()
                            with open(save_path, 'wb') as f:
                                f.write(content)
                            return save_path
            except ImportError:
                # 如果没有aiohttp，使用urllib
                import urllib.request
                urllib.request.urlretrieve(url, save_path)
                return save_path
        except Exception:
            pass
    
    return url


def generate_star_string(luck_value: int) -> str:
    """根据运势数值生成星星字符串"""
    # 使用默认映射
    if luck_value >= 98:
        return '★★★★★★★'
    elif luck_value >= 84:
        return '★★★★★★☆'
    elif luck_value >= 70:
        return '★★★★★☆☆'
    elif luck_value >= 56:
        return '★★★★☆☆☆'
    elif luck_value >= 42:
        return '★★★☆☆☆☆'
    elif luck_value >= 28:
        return '★★☆☆☆☆☆'
    elif luck_value >= 14:
        return '★☆☆☆☆☆☆'
    else:
        return '☆☆☆☆☆☆☆'


def get_fortune_level_name(luck_value: int) -> str:
    """根据运势数值获取等级名称"""
    # 使用默认映射
    if luck_value >= 98:
        return '大吉'
    elif luck_value >= 84:
        return '中吉'
    elif luck_value >= 70:
        return '小吉'
    elif luck_value >= 56:
        return '吉'
    elif luck_value >= 42:
        return '末吉'
    elif luck_value >= 28:
        return '凶'
    elif luck_value >= 14:
        return '小凶'
    else:
        return '大凶'


def get_available_luck_values() -> List[int]:
    """获取所有可用的运势数值"""
    # 返回0-100的所有整数值
    return list(range(0, 101))


# JSON存储相关功能

def get_userjrys_path() -> Path:
    """获取用户运势数据存储路径"""
    return Path(__file__).parent / 'userjrys'


def ensure_userjrys_dir():
    """确保userjrys目录存在"""
    userjrys_path = get_userjrys_path()
    userjrys_path.mkdir(exist_ok=True)
    return userjrys_path


def get_date_json_path(date: str) -> Path:
    """获取指定日期的JSON文件路径"""
    userjrys_path = ensure_userjrys_dir()
    return userjrys_path / f"{date}.json"


async def save_fortune_record(user_id: str, date: str, fortune_data: Dict[str, Any], 
                            background_image: str = '', bot_id: str = '') -> bool:
    """保存运势记录到JSON文件"""
    try:
        json_file = get_date_json_path(date)
        
        # 读取现有数据
        data = {}
        if json_file.exists():
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        
        # 添加用户记录
        data[user_id] = {
            'user_id': user_id,
            'date': date,
            'fortune_data': fortune_data,
            'background_image': background_image,
            'bot_id': bot_id,
            'created_at': datetime.now().isoformat()
        }
        
        # 保存文件
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        return True
    except Exception as e:
        print(f"保存运势记录失败: {e}")
        return False


async def get_fortune_record(user_id: str, date: str) -> Optional[Dict[str, Any]]:
    """获取用户指定日期的运势记录"""
    try:
        json_file = get_date_json_path(date)
        
        if not json_file.exists():
            return None
        
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return data.get(user_id)
    except Exception as e:
        print(f"读取运势记录失败: {e}")
        return None


async def cleanup_old_fortune_files(keep_days: int = 7) -> int:
    """清理超过指定天数的运势文件"""
    try:
        userjrys_path = get_userjrys_path()
        if not userjrys_path.exists():
            return 0
            
        from datetime import datetime, timedelta
        cutoff_date = datetime.now() - timedelta(days=keep_days)
        cleaned_count = 0
        
        for json_file in userjrys_path.glob('*.json'):
            try:
                # 从文件名提取日期 (YYYY-MM-DD.json)
                date_str = json_file.stem
                file_date = datetime.strptime(date_str, '%Y-%m-%d')
                
                if file_date < cutoff_date:
                    json_file.unlink()
                    cleaned_count += 1
            except (ValueError, OSError):
                # 忽略无法解析的文件名或删除失败的情况
                continue
                
        return cleaned_count
    except Exception as e:
        print(f"清理运势文件失败: {e}")
        return 0


async def get_user_fortune_history(user_id: str, limit: int = 7) -> List[Dict[str, Any]]:
    """获取用户的运势历史记录"""
    try:
        userjrys_path = get_userjrys_path()
        if not userjrys_path.exists():
            return []
            
        history = []
        json_files = sorted(userjrys_path.glob('*.json'), reverse=True)
        
        for json_file in json_files[:limit]:
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                if user_id in data:
                    history.append(data[user_id])
            except Exception:
                continue
                
        return history
    except Exception as e:
        print(f"获取运势历史失败: {e}")
        return []