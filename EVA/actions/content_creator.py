"""Create finished documents, presentations, PDFs, and source code from a request."""
from __future__ import annotations

import json
import html
import re
import tempfile
import time
import os
from pathlib import Path

import requests

from actions.file_controller import DocumentService


BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = Path.home() / "Documents" / "JARVIS Created"
CONTENT_MODELS = [
    "gemini-flash-latest",
    "gemini-3.8-flash",
    "gemini-flash-lite-latest",
    "gemini-3.5-flash",
    "gemini-3.6-flash",
]
CONTENT_MODEL = CONTENT_MODELS[0]

_CODE_EXTENSIONS = {
    "python": ".py", "javascript": ".js", "typescript": ".ts",
    "html": ".html", "css": ".css", "java": ".java", "c": ".c",
    "cpp": ".cpp", "c++": ".cpp", "csharp": ".cs", "go": ".go",
    "rust": ".rs", "php": ".php", "sql": ".sql", "powershell": ".ps1",
}
_TEXT_FORMATS = {"txt", "md", "html", "json"}


def _api_key() -> str:
    with open(BASE_DIR / "config" / "api_keys.json", encoding="utf-8") as f:
        return json.load(f)["gemini_api_key"]


def _safe_name(value: str, fallback: str = "jarvis_document") -> str:
    value = re.sub(r"[^A-Za-z0-9 _-]", "", value).strip().replace(" ", "_")
    return value[:60] or fallback


def _available_path(destination: Path, stem: str, extension: str) -> Path:
    """Avoid replacing a previous user-created file."""
    candidate = destination / f"{stem}.{extension}"
    if not candidate.exists():
        return candidate
    for index in range(2, 1000):
        candidate = destination / f"{stem}_{index}.{extension}"
        if not candidate.exists():
            return candidate
    raise RuntimeError("Too many files with the same name in the output folder.")


def _research(topic: str) -> str:
    """Use the project's grounded web search when freshness is requested."""
    try:
        from actions.web_search import web_search
        result = web_search({"query": topic, "mode": "research"})
        return result[:12000]
    except Exception as exc:
        return f"No web research available ({exc}). Use general knowledge and say so."


def _generate(prompt: str) -> str:
    from google import genai
    client = genai.Client(api_key=_api_key())
    
    candidate_models = list(CONTENT_MODELS)
    last_exc = None
    for model_name in candidate_models:
        for attempt in range(2):
            try:
                response = client.models.generate_content(model=model_name, contents=prompt)
                text = (response.text or "").strip()
                if text:
                    return text
            except Exception as exc:
                last_exc = exc
                err_msg = str(exc)
                if "503" in err_msg or "429" in err_msg:
                    time.sleep(1.0)
                    continue
                # For 404 or unsupported models, break to next candidate model
                break
    if last_exc:
        raise last_exc
    return ""


def _json_plan(request: str, format_name: str, research: str, count: int) -> dict:
    prompt = f'''Create a factual, well-structured plan for a {format_name}.
User request: {request}
Requested length/count: {count}
Research notes (may be empty): {research}
Return ONLY valid JSON with this exact shape:
{{"title":"...","subtitle":"...","sections":[{{"title":"...","points":["..."],"body":"...","image_query":"..."}}],"sources":["..."]}}
Create exactly {count} content sections for a presentation; for a document create 4-8 useful sections.
Each presentation section needs 3-5 concise points. Do not invent citations. Include source URLs only when present in research.'''
    raw = _generate(prompt)
    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(), flags=re.I)
    try:
        plan = json.loads(raw)
        if isinstance(plan.get("sections"), list) and plan["sections"]:
            plan.setdefault("title", _safe_name(request, "Untitled"))
            plan.setdefault("subtitle", "Created by JARVIS")
            plan.setdefault("sources", [])
            for section in plan["sections"]:
                if isinstance(section, dict):
                    section.setdefault("title", "Section")
                    section.setdefault("points", [])
                    section.setdefault("body", "")
                    section.setdefault("image_query", section["title"])
            return plan
    except json.JSONDecodeError:
        pass
    return {"title": _safe_name(request, "Untitled"), "subtitle": "Created by JARVIS", "sections": [
        {"title": "Overview", "points": [raw[:500] or request], "body": raw[:2500], "image_query": request}
    ], "sources": []}


def _fit_sections(plan: dict, count: int) -> list[dict]:
    """Guarantee a requested slide count even if an AI response is incomplete."""
    sections = [item for item in plan.get("sections", []) if isinstance(item, dict)]
    if not sections:
        sections = [{"title": "Overview", "points": [plan.get("title", "Overview")], "body": "", "image_query": ""}]
    while len(sections) < count:
        source = sections[-1]
        sections.append({
            "title": f"{source.get('title', 'Topic')} — continued",
            "points": list(source.get("points", [])),
            "body": source.get("body", ""),
            "image_query": source.get("image_query", ""),
        })
    return sections[:count]


