#!/usr/bin/env python3
"""Update an existing clip review workbook with Supabase rating data."""
from __future__ import annotations

import argparse
from pathlib import Path

from db import fetch_all_ratings, fetch_rating_summary
from excel_export import update_workbook_with_rating_summary


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Append/update average ratings and add an Individual Ratings tab to an existing workbook."
    )
    parser.add_argument("input_xlsx", help="Path to the existing visualization workbook.")
    parser.add_argument(
        "output_xlsx",
        nargs="?",
        help="Path for the updated workbook. Defaults to '<input>_with_ratings.xlsx'.",
    )
    args = parser.parse_args()

    input_path = Path(args.input_xlsx).expanduser().resolve()
    if not input_path.exists():
        raise FileNotFoundError(f"Workbook not found: {input_path}")

    output_path = (
        Path(args.output_xlsx).expanduser().resolve()
        if args.output_xlsx
        else input_path.with_name(f"{input_path.stem}_with_ratings{input_path.suffix}")
    )

    rating_summary = fetch_rating_summary()
    individual_ratings = fetch_all_ratings()
    updated_rows = update_workbook_with_rating_summary(
        input_path,
        output_path,
        rating_summary,
        individual_ratings,
    )
    print(f"Updated {updated_rows} clip rows")
    print(f"Included {len(individual_ratings)} individual rating rows")
    print(f"Saved: {output_path}")


if __name__ == "__main__":
    main()
