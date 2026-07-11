from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.database import init_db
from app.services.kaggle_importer import import_kaggle_archive


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Importe l'archive Kaggle Resume Dataset dans SQLite et ChromaDB."
    )
    parser.add_argument("archive", help="Chemin vers archive.zip")
    parser.add_argument("--limit", type=int, default=None, help="Nombre max de CV a importer")
    parser.add_argument(
        "--category",
        action="append",
        default=[],
        help="Categorie a importer, option repetable. Exemple: --category INFORMATION-TECHNOLOGY",
    )
    parser.add_argument(
        "--no-index",
        action="store_true",
        help="Importe uniquement SQLite sans embeddings ChromaDB.",
    )
    args = parser.parse_args()

    init_db()
    categories = {category.upper() for category in args.category} or None
    stats = import_kaggle_archive(
        args.archive,
        limit=args.limit,
        categories=categories,
        index_chroma=not args.no_index,
    )
    print(f"Imported resumes: {stats.imported}")
    print(f"Indexed chunks: {stats.indexed_chunks}")
    print(f"Skipped rows: {stats.skipped}")


if __name__ == "__main__":
    main()

