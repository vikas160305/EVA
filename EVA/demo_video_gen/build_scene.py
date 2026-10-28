import os
import sys
import math
import time
import subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont

# Canvas dimensions
W, H = 1920, 1080
FPS = 24

# Colors
C_BG          = (4, 10, 16)
C_PANEL       = (8, 20, 30)
C_PANEL2      = (12, 28, 42)
C_BORDER      = (22, 60, 85)
C_BORDER_HI   = (0, 190, 240)
C_CYAN        = (0, 212, 255)
C_CYAN_DIM    = (0, 120, 160)
C_CYAN_GHOST  = (0, 40, 60)
C_GREEN       = (0, 255, 136)
C_GREEN_DIM   = (0, 160, 85)
C_AMBER       = (255, 190, 0)
C_RED         = (255, 60, 80)
C_TEXT_WHITE  = (240, 250, 255)
C_TEXT_CYAN   = (140, 240, 255)
C_TEXT_MED    = (90, 180, 205)
C_TEXT_DIM    = (50, 115, 135)

# Fonts
FONT_TITLE = ImageFont.truetype(r"C:\Windows\Fonts\segoeuib.ttf", 26)
FONT_SUBTITLE = ImageFont.truetype(r"C:\Windows\Fonts\segoeuib.ttf", 20)
FONT_BODY = ImageFont.truetype(r"C:\Windows\Fonts\segoeui.ttf", 18)
FONT_BODY_B = ImageFont.truetype(r"C:\Windows\Fonts\segoeuib.ttf", 18)
FONT_SMALL = ImageFont.truetype(r"C:\Windows\Fonts\segoeui.ttf", 14)
FONT_CODE = ImageFont.truetype(r"C:\Windows\Fonts\consola.ttf", 16)
FONT_CODE_B = ImageFont.truetype(r"C:\Windows\Fonts\consolab.ttf", 17)
FONT_CODE_BIG = ImageFont.truetype(r"C:\Windows\Fonts\consolab.ttf", 22)
FONT_HUGE = ImageFont.truetype(r"C:\Windows\Fonts\segoeuib.ttf", 36)

CHAPTER_TITLES = [
    "01. Architecture & Core",
    "02. Cyberpunk HUD & Audio",
    "03. Windows OS Control",
    "04. Silent App Installer",
    "05. Media Downloader",
    "06. Doc & PPT Creator",
    "07. Universal Converter",
    "08. WhatsApp Automation",
    "09. Web & Mobile Dashboard",
    "10. Performance Milestones"
]

