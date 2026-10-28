import math
from PIL import Image, ImageDraw, ImageFont

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

FONT_TITLE = ImageFont.truetype(r"C:\Windows\Fonts\segoeuib.ttf", 26)
FONT_SUBTITLE = ImageFont.truetype(r"C:\Windows\Fonts\segoeuib.ttf", 20)
FONT_BODY = ImageFont.truetype(r"C:\Windows\Fonts\segoeui.ttf", 18)
FONT_BODY_B = ImageFont.truetype(r"C:\Windows\Fonts\segoeuib.ttf", 18)
FONT_SMALL = ImageFont.truetype(r"C:\Windows\Fonts\segoeui.ttf", 14)
FONT_CODE = ImageFont.truetype(r"C:\Windows\Fonts\consola.ttf", 16)
FONT_CODE_B = ImageFont.truetype(r"C:\Windows\Fonts\consolab.ttf", 17)
FONT_CODE_BIG = ImageFont.truetype(r"C:\Windows\Fonts\consolab.ttf", 22)
FONT_HUGE = ImageFont.truetype(r"C:\Windows\Fonts\segoeuib.ttf", 36)

# Main stage bounds: x: 350 to 1885, y: 210 to 936
SX1, SY1, SX2, SY2 = 350, 210, 1885, 936

def draw_stage_container(draw: ImageDraw.ImageDraw, title: str, subtitle: str):
    draw.rounded_rectangle([SX1, SY1, SX2, SY2], radius=10, fill=C_PANEL, outline=C_BORDER, width=2)
    # Stage header
    draw.text((SX1 + 30, SY1 + 20), title, font=FONT_TITLE, fill=C_CYAN)
    draw.text((SX1 + 30, SY1 + 54), subtitle, font=FONT_SMALL, fill=C_TEXT_MED)
    draw.line([SX1 + 30, SY1 + 80, SX2 - 30, SY1 + 80], fill=C_BORDER, width=1)

# Chapter 1: Architecture & Core
def draw_ch01(draw: ImageDraw.ImageDraw, t: float, dur: float, p: float):
    draw_stage_container(draw, "SYSTEM ARCHITECTURE & EVENT ENGINE", "End-to-End Multimodal Desktop Orchestration Pipeline")
    
    # Architecture Pipeline Nodes
    nodes = [
        ("AUDIO STREAM", "16kHz PCM Ingest\nsounddevice", 400, 320, 200, 120),
        ("GEMINI LIVE", "WebSocket Duplex\n2.5 Flash Native", 680, 320, 220, 120),
        ("INTENT ROUTER", "Sub-10ms Dispatch\nTool Manifest", 980, 320, 220, 120),
        ("EXECUTION ENGINE", "Actions & Native APIs\nAsync Executor", 1280, 320, 240, 120),
        ("WINDOWS SYSTEM", "OS & Process Level\nWin32, WMI, Winget", 1600, 320, 220, 120)
    ]
    
    # Draw arrows and connection lines
    for i in range(len(nodes) - 1):
        x1 = nodes[i][2] + nodes[i][4]
        y1 = nodes[i][3] + nodes[i][5] // 2
        x2 = nodes[i+1][2]
        y2 = nodes[i+1][3] + nodes[i+1][5] // 2
        draw.line([x1, y1, x2, y2], fill=C_BORDER_HI, width=3)
        # Pulsing packet
        packet_x = x1 + (x2 - x1) * ((t * 1.5 + i * 0.25) % 1.0)
        draw.ellipse([packet_x - 6, y1 - 6, packet_x + 6, y1 + 6], fill=C_GREEN)
    
    for title, desc, nx, ny, nw, nh in nodes:
        draw.rounded_rectangle([nx, ny, nx + nw, ny + nh], radius=8, fill=C_PANEL2, outline=C_CYAN, width=2)
        draw.text((nx + 16, ny + 16), title, font=FONT_BODY_B, fill=C_TEXT_WHITE)
        lines = desc.split("\n")
        draw.text((nx + 16, ny + 50), lines[0], font=FONT_SMALL, fill=C_TEXT_CYAN)
        if len(lines) > 1:
            draw.text((nx + 16, ny + 72), lines[1], font=FONT_SMALL, fill=C_TEXT_MED)
    
    # Lower Section: Diagnostic & Health Checklist
    draw.rounded_rectangle([400, 500, 1100, 890], radius=8, fill=C_PANEL2, outline=C_BORDER, width=1)
    draw.text((430, 525), "SYSTEM INITIALIZATION & HEALTH VERIFICATION", font=FONT_SUBTITLE, fill=C_CYAN)
    
    checks = [
        ("Windows 10/11 Core Audio API (WASAPI)", "ONLINE (Buffer 256 samples)", C_GREEN),
        ("Gemini Live Bidirectional WebSocket", "ESTABLISHED (TLS 1.3)", C_GREEN),
        ("Vector Memory Store (Local Embeddings)", "LOADED (1,420 Items, Recall 0.02s)", C_GREEN),
        ("Safety Process Boundary Policy", "ENFORCED (Zero Credential Leakage)", C_GREEN),
        ("Process Subprocess Window Hide Guard", "ACTIVE (Clean Desktop)", C_GREEN),
        ("Automated Regression Tests Passed", "114 of 114 Passed (100%)", C_GREEN)
    ]
    cy = 575
    for item, status, col in checks:
        draw.text((430, cy), "[✓]", font=FONT_CODE_B, fill=col)
        draw.text((470, cy), item, font=FONT_BODY, fill=C_TEXT_WHITE)
        draw.text((850, cy), status, font=FONT_SMALL, fill=col)
        cy += 48
    
    # Right Box: Vector Memory & Latency Stats
    draw.rounded_rectangle([1140, 500, 1820, 890], radius=8, fill=C_PANEL2, outline=C_BORDER, width=1)
    draw.text((1170, 525), "CORE CAPABILITIES OVERVIEW", font=FONT_SUBTITLE, fill=C_CYAN)
    
    specs = [
        ("Architecture Paradigm", "Asynchronous Event Loop (PyQt6 + asyncio)"),
        ("Voice Processing Engine", "Gemini Live Native Audio 24kHz"),
        ("Application Installer", "Zero-Permission Headless Winget (0.00s Lookup)"),
        ("Downloader Engine", "Multi-Engine DuckDuckGo/Bing with Ad-Filter"),
        ("Document Engine", "In-Memory python-docx / pptx / reportlab"),
        ("Desktop Control", "Native Win32, PyAutoGUI, PyGetWindow"),
        ("Remote Access", "FastAPI WebSocket Dashboard + Mobile QR")
    ]
    sy = 575
    for k, v in specs:
        draw.text((1170, sy), k, font=FONT_BODY_B, fill=C_TEXT_CYAN)
        draw.text((1170, sy + 24), v, font=FONT_SMALL, fill=C_TEXT_WHITE)
        sy += 44

