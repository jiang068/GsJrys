"""
运势卡片绘制模块
"""

import re
import math
from typing import Tuple, Dict, Any, Optional
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from io import BytesIO
import asyncio

from .config import jrys_config


async def load_image_from_url(url: str, timeout: int = 10) -> Optional[Image.Image]:
    """从URL加载图片"""
    try:
        # 尝试使用aiohttp
        try:
            import aiohttp
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        content = await response.read()
                        return Image.open(BytesIO(content)).convert('RGBA')
        except ImportError:
            # 如果没有aiohttp，使用urllib (需要在异步中运行同步代码)
            import urllib.request
            import urllib.error
            
            def download_sync():
                try:
                    with urllib.request.urlopen(url, timeout=timeout) as response:
                        content = response.read()
                        return Image.open(BytesIO(content)).convert('RGBA')
                except Exception:
                    return None
            
            # 在线程池中运行同步代码
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, download_sync)
    except Exception as e:
        print(f"下载图片失败 {url}: {e}")
        return None


def create_gradient_background(width: int, height: int) -> Image.Image:
    """创建渐变背景"""
    img = Image.new('RGBA', (width, height), (135, 206, 235, 255))
    
    # 创建简单的垂直渐变
    for y in range(height):
        ratio = y / height
        r = int(135 * (1 - ratio * 0.3))
        g = int(206 * (1 - ratio * 0.2))
        b = int(235 * (1 - ratio * 0.1))
        color = (r, g, b, 255)
        
        for x in range(width):
            img.putpixel((x, y), color)
    
    return img


def crop_center_img(img: Image.Image, width: int, height: int) -> Image.Image:
    """裁剪图片到指定尺寸（居中裁剪）"""
    # 计算原始图片的宽高
    orig_width, orig_height = img.size
    
    # 计算缩放比例
    scale_w = width / orig_width
    scale_h = height / orig_height
    scale = max(scale_w, scale_h)  # 使用较大的缩放比例以完全覆盖目标尺寸
    
    # 计算缩放后的尺寸
    new_width = int(orig_width * scale)
    new_height = int(orig_height * scale)
    
    # 缩放图片
    img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
    
    # 计算裁剪位置（居中）
    left = (new_width - width) // 2
    top = (new_height - height) // 2
    right = left + width
    bottom = top + height
    
    # 裁剪图片
    return img.crop((left, top, right, bottom))


def parse_color(color_str: str, alpha: int = 255) -> Tuple[int, int, int, int]:
    """解析颜色字符串为RGBA元组"""
    if ',' in color_str:
        parts = color_str.split(',')
        if len(parts) == 3:
            r, g, b = map(int, parts)
            return (r, g, b, alpha)
        elif len(parts) == 4:
            r, g, b, a = map(int, parts)
            return (r, g, b, a)
    return (255, 255, 255, alpha)


def create_star_gradient_image(width: int, height: int) -> Image.Image:
    """创建星星渐变背景"""
    img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # 创建彩虹渐变效果
    for x in range(width):
        ratio = x / width
        hue = int(ratio * 360)
        
        # HSV to RGB conversion for rainbow effect
        import colorsys
        r, g, b = colorsys.hsv_to_rgb(hue / 360, 1, 1)
        color = (int(r * 255), int(g * 255), int(b * 255), 255)
        
        draw.line([(x, 0), (x, height)], fill=color)
    
    return img


def draw_star_with_gradient(draw: ImageDraw.Draw, center: Tuple[int, int], 
                           size: int, filled: bool = True, use_gradient: bool = True) -> None:
    """绘制星星"""
    x, y = center
    points = []
    
    # 计算五角星的点
    for i in range(10):
        angle = math.radians(i * 36 - 90)  # -90度让星星顶点朝上
        if i % 2 == 0:  # 外点
            radius = size
        else:  # 内点
            radius = size * 0.4
        
        px = x + radius * math.cos(angle)
        py = y + radius * math.sin(angle)
        points.append((px, py))
    
    if filled:
        if use_gradient:
            # 使用金黄色渐变
            fill_color = (255, 215, 0, 255)  # 金色
        else:
            fill_color = (255, 255, 255, 255)  # 白色
        
        draw.polygon(points, fill=fill_color, outline=(0, 0, 0, 128))
    else:
        # 空心星星
        outline_color = (200, 200, 200, 200)
        draw.polygon(points, fill=(0, 0, 0, 0), outline=outline_color, width=2)


