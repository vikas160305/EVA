import os
import sys

sys.path.insert(0, r"c:\Users\ghana\Downloads\major project working\EVA")
os.environ["QT_QPA_PLATFORM"] = "offscreen"
from ui import JarvisUI

out_dir = r"c:\Users\ghana\Downloads\major project working\EVA\demo_video_gen"
os.makedirs(out_dir, exist_ok=True)

# Capture State 1: System Online & Listening
ui1 = JarvisUI("")
ui1.write_log("[System] EVA Assistant Online and Listening...")
ui1.write_log("[Gemini Live] Duplex 24kHz Audio Session Established")
ui1.write_log("[Intent Router] Sub-10ms Fast Intent Matcher: READY")
ui1.write_log("[Hardware] WASAPI Core Audio & WMI Display Controller: ONLINE")
ui1.set_state("listening")
for _ in range(25):
    ui1._app.processEvents()
ui1._win.grab().save(os.path.join(out_dir, "real_hud_listening.png"))

# Capture State 2: Silent App Installation
ui2 = JarvisUI("")
ui2.write_log("[System] Voice Command: 'EVA, install VLC media player'")
ui2.write_log("[Router] Fast Intent Matched: install_app(app_name='vlc')")
ui2.write_log("[Installer] Windows Registry fast-check: 0.02s (Not Installed)")
ui2.write_log("[Winget] winget install --id VideoLAN.VLC --silent --accept-package-agreements")
ui2.write_log("[Progress] Downloading package (43.8 MB)... 100%")
ui2.write_log("[Success] Silent installation verified. Launching VLC Media Player.")
ui2.set_state("listening")
for _ in range(25):
    ui2._app.processEvents()
ui2._win.grab().save(os.path.join(out_dir, "real_hud_installing.png"))

# Capture State 3: Media Downloader
ui3 = JarvisUI("")
ui3.write_log("[System] Voice Command: 'EVA, download an image of a red vintage sports car'")
ui3.write_log("[Router] Fast Intent Matched: media_downloader(category='image', count=1)")
ui3.write_log("[Downloader] DuckDuckGo Image API search: 1 direct source resolved")
ui3.write_log("[Downloader] Saved to: OneDrive\\Pictures\\EVA Images\\vintage_red_sports_car.jpg")
ui3.write_log("[Explorer] Windows File Explorer auto-reveal triggered and selected")
ui3.set_state("speaking")
for _ in range(25):
    ui3._app.processEvents()
ui3._win.grab().save(os.path.join(out_dir, "real_hud_downloader.png"))

# Capture State 4: Content Creator & Conversion
ui4 = JarvisUI("")
ui4.write_log("[System] Voice Command: 'EVA, generate 5-slide presentation on AI in Healthcare'")
ui4.write_log("[Content Creator] python-pptx compilation started: in-memory assembly")
ui4.write_log("[Content Creator] 5 slides generated with web sourced medical imaging diagram")
ui4.write_log("[File Controller] Universal conversion: docx to pdf (0.38s)")
ui4.write_log("[WhatsApp] Prepared dispatch: Quarterly_Project_Report.pdf to Alex")
ui4.set_state("speaking")
for _ in range(25):
    ui4._app.processEvents()
ui4._win.grab().save(os.path.join(out_dir, "real_hud_content.png"))

print("ALL REAL HUD SCREENSHOTS GENERATED SUCCESSFULLY!")