# Chapter 2: The Cybernetic HUD & Audio Engine
def draw_ch02(draw: ImageDraw.ImageDraw, t: float, dur: float, p: float):
    draw_stage_container(draw, "CYBERNETIC HUD & LOW-LATENCY AUDIO ENGINE", "Dual-Layer Echo Cancellation, Jitter Buffer & Live Spectrogram")
    
    # Large Animated Frequency Spectrogram
    draw.rounded_rectangle([400, 310, 1300, 640], radius=8, fill=C_PANEL2, outline=C_BORDER, width=1)
    draw.text((425, 330), "REAL-TIME MULTI-BAND SPECTRUM ANALYZER", font=FONT_SUBTITLE, fill=C_CYAN)
    
    # Draw 48 bars
    bx = 430
    for i in range(48):
        freq_energy = abs(math.sin(t * 8 + i * 0.35) * math.cos(t * 3.5 + i * 0.15))
        bar_h = int(freq_energy * 200) + 10
        by = 600 - bar_h
        col = C_CYAN if i < 28 else (C_GREEN if i < 40 else C_AMBER)
        draw.rectangle([bx, by, bx + 14, 600], fill=col)
        bx += 18
    draw.line([420, 601, 1280, 601], fill=C_BORDER, width=1)
    draw.text((430, 612), "20 Hz               250 Hz               1 kHz                4 kHz               16 kHz", font=FONT_SMALL, fill=C_TEXT_DIM)
    
    # Audio Engineering Metrics Cards (Right Side)
    draw.rounded_rectangle([1330, 310, 1820, 640], radius=8, fill=C_PANEL2, outline=C_BORDER, width=1)
    draw.text((1355, 330), "AUDIO PIPELINE TELEMETRY", font=FONT_SUBTITLE, fill=C_CYAN)
    
    metrics = [
        ("Echo Suppression", "-42 dB", "Dual-layer spectral subtraction"),
        ("Jitter Buffer", "35 ms", "Zero dropped audio frames"),
        ("Streaming Latency", "118 ms", "Microphone to Gemini cloud"),
        ("Intent Resolution", "8.4 ms", "Local tokenizer classification"),
        ("Audio Sampling", "24 kHz / 16-bit", "High-fidelity native PCM")
    ]
    my = 375
    for label, val, sub in metrics:
        draw.text((1355, my), label, font=FONT_SMALL, fill=C_TEXT_DIM)
        draw.text((1600, my), val, font=FONT_BODY_B, fill=C_GREEN)
        draw.text((1355, my + 20), sub, font=FONT_SMALL, fill=C_TEXT_MED)
        draw.line([1355, my + 44, 1800, my + 44], fill=C_BORDER, width=1)
        my += 52
    
    # Bottom: Live Token Transcription Feed
    draw.rounded_rectangle([400, 660, 1820, 890], radius=8, fill=C_PANEL2, outline=C_BORDER, width=1)
    draw.text((425, 680), "LIVE SPEECH TRANSCRIPTION & INTENT PARSING", font=FONT_SUBTITLE, fill=C_CYAN)
    
    sim_tokens = [
        "EVA", "switch", "to", "live", "audio", "monitoring", "mode", "and", "verify", "stream", "health"
    ]
    num_tokens = int(min(len(sim_tokens), t * 3.5))
    shown_tokens = "  ".join([f"[{tk}]" for tk in sim_tokens[:num_tokens]])
    draw.text((425, 720), shown_tokens, font=FONT_CODE_B, fill=C_TEXT_WHITE)
    
    draw.text((425, 770), "INTENT RESOLUTION: SystemDiagnostics -> ModeSwitch('live_audio_monitor')", font=FONT_CODE, fill=C_GREEN)
    draw.text((425, 800), "DISPATCH TARGET: core.audio_engine.set_monitoring_mode(active=True)", font=FONT_CODE, fill=C_TEXT_CYAN)
    draw.text((425, 830), "EXECUTION RESULT: Success | Latency: 7.6ms | UI Acknowledgment: Instant", font=FONT_CODE, fill=C_TEXT_MED)

