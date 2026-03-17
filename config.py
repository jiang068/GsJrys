from typing import Dict
from pathlib import Path
from gsuid_core.data_store import get_res_path
from gsuid_core.utils.plugins_config.gs_config import StringConfig
from gsuid_core.utils.plugins_config.models import GSC, GsStrConfig, GsBoolConfig, GsIntConfig, GsListStrConfig

STATIC_DIR = Path(__file__).parent / 'data'
USER_DATA_DIR = get_res_path('GsJrys')

CONFIG_DEFAULT: Dict[str, GSC] = {
    'keep_days': GsIntConfig('记录保存天数', '超期的记录将被自动清理以节省空间', 7, 365),
    'enable_auto_cleanup': GsBoolConfig('启用自动清理', '每天有人抽签时顺手清理过期文件', True),
    'footer_text': GsStrConfig('卡片页脚文字', '显示在底部的说明', '仅供娱乐哦 | GsCore & GsJrys'),
    'panel_opacity': GsIntConfig('黑框不透明度', '毛玻璃黑底的不透明度(0-255，越小越透明)', 120, 255),
    'redraw_limit': GsIntConfig('每日悔签次数', '每人每天可以重新抽取运势的次数，0为不可悔签', 1, 10),
    'redraw_empty_message': GsStrConfig('悔签次数耗尽提示', '悔签次数用完时的回复文本', '你的悔签次数已用完，请明天再来吧！'),
    'fortune_levels': GsListStrConfig(
        '运势概率与星级配置',
        '格式 => 星级(0-7):抽中概率(%)。例如 7:10 表示7星概率为10%。即使打成中文冒号系统也会自动修复！',
        [
            '0:3',
            '1:5', 
            '2:7',
            '3:10',
            '4:20',
            '5:25',
            '6:20',
            '7:10'
        ]
    )
}

CONFIG_PATH = USER_DATA_DIR / 'config.json'
jrys_config = StringConfig('GsJrys', CONFIG_PATH, CONFIG_DEFAULT)