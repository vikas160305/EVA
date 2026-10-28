import math
from PIL import Image, ImageDraw, ImageFont

W, H = 1920, 1080

C_BG          = (4, 10, 16)
C_PANEL       = (8, 20, 30)
C_PANEL2      = (12, 28, 42)
C_BORDER      = (22, 60, 85)
C_BORDER_HI   = (0, 190, 240)
C_CYAN        = (0, 212, 255)
C_CYAN_GHOST  = (0, 40, 60)
C_GREEN       = (0, 255, 136)
C_AMBER       = (255, 190, 0)
C_TEXT_WHITE  = (240, 250, 255)
C_TEXT_CYAN   = (140, 240, 255)
C_TEXT_MED    = (90, 180, 205)
C_TEXT_DIM    = (50, 115, 135)

FONT_TITLE = ImageFont.truetype(r"C:\Windows\Fonts\segoeuib.ttf", 26)
FONT_SUBTITLE = ImageFont.truetype(r"C:\Windows\Fonts\segoeuib.ttf", 20)
FONT_BODY = ImageFont.truetype(r"C:\Windows\Fonts\segoeui.ttf", 18)
FONT_BODY_B = ImageFont.truetype(r"C:\Windows\Fonts\segoeuib.ttf", 18)
FONT_SMALL = ImageFont.truetype(r"C:\Windows\Fonts\segoeui.ttf", 14)
FONT_CODE = ImageFont.truetype(r"C:\Windows\Fonts\consola.ttf", 16)
FONT_CODE_B = ImageFont.truetype(r"C:\Windows\Fonts\consolab.ttf", 18)
FONT_CODE_BIG = ImageFont.truetype(r"C:\Windows\Fonts\consolab.ttf", 24)
FONT_HUGE = ImageFont.truetype(r"C:\Windows\Fonts\segoeuib.ttf", 48)
FONT_HERO = ImageFont.truetype(r"C:\Windows\Fonts\segoeuib.ttf", 72)

def draw_intro_frame(t: float, dur: float, p: float, subtitle: str) -> Image.Image:
    img = Image.new('RGB', (W, H), C_BG)
    draw = ImageDraw.Draw(img)
    
    # Scanning laser grid
    for gx in range(0, W, 80):
        draw.line([gx, 0, gx, H], fill=(8, 18, 28), width=1)
    for gy in range(0, H, 80):
        draw.line([0, gy, W, gy], fill=(8, 18, 28), width=1)
    
    scan_y = int((t * 240) % H)
    draw.line([0, scan_y, W, scan_y], fill=C_CYAN_GHOST, width=2)
    
    # Expanding concentric holographic circles
    cx, cy = W // 2, H // 2 - 60
    for r in [180, 260, 340, 420]:
        radius = r + int(math.sin(t * 3 + r * 0.01) * 8)
        draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], outline=(0, 60, 90), width=1)
    
    # Center Hero Box
    draw.rounded_rectangle([cx - 480, cy - 180, cx + 480, cy + 180], radius=16, fill=(8, 22, 34), outline=C_CYAN, width=3)
    
    # Holographic Badge
    draw.rounded_rectangle([cx - 100, cy - 150, cx + 100, cy - 110], radius=6, fill=C_CYAN_GHOST, outline=C_CYAN, width=2)
    draw.text((cx - 75, cy - 144), "MARK L / EVA", font=FONT_BODY_B, fill=C_CYAN)
    
    # Title
    draw.text((cx - 130, cy - 90), "E V A", font=FONT_HERO, fill=C_TEXT_WHITE)
    draw.text((cx - 360, cy + 10), "ADVANCED WINDOWS DESKTOP AI COPILOT", font=FONT_TITLE, fill=C_TEXT_CYAN)
    draw.text((cx - 400, cy + 60), "Official Live System Demonstration & Deep OS Orchestration Walkthrough", font=FONT_BODY, fill=C_TEXT_MED)
    
    # Tech Stack Badges
    badges = [
        "Windows 10 / 11 Native",
        "Google Gemini Live 2.5",
        "PyQt6 Cyberpunk HUD",
        "Zero-Permission Winget",
        "Full Duplex Audio Engine"
    ]
    bx = cx - 440
    for b in badges:
        draw.rounded_rectangle([bx, cy + 115, bx + 165, cy + 155], radius=6, fill=C_PANEL, outline=C_BORDER, width=1)
        draw.text((bx + 10, cy + 125), b, font=FONT_SMALL, fill=C_GREEN)
        bx += 178
    
    # Subtitle bar
    draw.rounded_rectangle([80, 950, W - 80, 1045], radius=10, fill=C_PANEL, outline=C_BORDER, width=2)
    draw.rounded_rectangle([100, 970, 230, 1025], radius=6, fill=(0, 45, 70), outline=C_CYAN, width=1)
    draw.text((115, 986), "NARRATION", font=FONT_BODY_B, fill=C_CYAN)
    draw.text((255, 986), subtitle, font=FONT_BODY_B, fill=C_TEXT_WHITE)
    
    return img

