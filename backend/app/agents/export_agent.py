"""Export Agent — renders a set of GeneratedDocument rows to the requested
export format. Deterministic — export is a formatting transform over
already-generated, already-reviewed content, not a content generation task,
so no LLM call is involved.
"""

import markdown as markdown_lib

from app.models.enums import ExportFormat

_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Documentation Export</title>
<style>
body {{ font-family: -apple-system, system-ui, sans-serif; max-width: 860px; margin: 2rem auto; padding: 0 1rem; line-height: 1.6; }}
pre {{ background: #f5f5f5; padding: 1rem; overflow-x: auto; border-radius: 6px; }}
code {{ background: #f5f5f5; padding: 0.15em 0.4em; border-radius: 4px; }}
h1, h2, h3 {{ border-bottom: 1px solid #e0e0e0; padding-bottom: 0.3em; }}
</style>
</head>
<body>
{body}
</body>
</html>
"""


def render_export(documents: dict[str, str], export_format: ExportFormat) -> bytes:
    """documents: DocumentType.value -> markdown content, already in the
    desired output order (the caller — ExportService — orders them per the
    canonical sequence from Step 1's "AI Documentation Generation" list).
    Returns the rendered file's raw bytes.
    """
    combined_markdown = "\n\n".join(
        f"# {doc_type.replace('_', ' ').title()}\n\n{content}"
        for doc_type, content in documents.items()
    )

    if export_format == ExportFormat.MARKDOWN:
        return combined_markdown.encode("utf-8")

    if export_format == ExportFormat.HTML:
        body_html = markdown_lib.markdown(
            combined_markdown, extensions=["fenced_code", "tables", "toc"]
        )
        return _HTML_TEMPLATE.format(body=body_html).encode("utf-8")

    if export_format == ExportFormat.PDF:
        # WeasyPrint needs system-level libraries (Cairo, Pango, GDK-Pixbuf)
        # that aren't part of a base Python image — see the `pdf-export`
        # apt packages installed in backend/Dockerfile. Imported lazily
        # (not at module top) so the rest of this module — and every other
        # export format — still works in an environment that hasn't
        # installed those system libraries (e.g. this sandbox).
        from weasyprint import HTML

        body_html = markdown_lib.markdown(
            combined_markdown, extensions=["fenced_code", "tables", "toc"]
        )
        full_html = _HTML_TEMPLATE.format(body=body_html)
        return HTML(string=full_html).write_pdf()

    raise ValueError(f"Unsupported export format: {export_format}")