def draw_text_with_shadow(draw: ImageDraw.Draw, position: Tuple[int, int], 
                         text: str, font: ImageFont.FreeTypeFont,
                         text_color: Tuple[int, int, int, int],
                         shadow_color: Tuple[int, int, int, int],
                         shadow_offset: Tuple[int, int] = (2, 2)) -> None:
    """绘制带阴影的文字"""
    x, y = position
    shadow_x, shadow_y = shadow_offset
    
    # 绘制阴影
    draw.text((x + shadow_x, y + shadow_y), text, font=font, fill=shadow_color)
    # 绘制主文字
    draw.text((x, y), text, font=font, fill=text_color)


async def draw_fortune_card(user_name: str, fortune_data: Dict[str, Any]) -> bytes:
    """绘制运势卡片"""
    
    # 获取配置
    card_width = jrys_config.get_config('card_width').data
    card_height = jrys_config.get_config('card_height').data
    text_color_str = jrys_config.get_config('text_color').data
    shadow_color_str = jrys_config.get_config('shadow_color').data
    font_path = jrys_config.get_config('font_path').data
    mask_opacity = jrys_config.get_config('mask_opacity').data
    enable_gradient = jrys_config.get_config('enable_gradient_stars').data
    
    # 解析颜色
    text_color = parse_color(text_color_str, 255)
    shadow_color = parse_color(shadow_color_str, 128)
    
    # 加载背景图片
    background_path = fortune_data.get('backgroundImage', '')
    background = None
    
    try:
        if background_path:
            if background_path.startswith(('http://', 'https://')):
                # 网络图片 - 尝试下载
                background = await load_image_from_url(background_path)
            else:
                # 本地图片
                path_obj = Path(background_path)
                if path_obj.exists():
                    background = Image.open(path_obj).convert('RGBA')
        
        # 如果背景图加载失败，使用备用图片
        if background is None:
            fallback_path = Path(__file__).parent / 'data' / 'backgroundFolder' / 'miao.jpg'
            if fallback_path.exists():
                background = Image.open(fallback_path).convert('RGBA')
            else:
                # 最后的备用方案：使用渐变背景
                background = create_gradient_background(card_width, card_height)
    except Exception as e:
        print(f"加载背景图片失败: {e}")
        # 使用备用图片
        fallback_path = Path(__file__).parent / 'data' / 'backgroundFolder' / 'miao.jpg'
        try:
            if fallback_path.exists():
                background = Image.open(fallback_path).convert('RGBA')
            else:
                background = create_gradient_background(card_width, card_height)
        except Exception:
            background = create_gradient_background(card_width, card_height)
    
    # 调整背景图片大小并裁剪
    background = crop_center_img(background, card_width, card_height)
    
    # 创建画布
    img = Image.new('RGBA', (card_width, card_height), (0, 0, 0, 0))
    
    # 粘贴背景
    img.paste(background, (0, 0))
    
    # 计算下面遮罩区域 - 固定为650像素高度
    mask_height = 650
    mask_start_y = card_height - mask_height  # 从底部开始向上650像素
    
    # 创建磨砂玻璃效果遮罩层（只覆盖下面650像素）
    mask = Image.new('RGBA', (card_width, card_height), (0, 0, 0, 0))
    
    # 对下面650像素应用磨砂玻璃效果
    lower_section = background.crop((0, mask_start_y, card_width, card_height))
    # 应用模糊效果
    blurred = lower_section.filter(ImageFilter.GaussianBlur(radius=3))
    
    # 创建半透明遮罩
    lower_mask = Image.new('RGBA', (card_width, mask_height), (0, 0, 0, mask_opacity))
    blurred_with_mask = Image.alpha_composite(blurred, lower_mask)
    
    # 将处理后的下面650像素区域粘贴回原图
    img.paste(blurred_with_mask, (0, mask_start_y))
    
    # 创建绘制对象
    draw = ImageDraw.Draw(img)
    
    # 加载字体
    try:
        if Path(font_path).exists():
            title_font = ImageFont.truetype(font_path, 48)
            name_font = ImageFont.truetype(font_path, 36)
            fortune_font = ImageFont.truetype(font_path, 56)  # 运势专用字体，更大
            content_font = ImageFont.truetype(font_path, 36)  # 正文字体，从28改为36
            small_font = ImageFont.truetype(font_path, 36)    # 小字字体，从24改为32
        else:
            # 使用默认字体
            title_font = ImageFont.load_default()
            name_font = ImageFont.load_default()
            fortune_font = ImageFont.load_default()
            content_font = ImageFont.load_default()
            small_font = ImageFont.load_default()
    except Exception:
        # 字体加载失败，使用默认字体
        title_font = ImageFont.load_default()
        name_font = ImageFont.load_default()
        fortune_font = ImageFont.load_default()
        content_font = ImageFont.load_default()
        small_font = ImageFont.load_default()
    
    # 计算文字区域的起始位置（遮罩区域内）
    text_area_start = mask_start_y + 20  # 遮罩开始位置 + 一些边距
    text_area_width = card_width - 40  # 留出左右边距
    
    # 绘制用户名
    user_text = f"@{user_name}"
    name_bbox = draw.textbbox((0, 0), user_text, font=name_font)
    name_width = name_bbox[2] - name_bbox[0]
    name_x = (card_width - name_width) // 2
    current_y = text_area_start
    draw_text_with_shadow(draw, (name_x, current_y), user_text, name_font, text_color, shadow_color)
    current_y += 50
    
    # 绘制运势总结（放在星级之前）
    fortune_summary = fortune_data.get('fortuneSummary', '运势未知')
    summary_bbox = draw.textbbox((0, 0), fortune_summary, font=fortune_font)
    summary_width = summary_bbox[2] - summary_bbox[0]
    summary_x = (card_width - summary_width) // 2
    draw_text_with_shadow(draw, (summary_x, current_y), fortune_summary, fortune_font, text_color, shadow_color)
    current_y += 110  # 增加间距，避免与星星重叠
    
    # 绘制运势等级（星星，放在运势总结之后）
    lucky_star = fortune_data.get('luckyStar', '★★★☆☆☆☆')
    star_size = 20
    star_spacing = 45
    total_star_width = len(lucky_star) * star_spacing - star_spacing
    start_x = (card_width - total_star_width) // 2
    
    for i, star in enumerate(lucky_star):
        star_x = start_x + i * star_spacing
        if star == '★':
            draw_star_with_gradient(draw, (star_x, current_y), star_size, True, enable_gradient)
        else:
            draw_star_with_gradient(draw, (star_x, current_y), star_size, False, enable_gradient)
    current_y += 80
    
    # 绘制签文
    sign_text = fortune_data.get('signText', '无签文')
    # 自动换行处理签文
    lines = wrap_text(sign_text, content_font, text_area_width)
    for line in lines:
        line_bbox = draw.textbbox((0, 0), line, font=content_font)
        line_width = line_bbox[2] - line_bbox[0]
        line_x = (card_width - line_width) // 2
        draw_text_with_shadow(draw, (line_x, current_y), line, content_font, text_color, shadow_color)
        current_y += 35
    
    current_y += 30  # 增加一些段落间距
    
    # 绘制详细说明
    unsign_text = fortune_data.get('unsignText', '无详细说明')
    detail_lines = wrap_text(unsign_text, small_font, text_area_width)
    for line in detail_lines:
        line_bbox = draw.textbbox((0, 0), line, font=small_font)
        line_width = line_bbox[2] - line_bbox[0]
        line_x = (card_width - line_width) // 2
        draw_text_with_shadow(draw, (line_x, current_y), line, small_font, text_color, shadow_color)
        current_y += 40
    
    # 绘制运势数值（放在底部）
    luck_value = fortune_data.get('luckValue', 50)
    value_text = f"运势指数: {luck_value}"
    value_bbox = draw.textbbox((0, 0), value_text, font=content_font)
    value_width = value_bbox[2] - value_bbox[0]
    value_x = (card_width - value_width) // 2
    value_y = card_height - 50  # 距离底部50像素
    draw_text_with_shadow(draw, (value_x, value_y), value_text, content_font, text_color, shadow_color)
    
    # 转换为字节
    img_byte_arr = BytesIO()
    img.save(img_byte_arr, format='PNG', quality=95)
    img_byte_arr.seek(0)
    
    return img_byte_arr.getvalue()


def wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list:
    """文字自动换行"""
    lines = []
    current_line = ""
    
    for char in text:
        test_line = current_line + char
        bbox = ImageDraw.Draw(Image.new('RGB', (1, 1))).textbbox((0, 0), test_line, font=font)
        width = bbox[2] - bbox[0]
        
        if width <= max_width:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
                current_line = char
            else:
                lines.append(char)
                current_line = ""
    
    if current_line:
        lines.append(current_line)
    
    return lines