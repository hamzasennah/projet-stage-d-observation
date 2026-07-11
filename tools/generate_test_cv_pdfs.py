from __future__ import annotations

import argparse
import csv
import re
import textwrap
import unicodedata
import zipfile
from dataclasses import dataclass
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer


TARGET_COUNTS = {
    "high": 8,
    "medium": 7,
    "low": 5,
}

HIGH_CATEGORIES = {
    "INFORMATION-TECHNOLOGY",
    "BUSINESS-DEVELOPMENT",
    "ENGINEERING",
    "CONSULTANT",
}

MEDIUM_CATEGORIES = {
    "FINANCE",
    "ACCOUNTANT",
    "BANKING",
    "HR",
    "SALES",
}

LOW_CATEGORIES = {
    "CHEF",
    "FITNESS",
    "TEACHER",
    "ARTS",
    "APPAREL",
    "HEALTHCARE",
}

RELEVANCE_KEYWORDS = [
    "data",
    "analysis",
    "analyst",
    "analytics",
    "dashboard",
    "reporting",
    "kpi",
    "excel",
    "power bi",
    "sql",
    "database",
    "project",
    "business",
    "process",
    "supply chain",
    "logistics",
    "documentation",
    "requirements",
    "stakeholder",
    "python",
]


@dataclass(frozen=True)
class ResumeRow:
    source_id: str
    category: str
    text: str
    group: str
    score: int


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate anonymized PDF CVs for manual RAG testing.")
    parser.add_argument(
        "archive",
        nargs="?",
        default=r"C:\Users\pc\Desktop\archive.zip",
        help="Path to Kaggle archive.zip.",
    )
    parser.add_argument(
        "--output",
        default="output/pdf/test_cvs",
        help="Output directory for generated PDF CVs.",
    )
    args = parser.parse_args()

    archive_path = Path(args.archive)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    rows = load_rows(archive_path)
    selected = select_rows(rows)
    manifest_rows: list[dict[str, str | int]] = []

    for index, row in enumerate(selected, start=1):
        filename = (
            f"cv_test_{index:02d}_{row.group}_{safe_slug(row.category)}_{row.source_id}.pdf"
        )
        output_path = output_dir / filename
        build_pdf(output_path, index, row)
        manifest_rows.append(
            {
                "filename": filename,
                "candidate": f"Candidat Test {index:02d}",
                "source_id": row.source_id,
                "source_category": row.category,
                "relevance_group": row.group,
                "keyword_score": row.score,
            }
        )

    write_manifest(output_dir / "manifest.csv", manifest_rows)
    print(f"Generated {len(selected)} PDF CVs in {output_dir.resolve()}")


def load_rows(archive_path: Path) -> list[ResumeRow]:
    if not archive_path.exists():
        raise FileNotFoundError(f"Archive not found: {archive_path}")

    rows: list[ResumeRow] = []
    with zipfile.ZipFile(archive_path) as archive:
        with archive.open("Resume/Resume.csv") as handle:
            decoded = (line.decode("utf-8", errors="replace") for line in handle)
            reader = csv.DictReader(decoded)
            for item in reader:
                source_id = str(item.get("ID") or "").strip()
                category = str(item.get("Category") or "").strip().upper()
                text = clean_text(str(item.get("Resume_str") or ""))
                if not source_id or not category or len(text) < 900:
                    continue
                group = classify_category(category)
                if not group:
                    continue
                rows.append(
                    ResumeRow(
                        source_id=source_id,
                        category=category,
                        text=text,
                        group=group,
                        score=keyword_score(text),
                    )
                )
    return rows


def select_rows(rows: list[ResumeRow]) -> list[ResumeRow]:
    selected: list[ResumeRow] = []
    used_ids: set[str] = set()
    for group, count in TARGET_COUNTS.items():
        candidates = [
            row for row in rows if row.group == group and row.source_id not in used_ids
        ]
        reverse = group != "low"
        candidates.sort(key=lambda row: (row.score, row.category, row.source_id), reverse=reverse)
        for row in candidates[:count]:
            selected.append(row)
            used_ids.add(row.source_id)
    selected.sort(key=lambda row: ({"high": 0, "medium": 1, "low": 2}[row.group], row.category, row.source_id))
    return selected


def classify_category(category: str) -> str | None:
    if category in HIGH_CATEGORIES:
        return "high"
    if category in MEDIUM_CATEGORIES:
        return "medium"
    if category in LOW_CATEGORIES:
        return "low"
    return None


def keyword_score(text: str) -> int:
    normalized = text.lower()
    return sum(normalized.count(keyword) for keyword in RELEVANCE_KEYWORDS)


def build_pdf(path: Path, index: int, row: ResumeRow) -> None:
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "CvTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#17332b"),
        spaceAfter=6,
    )
    meta_style = ParagraphStyle(
        "Meta",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#4b5f58"),
        spaceAfter=12,
    )
    heading_style = ParagraphStyle(
        "Heading",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        textColor=colors.HexColor("#1f6a58"),
        spaceBefore=10,
        spaceAfter=5,
    )
    body_style = ParagraphStyle(
        "Body",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=13.2,
        textColor=colors.HexColor("#1f2925"),
        spaceAfter=7,
    )

    doc = SimpleDocTemplate(
        str(path),
        pagesize=A4,
        rightMargin=1.45 * cm,
        leftMargin=1.45 * cm,
        topMargin=1.25 * cm,
        bottomMargin=1.25 * cm,
        title=f"CV Test {index:02d}",
        author="Generated anonymized test dataset",
    )

    story = [
        Paragraph(f"Candidat Test {index:02d}", title_style),
        Paragraph(
            (
                f"Profil anonymise pour test RAG | Categorie source: {row.category} | "
                f"Niveau attendu: {row.group.upper()} | Email: candidat.test{index:02d}@example.com"
            ),
            meta_style,
        ),
        Paragraph("Resume professionnel", heading_style),
    ]

    sections = split_into_sections(row.text)
    for section_index, paragraph in enumerate(sections, start=1):
        if section_index == 2:
            story.append(Paragraph("Experience et competences extraites", heading_style))
        if section_index == 5:
            story.append(Paragraph("Informations complementaires", heading_style))
        story.append(Paragraph(escape_xml(paragraph), body_style))
        story.append(Spacer(1, 2))

    doc.build(story)


def split_into_sections(text: str) -> list[str]:
    wrapped = textwrap.wrap(text, width=850, break_long_words=False, replace_whitespace=False)
    return wrapped[:10]


def clean_text(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"\b[\w.+-]+@[\w.-]+\.\w+\b", " email@example.com ", text)
    text = re.sub(r"https?://\S+|www\.\S+", " portfolio.example.com ", text)
    text = re.sub(r"(?<!\w)(?:\+?\d[\d().\-\s]{7,}\d)(?!\w)", " 000-000-0000 ", text)
    text = text.replace("\u2022", " - ")
    text = text.replace("\u2013", "-").replace("\u2014", "-")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def escape_xml(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def safe_slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def write_manifest(path: Path, rows: list[dict[str, str | int]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "filename",
                "candidate",
                "source_id",
                "source_category",
                "relevance_group",
                "keyword_score",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
