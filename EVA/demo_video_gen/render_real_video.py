import os
import sys
import subprocess
import time
from PIL import Image, ImageDraw

sys.path.insert(0, r"c:\Users\ghana\Downloads\major project working\EVA\demo_video_gen")

from real_stage_drawers import (
    W, H, C_WIN_BG,
    draw_windows_taskbar, draw_subtitles_banner,
    REAL_DRAWERS
)
from synthesize_audio import CHAPTERS
from intro_outro_drawers import draw_intro_frame, draw_outro_frame
from build_scene import get_subtitle_segment

FPS = 24
AUDIO_DIR = r"c:\Users\ghana\Downloads\major project working\EVA\demo_video_gen\audio"
REAL_CLIPS_DIR = r"c:\Users\ghana\Downloads\major project working\EVA\demo_video_gen\real_clips"
FINAL_VIDEO = r"c:\Users\ghana\Downloads\major project working\EVA_Live_Demonstration_Walkthrough.mp4"

os.makedirs(REAL_CLIPS_DIR, exist_ok=True)

def render_real_intro():
    out_mp4 = os.path.join(REAL_CLIPS_DIR, "intro.mp4")
    if os.path.exists(out_mp4) and os.path.getsize(out_mp4) > 100000:
        print("[INTRO] [SKIP] intro.mp4 already rendered.")
        return
    audio_file = os.path.join(AUDIO_DIR, "intro.mp3")
        
    total_frames = int(FPS * dur)
    print(f"[INTRO] Rendering intro.mp4 ({dur:.2f}s, {total_frames} frames)...")
    
    cmd = [
        'ffmpeg', '-y',
        '-f', 'rawvideo', '-vcodec', 'rawvideo',
        '-s', f'{W}x{H}', '-pix_fmt', 'rgb24', '-r', str(FPS),
        '-i', '-',
        '-i', audio_file,
        '-c:v', 'libx264', '-preset', 'ultrafast', '-pix_fmt', 'yuv420p',
        '-c:a', 'aac', '-b:a', '192k',
        '-shortest',
        out_mp4
    ]
    
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
    intro_txt = "Welcome to the official live demonstration of EVA, the next-generation desktop AI copilot for Windows 10 and 11. Please sit back and enjoy this live in-depth system walkthrough."
    
    for f in range(total_frames):
        t = f / FPS
        p = t / dur
        img = draw_intro_frame(t, dur, p, intro_txt)
        proc.stdin.write(img.tobytes())
        
    proc.stdin.close()
    proc.wait()
    print(f"[INTRO] Done -> {out_mp4}")

def render_real_outro():
    out_mp4 = os.path.join(REAL_CLIPS_DIR, "outro.mp4")
    if os.path.exists(out_mp4) and os.path.getsize(out_mp4) > 100000:
        print("[OUTRO] [SKIP] outro.mp4 already rendered.")
        return
    audio_file = os.path.join(AUDIO_DIR, "outro.mp3")
    dur_str = subprocess.check_output([
        'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1', audio_file
    ]).decode().strip()
    dur = float(dur_str)
    total_frames = int(FPS * dur)
    print(f"[OUTRO] Rendering outro.mp4 ({dur:.2f}s, {total_frames} frames)...")
    
    cmd = [
        'ffmpeg', '-y',
        '-f', 'rawvideo', '-vcodec', 'rawvideo',
        '-s', f'{W}x{H}', '-pix_fmt', 'rgb24', '-r', str(FPS),
        '-i', '-',
        '-i', audio_file,
        '-c:v', 'libx264', '-preset', 'ultrafast', '-pix_fmt', 'yuv420p',
        '-c:a', 'aac', '-b:a', '192k',
        '-shortest',
        out_mp4
    ]
    
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
    outro_txt = "This concludes our comprehensive live demonstration of EVA. With deep Windows OS integration, zero-latency voice interaction, and autonomous desktop workflows, EVA redefines personal computing. Thank you for watching."
    
    for f in range(total_frames):
        t = f / FPS
        p = t / dur
        img = draw_outro_frame(t, dur, p, outro_txt)
        proc.stdin.write(img.tobytes())
        
    proc.stdin.close()
    proc.wait()
    print(f"[OUTRO] Done -> {out_mp4}")