# Chapter 3: Windows OS Control
def draw_ch03(draw: ImageDraw.ImageDraw, t: float, dur: float, p: float):
    draw_stage_container(draw, "WINDOWS OS & HARDWARE AUTOMATION", "Hardware Controllers, Window Docking & Process Management")
    
    # Left Card: Hardware Controls (Volume & Brightness)
    draw.rounded_rectangle([400, 310, 950, 890], radius=8, fill=C_PANEL2, outline=C_BORDER, width=1)
    draw.text((425, 330), "HARDWARE & DISPLAY REGULATION", font=FONT_SUBTITLE, fill=C_CYAN)
    
    # Volume Slider (moving from 30% to 60%)
    vol_pct = int(30 + min(30, p * 60))
    draw.text((425, 380), f"Master Volume: {vol_pct}%", font=FONT_BODY_B, fill=C_TEXT_WHITE)
    draw.rounded_rectangle([425, 415, 920, 445], radius=6, fill=C_BG, outline=C_BORDER, width=1)
    fill_w = int((vol_pct / 100) * (920 - 425))
    draw.rounded_rectangle([425, 415, 425 + fill_w, 445], radius=6, fill=C_CYAN)
    draw.text((425, 455), "Native WASAPI Core Audio Endpoint: Speakers (Realtek High Definition)", font=FONT_SMALL, fill=C_TEXT_DIM)
    
    # Brightness Slider (moving from 50% to 80%)
    bright_pct = int(50 + min(30, p * 50))
    draw.text((425, 510), f"Display Brightness: {bright_pct}%", font=FONT_BODY_B, fill=C_TEXT_WHITE)
    draw.rounded_rectangle([425, 545, 920, 575], radius=6, fill=C_BG, outline=C_BORDER, width=1)
    fill_b = int((bright_pct / 100) * (920 - 425))
    draw.rounded_rectangle([425, 545, 425 + fill_b, 575], radius=6, fill=C_GREEN)
    draw.text((425, 585), "WMI Monitor Brightness Controller: Primary Display (1920x1080@144Hz)", font=FONT_SMALL, fill=C_TEXT_DIM)
    
    # Battery & Power State
    draw.text((425, 640), "Power Telemetry: AC Connected (100% Battery, Healthy)", font=FONT_BODY, fill=C_TEXT_CYAN)
    draw.text((425, 670), "Thermals: CPU 42°C | GPU 38°C (Optimal Performance Mode)", font=FONT_BODY, fill=C_TEXT_MED)
    
    # Lower checklist in Left Card
    draw.line([425, 720, 920, 720], fill=C_BORDER, width=1)
    draw.text((425, 740), "[✓] Direct Win32 Hardware Invocation (No Setting Menus)", font=FONT_SMALL, fill=C_GREEN)
    draw.text((425, 775), "[✓] Zero Latency System Call Execution (1.2ms)", font=FONT_SMALL, fill=C_GREEN)
    draw.text((425, 810), "[✓] Multi-Display Arrangement & DPI Scaling Synced", font=FONT_SMALL, fill=C_GREEN)
    draw.text((425, 845), "[✓] Asynchronous Non-blocking WMI Dispatch", font=FONT_SMALL, fill=C_GREEN)
    
    # Right Card: Window Tiling & Workspace Organization
    draw.rounded_rectangle([980, 310, 1820, 890], radius=8, fill=C_PANEL2, outline=C_BORDER, width=1)
    draw.text((1005, 330), "INTELLIGENT WINDOW DOCKING & TILING", font=FONT_SUBTITLE, fill=C_CYAN)
    
    # Screen Graphic Mockup
    draw.rounded_rectangle([1005, 375, 1795, 710], radius=6, fill=C_BG, outline=C_CYAN, width=2)
    # Split screen (50% VS Code, 50% Chrome)
    mid_x = (1005 + 1795) // 2
    draw.rectangle([1010, 380, mid_x - 5, 705], fill=(15, 25, 38), outline=C_BORDER, width=1)
    draw.rectangle([1010, 380, mid_x - 5, 415], fill=(20, 38, 55))
    draw.text((1025, 390), "Visual Studio Code - [main.py] (Left 50%)", font=FONT_SMALL, fill=C_CYAN)
    draw.text((1025, 430), "# EVA Main Orchestrator Loop\nasync def run_eva():\n    await audio.stream()\n    await agent.listen()", font=FONT_CODE, fill=C_TEXT_WHITE)
    
    draw.rectangle([mid_x + 5, 380, 1790, 705], fill=(15, 25, 38), outline=C_BORDER, width=1)
    draw.rectangle([mid_x + 5, 380, 1790, 415], fill=(20, 38, 55))
    draw.text((mid_x + 20, 390), "Google Chrome - [Gemini Live Dashboard] (Right 50%)", font=FONT_SMALL, fill=C_GREEN)
    draw.text((mid_x + 20, 430), "WebSocket Status: Connected (200 OK)\nActive Sessions: 1\nStream Audio: Active 24kHz PCM", font=FONT_CODE, fill=C_TEXT_WHITE)
    
    # Process Table below graphic
    draw.text((1005, 735), "ACTIVE PROCESS MANAGEMENT", font=FONT_BODY_B, fill=C_TEXT_CYAN)
    pt = [
        ("Code.exe", "14820", "2.1%", "340 MB", "Tiled Left (Active)"),
        ("chrome.exe", "9240", "4.5%", "680 MB", "Tiled Right (Active)"),
        ("explorer.exe", "1120", "0.2%", "110 MB", "Background (Minimized)"),
        ("spotify.exe", "5480", "0.4%", "180 MB", "Background (Minimized)")
    ]
    py = 765
    for proc, pid, cpu, ram, st in pt:
        draw.text((1005, py), proc, font=FONT_CODE, fill=C_TEXT_WHITE)
        draw.text((1160, py), pid, font=FONT_CODE, fill=C_TEXT_DIM)
        draw.text((1280, py), cpu, font=FONT_CODE, fill=C_AMBER)
        draw.text((1400, py), ram, font=FONT_CODE, fill=C_TEXT_CYAN)
        draw.text((1550, py), st, font=FONT_CODE, fill=C_GREEN)
        py += 28

# Chapter 4: Zero-Permission Silent App Installation
def draw_ch04(draw: ImageDraw.ImageDraw, t: float, dur: float, p: float):
    draw_stage_container(draw, "ZERO-PERMISSION SILENT APPLICATION INSTALLER", "Headless WinGet Orchestration with Live Progress Streaming")
    
    # Top Information Bar
    draw.rounded_rectangle([400, 310, 1820, 390], radius=8, fill=C_PANEL2, outline=C_BORDER, width=1)
    draw.text((425, 325), "TARGET APPLICATION:", font=FONT_BODY_B, fill=C_TEXT_DIM)
    draw.text((630, 325), "VLC Media Player (VideoLAN.VLC)", font=FONT_BODY_B, fill=C_CYAN)
    
    draw.text((425, 355), "REGISTRY PRE-CHECK:", font=FONT_BODY_B, fill=C_TEXT_DIM)
    draw.text((630, 355), "Direct HKLM/HKCU Scan Completed in 0.02s [Result: Not Installed]", font=FONT_BODY_B, fill=C_GREEN)
    
    draw.text((1250, 325), "CATALOG RESOLUTION:", font=FONT_BODY_B, fill=C_TEXT_DIM)
    draw.text((1460, 325), "Instant 0.00s (Curated ID)", font=FONT_BODY_B, fill=C_CYAN)
    draw.text((1250, 355), "INSTALLATION MODE:", font=FONT_BODY_B, fill=C_TEXT_DIM)
    draw.text((1460, 355), "Silent Headless (--silent)", font=FONT_BODY_B, fill=C_GREEN)
    
    # Main Terminal Console
    draw.rounded_rectangle([400, 410, 1820, 770], radius=8, fill=(3, 8, 14), outline=C_CYAN, width=2)
    draw.rectangle([400, 410, 1820, 445], fill=(12, 28, 42))
    draw.text((420, 420), "WINGET SILENT EXECUTION TERMINAL - HEADLESS STREAM", font=FONT_CODE_B, fill=C_TEXT_CYAN)
    
    # Calculate progress % (0 to 100%)
    inst_pct = int(min(100, max(0, (p - 0.15) / 0.70 * 100)))
    mb_downloaded = (inst_pct / 100) * 43.8
    
    lines = [
        "[00:00.02] Querying Windows Registry uninstall registry hives... Done in 21ms.",
        "[00:00.03] Package VideoLAN.VLC matched via internal curated instant catalog (0.00s lookup).",
        "[00:00.05] Invoking: winget install --id VideoLAN.VLC --silent --accept-package-agreements --disable-interactivity",
        f"[00:01.20] Connecting to source repository: https://download.videolan.org/vlc/3.0.21/win64/vlc.exe",
        f"[00:02.40] Downloading installer package: {mb_downloaded:.1f} MB / 43.8 MB (Speed: 19.2 MB/s)...",
    ]
    if inst_pct > 60:
        lines.append("[00:04.10] Verifying package hash integrity: SHA-256 e9f4a18b7... Hash verified.")
        lines.append("[00:04.80] Executing silent installer in headless execution sandbox with verb RunAs...")
    if inst_pct >= 95:
        lines.append("[00:06.50] [SUCCESS] Installation completed successfully with process exit code 0.")
        lines.append("[00:06.80] [AUTO-LAUNCH] Initializing process: C:\\Program Files\\VideoLAN\\VLC\\vlc.exe")
        lines.append("[00:07.10] Application VLC Media Player is running and active on desktop.")
    
    ty = 460
    for l in lines:
        col = C_GREEN if "SUCCESS" in l or "AUTO-LAUNCH" in l else C_TEXT_WHITE
        draw.text((425, ty), l, font=FONT_CODE, fill=col)
        ty += 26
    
    # Progress Bar Container inside terminal
    draw.rounded_rectangle([425, 710, 1795, 745], radius=6, fill=C_PANEL, outline=C_BORDER, width=1)
    bar_fill = int((inst_pct / 100) * (1795 - 425))
    draw.rounded_rectangle([425, 710, 425 + bar_fill, 745], radius=6, fill=C_GREEN if inst_pct >= 95 else C_CYAN)
    draw.text((1050, 718), f"{inst_pct}% COMPLETED", font=FONT_CODE_B, fill=(0, 20, 30))
    
    # Bottom Milestone Banner
    draw.rounded_rectangle([400, 790, 1820, 890], radius=8, fill=C_PANEL2, outline=C_BORDER, width=1)
    draw.text((430, 810), "ZERO-PERMISSION ADVANTAGES:", font=FONT_BODY_B, fill=C_AMBER)
    draw.text((430, 840), "• No Microsoft Account Login Required   • Bypasses User Agreement Wizard Dialogs   • 95% Faster Execution", font=FONT_BODY, fill=C_TEXT_WHITE)

