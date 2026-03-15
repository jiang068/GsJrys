import httpx
import math
from pathlib import Path
from typing import Tuple, Dict
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from .config import jrys_config, STATIC_DIR

async def load_image_from_url(url: str, timeout: int = 10) -> Image.Image:
    """现代异步网络请求 (使用 httpx)"""
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return Image.open(BytesIO(resp.content)).convert('RGBA')
    except Exception as e:
        print(f"背景图片下载失败: {e}")
        return None

def crop_center_img(img: Image.Image, width: int, height: int) -> Image.Image:
    orig_w, orig_h = img.size
    scale = max(width / orig_w, height / orig_h)
    new_w, new_h = int(orig_w * scale), int(orig_h * scale)
    
    img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    left, top = (new_w - width) // 2, (new_h - height) // 2
    return img.crop((left, top, left + width, top + height))

def draw_star_with_gradient(draw: ImageDraw.Draw, center: Tuple[int, int], size: int, filled: bool) -> None:
    x, y = center
    points = []
    for i in range(10):
        angle = math.radians(i * 36 - 90)
        radius = size if i % 2 == 0 else size * 0.4
        points.append((x + radius * math.cos(angle), y + radius * math.sin(angle)))
        
    fill_c = (255, 215, 0, 255) if filled else (0, 0, 0, 0)
    out_c = (0, 0, 0, 128) if filled else (200, 200, 200, 200)
    draw.polygon(points, fill=fill_c, outline=out_c, width=2)

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

async def draw_fortune_card(user_name: str, fortune_data: Dict) -> bytes:
    W = jrys_config.get_config('card_width').data
    H = jrys_config.get_config('card_height').data
    mask_op = jrys_config.get_config('mask_opacity').data
    
    bg_path = fortune_data.get('backgroundImage', '')
    bg = None
    
    # 智能加载背景图
    if bg_path:
        if bg_path.startswith('http'):
            bg = await load_image_from_url(bg_path)
        elif Path(bg_path).exists():
            bg = Image.open(bg_path).convert('RGBA')
            
    # 兜底纯色背景
    if not bg:
        bg = Image.new('RGBA', (W, H), (161, 196, 253, 255))
        
    bg = crop_center_img(bg, W, H)
    img = Image.new('RGBA', (W, H))
    img.paste(bg, (0, 0))
    
    # 底部磨砂玻璃遮罩
    mask_h = 700
    mask_y = H - mask_h
    lower_bg = img.crop((0, mask_y, W, H)).filter(ImageFilter.BoxBlur(10))
    tint = Image.new('RGBA', (W, mask_h), (0, 0, 0, mask_op))
    img.paste(Image.alpha_composite(lower_bg, tint), (0, mask_y))
    
    draw = ImageDraw.Draw(img)
    
    # 智能加载字体
    font_file = STATIC_DIR / 'AaTianMeiXinDongNaiLaoTi-2.ttf'
    try:
        font_path = str(font_file) if font_file.exists() else None
        fn_name = ImageFont.truetype(font_path, 36) if font_path else ImageFont.load_default()
        fn_title = ImageFont.truetype(font_path, 60) if font_path else ImageFont.load_default()
        fn_body = ImageFont.truetype(font_path, 38) if font_path else ImageFont.load_default()
    except Exception:
        fn_name = fn_title = fn_body = ImageFont.load_default()

    # 排版文字
    curr_y = mask_y + 40
    
    # 名字
    draw.text((W//2, curr_y), f"@{user_name}", font=fn_name, fill=(255,255,255), anchor="mm")
    curr_y += 70
    
    # 大字：吉凶
    draw.text((W//2, curr_y), fortune_data['fortuneSummary'], font=fn_title, fill=(255,215,0), anchor="mm")
    curr_y += 80
    
    # 星星
    stars = fortune_data['luckyStar']
    star_spacing = 45
    start_x = (W - len(stars) * star_spacing) // 2 + 20
    for i, star in enumerate(stars):
        draw_star_with_gradient(draw, (start_x + i * star_spacing, curr_y), 20, star == '★')
    curr_y += 70
    
    # 正文
    for txt in [fortune_data['signText'], fortune_data['unsignText']]:
        for line in wrap_text(txt, fn_body, W - 100):
            draw.text((W//2, curr_y), line, font=fn_body, fill=(255,255,255), anchor="mm")
            curr_y += 50
        curr_y += 20
        
    buf = BytesIO()
    img.save(buf, format='PNG')
    return buf.getvalue()