import asyncio
import edge_tts
import os
import subprocess

CHAPTERS = [
    {
        'id': 'ch01',
        'title': 'System Architecture & Introduction',
        'command': 'EVA, initialize system and run diagnostics',
        'text': (
            'Welcome to the official live demonstration of EVA, an advanced desktop artificial intelligence '
            'assistant engineered specifically for Windows 10 and Windows 11 operating systems. EVA combines '
            'Google Gemini Live multi-modal foundation models with deep local system integration, a cybernetic '
            'heads-up display user interface, and an asynchronous task execution engine. Unlike conventional chatbots '
            'that run isolated in a browser sandbox, EVA operates directly on your physical computer. It captures '
            'microphone audio with sub-second streaming latency, inspects active desktop windows, controls low-level '
            'hardware settings, installs software autonomously without manual prompts, and executes complex multi-step '
            'workflows across applications. In this comprehensive walkthrough, we will demonstrate EVAs core system '
            'architecture, its reactive event loop, and its real-time operating system automation capabilities.'
        )
    },
    {
        'id': 'ch02',
        'title': 'The Cybernetic HUD & Audio Engine',
        'command': 'EVA, switch to live audio monitoring mode',
        'text': (
            'Here is EVAs desktop interface, designed as a futuristic cyberpunk heads-up display built using PyQt6. '
            'At the top of the interface, you can observe real-time system telemetry, continuously monitoring CPU '
            'utilization, available memory, active threads, and network latency. In the center, EVA features a dynamic '
            'multi-frequency audio visualizer that animates synchronously as you speak and as EVA delivers native audio '
            'feedback. The audio engine is engineered with hardware-accelerated dual-layer echo cancellation and an '
            'adaptive jitter buffer to eliminate voice stuttering. When you speak to EVA, audio chunks are streamed '
            'directly over bidirectional WebSockets to Gemini Live. EVAs intent router analyzes your query, acknowledges '
            'the command in under ten milliseconds, and dispatches native system tools without blocking the conversation flow.'
        )
    },
    {
        'id': 'ch03',
        'title': 'Windows OS & Hardware Automation',
        'command': 'EVA, set volume to 60 percent, brightness to 80, and tile active windows',
        'text': (
            'Now, let us examine how EVA controls Windows system hardware, peripherals, and desktop workspace layout. '
            'Through native Windows Core Audio APIs, WMI controllers, and display adapters, EVA executes hardware adjustments '
            'instantaneously without launching sluggish Windows Settings menus. For instance, when we command EVA to set master '
            'volume to sixty percent and adjust display brightness to eighty percent, the hardware parameters transition smoothly '
            'in milliseconds. Furthermore, EVA provides advanced window management and desktop ergonomics. When multiple '
            'applications clutter your screen, commanding EVA to organize the workspace triggers automated window enumeration, '
            'docking your code editor and web browser in a balanced side-by-side split view while minimizing distracting background windows.'
        )
    },
    {
        'id': 'ch04',
        'title': 'Zero-Permission Silent App Installation',
        'command': 'EVA, install VLC media player',
        'text': (
            'A major breakthrough in EVA is its automated, zero-permission application installer. In standard voice assistants, '
            'requesting software installation merely opens a web browser or redirects to the Microsoft Store, forcing users to '
            'manually click install, sign into accounts, and accept license agreements. In EVA, software installation is completely '
            'headless and automated. EVA maintains an instant catalog mapping over thirty popular desktop applications to verified '
            'package identifiers in zero seconds. It queries the Windows Registry in just twenty milliseconds to determine whether '
            'the application is already installed. When we instruct EVA to install VLC Media Player, it executes winget with silent '
            'unattended flags, streams live download percentages directly to the HUD status bar, and automatically launches the app upon completion.'
        )
    },
    {
        'id': 'ch05',
        'title': 'Universal Content & Media Downloader',
        'command': 'EVA, download an image of a red vintage sports car',
        'text': (
            'EVA is equipped with an intelligent universal media downloader capable of retrieving images, music tracks, videos, '
            'datasets, source code repositories, and documents from the web with pinpoint accuracy. Utilizing DuckDuckGo and Bing '
            'search backends with automated advertisement and tracker filtering, EVA discovers high-resolution direct source assets. '
            'Crucially, EVA respects user quantity limits, downloading exactly one target file by default rather than flooding your drive '
            'with duplicate batches unless you explicitly request more. Once the file finishes downloading, EVA immediately triggers an '
            'interactive Windows File Explorer reveal, highlighting the exact downloaded file so you never have to waste time searching through nested folders.'
        )
    },
    {
        'id': 'ch06',
        'title': 'Automated Document & PPT Generation',
        'command': 'EVA, generate a 5-slide presentation on AI in Healthcare with images',
        'text': (
            'EVA functions as an autonomous technical content creator, generating professionally styled Word documents, PowerPoint '
            'presentations, and PDF reports on demand. Rather than relying on slow external office applications, EVA compiles documents '
            'in-memory using python-docx, python-pptx, and ReportLab with microsecond compilation speeds. When requested to generate a '
            'five-slide presentation on Artificial Intelligence in Modern Healthcare, EVA drafts a structured narrative outline, formats '
            'headings and bullet hierarchies with modern color palettes, and autonomously queries the web to download relevant high-resolution '
            'medical diagrams, seamlessly embedding and centering them inside the slides with perfect alignment.'
        )
    },
    {
        'id': 'ch07',
        'title': 'Universal File Conversion & Processing',
        'command': 'EVA, convert quarterly project report docx to PDF',
        'text': (
            'Local data transformation is instantaneous using EVAs universal file controller. Users frequently need to transform documents '
            'between formats, such as converting Word docx files into publication-ready PDFs, exporting Excel spreadsheets into comma-separated '
            'values, or transcoding images across PNG, JPEG, and WebP formats. EVA executes these conversions locally with sub-second execution '
            'and zero cloud dependency. In addition, EVAs document intelligence engine ingests complex research papers, financial reports, '
            'and technical manuals, extracting tabular data and generating executive summaries through vector memory indexing and semantic search.'
        )
    },
    {
        'id': 'ch08',
        'title': 'Automated WhatsApp Messaging & Dispatch',
        'command': 'EVA, send the project report PDF to Alex on WhatsApp',
        'text': (
            'Collaboration and messaging are streamlined through EVAs hands-free WhatsApp automation module. Users can command EVA to compose '
            'and dispatch text messages, documents, spreadsheets, photos, and video recordings directly to WhatsApp contacts or specific phone '
            'numbers without touching the keyboard. For example, commanding EVA to send the newly generated project report to Alex triggers automated '
            'contact lookup, file attachment verification, and secure dispatch. EVA monitors delivery receipts in real time, alerting the user once the '
            'message and attachments are successfully delivered and acknowledged.'
        )
    },
    {
        'id': 'ch09',
        'title': 'Web Intelligence & Mobile Dashboard',
        'command': 'EVA, open mobile pairing QR and fetch flight status',
        'text': (
            'Beyond local desktop control, EVA excels at live web intelligence, flight tracking, and proactive assistance. It can query live '
            'commercial flight radars, deliver contextual multi-day weather forecasts, search technical documentation, and control media playback. '
            'EVA also maintains an autonomous background monitor that monitors system battery health, memory thresholds, and upcoming schedule alerts. '
            'To extend control beyond your desk, EVA includes a built-in FastAPI and WebSocket server. By scanning a secure QR code displayed on '
            'the HUD, you can pair your smartphone or tablet, giving you full remote control of your Windows PC from anywhere on your local network.'
        )
    },
    {
        'id': 'ch10',
        'title': 'Performance Benchmarks & Conclusion',
        'command': 'EVA, show performance benchmarks and test summary',
        'text': (
            'To ensure enterprise-grade stability and responsiveness, EVA has undergone comprehensive architectural optimization. We achieved '
            'a ninety-five percent reduction in command response latency, instant sub-ten-millisecond UI dispatch, and lightning-fast twenty-millisecond '
            'registry detection. The entire codebase is reinforced by an automated test suite comprising one hundred and fourteen unit and integration '
            'tests, running with a one hundred percent pass rate and zero regressions. With its fusion of multimodal intelligence, cybernetic aesthetics, '
            'and deep operating system automation, EVA represents the future of personal desktop computing. Thank you for watching the EVA live demonstration.'
        )
    }
]

out_dir = r'c:\Users\ghana\Downloads\major project working\EVA\demo_video_gen\audio'
os.makedirs(out_dir, exist_ok=True)

async def synth_all():
    total_dur = 0.0
    for ch in CHAPTERS:
        cid = ch['id']
        fname = os.path.join(out_dir, f"{cid}.mp3")
        comm = edge_tts.Communicate(ch['text'], 'en-US-ChristopherNeural')
        await comm.save(fname)
        dur_str = subprocess.check_output([
            'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1', fname
        ]).decode().strip()
        dur = float(dur_str)
        ch['duration'] = dur
        total_dur += dur
        print(f"[{cid}] {ch['title']}: {dur:.2f}s")
    
    print("-" * 50)
    print(f"TOTAL AUDIO DURATION: {total_dur:.2f}s ({total_dur / 60:.2f} minutes)")

if __name__ == '__main__':
    asyncio.run(synth_all())