# Chapter 5: Universal Content & Media Downloader
def draw_ch05(draw: ImageDraw.ImageDraw, t: float, dur: float, p: float):
    draw_stage_container(draw, "UNIVERSAL CONTENT & MEDIA DOWNLOADER", "Intelligent Asset Retrieval with Automated Windows File Explorer Reveal")
    
    # Left Card: Downloader Parameters & Media Card
    draw.rounded_rectangle([400, 310, 1050, 890], radius=8, fill=C_PANEL2, outline=C_BORDER, width=1)
    draw.text((425, 330), "MEDIA RETRIEVAL PIPELINE", font=FONT_SUBTITLE, fill=C_CYAN)
    
    draw.text((425, 375), "Search Query:", font=FONT_BODY_B, fill=C_TEXT_DIM)
    draw.text((560, 375), '"vintage red sports car"', font=FONT_BODY_B, fill=C_TEXT_WHITE)
    draw.text((425, 405), "Engine Route:", font=FONT_BODY_B, fill=C_TEXT_DIM)
    draw.text((560, 405), "DuckDuckGo Image API (Bing Ad-Filter Fallback)", font=FONT_BODY_B, fill=C_CYAN)
    draw.text((425, 435), "Target Quantity:", font=FONT_BODY_B, fill=C_TEXT_DIM)
    draw.text((560, 435), "1 Asset (User Default Protection Enforced)", font=FONT_BODY_B, fill=C_GREEN)
    
    # Simulated High-Res Image Preview Box
    draw.rounded_rectangle([425, 480, 1025, 780], radius=8, fill=(10, 20, 32), outline=C_CYAN, width=2)
    # Draw classic car schematic / illustration
    cx, cy = 725, 630
    draw.ellipse([cx - 240, cy - 30, cx + 240, cy + 60], fill=(220, 30, 45)) # car body
    draw.rectangle([cx - 150, cy - 80, cx + 100, cy - 25], fill=(30, 50, 70), outline=C_BORDER_HI, width=2) # cabin
    draw.ellipse([cx - 170, cy + 30, cx - 90, cy + 110], fill=(20, 20, 20), outline=C_CYAN, width=3) # wheel
    draw.ellipse([cx + 90, cy + 30, cx + 170, cy + 110], fill=(20, 20, 20), outline=C_CYAN, width=3) # wheel
    draw.text((445, 495), "PREVIEW: vintage_red_sports_car.jpg [1920x1080 | 1.42 MB]", font=FONT_SMALL, fill=C_TEXT_CYAN)
    
    draw.text((425, 810), "Destination Path: C:\\Users\\User\\Downloads\\Media\\", font=FONT_SMALL, fill=C_TEXT_MED)
    draw.text((425, 840), "Status: 100% Downloaded & Verified (MD5: d41d8cd98f00b204e9800998ecf8427e)", font=FONT_SMALL, fill=C_GREEN)
    
    # Right Card: Windows File Explorer Mockup
    draw.rounded_rectangle([1080, 310, 1820, 890], radius=8, fill=C_PANEL2, outline=C_BORDER, width=1)
    draw.text((1105, 330), "WINDOWS FILE EXPLORER AUTO-REVEAL", font=FONT_SUBTITLE, fill=C_CYAN)
    
    # File Explorer Window Simulation
    draw.rounded_rectangle([1105, 375, 1795, 850], radius=6, fill=C_BG, outline=C_BORDER, width=1)
    draw.rectangle([1105, 375, 1795, 415], fill=(18, 38, 56))
    draw.text((1125, 388), "File Explorer - > This PC > Downloads > Media", font=FONT_SMALL, fill=C_TEXT_WHITE)
    
    # Highlighted File Row
    draw.rounded_rectangle([1120, 440, 1780, 500], radius=6, fill=(0, 60, 95), outline=C_GREEN, width=2)
    draw.text((1140, 455), "📷  vintage_red_sports_car.jpg", font=FONT_BODY_B, fill=C_TEXT_WHITE)
    draw.text((1500, 455), "1,452 KB", font=FONT_BODY, fill=C_TEXT_CYAN)
    draw.text((1640, 455), "JPEG Image", font=FONT_BODY, fill=C_TEXT_MED)
    
    # Other files in directory
    other_files = [
        ("📄  project_specifications.pdf", "3,210 KB", "PDF Document"),
        ("📊  quarterly_budget_2026.xlsx", "840 KB", "Excel Worksheet"),
        ("🎵  ambient_coding_track.mp3", "8,420 KB", "MP3 Audio"),
        ("📦  installer_vlc_win64.exe", "43,800 KB", "Application"),
        ("📝  meeting_notes_october.docx", "520 KB", "Word Document")
    ]
    oy = 520
    for fn, fsz, ftp in other_files:
        draw.text((1140, oy), fn, font=FONT_BODY, fill=C_TEXT_DIM)
        draw.text((1500, oy), fsz, font=FONT_BODY, fill=C_TEXT_DIM)
        draw.text((1640, oy), ftp, font=FONT_BODY, fill=C_TEXT_DIM)
        oy += 45
    
    draw.rounded_rectangle([1120, 770, 1780, 830], radius=6, fill=C_PANEL2, outline=C_GREEN, width=1)
    draw.text((1140, 788), "✓ Automated File Explorer Selection Executed (No Manual Browsing Needed)", font=FONT_BODY_B, fill=C_GREEN)