def render_real_chapter(ch_idx: int):
    ch = CHAPTERS[ch_idx]
    cid = ch['id']
    out_mp4 = os.path.join(REAL_CLIPS_DIR, f"{cid}.mp4")
    audio_file = os.path.join(AUDIO_DIR, f"{cid}.mp3")
    
    dur_str = subprocess.check_output([
        'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1', audio_file
    ]).decode().strip()
    dur = float(dur_str)
    
    if os.path.exists(out_mp4) and os.path.getsize(out_mp4) > 500000:
        print(f"[{cid}] [SKIP] already rendered ({dur:.2f}s) -> {out_mp4}")
        return dur
        
    total_frames = int(FPS * dur)
    print(f"[{cid}] Rendering {ch['title']} ({dur:.2f}s, {total_frames} frames)...")
    
    cmd = [
        'ffmpeg', '-y',
        '-f', 'rawvideo', '-vcodec', 'rawvideo',
        '-s', f'{W}x{H}', '-pix_fmt', 'rgb24', '-r', str(FPS),
        '-i', '-',
        '-i', audio_file,
        '-c:v', 'libx264', '-preset', 'ultrafast', '-pix_fmt', 'yuv420p',
        '-c:a', 'aac', '-b:a', '192k',
        '-shortest',
        out_mp4
    ]
    
    t0 = time.time()
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
    drawer = REAL_DRAWERS[cid]
    
    for f in range(total_frames):
        t = f / FPS
        p = t / dur
        
        img = Image.new('RGB', (W, H), C_WIN_BG)
        draw = ImageDraw.Draw(img)
        
        # 1. Draw chapter content (real HUD / Windows apps / authentic photos)
        drawer(img, t, dur, p)
        
        # 2. Draw Windows 11 Taskbar
        draw_windows_taskbar(draw, t)
        
        # 3. Draw Synchronized Subtitle Banner
        sub = get_subtitle_segment(ch['text'], p)
        draw_subtitles_banner(draw, sub)
        
        proc.stdin.write(img.tobytes())
        
    proc.stdin.close()
    proc.wait()
    t1 = time.time()
    fps_actual = total_frames / max(0.001, t1 - t0)
    print(f"[{cid}] Done in {t1 - t0:.2f}s ({fps_actual:.1f} fps) -> {out_mp4}")
    return dur

def main():
    start_time = time.time()
    print("=" * 65)
    print("STARTING 100% REAL OUTPUT EVA LIVE DEMONSTRATION VIDEO BUILD")
    print("=" * 65)
    
    # 1. Render Intro
    render_real_intro()
    
    # 2. Render Chapters 01 to 10 with Real Outputs
    for idx in range(len(CHAPTERS)):
        render_real_chapter(idx)
        
    # 3. Render Outro
    render_real_outro()
    
    # 4. Concatenate all real scenes
    print("=" * 65)
    print("CONCATENATING REAL SCENES INTO FINAL MP4...")
    print("=" * 65)
    
    concat_list_file = os.path.join(REAL_CLIPS_DIR, "concat_list.txt")
    clips = ["intro.mp4"] + [f"{ch['id']}.mp4" for ch in CHAPTERS] + ["outro.mp4"]
    
    with open(concat_list_file, "w", encoding="utf-8") as f:
        for c in clips:
            full_clip_path = os.path.join(REAL_CLIPS_DIR, c).replace("\\", "/")
            f.write(f"file '{full_clip_path}'\n")
            
    concat_cmd = [
        'ffmpeg', '-y',
        '-f', 'concat', '-safe', '0',
        '-i', concat_list_file,
        '-c', 'copy',
        FINAL_VIDEO
    ]
    subprocess.run(concat_cmd, check=True)
    
    dur_str = subprocess.check_output([
        'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1', FINAL_VIDEO
    ]).decode().strip()
    final_dur = float(dur_str)
    file_size_mb = os.path.getsize(FINAL_VIDEO) / (1024 * 1024)
    total_sec = time.time() - start_time
    
    print("=" * 65)
    print("SUCCESS: REAL OUTPUT EVA LIVE DEMONSTRATION VIDEO GENERATED!")
    print(f"Path: {FINAL_VIDEO}")
    print(f"Duration: {final_dur:.2f} seconds ({final_dur / 60:.2f} minutes)")
    print(f"File Size: {file_size_mb:.2f} MB")
    print(f"Resolution: 1920x1080 (1080p Full HD @ 24 fps)")
    print(f"Total Build Time: {total_sec:.2f}s ({total_sec / 60:.2f} minutes)")
    print("=" * 65)

if __name__ == '__main__':
    main()
