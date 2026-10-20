import re
from pathlib import Path

def generate_html_presentation():
    slides_dir = Path(__file__).resolve().parent
    md_file = slides_dir / "presentation_deck.md"
    html_file = slides_dir / "presentation_deck.html"

    with open(md_file, "r") as f:
        content = f.read()

    # Split into slides by '---'
    raw_slides = content.split("\n---\n")

    slides_html = []
    for idx, slide_text in enumerate(raw_slides):
        lines = slide_text.strip().split("\n")
        title = ""
        body_lines = []

        for line in lines:
            if line.startswith("# ") or line.startswith("## ") or line.startswith("### "):
                clean_title = re.sub(r"^#+\s*", "", line)
                if not title:
                    title = clean_title
                else:
                    body_lines.append(f"<h4 class='text-primary mt-3'>{clean_title}</h4>")
            elif line.startswith("- "):
                body_lines.append(f"<li>{line[2:]}</li>")
            elif line.startswith("  - "):
                body_lines.append(f"<li class='ms-4 text-muted'>{line[4:]}</li>")
            elif line.startswith("|"):
                # Table formatting
                body_lines.append(f"<div class='table-responsive my-2'>{line}</div>")
            elif line.strip():
                body_lines.append(f"<p>{line}</p>")

        # Clean lists
        body_content = "\n".join(body_lines)
        body_content = re.sub(r"(<li>.*</li>)", r"<ul class='slide-list'>\1</ul>", body_content)
        # Fix consecutive uls
        body_content = body_content.replace("</ul>\n<ul class='slide-list'>", "\n")

        slides_html.append(f"""
        <div class="slide {'active' if idx == 0 else ''}" id="slide-{idx}">
            <div class="slide-header d-flex justify-content-between align-items-center">
                <span class="badge bg-primary px-3 py-2">Smart OPD System</span>
                <span class="text-muted small">Slide {idx + 1} of {len(raw_slides)}</span>
            </div>
            <div class="slide-body mt-4">
                <h2 class="slide-title fw-bold text-dark border-bottom pb-2 mb-4">{title}</h2>
                <div class="slide-content fs-5 leading-relaxed">
                    {body_content}
                </div>
            </div>
        </div>
        """)

    full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Smart OPD Project Defense Presentation</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.2/font/bootstrap-icons.min.css">
    <style>
        body {{
            background-color: #0f172a;
            color: #1e293b;
            font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
            height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0;
            overflow: hidden;
        }}
        .deck-container {{
            width: 90vw;
            max-width: 1100px;
            height: 85vh;
            background: #ffffff;
            border-radius: 16px;
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
            display: flex;
            flex-column: column;
            padding: 40px;
            position: relative;
        }}
        .slide {{
            display: none;
            height: 100%;
            overflow-y: auto;
        }}
        .slide.active {{
            display: flex;
            flex-direction: column;
            animation: fadeIn 0.3s ease;
        }}
        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(10px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        .slide-list {{
            line-height: 1.8;
            font-size: 1.15rem;
        }}
        .nav-controls {{
            position: absolute;
            bottom: 25px;
            right: 40px;
            display: flex;
            gap: 10px;
        }}
        .progress-bar-container {{
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 5px;
            background-color: #e2e8f0;
            border-top-left-radius: 16px;
            border-top-right-radius: 16px;
        }}
        .progress-fill {{
            height: 100%;
            background-color: #0d6efd;
            transition: width 0.3s ease;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.95rem;
        }}
        th, td {{
            padding: 8px 12px;
            border: 1px solid #cbd5e1;
        }}
        th {{
            background-color: #f1f5f9;
        }}
    </style>
</head>
<body>
    <div class="deck-container">
        <div class="progress-bar-container">
            <div class="progress-fill" id="progressFill" style="width: {100 / len(raw_slides)}%;"></div>
        </div>

        {"".join(slides_html)}

        <div class="nav-controls">
            <button class="btn btn-outline-secondary" onclick="prevSlide()"><i class="bi bi-chevron-left me-1"></i> Prev</button>
            <button class="btn btn-primary" onclick="nextSlide()">Next <i class="bi bi-chevron-right ms-1"></i></button>
        </div>
    </div>

    <script>
        let currentSlide = 0;
        const totalSlides = {len(raw_slides)};

        function showSlide(index) {{
            if (index < 0 || index >= totalSlides) return;
            document.querySelectorAll('.slide').forEach(s => s.classList.remove('active'));
            document.getElementById(`slide-${{index}}`).classList.add('active');
            currentSlide = index;
            document.getElementById('progressFill').style.width = `${{((currentSlide + 1) / totalSlides) * 100}}%`;
        }}

        function nextSlide() {{
            if (currentSlide < totalSlides - 1) showSlide(currentSlide + 1);
        }}

        function prevSlide() {{
            if (currentSlide > 0) showSlide(currentSlide - 1);
        }}

        document.addEventListener('keydown', (e) => {{
            if (e.key === 'ArrowRight' || e.key === ' ') nextSlide();
            if (e.key === 'ArrowLeft') prevSlide();
        }});
    </script>
</body>
</html>
"""

    with open(html_file, "w") as f:
        f.write(full_html)
    print(f"✅ Generated Interactive HTML Slide Deck: {html_file}")

if __name__ == "__main__":
    generate_html_presentation()