# Chapter 6: Automated Document & PPT Generation
def draw_ch06(draw: ImageDraw.ImageDraw, t: float, dur: float, p: float):
    draw_stage_container(draw, "AUTOMATED CONTENT CREATOR (DOCX, PPTX & PDF)", "In-Memory Native Assembly with Web Image Sourcing & Visual Alignment")
    
    # Topic & Parameters
    draw.rounded_rectangle([400, 310, 1820, 380], radius=8, fill=C_PANEL2, outline=C_BORDER, width=1)
    draw.text((425, 325), "TOPIC: Artificial Intelligence in Modern Healthcare", font=FONT_SUBTITLE, fill=C_CYAN)
    draw.text((425, 352), "OUTPUT: PowerPoint Presentation (.pptx)  |  SLIDES: 5 Decks  |  ENGINE: python-pptx (In-Memory Compilation in 2.14s)", font=FONT_SMALL, fill=C_TEXT_WHITE)
    
    # 5 Slide Cards Grid
    slides = [
        ("SLIDE 1", "AI in Modern Healthcare", "Transforming Clinical Diagnostics\n& Surgical Outcomes", "Header & Subtitle"),
        ("SLIDE 2", "Deep Learning Diagnostics", "• High-precision MRI scanning\n• Early oncology detection\n• Automated pathology screening", "Medical Scan Diagram"),
        ("SLIDE 3", "Predictive Analytics", "• Patient vitals monitoring\n• ICU risk escalation alerts\n• Hospital resource forecasting", "Telemetry Chart"),
        ("SLIDE 4", "Robotic Surgery", "• Sub-millimeter precision\n• Real-time computer vision\n• Reduced recovery duration", "Surgical Robotics Visual"),
        ("SLIDE 5", "Future Horizons", "• Personalized genomics\n• Autonomous drug discovery\n• Universal telemedicine access", "DNA Sequencing Graphic")
    ]
    
    sx = 400
    for s_idx, (s_num, s_title, s_bullets, s_img) in enumerate(slides):
        sw = 265
        draw.rounded_rectangle([sx, 400, sx + sw, 780], radius=8, fill=C_PANEL2, outline=C_CYAN if s_idx == 1 else C_BORDER, width=2)
        draw.rectangle([sx, 400, sx + sw, 435], fill=(16, 40, 60))
        draw.text((sx + 15, 410), s_num, font=FONT_BODY_B, fill=C_CYAN)
        
        draw.text((sx + 15, 450), s_title, font=FONT_BODY_B, fill=C_TEXT_WHITE)
        draw.line([sx + 15, 485, sx + sw - 15, 485], fill=C_BORDER, width=1)
        
        # Bullets
        by = 500
        for b_line in s_bullets.split("\n"):
            draw.text((sx + 15, by), b_line, font=FONT_SMALL, fill=C_TEXT_MED)
            by += 28
        
        # Image box mockup inside slide
        draw.rounded_rectangle([sx + 15, 640, sx + sw - 15, 755], radius=5, fill=(10, 20, 30), outline=C_CYAN_DIM, width=1)
        draw.text((sx + 25, 675), f"[IMG]\n{s_img}", font=FONT_SMALL, fill=C_GREEN)
        
        sx += 288
    
    # Bottom Milestone Banner
    draw.rounded_rectangle([400, 800, 1820, 890], radius=8, fill=C_PANEL2, outline=C_BORDER, width=1)
    draw.text((430, 820), "ADVANCED CONTENT ENGINE HIGHLIGHTS:", font=FONT_BODY_B, fill=C_GREEN)
    draw.text((430, 850), "• Native In-Memory Assembly (No Microsoft Office Required)   • Automatic Web Sourced Image Centering   • Perfect PPTX Typography", font=FONT_BODY, fill=C_TEXT_WHITE)

