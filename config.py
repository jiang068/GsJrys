from typing import Dict
from pathlib import Path
from gsuid_core.data_store import get_res_path
from gsuid_core.utils.plugins_config.gs_config import StringConfig
from gsuid_core.utils.plugins_config.models import GSC, GsStrConfig, GsBoolConfig, GsIntConfig, GsListStrConfig

# ★ 静态资源目录 (存放字体、预设背景图、文案 json)
STATIC_DIR = Path(__file__).parent / 'data'
# ★ 用户数据目录 (存放在 GsCore 集中数据管理的目录中)
USER_DATA_DIR = get_res_path('GsJrys')

CONFIG_DEFAULT: Dict[str, GSC] = {
    'keep_days': GsIntConfig('记录保存天数', '超期的记录将被自动清理以节省空间', 7, 365),
    'enable_auto_cleanup': GsBoolConfig('启用自动清理', '每天有人抽签时顺手清理过期文件', True),
    
    # UI 排版配置
    'card_width': GsIntConfig('卡片宽度', '默认 1080', 1080, 2000),
    'card_height': GsIntConfig('卡片高度', '默认 1920', 1920, 3000),
    'text_color': GsStrConfig('文字颜色', 'RGB格式', '255,255,255'),
    'mask_opacity': GsIntConfig('底部遮罩透明度', '0-255，越大底色越黑', 128, 255),
    'enable_gradient_stars': GsBoolConfig('启用彩色星星', '关闭则显示纯白色星星', True),
    
    # 核心概率配置：格式超级简单
    'fortune_levels': GsListStrConfig(
        '运势概率与星级配置',
        '格式 => 运势名称 : 星级符号 : 抽中概率(%)。请确保概率加起来等于 100。',
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
    )
}

CONFIG_PATH = USER_DATA_DIR / 'config.json'
jrys_config = StringConfig('GsJrys', CONFIG_PATH, CONFIG_DEFAULT)