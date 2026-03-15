### 每日运势（简明说明）

 本插件为 GsCore 机器人提供每日运势卡片生成功能，使用 Pillow 绘制图片，支持本地或网络背景，并可自定义运势等级与概率。

 #### 主要功能
 - 快速命令：`运势`、`jrys`、`今日运势`、`抽签`
 - 管理命令：`清理运势记录`、`查看运势等级`、`测试运势等级 [数值]`（需管理员权限）
 - 存储：使用 `userjrys` 下的 JSON 

 #### 安装与依赖
 1. 放入 GsCore 插件目录
 2. 如果你的gscore不能自动安装依赖，你要自己用pip poetry uv 等安装依赖，示例：
 `pip install -r requirements.txt` 
 （包含 pillow；`aiohttp` 可选）
 3. 将 `data/jrys.json` 与字体文件放入 `data/` 目录

 #### 配置要点
 - 运势等级格式：`名称:星级字符串:概率(%)`（示例：`大吉:★★★★★★★★:15`）
 - 概率会自动归一化，但建议总和为 100%
 - 可在 gscore 配置中调整卡片尺寸、字体与背景路径

 #### 使用建议
 - 背景图片建议不要太大，不要横板
 - 如需更换自定义字体，需包含中文字符

 #### 致谢
 本插件深度参考了 [koishi-plugin-jrys-prpr](https://github.com/koishi-shangxue-plugins/koishi-shangxue-apps/tree/main/plugins/jrys-prpr)