# Chapter 7: Universal File Conversion Engine
def draw_ch07(draw: ImageDraw.ImageDraw, t: float, dur: float, p: float):
    draw_stage_container(draw, "UNIVERSAL FILE CONVERSION & INTELLIGENCE ENGINE", "Zero-Dependency Native Format Transformation & Semantic Document Parsing")
    
    # Pipeline Graphic (DOCX -> Local Engine -> PDF)
    draw.rounded_rectangle([400, 310, 850, 470], radius=8, fill=C_PANEL2, outline=C_BORDER, width=1)
    draw.text((425, 330), "SOURCE DOCUMENT", font=FONT_SUBTITLE, fill=C_CYAN)
    draw.text((425, 375), "Quarterly_Project_Report.docx", font=FONT_BODY_B, fill=C_TEXT_WHITE)
    draw.text((425, 405), "Size: 3,840 KB | Format: Microsoft Word (OOXML)", font=FONT_SMALL, fill=C_TEXT_DIM)
    draw.text((425, 430), "Pages: 18 | Tables: 6 | Embedded Graphics: 12", font=FONT_SMALL, fill=C_TEXT_MED)
    
    # Center Conversion Pulse
    draw.line([850, 390, 990, 390], fill=C_CYAN, width=3)
    draw.rounded_rectangle([990, 330, 1230, 450], radius=8, fill=(0, 60, 95), outline=C_GREEN, width=2)
    draw.text((1015, 355), "UNIVERSAL CONVERTER", font=FONT_BODY_B, fill=C_GREEN)
    draw.text((1015, 385), "In-Process Execution", font=FONT_SMALL, fill=C_TEXT_WHITE)
    draw.text((1015, 408), "Time: 0.38 seconds", font=FONT_BODY_B, fill=C_AMBER)
    draw.line([1230, 390, 1370, 390], fill=C_CYAN, width=3)
    
    draw.rounded_rectangle([1370, 310, 1820, 470], radius=8, fill=C_PANEL2, outline=C_BORDER, width=1)
    draw.text((1395, 330), "GENERATED VECTOR OUTPUT", font=FONT_SUBTITLE, fill=C_CYAN)
    draw.text((1395, 375), "Quarterly_Project_Report.pdf", font=FONT_BODY_B, fill=C_GREEN)
    draw.text((1395, 405), "Size: 2,120 KB | Format: Adobe PDF 1.7 Vector", font=FONT_SMALL, fill=C_TEXT_DIM)
    draw.text((1395, 430), "Quality: Lossless Vector Typography (100% Fidelity)", font=FONT_SMALL, fill=C_TEXT_MED)
    
    # Supported Matrix Table (Lower Left)
    draw.rounded_rectangle([400, 500, 1050, 890], radius=8, fill=C_PANEL2, outline=C_BORDER, width=1)
    draw.text((425, 525), "SUPPORTED CONVERSION MATRIX", font=FONT_SUBTITLE, fill=C_CYAN)
    
    mat = [
        ("Word to PDF", ".docx  ➔  .pdf", "Native docx2pdf / reportlab", "0.38s"),
        ("PDF to Text / MD", ".pdf   ➔  .txt / .md", "Semantic table & text parser", "0.15s"),
        ("Spreadsheet to CSV", ".xlsx  ➔  .csv", "High-speed openpyxl engine", "0.08s"),
        ("Image Transcoding", ".png   ➔  .jpg / .webp", "Lossless Pillow pipeline", "0.04s"),
        ("Presentation Export", ".pptx  ➔  .pdf", "Vector slide rasterizer", "0.82s")
    ]
    my = 575
    for src, arrow, eng, spd in mat:
        draw.text((425, my), src, font=FONT_BODY_B, fill=C_TEXT_WHITE)
        draw.text((620, my), arrow, font=FONT_CODE_B, fill=C_GREEN)
        draw.text((425, my + 22), eng, font=FONT_SMALL, fill=C_TEXT_DIM)
        draw.text((950, my + 10), spd, font=FONT_BODY_B, fill=C_AMBER)
        draw.line([425, my + 46, 1025, my + 46], fill=C_BORDER, width=1)
        my += 58
    
    # Semantic Intelligence Box (Lower Right)
    draw.rounded_rectangle([1080, 500, 1820, 890], radius=8, fill=C_PANEL2, outline=C_BORDER, width=1)
    draw.text((1105, 525), "DOCUMENT INTELLIGENCE & SEMANTIC EXTRACTION", font=FONT_SUBTITLE, fill=C_CYAN)
    
    draw.text((1105, 570), "EXECUTIVE SUMMARY EXTRACTED FROM DOCUMENT:", font=FONT_BODY_B, fill=C_TEXT_CYAN)
    summary_text = (
        "• Total Q3 operating revenue surpassed initial targets by 14.2% across engineering divisions.\n"
        "• Assistant automation initiatives reduced manual desktop operations by 82 hours per developer.\n"
        "• Infrastructure migration to local native model execution achieved 95% latency reduction.\n"
        "• Zero compliance infractions recorded under enterprise safety boundary policies."
    )
    sy = 610
    for s_line in summary_text.split("\n"):
        draw.text((1105, sy), s_line, font=FONT_BODY, fill=C_TEXT_WHITE)
        sy += 36
    
    draw.rounded_rectangle([1105, 780, 1795, 850], radius=6, fill=(0, 45, 70), outline=C_GREEN, width=1)
    draw.text((1125, 802), "✓ 1,420 Embeddings Indexed into Local Vector Memory Store for Instant Recall", font=FONT_BODY_B, fill=C_GREEN)

# Chapter 8: Automated WhatsApp Messaging & Dispatch
def draw_ch08(draw: ImageDraw.ImageDraw, t: float, dur: float, p: float):
    draw_stage_container(draw, "AUTOMATED WHATSAPP MESSAGING & MEDIA DISPATCH", "Hands-Free Desktop Dispatch for Documents, Media & Voice Messages")
    
    # Left Card: Dispatch Metadata & Status
    draw.rounded_rectangle([400, 310, 950, 890], radius=8, fill=C_PANEL2, outline=C_BORDER, width=1)
    draw.text((425, 330), "DISPATCH CONTROLLER", font=FONT_SUBTITLE, fill=C_CYAN)
    
    draw.text((425, 380), "Target Contact:", font=FONT_BODY_B, fill=C_TEXT_DIM)
    draw.text((580, 380), "Alex (Engineering Lead)", font=FONT_BODY_B, fill=C_TEXT_WHITE)
    draw.text((425, 415), "Phone Number:", font=FONT_BODY_B, fill=C_TEXT_DIM)
    draw.text((580, 415), "+1 (555) 019-2834", font=FONT_BODY_B, fill=C_CYAN)
    draw.text((425, 450), "Routing Engine:", font=FONT_BODY_B, fill=C_TEXT_DIM)
    draw.text((580, 450), "WhatsApp Desktop / Playwright", font=FONT_BODY_B, fill=C_TEXT_WHITE)
    draw.text((425, 485), "Attachment:", font=FONT_BODY_B, fill=C_TEXT_DIM)
    draw.text((580, 485), "Quarterly_Project_Report.pdf", font=FONT_BODY_B, fill=C_GREEN)
    
    draw.line([425, 530, 925, 530], fill=C_BORDER, width=1)
    draw.text((425, 550), "EXECUTION SEQUENCE TIMELINE:", font=FONT_BODY_B, fill=C_CYAN)
    
    seq = [
        ("[00:00.10]", "Contact Resolution: Alex -> Verified Online", C_GREEN),
        ("[00:00.45]", "File Verification: PDF located (2,120 KB)", C_GREEN),
        ("[00:01.10]", "Desktop Client Focused & Message Composed", C_CYAN),
        ("[00:01.60]", "Attachment Upload & Encryption Completed", C_CYAN),
        ("[00:01.85]", "Message Dispatched with Delivery Receipt", C_GREEN)
    ]
    sqy = 590
    for ts, ev, col in seq:
        draw.text((425, sqy), ts, font=FONT_CODE, fill=C_TEXT_DIM)
        draw.text((540, sqy), ev, font=FONT_SMALL, fill=col)
        sqy += 40
    
    draw.rounded_rectangle([425, 800, 925, 860], radius=6, fill=(0, 50, 80), outline=C_GREEN, width=1)
    draw.text((445, 818), "✓ Total Dispatch Latency: 1.85 Seconds", font=FONT_BODY_B, fill=C_GREEN)
    
    # Right Card: WhatsApp Chat UI Simulation
    draw.rounded_rectangle([980, 310, 1820, 890], radius=8, fill=(11, 20, 26), outline=C_BORDER, width=1)
    
    # WhatsApp Header
    draw.rectangle([980, 310, 1820, 380], fill=(32, 44, 51))
    draw.ellipse([1005, 325, 1045, 365], fill=(0, 168, 132))
    draw.text((1018, 332), "A", font=FONT_BODY_B, fill=(255, 255, 255))
    draw.text((1060, 328), "Alex (Engineering Lead)", font=FONT_BODY_B, fill=(233, 237, 239))
    draw.text((1060, 352), "online • WhatsApp Desktop", font=FONT_SMALL, fill=(0, 168, 132))
    
    # Chat Background & Message Bubbles
    draw.rectangle([980, 380, 1820, 830], fill=(11, 20, 26))
    
    # Incoming Message from Alex
    draw.rounded_rectangle([1010, 420, 1420, 490], radius=8, fill=(32, 44, 51))
    draw.text((1030, 435), "Hey! Do you have the latest quarterly report\nand slides ready to review?", font=FONT_BODY, fill=(233, 237, 239))
    draw.text((1360, 465), "10:41 AM", font=FONT_SMALL, fill=(134, 150, 160))
    
    # Outgoing Message from EVA
    draw.rounded_rectangle([1220, 520, 1790, 750], radius=8, fill=(0, 92, 75))
    draw.text((1240, 535), "Hi Alex, here is the generated quarterly project\nreport and presentation slides compiled by EVA.", font=FONT_BODY, fill=(233, 237, 239))
    
    # Attachment Card inside outgoing bubble
    draw.rounded_rectangle([1240, 600, 1770, 690], radius=6, fill=(18, 48, 42), outline=(0, 168, 132), width=1)
    draw.text((1260, 615), "📄  Quarterly_Project_Report.pdf", font=FONT_BODY_B, fill=(255, 255, 255))
    draw.text((1260, 645), "2.1 MB • 18 Pages • Verified Vector PDF", font=FONT_SMALL, fill=(134, 150, 160))
    
    draw.text((1700, 715), "10:42 AM", font=FONT_SMALL, fill=(134, 150, 160))
    draw.text((1760, 715), "✓✓", font=FONT_BODY_B, fill=(83, 189, 235)) # Blue double check
    
    # Bottom Input Bar Mockup
    draw.rectangle([980, 830, 1820, 890], fill=(32, 44, 51))
    draw.text((1010, 848), "Type a message or use voice with EVA...", font=FONT_BODY, fill=(134, 150, 160))

