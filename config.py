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
    
    # ================= 新增毁签相关配置 =================
    'redraw_limit': GsIntConfig('每日毁签次数', '每人每天可以重新抽取运势的次数，0为不可毁签', 1, 10),
    'redraw_empty_message': GsStrConfig('毁签次数耗尽提示', '毁签次数用完时的回复文本', '你的毁签次数已用完，请明天再来吧！'),
    # ====================================================

    'fortune_levels': GsListStrConfig(
        '运势概率与星级配置',
        '格式 => 运势名称:星级符号:抽中概率(%)。即使不小心打成中文冒号，系统也会自动修复！',
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