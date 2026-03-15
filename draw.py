import httpx
from pathlib import Path
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from .config import jrys_config, STATIC_DIR
from .utils import get_formatted_date

_font_cache = {}
_avatar_cache = {}

def get_font(size: int) -> ImageFont.FreeTypeFont:
    if size in _font_cache:
        return _font_cache[size]
    font_file = STATIC_DIR / 'AaTianMeiXinDongNaiLaoTi-2.ttf'
    font = ImageFont.truetype(str(font_file), size) if font_file.exists() else ImageFont.load_default()
    _font_cache[size] = font
    return font

async def load_image_from_url(url: str, timeout: int = 10) -> Image.Image:
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return Image.open(BytesIO(resp.content)).convert('RGBA')
    except Exception:
        return None

async def get_avatar_image(user_id: str) -> Image.Image:
    """获取并缓存QQ头像"""
    if user_id in _avatar_cache:
        return _avatar_cache[user_id]
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            res = await client.get(f"http://q1.qlogo.cn/g?b=qq&nk={user_id}&s=640")
            if res.status_code == 200:
                img = Image.open(BytesIO(res.content)).convert('RGBA')
                _avatar_cache[user_id] = img
                return img
    except Exception:
        pass
    return None

def crop_center_img(img: Image.Image, width: int, height: int) -> Image.Image:
    orig_w, orig_h = img.size
    scale = max(width / orig_w, height / orig_h)
    new_w, new_h = int(orig_w * scale), int(orig_h * scale)
    img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    left, top = (new_w - width) // 2, (new_h - height) // 2
    return img.crop((left, top, left + width, top + height))

def wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list:
    lines, curr = [], ""
    for char in text:
        if font.getlength(curr + char) <= max_width:
            curr += char
        else:
            lines.append(curr)
            curr = char
    if curr: lines.append(curr)
    return lines

def draw_dashed_box(draw: ImageDraw.Draw, box: tuple, fill: tuple, width: int = 2, dash_len: int = 12):
    """绘制虚线边框"""
    x1, y1, x2, y2 = box
    # 横向虚线
    for x in range(int(x1), int(x2), dash_len * 2):
        draw.line([(x, y1), (min(x + dash_len, x2), y1)], fill=fill, width=width)
        draw.line([(x, y2), (min(x + dash_len, x2), y2)], fill=fill, width=width)
    # 纵向虚线
    for y in range(int(y1), int(y2), dash_len * 2):
        draw.line([(x1, y), (x1, min(y + dash_len, y2))], fill=fill, width=width)
        draw.line([(x2, y), (x2, min(y + dash_len, y2))], fill=fill, width=width)