# Chapter 9: Web Intelligence & Mobile Dashboard
def draw_ch09(draw: ImageDraw.ImageDraw, t: float, dur: float, p: float):
    draw_stage_container(draw, "WEB INTELLIGENCE & REMOTE MOBILE DASHBOARD", "Live Flight Radar, Weather, Proactive Monitors & QR Mobile Control")
    
    # Top Left: Live Weather Forecast
    draw.rounded_rectangle([400, 310, 1050, 580], radius=8, fill=C_PANEL2, outline=C_BORDER, width=1)
    draw.text((425, 330), "REAL-TIME CONTEXTUAL WEATHER FORECAST", font=FONT_SUBTITLE, fill=C_CYAN)
    draw.text((425, 380), "24°C", font=FONT_HUGE, fill=C_AMBER)
    draw.text((540, 390), "Clear Skies & Sunny (New York, NY)", font=FONT_BODY_B, fill=C_TEXT_WHITE)
    draw.text((540, 415), "Wind: 8 km/h NW | Humidity: 46% | Pressure: 1014 hPa", font=FONT_SMALL, fill=C_TEXT_MED)
    
    # 3-Day Forecast Chips
    days = [("Today", "24° / 16°", "☀️ Sunny"), ("Tomorrow", "22° / 14°", "⛅ Partly Cloudy"), ("Friday", "20° / 13°", "🌧️ Light Rain")]
    dx = 425
    for dy, temp, icon in days:
        draw.rounded_rectangle([dx, 470, dx + 185, 550], radius=6, fill=C_BG, outline=C_BORDER, width=1)
        draw.text((dx + 15, 482), dy, font=FONT_BODY_B, fill=C_CYAN)
        draw.text((dx + 15, 506), temp, font=FONT_SMALL, fill=C_TEXT_WHITE)
        draw.text((dx + 15, 526), icon, font=FONT_SMALL, fill=C_TEXT_MED)
        dx += 205
    
    # Bottom Left: Live Flight Radar Tracker
    draw.rounded_rectangle([400, 600, 1050, 890], radius=8, fill=C_PANEL2, outline=C_BORDER, width=1)
    draw.text((425, 620), "LIVE COMMERCIAL FLIGHT TRACKER", font=FONT_SUBTITLE, fill=C_CYAN)
    draw.text((425, 665), "Flight: United Airlines UA 428 (Boeing 787-9)", font=FONT_BODY_B, fill=C_TEXT_WHITE)
    draw.text((425, 695), "Route: JFK (New York) ➔ SFO (San Francisco)", font=FONT_BODY, fill=C_TEXT_CYAN)
    draw.text((425, 725), "Status: EN ROUTE (ON TIME) | Altitude: 34,000 ft | Speed: 520 kts", font=FONT_BODY, fill=C_GREEN)
    
    # Flight progress line
    draw.line([425, 780, 1010, 780], fill=C_BORDER, width=4)
    plane_x = 425 + int(0.68 * (1010 - 425))
    draw.line([425, 780, plane_x, 780], fill=C_GREEN, width=4)
    draw.ellipse([plane_x - 10, 770, plane_x + 10, 790], fill=C_CYAN)
    draw.text((plane_x - 12, 745), "✈", font=FONT_SUBTITLE, fill=C_TEXT_WHITE)
    draw.text((425, 810), "Departed: 08:30 AM EST", font=FONT_SMALL, fill=C_TEXT_DIM)
    draw.text((860, 810), "Estimated: 11:45 AM PST", font=FONT_SMALL, fill=C_TEXT_DIM)
    
    # Right: Remote Mobile Dashboard & QR Pairing
    draw.rounded_rectangle([1080, 310, 1820, 890], radius=8, fill=C_PANEL2, outline=C_BORDER, width=1)
    draw.text((1105, 330), "FASTAPI REMOTE DASHBOARD & MOBILE QR PAIRING", font=FONT_SUBTITLE, fill=C_CYAN)
    
    # High-Contrast QR Code Graphic Simulation
    qrx, qry = 1130, 380
    draw.rounded_rectangle([qrx, qry, qrx + 240, qry + 240], radius=8, fill=(255, 255, 255), outline=C_CYAN, width=3)
    # Draw QR code pattern modules
    qr_data = [
        (20, 20, 60, 60), (160, 20, 60, 60), (20, 160, 60, 60), # 3 corner eyes
        (40, 40, 20, 20), (180, 40, 20, 20), (40, 180, 20, 20),
        (100, 30, 20, 40), (120, 80, 40, 20), (80, 120, 40, 40),
        (140, 140, 30, 30), (180, 180, 30, 30), (100, 180, 30, 30)
    ]
    for qx, qy, qw, qh in qr_data:
        draw.rectangle([qrx + qx, qry + qy, qrx + qx + qw, qry + qy + qh], fill=(0, 0, 0))
    
    # QR instructions beside QR
    draw.text((1400, 390), "LOCAL NETWORK PAIRING", font=FONT_BODY_B, fill=C_TEXT_WHITE)
    draw.text((1400, 425), "URL: http://192.168.1.140:8000/dashboard", font=FONT_CODE_B, fill=C_CYAN)
    draw.text((1400, 460), "Protocol: WebSocket Duplex (ws://...)", font=FONT_SMALL, fill=C_TEXT_MED)
    draw.text((1400, 490), "Security: LAN Restricted Token Pairing", font=FONT_SMALL, fill=C_GREEN)
    draw.text((1400, 520), "Scan with your smartphone camera to access\nthe live EVA Mobile HUD without installing apps.", font=FONT_BODY, fill=C_TEXT_WHITE)
    
    # Proactive Background Monitors
    draw.rounded_rectangle([1110, 650, 1790, 860], radius=6, fill=C_BG, outline=C_BORDER, width=1)
    draw.text((1130, 665), "PROACTIVE BACKGROUND MONITORS & ALERTS", font=FONT_BODY_B, fill=C_CYAN)
    
    p_alerts = [
        ("📅  Calendar Alert", "Project Review with Executive Team in 35 minutes", C_TEXT_WHITE),
        ("🔋  Battery Health", "Cycle count: 84 | Health: 98% (No degradation)", C_GREEN),
        ("🛡️  System Security", "All subprocess execution boundaries intact (0 warnings)", C_GREEN)
    ]
    pay = 705
    for tit, desc, col in p_alerts:
        draw.text((1130, pay), tit, font=FONT_BODY_B, fill=col)
        draw.text((1350, pay), desc, font=FONT_SMALL, fill=C_TEXT_CYAN)
        pay += 42

