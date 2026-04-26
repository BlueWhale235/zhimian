import html
import uuid
from pathlib import Path
from typing import Any

import fitz

from .db import STATIC_DIR


def rel(path: Path) -> str:
    return path.relative_to(STATIC_DIR.parent).as_posix()


def make_thumbnail(pdf_path: Path) -> str | None:
    try:
        doc = fitz.open(pdf_path)
        page = doc.load_page(0)
        pix = page.get_pixmap(matrix=fitz.Matrix(0.35, 0.35), alpha=False)
        target = STATIC_DIR / "thumbnails" / f"{pdf_path.stem}.png"
        pix.save(target)
        doc.close()
        return rel(target)
    except Exception:
        return None


def profile_to_html(data: dict[str, Any]) -> str:
    personal = data.get("personal", {})
    sections = [
        ("教育背景", data.get("education", [])),
        ("实习经历", data.get("internships", [])),
        ("项目经历", data.get("projects", [])),
    ]
    summary = html.escape(str(data.get("summary", "")))
    section_html = ""
    for title, items in sections:
        rows = ""
        for item in items or []:
            rows += (
                "<div class='item'>"
                f"<h3>{html.escape(str(item.get('title', '')))}</h3>"
                f"<p>{html.escape(str(item.get('meta', '')))}</p>"
                f"<div>{html.escape(str(item.get('description', '')))}</div>"
                "</div>"
            )
        section_html += f"<section><h2>{title}</h2>{rows or '<p>暂无</p>'}</section>"
    return f"""
    <!doctype html>
    <html>
    <head>
      <meta charset="utf-8">
      <style>
        body {{ font-family: sans-serif; color: #1f2937; padding: 34px; }}
        h1 {{ margin: 0; font-size: 30px; }}
        .contact {{ color: #5f6b7a; margin: 8px 0 22px; }}
        h2 {{ border-bottom: 2px solid #2563eb; padding-bottom: 6px; margin-top: 24px; }}
        h3 {{ margin-bottom: 4px; }}
        .item {{ margin: 12px 0; }}
        p {{ margin: 4px 0; }}
      </style>
    </head>
    <body>
      <h1>{html.escape(str(personal.get('name', '未命名候选人')))}</h1>
      <div class="contact">
        {html.escape(str(personal.get('email', '')))} · {html.escape(str(personal.get('phone', '')))} · {html.escape(str(personal.get('city', '')))}
      </div>
      <section><h2>个人总结</h2><p>{summary or '暂无'}</p></section>
      {section_html}
    </body>
    </html>
    """


def export_profile_pdf(data: dict[str, Any]) -> tuple[str, str | None, str]:
    filename = f"online-resume-{uuid.uuid4().hex[:10]}.pdf"
    target = STATIC_DIR / "generated" / filename
    try:
        from weasyprint import HTML

        HTML(string=profile_to_html(data)).write_pdf(target)
    except Exception:
        export_profile_pdf_with_pymupdf(data, target)
    thumbnail = make_thumbnail(target)
    return filename, rel(target), thumbnail


def export_profile_pdf_with_pymupdf(data: dict[str, Any], target: Path) -> None:
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    y = 52
    personal = data.get("personal", {})
    lines = [
        str(personal.get("name") or "未命名候选人"),
        f"{personal.get('email', '')}  {personal.get('phone', '')}  {personal.get('city', '')}",
        "",
        "个人总结",
        str(data.get("summary") or "暂无"),
    ]
    for title, key in (("教育背景", "education"), ("实习经历", "internships"), ("项目经历", "projects")):
        lines.extend(["", title])
        for item in data.get(key, []) or []:
            lines.append(str(item.get("title", "")))
            lines.append(str(item.get("meta", "")))
            lines.append(str(item.get("description", "")))

    for index, line in enumerate(lines):
        if y > 790:
            page = doc.new_page(width=595, height=842)
            y = 52
        size = 20 if index == 0 else 12
        page.insert_textbox(
            fitz.Rect(48, y, 545, y + 42),
            line,
            fontsize=size,
            fontname="helv",
            color=(0.1, 0.13, 0.2),
        )
        y += 30 if size == 20 else 22
    doc.save(target)
    doc.close()
