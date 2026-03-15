"""
运势插件配置
"""

from typing import Dict, List
from pathlib import Path

from gsuid_core.data_store import get_res_path
from gsuid_core.utils.plugins_config.gs_config import StringConfig
from gsuid_core.utils.plugins_config.models import (
    GSC,
    GsStrConfig,
    GsBoolConfig,
    GsIntConfig,
    GsListStrConfig,
)

# 插件数据路径
PLUGIN_DATA_PATH = get_res_path('DailyFortune')

# 默认配置
CONFIG_DEFAULT: Dict[str, GSC] = {
    'commands': GsListStrConfig(
        '运势命令',
        '用户可以使用的运势查询命令列表',
        ['运势', 'jrys', '今日运势', '抽签']
    ),
    'keep_days': GsIntConfig(
        '运势记录保存天数',
        '运势记录在数据库中保存的天数，超过此天数的记录将被自动清理',
        7,
        max_value=365
    ),
    'enable_auto_cleanup': GsBoolConfig(
        '启用自动清理',
        '每日自动清理过期的运势记录',
        True
    ),
    'background_images': GsListStrConfig(
        '背景图片路径',
        '运势卡片的背景图片路径列表，支持本地路径和URL',
        [
            str(Path(__file__).parent / 'data' / 'backgroundFolder' / 'ba.txt'),
            str(Path(__file__).parent / 'data' / 'backgroundFolder' / '猫羽雫.txt'),
            str(Path(__file__).parent / 'data' / 'backgroundFolder' / '魔卡.txt'),
            str(Path(__file__).parent / 'data' / 'backgroundFolder' / 'miku.txt'),
            str(Path(__file__).parent / 'data' / 'backgroundFolder' / '白圣女.txt'),
            str(Path(__file__).parent / 'data' / 'backgroundFolder' / 'miao.jpg')
        ]
    ),
    'font_path': GsStrConfig(
        '字体文件路径',
        '运势卡片使用的字体文件路径',
        str(Path(__file__).parent / 'data' / 'AaTianMeiXinDongNaiLaoTi-2.ttf')
    ),
    'card_width': GsIntConfig(
        '卡片宽度',
        '运势卡片的宽度像素',
        1080,
        max_value=2000
    ),
    'card_height': GsIntConfig(
        '卡片高度', 
        '运势卡片的高度像素',
        1920,
        max_value=3000
    ),
    'text_color': GsStrConfig(
        '文字颜色',
        '运势卡片文字的颜色 (RGB格式: 255,255,255)',
        '255,255,255'
    ),
    'shadow_color': GsStrConfig(
        '阴影颜色',
        '运势卡片文字阴影的颜色 (RGBA格式: 0,0,0,128)',
        '0,0,0,128'
    ),
    'mask_opacity': GsIntConfig(
        '遮罩透明度',
        '背景图片遮罩的透明度 (0-255)',
        128,
        max_value=255
    ),
    'enable_gradient_stars': GsBoolConfig(
        '启用星星渐变',
        '运势星星是否使用彩色渐变效果',
        True
    ),
    'fortune_levels': GsListStrConfig(
        '运势等级配置',
        '自定义运势等级名称和抽取概率，格式：等级名称:星级字符串:概率(%) 注意：所有概率总和应为100%',
        [
            '大凶:☆☆☆☆☆☆☆:3',
            '小凶:★☆☆☆☆☆☆:5', 
            '凶:★★☆☆☆☆☆:7',
            '末吉:★★★☆☆☆☆:10',
            '吉:★★★★☆☆☆:20',
            '小吉:★★★★★☆☆:25',
            '中吉:★★★★★★☆:20',
            '大吉:★★★★★★★:10'
        ]
    ),
    'fortune_probabilities': GsListStrConfig(
        '运势概率权重（已弃用）',
        '此配置项已被运势等级配置取代，请使用上面的运势等级配置',
        [
            '0:5',    # 保留用于向后兼容
            '14:10',  
            '28:12',  
            '42:15',  
            '56:30',  
            '70:35',  
            '84:45',  
            '98:25'   
        ]
    )
}

# 配置文件路径
CONFIG_PATH = PLUGIN_DATA_PATH / 'config.json'

# 创建配置对象
jrys_config = StringConfig('DailyFortune', CONFIG_PATH, CONFIG_DEFAULT)