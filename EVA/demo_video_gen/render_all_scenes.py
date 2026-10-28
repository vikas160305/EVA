import os
import sys
import subprocess
import time
from PIL import Image, ImageDraw

from build_scene import (
    W, H, FPS, C_BG,
    draw_header, draw_sidebar, draw_action_bar, draw_subtitles,
    get_subtitle_segment
)
from stage_drawers import STAGE_DRAWERS
from synthesize_audio import CHAPTERS
from intro_outro_drawers import draw_intro_frame, draw_outro_frame

CLIPS_DIR = r"c:\Users\ghana\Downloads\major project working\EVA\demo_video_gen\clips"
AUDIO_DIR = r"c:\Users\ghana\Downloads\major project working\EVA\demo_video_gen\audio"
FINAL_VIDEO = r"c:\Users\ghana\Downloads\major project working\EVA_Live_Demonstration_Walkthrough.mp4"

os.makedirs(CLIPS_DIR, exist_ok=True)

def render_intro():
    out_mp4 = os.path.join(CLIPS_DIR, "intro.mp4")
    if os.path.exists(out_mp4) and os.path.getsize(out_mp4) > 100000:
        print("[SKIP] intro.mp4 already exists.")
        return
    
    audio_file = os.path.join(AUDIO_DIR, "intro.mp3")
    dur_str = subprocess.check_output([
        'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1', audio_file
    ]).decode().strip()
    dur = float(dur_str)
    total_frames = int(FPS * dur)
    print(f"Rendering intro.mp4: {dur:.2f}s, {total_frames} frames...")
    
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
    print(f"Done intro.mp4 -> {out_mp4}")

def render_outro():
    out_mp4 = os.path.join(CLIPS_DIR, "outro.mp4")
    if os.path.exists(out_mp4) and os.path.getsize(out_mp4) > 100000:
        print("[SKIP] outro.mp4 already exists.")
        return
    
    audio_file = os.path.join(AUDIO_DIR, "outro.mp3")
    dur_str = subprocess.check_output([
        'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1', audio_file
    ]).decode().strip()
    dur = float(dur_str)
    total_frames = int(FPS * dur)
    print(f"Rendering outro.mp4: {dur:.2f}s, {total_frames} frames...")
    
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
    print(f"Done outro.mp4 -> {out_mp4}")

def render_chapter_scene(ch_idx: int, cumulative_time: float):
    ch = CHAPTERS[ch_idx]
    cid = ch['id']
    out_mp4 = os.path.join(CLIPS_DIR, f"{cid}.mp4")
    
    audio_file = os.path.join(AUDIO_DIR, f"{cid}.mp3")
    dur_str = subprocess.check_output([
        'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1', audio_file
    ]).decode().strip()
    dur = float(dur_str)
    
    if os.path.exists(out_mp4) and os.path.getsize(out_mp4) > 500000:
        # Check existing clip duration
        try:
            curr_dur_str = subprocess.check_output([
                'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1', out_mp4
            ]).decode().strip()
            curr_dur = float(curr_dur_str)
            if abs(curr_dur - dur) < 1.0:
                print(f"[SKIP] {cid}.mp4 already rendered ({curr_dur:.2f}s).")
                return dur
        except Exception:
            pass
    
    total_frames = int(FPS * dur)
    print(f"Rendering {cid} ({ch['title']}): {dur:.2f}s, {total_frames} frames...")
    
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
    drawer = STAGE_DRAWERS[cid]
    
    for f in range(total_frames):
        t = f / FPS
        p = t / dur
        
        img = Image.new('RGB', (W, H), C_BG)
        draw = ImageDraw.Draw(img)
        
        draw_header(draw, t, ch_idx, cumulative_time + t)
        draw_sidebar(draw, ch_idx)
        draw_action_bar(draw, ch['command'], t, p)
        drawer(draw, t, dur, p)
        
        sub = get_subtitle_segment(ch['text'], p)
        draw_subtitles(draw, sub)
        
        proc.stdin.write(img.tobytes())
    
    proc.stdin.close()
    proc.wait()
    t1 = time.time()
    print(f"Done {cid} in {t1 - t0:.2f}s ({(total_frames / (t1 - t0)):.1f} fps) -> {out_mp4}")
    return dur

def main():
    start_all = time.time()
    print("=" * 60)
    print("STARTING EVA 8-10 MINUTE LIVE DEMONSTRATION VIDEO GENERATION")
    print("=" * 60)
    
    # 1. Render Intro
    render_intro()
    cumulative_time = 12.29
    
    # 2. Render Chapters 01 to 10
    for idx in range(len(CHAPTERS)):
        dur = render_chapter_scene(idx, cumulative_time)
        cumulative_time += dur
    
    # 3. Render Outro
    render_outro()
    
    # 4. Concatenate all clips
    print("=" * 60)
    print("CONCATENATING ALL SCENES INTO FINAL VIDEO...")
    print("=" * 60)
    
    concat_list_file = os.path.join(r"c:\Users\ghana\Downloads\major project working\EVA\demo_video_gen", "concat_list.txt")
    clips = ["intro.mp4"] + [f"{ch['id']}.mp4" for ch in CHAPTERS] + ["outro.mp4"]
    
    with open(concat_list_file, "w", encoding="utf-8") as f:
        for c in clips:
            full_clip_path = os.path.join(CLIPS_DIR, c).replace("\\", "/")
            f.write(f"file '{full_clip_path}'\n")
    
    concat_cmd = [
        'ffmpeg', '-y',
        '-f', 'concat', '-safe', '0',
        '-i', concat_list_file,
        '-c', 'copy',
        FINAL_VIDEO
    ]
    
    subprocess.run(concat_cmd, check=True)
    
    # Get final video metadata
    dur_str = subprocess.check_output([
        'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1', FINAL_VIDEO
    ]).decode().strip()
    final_dur = float(dur_str)
    file_size_mb = os.path.getsize(FINAL_VIDEO) / (1024 * 1024)
    
    total_render_time = time.time() - start_all
    print("=" * 60)
    print("SUCCESS: EVA LIVE DEMONSTRATION VIDEO GENERATED!")
    print(f"Path: {FINAL_VIDEO}")
    print(f"Duration: {final_dur:.2f} seconds ({final_dur / 60:.2f} minutes)")
    print(f"File Size: {file_size_mb:.2f} MB")
    print(f"Resolution: {W}x{H} (1080p Full HD @ {FPS} fps)")
    print(f"Total Build Time: {total_render_time:.2f}s ({total_render_time / 60:.2f} min)")
    print("=" * 60)

if __name__ == '__main__':
    main()