def draw_outro_frame(t: float, dur: float, p: float, subtitle: str) -> Image.Image:
    img = Image.new('RGB', (W, H), C_BG)
    draw = ImageDraw.Draw(img)
    
    # Grid
    for gx in range(0, W, 80):
        draw.line([gx, 0, gx, H], fill=(8, 18, 28), width=1)
    for gy in range(0, H, 80):
        draw.line([0, gy, W, gy], fill=(8, 18, 28), width=1)
    
    # Outro Container
    cx, cy = W // 2, H // 2 - 50
    draw.rounded_rectangle([cx - 560, cy - 240, cx + 560, cy + 240], radius=16, fill=(8, 22, 34), outline=C_GREEN, width=3)
    
    draw.text((cx - 260, cy - 210), "EVA LIVE DEMONSTRATION COMPLETE", font=FONT_HUGE, fill=C_TEXT_WHITE)
    draw.text((cx - 320, cy - 145), "Autonomous Desktop Intelligence for Windows 10 & 11", font=FONT_TITLE, fill=C_CYAN)
    draw.line([cx - 500, cy - 100, cx + 500, cy - 100], fill=C_BORDER, width=1)
    
    # Highlights Grid
    hl = [
        ("Response Latency", "< 10 ms (Instant Dispatch)", C_GREEN),
        ("Voice Engine", "Gemini Live Native Audio 24kHz", C_CYAN),
        ("Silent Installer", "0.00s Catalog / 0.02s Registry", C_GREEN),
        ("Content Creator", "Pure Python-docx/pptx In-Memory", C_TEXT_WHITE),
        ("Universal Converter", "Lossless Vector PDF & Office", C_TEXT_WHITE),
        ("Test Suite Stability", "114 / 114 Passed (100% Zero Regression)", C_GREEN)
    ]
    
    hy = cy - 70
    for i, (k, v, col) in enumerate(hl):
        col_x = cx - 480 if i % 2 == 0 else cx + 40
        draw.text((col_x, hy), f"• {k}:", font=FONT_BODY_B, fill=C_TEXT_MED)
        draw.text((col_x + 190, hy), v, font=FONT_BODY_B, fill=col)
        if i % 2 == 1:
            hy += 45
    
    draw.line([cx - 500, cy + 85, cx + 500, cy + 85], fill=C_BORDER, width=1)
    draw.text((cx - 260, cy + 110), "EVA / MARK L  |  PROJECT STATUS: DEPLOYMENT READY", font=FONT_BODY_B, fill=C_GREEN)
    draw.text((cx - 160, cy + 145), "All 114 Unit & Integration Tests Passing", font=FONT_SMALL, fill=C_TEXT_DIM)
    
    # Subtitle bar
    draw.rounded_rectangle([80, 950, W - 80, 1045], radius=10, fill=C_PANEL, outline=C_BORDER, width=2)
    draw.rounded_rectangle([100, 970, 230, 1025], radius=6, fill=(0, 45, 70), outline=C_CYAN, width=1)
    draw.text((115, 986), "NARRATION", font=FONT_BODY_B, fill=C_CYAN)
    draw.text((255, 986), subtitle, font=FONT_BODY_B, fill=C_TEXT_WHITE)
    
    return img