# Chapter 10: Performance Benchmarks & Conclusion
def draw_ch10(draw: ImageDraw.ImageDraw, t: float, dur: float, p: float):
    draw_stage_container(draw, "PERFORMANCE BENCHMARKS & ARCHITECTURE MILESTONES", "Sub-10ms UI Latency, 95% Response Time Reduction & 100% Test Stability")
    
    # Top Latency Comparison Cards
    benchmarks = [
        ("REGISTRY APP DETECTION", "15.00s", "0.02s", "99.8% Faster"),
        ("COMMAND ACKNOWLEDGMENT", "12.00s", "<10ms", "Instant"),
        ("MEDIA ASSET SEARCH", "14.50s", "2.80s", "80.7% Faster"),
        ("DOC/PPT COMPILATION", "18.00s", "2.14s", "88.1% Faster")
    ]
    
    bx = 400
    for title, before, after, pct in benchmarks:
        draw.rounded_rectangle([bx, 310, bx + 335, 470], radius=8, fill=C_PANEL2, outline=C_BORDER, width=1)
        draw.text((bx + 16, 325), title, font=FONT_BODY_B, fill=C_CYAN)
        draw.text((bx + 16, 360), f"Previous: {before}", font=FONT_BODY, fill=C_RED)
        draw.text((bx + 16, 390), f"Current:  {after}", font=FONT_TITLE, fill=C_GREEN)
        draw.text((bx + 16, 430), f"SPEEDUP: {pct}", font=FONT_BODY_B, fill=C_AMBER)
        bx += 362
    
    # Big Test Suite Card (Lower Left)
    draw.rounded_rectangle([400, 500, 1050, 890], radius=8, fill=C_PANEL2, outline=C_GREEN, width=2)
    draw.text((430, 525), "AUTOMATED TEST SUITE VERIFICATION", font=FONT_SUBTITLE, fill=C_GREEN)
    
    draw.text((430, 570), "114 / 114 TESTS PASSED", font=FONT_HUGE, fill=C_GREEN)
    draw.text((430, 620), "Pass Rate: 100.0%  |  Zero Regressions  |  Coverage: Full Module Suite", font=FONT_BODY_B, fill=C_TEXT_WHITE)
    
    test_modules = [
        "✓ test_install_app.py                (13 tests passed)",
        "✓ test_media_downloader.py           (11 tests passed)",
        "✓ test_content_creator_integration.py (14 tests passed)",
        "✓ test_file_controller.py            (10 tests passed)",
        "✓ test_file_conversion.py            (12 tests passed)",
        "✓ test_voice_latency_regressions.py  (15 tests passed)"
    ]
    tmy = 665
    for tm in test_modules:
        draw.text((430, tmy), tm, font=FONT_CODE, fill=C_TEXT_CYAN)
        tmy += 32
    
    # Conclusion Summary (Lower Right)
    draw.rounded_rectangle([1080, 500, 1820, 890], radius=8, fill=C_PANEL2, outline=C_CYAN, width=2)
    draw.text((1110, 525), "EVA: THE FUTURE OF DESKTOP AI COMPUTING", font=FONT_SUBTITLE, fill=C_CYAN)
    
    points = [
        ("Native Windows 10/11 Integration", "Direct Core Audio, WMI, and Display Adapter control"),
        ("Gemini Live Native Multimodal Audio", "Bidirectional streaming with sub-second voice latency"),
        ("Zero-Permission App Installation", "Headless WinGet execution with live UI streaming"),
        ("Autonomous Content & Document Engine", "In-memory creation of Word, PowerPoint, and PDF files"),
        ("Local Privacy & Boundary Security", "Sanitized logs, strict subprocess isolation, and LAN safety")
    ]
    py = 575
    for tit, sub in points:
        draw.text((1110, py), f"★ {tit}", font=FONT_BODY_B, fill=C_TEXT_WHITE)
        draw.text((1135, py + 24), sub, font=FONT_SMALL, fill=C_TEXT_MED)
        py += 52
    
    draw.rounded_rectangle([1110, 820, 1790, 870], radius=6, fill=(0, 60, 95), outline=C_GREEN, width=1)
    draw.text((1180, 834), "THANK YOU FOR WATCHING THE EVA LIVE DEMONSTRATION", font=FONT_BODY_B, fill=C_GREEN)

# Dispatch dictionary
STAGE_DRAWERS = {
    'ch01': draw_ch01,
    'ch02': draw_ch02,
    'ch03': draw_ch03,
    'ch04': draw_ch04,
    'ch05': draw_ch05,
    'ch06': draw_ch06,
    'ch07': draw_ch07,
    'ch08': draw_ch08,
    'ch09': draw_ch09,
    'ch10': draw_ch10
}