def _wikimedia_image(query: str, folder: Path) -> Path | None:
    """Fetch one openly hosted thumbnail for a slide; failure is non-fatal."""
    try:
        response = requests.get(
            "https://commons.wikimedia.org/w/api.php",
            params={"action": "query", "generator": "search", "gsrsearch": query,
                    "gsrnamespace": 6, "gsrlimit": 1, "prop": "imageinfo",
                    "iiprop": "url", "iiurlwidth": 1200, "format": "json"}, timeout=12,
        )
        pages = response.json().get("query", {}).get("pages", {}).values()
        info = next(iter(pages), {}).get("imageinfo", [{}])[0]
        url = info.get("thumburl") or info.get("url")
        if not url:
            return None
        data = requests.get(url, timeout=18).content
        target = folder / f"image_{_safe_name(query, 'slide')}.jpg"
        target.write_bytes(data)
        return target
    except Exception:
        return None


def _create_docx(plan: dict, output: Path) -> None:
    from docx import Document
    from docx.shared import Inches, Pt
    doc = Document()
    section = doc.sections[0]
    section.top_margin = section.bottom_margin = Inches(0.8)
    style = doc.styles["Normal"]
    style.font.name, style.font.size = "Aptos", Pt(11)
    doc.add_heading(plan["title"], 0)
    if plan.get("subtitle"):
        doc.add_paragraph(plan["subtitle"])
    for item in plan["sections"]:
        doc.add_heading(item.get("title", "Section"), level=1)
        if item.get("body"):
            doc.add_paragraph(item["body"])
        for point in item.get("points", []):
            doc.add_paragraph(point, style="List Bullet")
    if plan.get("sources"):
        doc.add_heading("Sources", level=1)
        for source in plan["sources"]:
            doc.add_paragraph(source, style="List Bullet")
    doc.save(output)


def _create_pdf(plan: dict, output: Path) -> None:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, ListFlowable, ListItem
    styles = getSampleStyleSheet()
    story = [Paragraph(plan["title"], styles["Title"]), Spacer(1, 0.2 * inch)]
    for item in plan["sections"]:
        story += [Paragraph(item.get("title", "Section"), styles["Heading1"])]
        if item.get("body"):
            story += [Paragraph(item["body"], styles["BodyText"])]
        story += [ListFlowable([ListItem(Paragraph(p, styles["BodyText"])) for p in item.get("points", [])])]
        story += [Spacer(1, 0.12 * inch)]
    if plan.get("sources"):
        story += [Paragraph("Sources", styles["Heading1"])]
        story += [ListFlowable([ListItem(Paragraph(s, styles["BodyText"])) for s in plan["sources"]])]
    SimpleDocTemplate(str(output), pagesize=letter, rightMargin=54, leftMargin=54).build(story)


def _create_pptx(plan: dict, output: Path, total_slides: int, include_images: bool = False) -> None:
    from pptx import Presentation
    from pptx.util import Inches, Pt
    from pptx.enum.text import PP_ALIGN
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
    title = prs.slides.add_slide(prs.slide_layouts[0])
    title.shapes.title.text = plan["title"]
    title.placeholders[1].text = plan.get("subtitle", "Created by JARVIS")
    with tempfile.TemporaryDirectory() as temp:
        image_dir = Path(temp)
        for index, item in enumerate(_fit_sections(plan, max(1, total_slides - 1)), 1):
            slide = prs.slides.add_slide(prs.slide_layouts[5])
            heading = slide.shapes.add_textbox(Inches(0.6), Inches(0.35), Inches(12), Inches(0.7))
            heading.text_frame.text = item.get("title", f"Slide {index}")
            heading.text_frame.paragraphs[0].font.size = Pt(32)
            box = slide.shapes.add_textbox(Inches(0.75), Inches(1.35), Inches(6.0), Inches(5.5))
            frame = box.text_frame
            frame.word_wrap = True
            for point_index, point in enumerate(item.get("points", [])[:5]):
                para = frame.paragraphs[0] if point_index == 0 else frame.add_paragraph()
                para.text, para.level, para.font.size = str(point), 0, Pt(18)
            if include_images:
                image = _wikimedia_image(item.get("image_query") or item.get("title", ""), image_dir)
                if image:
                    try:
                        slide.shapes.add_picture(str(image), Inches(7.1), Inches(1.35), width=Inches(5.55), height=Inches(4.85))
                    except Exception:
                        pass
    prs.save(output)


