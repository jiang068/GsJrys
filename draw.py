import httpx
import math
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

def draw_dashed_line(draw: ImageDraw.Draw, pt1: tuple, pt2: tuple, fill: tuple, width: int, dash_len: int):
    """两点之间绘制虚线"""
    x1, y1 = pt1
    x2, y2 = pt2
    dist = math.hypot(x2 - x1, y2 - y1)
    if dist <= 0: return
    dashes = max(1, int(dist / dash_len))
    for i in range(dashes):
        if i % 2 == 0:
            start_x = x1 + (x2 - x1) * i / dashes
            start_y = y1 + (y2 - y1) * i / dashes
            end_x = x1 + (x2 - x1) * (i + 1) / dashes
            end_y = y1 + (y2 - y1) * (i + 1) / dashes
            draw.line([(start_x, start_y), (end_x, end_y)], fill=fill, width=width)

def draw_rounded_dashed_box(draw: ImageDraw.Draw, xy: tuple, radius: int, fill: tuple, width: int = 2, dash_len: int = 12):
    """绘制半圆角虚线框"""
    x1, y1, x2, y2 = xy
    draw_dashed_line(draw, (x1+radius, y1), (x2-radius, y1), fill, width, dash_len)
    draw_dashed_line(draw, (x1+radius, y2), (x2-radius, y2), fill, width, dash_len)
    draw_dashed_line(draw, (x1, y1+radius), (x1, y2-radius), fill, width, dash_len)
    draw_dashed_line(draw, (x2, y1+radius), (x2, y2-radius), fill, width, dash_len)
    draw.arc((x1, y1, x1+2*radius, y1+2*radius), 180, 270, fill=fill, width=width)
    draw.arc((x2-2*radius, y1, x2, y1+2*radius), 270, 360, fill=fill, width=width)
    draw.arc((x1, y2-2*radius, x1+2*radius, y2), 90, 180, fill=fill, width=width)
    draw.arc((x2-2*radius, y2-2*radius, x2, y2), 0, 90, fill=fill, width=width)

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
    
    # 获取透明度配置 (默认 120，约 47% 不透明)
    try:
        opacity = jrys_config.get_config('panel_opacity').data
    except Exception:
        opacity = 120

    glass_blur = 15
    glass_tint = (20, 20, 25, opacity)
    
    color_gold = (245, 205, 145, 255)
    color_white = (255, 255, 255, 255)
    color_dash = (255, 255, 255, 200)       # 虚线提亮
    color_footer = (255, 255, 255, 245)     # 页脚极致提亮
    
    # 2. 绘制右上角 "今日运势" Badge
    # 【彻底修复】：独立切割原生底图进行高斯模糊，杜绝边缘混色发灰！
    font_badge = get_font(38)
    badge_w, badge_h = 240, 80
    badge_x, badge_y = W - badge_w - 40, 50
    badge_box = (badge_x, badge_y, badge_x + badge_w, badge_y + badge_h)
    
    b_glass = img.crop(badge_box).filter(ImageFilter.GaussianBlur(12)) # 使用高斯模糊直采
    b_tint = Image.new('RGBA', b_glass.size, glass_tint)
    b_glass = Image.alpha_composite(b_glass, b_tint)
    
    b_mask = Image.new('L', b_glass.size, 0)
    ImageDraw.Draw(b_mask).rounded_rectangle((0, 0, badge_w, badge_h), radius=40, fill=255)
    img.paste(b_glass, (badge_x, badge_y), b_mask)
    
    draw.rounded_rectangle(badge_box, radius=40, outline=color_gold, width=3)
    draw.text((badge_x + badge_w//2, badge_y + badge_h//2 - 2), "今日运势", font=font_badge, fill=color_gold, anchor="mm")
    
    # 3. 生成底部暗态毛玻璃面板
    panel_h = 680  
    panel_x = 30
    panel_w = W - 60
    panel_y = H - panel_h - 40
    panel_box = (panel_x, panel_y, panel_x + panel_w, panel_y + panel_h)
    
    glass = img.crop(panel_box).filter(ImageFilter.BoxBlur(glass_blur))
    tint = Image.new('RGBA', glass.size, glass_tint)
    glass = Image.alpha_composite(glass, tint)
    
    mask = Image.new('L', glass.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, glass.size[0], glass.size[1]), radius=50, fill=255)
    img.paste(glass, (panel_x, panel_y), mask)
    
    # 4. 绘制左上角交叠头像
    avatar_r = 70
    avatar_cx, avatar_cy = panel_x + 110, panel_y
    draw.ellipse((avatar_cx - avatar_r - 6, avatar_cy - avatar_r - 6, 
                  avatar_cx + avatar_r + 6, avatar_cy + avatar_r + 6), fill=color_white)
    
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
    center_x = W // 2
    
    # 日期 (整体往上提)
    current_y = panel_y + 55
    font_date = get_font(34)
    draw.text((center_x, current_y), get_formatted_date(), font=font_date, fill=color_gold, anchor="mm")
    current_y += 65
    
    # 运势大字 (精确适配日期)
    font_huge = get_font(72)
    summary_text = fortune_data['fortuneSummary']
    main_char = summary_text[-1] if summary_text else "吉"
    draw.text((center_x, current_y), main_char, font=font_huge, fill=color_white, anchor="mm")
    current_y += 75
    
    # 星级
    font_star = get_font(50)
    draw.text((center_x, current_y), fortune_data['luckyStar'], font=font_star, fill=color_gold, anchor="mm")
    current_y += 60
    
    # 虚线框布局设定
    box_x = panel_x + 40
    box_w = panel_w - 80
    
    # 【第一个虚线框】：小签文
    font_short = get_font(34)
    box1_h = 75
    draw_rounded_dashed_box(draw, (box_x, current_y, box_x + box_w, current_y + box1_h), 15, color_dash, 2, 10)
    draw.text((center_x, current_y + box1_h // 2 - 2), fortune_data['signText'], font=font_short, fill=color_white, anchor="mm")
    current_y += box1_h + 20
    
    # 【第二个虚线框】：大签文 (自适应行距黑科技)
    font_long = get_font(30)
    lines = wrap_text(fortune_data['unsignText'], font_long, box_w - 40)
    
    box2_y = current_y
    # 底部预留 65px 的绝对空间给页脚，剩余的所有空间全部留给大签文框
    box2_h = (panel_y + panel_h) - box2_y - 65
    draw_rounded_dashed_box(draw, (box_x, box2_y, box_x + box_w, box2_y + box2_h), 15, color_dash, 2, 10)
    
    if lines:
        available_h = box2_h - 20  # 框内上下各留出 10px 边距
        # 弹簧行距：根据行数自动撑开剩余空间
        line_h = available_h / len(lines)
        line_h = min(line_h, 55)   # 但限制最大行距为 55，防止只有两行字时被拉得太散
        
        # 将整个文本块居中悬浮
        total_text_h = line_h * len(lines)
        text_start_y = box2_y + (box2_h - total_text_h) / 2 + line_h / 2 - 2
        
        for line in lines:
            draw.text((center_x, text_start_y), line, font=font_long, fill=color_white, anchor="mm")
            text_start_y += line_h
            
    # 底部页脚
    font_footer = get_font(26)
    try:
        footer_text = jrys_config.get_config('footer_text').data
    except Exception:
        footer_text = "仅供娱乐哦 | GsCore & GsJrys"
        
    draw.text((center_x, panel_y + panel_h - 35), footer_text, font=font_footer, fill=color_footer, anchor="mm")
        
    buf = BytesIO()
    img.save(buf, format='PNG')
    return buf.getvalue()