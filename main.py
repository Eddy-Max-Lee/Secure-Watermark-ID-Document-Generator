import argparse, hashlib, os, sys, datetime
from typing import List, Tuple
from PIL import Image, ImageDraw, ImageFont
import pikepdf
import pymupdf as fitz  # 使用 pymupdf 替代 fitz

# ========== 預設值 ==========
DEFAULT_INPUT = "原始文件的圖片或PDF檔"
DEFAULT_OUTPUT = "output_with_watermark.pdf"
DEFAULT_WHO = "XXX股份有限公司"
DEFAULT_PURPOSE = "僅供Hero 零元挑戰計畫申請退費使用"
DEFAULT_NAME = "你的名字"
DEFAULT_DATE = datetime.date.today().isoformat()  # 預設為今天
DEFAULT_FONT_PATH = "C:\\Windows\\Fonts\\mingliu.ttc"  # 確保提供支持中文的字型檔案路徑
DEFAULT_FONT_SIZE_RATIO = 0.015 # 調整浮水印大小
# DEFAULT_FONT_PATH = "C:"

# ========== 基本工具 ==========
def get_font(px: int, font_path: str | None):
    if font_path and os.path.exists(font_path):
        try:
            return ImageFont.truetype(font_path, px)
        except Exception:
            pass
    return ImageFont.load_default()

def rasterize_pdf_to_images(pdf_path: str, dpi: int = 300) -> List[Image.Image]:
    imgs = []
    with fitz.open(pdf_path) as doc:
        zoom = dpi / 72.0
        matrix = fitz.Matrix(zoom, zoom)
        for page in doc:
            pix = page.get_pixmap(matrix=matrix, alpha=False)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            imgs.append(img)
    return imgs

def ensure_image_list(input_path: str, dpi: int = 300) -> List[Image.Image]:
    ext = os.path.splitext(input_path.lower())[1]
    if ext == ".pdf":
        return rasterize_pdf_to_images(input_path, dpi=dpi)
    im = Image.open(input_path)
    frames = []
    try:
        i = 0
        while True:
            im.seek(i)
            frames.append(im.convert("RGB"))
            i += 1
    except EOFError:
        pass
    return frames or [im.convert("RGB")]

# ========== 覆寫與水印 ==========
def draw_masks(img: Image.Image, boxes: List[Tuple[int,int,int,int]]):
    canvas = img.copy()
    draw = ImageDraw.Draw(canvas)
    for (x1, y1, x2, y2) in boxes:
        draw.rectangle([x1, y1, x2, y2], fill=(0, 0, 0))
    return canvas

def draw_repeated_diagonal_text(
    base: Image.Image, text: str, opacity: int = 80, angle: float = 30.0,
    density: float = 0.22, font_path: str | None = None, font_size_ratio: float = DEFAULT_FONT_SIZE_RATIO

):
    W, H = base.size
    font = get_font(int(min(W, H) * font_size_ratio), font_path)

    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)

    # 計算文字貼片的尺寸
    bbox = d.textbbox((0, 0), text, font=font, stroke_width=2)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    pad = int(min(W, H) * 0.02)
    tile = Image.new("RGBA", (tw + pad * 2, th + pad * 2), (0, 0, 0, 0))
    td = ImageDraw.Draw(tile)
    td.text(
        (pad, pad), text, font=font,
        fill=(255, 255, 255, opacity),
        stroke_width=2, stroke_fill=(0, 0, 0, int(opacity * 0.9))
    )
    tile = tile.rotate(angle, expand=True)

    # 根據 density 計算間距
    step = int(min(W, H) * density)
    if step < max(tile.size):  # 確保水印間距不會太大，超過圖片範圍
        step = max(tile.size) + 2  # 這裡調整步長，使水印距離更合理

    # 確保浮水印能平鋪滿整個圖片
    for y in range(-tile.size[1], H + tile.size[1], step):
        for x in range(-tile.size[0], W + tile.size[0], step):
            layer.alpha_composite(tile, (x, y))

    # 低透明度斜線網紋，增加修補難度
    hatch = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    hd = ImageDraw.Draw(hatch)
    gap = int(min(W, H) * 0.06)
    for i in range(0, W + H, gap):
        hd.line([(i, 0), (0, i)], fill=(0, 0, 0, 18), width=1)
        hd.line([(W, i), (i, H)], fill=(0, 0, 0, 18), width=1)

    merged = Image.alpha_composite(base.convert("RGBA"), layer)
    merged = Image.alpha_composite(merged, hatch)
    return merged.convert("RGB")