async def draw_fortune_card(user_id: str, fortune_data: dict) -> bytes:
    W, H = 1080, 1920
    
    # 1. 加载并处理背景图
    bg_path = fortune_data.get('backgroundImage', '')
    bg = None
    if bg_path:
        if bg_path.startswith('http'):
            bg = await load_image_from_url(bg_path)
        elif Path(bg_path).exists():
            bg = Image.open(bg_path).convert('RGBA')
    if not bg:
        bg = Image.new('RGBA', (W, H), (161, 196, 253, 255))
        
    bg = crop_center_img(bg, W, H)
    img = Image.new('RGBA', (W, H))
    img.paste(bg, (0, 0))
    
    draw = ImageDraw.Draw(img)
    
    # 2. 绘制右上角 "今日运势" Badge
    font_badge = get_font(42)
    badge_w, badge_h = 240, 80
    badge_x, badge_y = W - badge_w - 50, 60
    # 纯黑半透明底 + 金色边框
    draw.rounded_rectangle((badge_x, badge_y, badge_x + badge_w, badge_y + badge_h), 
                           radius=40, fill=(0, 0, 0, 180), outline=(235, 195, 135, 255), width=3)
    draw.text((badge_x + badge_w//2, badge_y + badge_h//2 - 2), "今日运势", 
              font=font_badge, fill=(235, 195, 135, 255), anchor="mm")
    
    # 3. 生成底部暗态毛玻璃面板
    panel_w = W - 100
    panel_x = 50
    panel_h = 920  # 面板高度
    panel_y = H - panel_h - 60
    panel_box = (panel_x, panel_y, panel_x + panel_w, panel_y + panel_h)
    
    # 抠出底部区域模糊并狠狠压暗 (参考图是很深的黑色)
    glass = img.crop(panel_box).filter(ImageFilter.BoxBlur(18))
    tint = Image.new('RGBA', glass.size, (20, 20, 25, 220))
    glass = Image.alpha_composite(glass, tint)
    
    # 圆角遮罩
    mask = Image.new('L', glass.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, glass.size[0], glass.size[1]), radius=50, fill=255)
    img.paste(glass, (panel_x, panel_y), mask)
    
    # 4. 绘制左上角交叠头像
    avatar_r = 85
    avatar_cx, avatar_cy = panel_x + 140, panel_y
    # 先画外圈白底
    draw.ellipse((avatar_cx - avatar_r - 8, avatar_cy - avatar_r - 8, 
                  avatar_cx + avatar_r + 8, avatar_cy + avatar_r + 8), fill=(255, 255, 255, 255))
    
    # 获取并贴上头像
    avatar_img = await get_avatar_image(user_id)
    if avatar_img:
        avatar_img = avatar_img.resize((avatar_r * 2, avatar_r * 2), Image.Resampling.LANCZOS)
        av_mask = Image.new('L', (avatar_r * 2, avatar_r * 2), 0)
        ImageDraw.Draw(av_mask).ellipse((0, 0, avatar_r * 2, avatar_r * 2), fill=255)
        img.paste(avatar_img, (avatar_cx - avatar_r, avatar_cy - avatar_r), av_mask)
    else:
        draw.ellipse((avatar_cx - avatar_r, avatar_cy - avatar_r, 
                      avatar_cx + avatar_r, avatar_cy + avatar_r), fill=(200, 200, 200, 255))
        
    # 5. 排版面板内部文字
    color_gold = (245, 205, 145, 255)
    color_white = (255, 255, 255, 255)
    color_gray = (200, 200, 200, 255)
    color_dark_gray = (130, 130, 130, 255)
    center_x = W // 2
    
    # 日期
    font_date = get_font(38)
    date_y = panel_y + 90
    draw.text((center_x, date_y), get_formatted_date(), font=font_date, fill=color_gold, anchor="mm")
    
    # 运势大字 (凶/吉等)
    font_huge = get_font(180)
    huge_y = date_y + 140
    # 提取大字 (例如 "大凶" 提取 "凶", "大吉" 提取 "吉")
    summary_text = fortune_data['fortuneSummary']
    main_char = summary_text[-1] if summary_text else "吉"
    draw.text((center_x, huge_y), main_char, font=font_huge, fill=color_white, anchor="mm")
    
    # 星级
    font_star = get_font(60)
    star_y = huge_y + 130
    draw.text((center_x, star_y), fortune_data['luckyStar'], font=font_star, fill=color_gold, anchor="mm")
    
    # 虚线框与小签文
    font_short = get_font(36)
    box_w = panel_w - 120
    box_h = 100
    box_x = panel_x + 60
    box_y = star_y + 60
    # 绘制虚线框 (手工虚线完美还原)
    draw_dashed_box(draw, (box_x, box_y, box_x + box_w, box_y + box_h), fill=(255, 255, 255, 120))
    # 小签文居中
    draw.text((center_x, box_y + box_h // 2 - 2), fortune_data['signText'], font=font_short, fill=color_white, anchor="mm")
    
    # 大签文 (自动换行)
    font_long = get_font(34)
    long_y = box_y + box_h + 50
    lines = wrap_text(fortune_data['unsignText'], font_long, box_w)
    for line in lines:
        draw.text((center_x, long_y), line, font=font_long, fill=color_gray, anchor="mm")
        long_y += 55
        
    # 底部页脚
    font_footer = get_font(28)
    footer_text = jrys_config.get_config('footer_text').data
    draw.text((center_x, panel_y + panel_h - 45), footer_text, font=font_footer, fill=color_dark_gray, anchor="mm")
        
    buf = BytesIO()
    img.save(buf, format='PNG')
    return buf.getvalue()