def _create_text(plan: dict, output: Path, format_name: str) -> None:
    if format_name == "json":
        output.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
        return
    lines = [plan["title"], "", plan.get("subtitle", ""), ""]
    for item in plan["sections"]:
        heading = item.get("title", "Section")
        if format_name == "html":
            lines += [f"<h2>{html.escape(str(heading))}</h2>", f"<p>{html.escape(str(item.get('body', '')))}</p>", "<ul>"]
            lines += [f"<li>{html.escape(str(point))}</li>" for point in item.get("points", [])]
            lines += ["</ul>"]
        else:
            lines += [f"## {heading}", item.get("body", "")]
            lines += [f"- {point}" for point in item.get("points", [])]
            lines += [""]
    if plan.get("sources"):
        if format_name == "html":
            lines += ["<h2>Sources</h2>", "<ul>"]
            lines += [f"<li>{html.escape(str(source))}</li>" for source in plan["sources"]]
            lines += ["</ul>"]
        else:
            lines += ["## Sources", *[str(source) for source in plan["sources"]]]
    body = "\n".join(lines)
    if format_name == "html":
        output.write_text(
            "<!doctype html><html><head><meta charset=\"utf-8\"><title>"
            + html.escape(str(plan["title"]))
            + f"</title></head><body><h1>{html.escape(str(plan['title']))}</h1>"
            + f"<p>{html.escape(str(plan.get('subtitle', '')))}</p>"
            + body
            + "</body></html>",
            encoding="utf-8",
        )
    else:
        output.write_text(body, encoding="utf-8")


def _create_code(request: str, language: str, output: Path) -> None:
    prompt = f"""Write complete production-ready {language} code for this request: {request}
Return ONLY code, without Markdown fences. Include clear error handling and comments where useful."""
    code = re.sub(r"^```[\w+-]*\s*|\s*```$", "", _generate(prompt).strip(), flags=re.S)
    output.write_text(code, encoding="utf-8")


def content_creator(parameters: dict, response=None, player=None, session_memory=None, speak=None) -> str:
    params = parameters or {}
    request = str(params.get("request") or params.get("description") or "").strip()
    format_name = str(params.get("format", "")).lower().strip(". ")
    requested_code = format_name in {"code", "program", "script"}
    if not request:
        return "Please say what you want to create and the format, for example a PowerPoint, Word document, PDF, or code file."
    if format_name in {"ppt", "powerpoint", "slides"}: format_name = "pptx"
    if format_name in {"word", "document", "doc"}: format_name = "docx"
    if format_name in {"markdown", "text"}: format_name = "md" if format_name == "markdown" else "txt"
    language = str(params.get("language", "python")).lower()
    if requested_code:
        format_name = _CODE_EXTENSIONS.get(language, "." + _safe_name(language, "txt").lower()).lstrip(".")
    supported_code_extensions = {e.lstrip(".") for e in _CODE_EXTENSIONS.values()}
    if format_name not in {"pdf", "docx", "pptx", *_TEXT_FORMATS, *supported_code_extensions} and not requested_code:
        return "Supported creation formats are PDF, DOCX/Word, PPTX/PowerPoint, TXT, Markdown, HTML, JSON, and code languages."
    count = max(1, min(int(params.get("count", params.get("slides", 10))), 30))
    destination = Path(params.get("destination") or OUTPUT_DIR).expanduser()
    destination.mkdir(parents=True, exist_ok=True)

    service = DocumentService()
    output = service._next_safe_path(destination, _safe_name(params.get('name') or request), format_name)
    started_at = time.monotonic()
    if player:
        player.write_log(f"[content_creator] Creating {format_name.upper()} at {output}")
    try:
        tmp = service._atomic_tmp_path(output)
        if requested_code or (format_name in supported_code_extensions and format_name not in _TEXT_FORMATS):
            _create_code(request, language, tmp)
            service._validate_artifact(tmp, format_name)
            os.replace(tmp, output)
        else:
            research = _research(request) if params.get("research", True) else ""
            plan = _json_plan(request, format_name, research, max(1, count - 1) if format_name == "pptx" else count)
            if format_name == "docx":
                _create_docx(plan, tmp)
                service._validate_artifact(tmp, "docx")
                os.replace(tmp, output)
            elif format_name == "pdf":
                _create_pdf(plan, tmp)
                service._validate_artifact(tmp, "pdf")
                os.replace(tmp, output)
            elif format_name == "pptx":
                request_lower = request.casefold()
                include_images = any(word in request_lower for word in ("image", "images", "photo", "photos", "picture", "pictures", "visual"))
                _create_pptx(plan, tmp, count, include_images=include_images)
                service._validate_artifact(tmp, "pptx")
                os.replace(tmp, output)
            else:
                _create_text(plan, tmp, format_name)
                service._validate_artifact(tmp, format_name)
                os.replace(tmp, output)
        if not output.exists() or output.stat().st_size == 0:
            raise RuntimeError("The output file was not written correctly.")
        result = f"Created {format_name.upper()} file: {output} ({time.monotonic() - started_at:.1f}s)"
        if speak:
            speak(result)
        return result
    except Exception as exc:
        detail = f"{type(exc).__name__}: {exc}"
        print(f"[content_creator] FAILED — {detail}")
        if player:
            player.write_log(f"[content_creator] ERROR: {detail[:220]}")
        return f"Could not create the {format_name.upper()} file: {detail}"