def add_footer(img: Image.Image, footer_text: str, font_path: str | None = None):
    W, H = img.size
    canvas = img.convert("RGBA")
    d = ImageDraw.Draw(canvas)
    font = get_font(int(min(W, H) * 0.035), font_path)

    bbox = d.textbbox((0, 0), footer_text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    margin = int(min(W, H) * 0.02)
    x = (W - tw) // 2
    y = H - th - margin

    # 半透明底條
    d.rectangle([(0, y - margin // 2), (W, y + th + margin // 2)],
                fill=(255, 255, 255, 200))
    d.text((x, y), footer_text, font=font, fill=(0, 0, 0, 255))
    return canvas.convert("RGB")

# ========== 輸出 ==========
def save_images_to_flat_pdf(images: List[Image.Image], out_pdf: str,
                            user_pw: str | None = None, owner_pw: str | None = None):
    tmp_pdf = out_pdf + ".__tmp.pdf"
    images[0].save(tmp_pdf, "PDF", resolution=300.0, save_all=True, append_images=images[1:])
    if user_pw or owner_pw:
        with pikepdf.open(tmp_pdf) as pdf:
            encrypt = pikepdf.Encryption(
                user=user_pw or "",
                owner=owner_pw or "",
                allow={pikepdf.Permissions.print_lowres}
            )
            pdf.save(out_pdf, encryption=encrypt)
        os.remove(tmp_pdf)
    else:
        os.replace(tmp_pdf, out_pdf)

# ========== 主流程 ==========
def process_pages(pages: List[Image.Image], wm_text: str, footer: str,
                  masks: List[Tuple[int,int,int,int]], font_path: str | None):
    out = []
    for im in pages:
        im2 = draw_masks(im, masks) if masks else im
        im3 = draw_repeated_diagonal_text(im2, wm_text, opacity=80, angle=30.0,
                                          density=0.1, font_path=font_path)
        # im4 = add_footer(im3, footer, font_path=font_path)
        out.append(im3)
    return out

def main():
    ap = argparse.ArgumentParser(description="為身分證影本燒錄難移除浮水印（無 QR 版，扁平化 PDF）")
    ap.add_argument("--input", default=DEFAULT_INPUT, help="輸入檔案，預設為 'default_input.pdf'")
    ap.add_argument("--output", default=DEFAULT_OUTPUT, help="輸出檔案，預設為 'output_with_watermark.pdf'")
    ap.add_argument("--who", default=DEFAULT_WHO, help="用途對象，預設為 'ABC銀行'")
    ap.add_argument("--purpose", default=DEFAULT_PURPOSE, help="用途，預設為 '僅供開戶使用'")
    ap.add_argument("--name", default=DEFAULT_NAME, help="姓名，預設為 '王小明'")
    ap.add_argument("--date", default=DEFAULT_DATE, help="日期，預設為今天")
    ap.add_argument("--mask", action="append", default=[], help="遮掩框 x1,y1,x2,y2，可多次")
    ap.add_argument("--userpw", default=None, help="PDF 開啟密碼（可選）")
    ap.add_argument("--ownerpw", default=None, help="PDF 擁有者密碼（可選）")
    ap.add_argument("--font", default=DEFAULT_FONT_PATH, help="字型檔路徑（可選，ttf/otf）")
    args = ap.parse_args()

    # 追溯碼（不做 QR，但仍存於文字水印與頁腳）
    token_src = f"{args.who}|{args.purpose}|{args.name}|{args.date}"
    token = hashlib.sha256(token_src.encode("utf-8")).hexdigest()[:16]

    wm_text = f"{args.purpose}｜僅供 {args.who} 使用｜{args.name}｜{args.date}｜ID:{token}"
    footer = f"本影本已用途綁定並含追溯碼（Token: {token}）。非供「{args.who}」之「{args.purpose}」不得使用。"

    masks = []
    for m in args.mask:
        try:
            x1,y1,x2,y2 = [int(v.strip()) for v in m.split(",")]
            masks.append((x1,y1,x2,y2))
        except Exception:
            print(f"[WARN] 遮掩框格式錯誤：{m}，應為 x1,y1,x2,y2", file=sys.stderr)

    pages = ensure_image_list(args.input, dpi=300)
    done = process_pages(pages, wm_text, footer, masks, font_path=args.font)
    save_images_to_flat_pdf(done, args.output, user_pw=args.userpw, owner_pw=args.ownerpw)
    print(f"[OK] 已輸出：{args.output}")

if __name__ == "__main__":
    main()