def draw_header(draw: ImageDraw.ImageDraw, t: float, ch_idx: int, elapsed_total: float):
    # Top bar container
    draw.rectangle([0, 0, W, 82], fill=C_PANEL)
    draw.line([0, 82, W, 82], fill=C_BORDER, width=2)
    draw.line([0, 83, W, 83], fill=C_CYAN_GHOST, width=1)
    
    # EVA Logo & Badge
    draw.rounded_rectangle([35, 18, 120, 62], radius=6, fill=C_CYAN_GHOST, outline=C_CYAN, width=2)
    draw.text((48, 26), "EVA", font=FONT_TITLE, fill=C_CYAN)
    draw.text((135, 24), "MARK L  |  WINDOWS DESKTOP AI COPILOT", font=FONT_SUBTITLE, fill=C_TEXT_WHITE)
    draw.text((135, 48), "Autonomous Operating System Orchestration Engine", font=FONT_SMALL, fill=C_TEXT_MED)
    
    # Live recording indicator
    blink = int(t * 2) % 2 == 0
    rec_col = C_RED if blink else (160, 30, 40)
    draw.ellipse([640, 32, 654, 46], fill=rec_col)
    draw.text((664, 30), "LIVE DEMO", font=FONT_BODY_B, fill=C_TEXT_WHITE)
    
    # Timer
    mins = int(elapsed_total // 60)
    secs = int(elapsed_total % 60)
    draw.text((770, 30), f"REC  [ {mins:02d}:{secs:02d} / 08:45 ]", font=FONT_CODE_B, fill=C_CYAN)
    
    # Waveform visualizer (20 animated bars)
    wx = 980
    for i in range(22):
        h_bar = int(abs(math.sin(t * 9 + i * 0.45) * math.cos(t * 4 + i * 0.2)) * 32) + 6
        y_bar = 50 - h_bar // 2
        bar_col = C_CYAN if i % 2 == 0 else C_GREEN
        draw.line([wx + i * 7, y_bar, wx + i * 7, y_bar + h_bar], fill=bar_col, width=3)
    
    # Telemetry Badges
    chips = [
        ("CPU", f"{int(14 + 5 * math.sin(t * 0.7))}%"),
        ("RAM", "5.8 / 16 GB"),
        ("MODEL", "Gemini Live 2.5"),
        ("LATENCY", "8.2ms")
    ]
    cx = 1200
    for label, val in chips:
        draw.rounded_rectangle([cx, 20, cx + 160, 62], radius=5, fill=(10, 24, 36), outline=C_BORDER, width=1)
        draw.text((cx + 12, 24), label, font=FONT_SMALL, fill=C_TEXT_DIM)
        draw.text((cx + 12, 40), val, font=FONT_BODY_B, fill=C_TEXT_CYAN if label != "LATENCY" else C_GREEN)
        cx += 172

def draw_sidebar(draw: ImageDraw.ImageDraw, active_idx: int):
    # Left drawer container
    draw.rounded_rectangle([35, 96, 330, 936], radius=10, fill=C_PANEL, outline=C_BORDER, width=2)
    
    draw.text((55, 115), "SYSTEM MODULES", font=FONT_BODY_B, fill=C_CYAN)
    draw.line([55, 142, 310, 142], fill=C_BORDER, width=1)
    
    sy = 155
    for idx, title in enumerate(CHAPTER_TITLES):
        is_active = (idx == active_idx)
        if is_active:
            draw.rounded_rectangle([48, sy - 4, 318, sy + 36], radius=6, fill=(0, 60, 95), outline=C_CYAN, width=2)
            draw.ellipse([58, sy + 10, 68, sy + 20], fill=C_GREEN)
            draw.text((76, sy + 4), title, font=FONT_BODY_B, fill=C_TEXT_WHITE)
        else:
            draw.text((76, sy + 4), title, font=FONT_BODY, fill=C_TEXT_DIM)
        sy += 45
    
    # Bottom assistant status box inside sidebar
    draw.rounded_rectangle([48, 650, 318, 920], radius=8, fill=C_PANEL2, outline=C_BORDER, width=1)
    draw.text((60, 665), "AGENT TELEMETRY", font=FONT_SUBTITLE, fill=C_CYAN)
    
    items = [
        ("Event Loop", "Running (60 Hz)", C_GREEN),
        ("Voice Pipe", "Full Duplex", C_CYAN),
        ("Intent Router", "Active (<10ms)", C_GREEN),
        ("Winget Engine", "Ready (Headless)", C_TEXT_CYAN),
        ("Media Downloader", "Idle (Standby)", C_TEXT_MED),
        ("Content Creator", "In-Process Ready", C_TEXT_MED),
        ("File Converter", "Local Native", C_GREEN),
        ("Safety Mode", "Strict Enforced", C_GREEN)
    ]
    iy = 705
    for k, v, c in items:
        draw.text((60, iy), k, font=FONT_SMALL, fill=C_TEXT_DIM)
        draw.text((180, iy), v, font=FONT_SMALL, fill=c)
        iy += 26

def draw_action_bar(draw: ImageDraw.ImageDraw, command: str, t: float, p: float):
    # Action prompt container
    draw.rounded_rectangle([350, 96, 1885, 195], radius=10, fill=C_PANEL, outline=C_BORDER, width=2)
    
    # Voice Input Pill
    draw.rounded_rectangle([368, 112, 490, 142], radius=5, fill=(0, 50, 80), outline=C_CYAN, width=1)
    draw.text((380, 118), "VOICE INPUT", font=FONT_BODY_B, fill=C_CYAN)
    
    # Animated typing text
    type_len = int(min(len(command), t * 30))
    typed_text = command[:type_len]
    cursor = "_" if (int(t * 2.5) % 2 == 0) else ""
    draw.text((505, 117), f'"{typed_text}{cursor}"', font=FONT_CODE_BIG, fill=C_TEXT_WHITE)
    
    # Sub-status row
    draw.text((370, 158), "EVA RESPONSE >", font=FONT_BODY_B, fill=C_GREEN)
    status_msg = "Acknowledging query... Executing system tool asynchronously in background." if p < 0.85 else "Tool execution completed successfully with exit code 0."
    draw.text((520, 159), status_msg, font=FONT_BODY, fill=C_TEXT_CYAN)
    
    # Status chip
    st_col = C_AMBER if p < 0.85 else C_GREEN
    st_txt = "EXECUTING" if p < 0.85 else "COMPLETED"
    draw.rounded_rectangle([1720, 120, 1860, 168], radius=6, fill=C_PANEL2, outline=st_col, width=2)
    draw.text((1740, 134), st_txt, font=FONT_BODY_B, fill=st_col)

def draw_subtitles(draw: ImageDraw.ImageDraw, subtitle: str):
    # Subtitle bar
    draw.rounded_rectangle([35, 950, 1885, 1050], radius=10, fill=C_PANEL, outline=C_BORDER, width=2)
    draw.rounded_rectangle([52, 970, 180, 1030], radius=6, fill=(0, 45, 70), outline=C_CYAN, width=1)
    draw.text((68, 988), "NARRATION", font=FONT_BODY_B, fill=C_CYAN)
    
    # Word wrap subtitle
    words = subtitle.split(" ")
    lines = []
    curr = ""
    for w in words:
        if len(curr + " " + w) > 130:
            lines.append(curr)
            curr = w
        else:
            curr = (curr + " " + w).strip()
    if curr:
        lines.append(curr)
    
    sy = 970 if len(lines) > 1 else 985
    for line in lines[:2]:
        draw.text((200, sy), line, font=FONT_BODY_B, fill=C_TEXT_WHITE)
        sy += 30

def get_subtitle_segment(text: str, p: float) -> str:
    # Break chapter text into sentences/clauses based on progress p (0.0 to 1.0)
    sentences = [s.strip() for s in text.replace(". ", ".\n").replace("! ", "!\n").split("\n") if s.strip()]
    if not sentences:
        return text
    idx = min(int(p * len(sentences)), len(sentences) - 1)
    return sentences[idx]
