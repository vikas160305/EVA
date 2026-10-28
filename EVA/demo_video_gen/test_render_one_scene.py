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

os.makedirs(r"c:\Users\ghana\Downloads\major project working\EVA\demo_video_gen\clips", exist_ok=True)

def render_single_scene(ch_idx: int):
    ch = CHAPTERS[ch_idx]
    cid = ch['id']
    audio_file = os.path.join(r"c:\Users\ghana\Downloads\major project working\EVA\demo_video_gen\audio", f"{cid}.mp3")
    out_mp4 = os.path.join(r"c:\Users\ghana\Downloads\major project working\EVA\demo_video_gen\clips", f"{cid}.mp4")
    
    # Get exact audio duration
    dur_str = subprocess.check_output([
        'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1', audio_file
    ]).decode().strip()
    dur = float(dur_str)
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
        
        draw_header(draw, t, ch_idx, t)
        draw_sidebar(draw, ch_idx)
        draw_action_bar(draw, ch['command'], t, p)
        drawer(draw, t, dur, p)
        
        sub = get_subtitle_segment(ch['text'], p)
        draw_subtitles(draw, sub)
        
        proc.stdin.write(img.tobytes())
    
    proc.stdin.close()
    proc.wait()
    t1 = time.time()
    print(f"Scene {cid} rendered in {t1 - t0:.2f}s ({total_frames / (t1 - t0):.1f} fps) -> {out_mp4}")

if __name__ == '__main__':
    render_single_scene(0)
