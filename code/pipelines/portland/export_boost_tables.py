# /// script
# requires-python = ">=3.12"
# dependencies = ["gerrytools==2.0.1"]
# ///
# NOTE: The comment above this line is used by uv to determine the Python version and dependencies
# required to run this script.
"""Export Portland focus-candidate boost matrices as colored LaTeX tables, PDFs, and PNGs."""

import argparse
import sys
from numbers import Real
from pathlib import Path

import numpy as np
import pandas as pd
from gerrytools.latex import TikzTable, latex_escape
from gerrytools.latex.formatters import highlight_between
from matplotlib import colormaps
from matplotlib.colors import Normalize

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from pipelines.portland.plots._boost_style import (
    BOOST_COLORMAP,
    FOCUS_CANDIDATES,
    HEATMAP_SIZE_INCHES,
    LABEL_FONT_SIZES,
    SLATE_COLORS,
    measure_heatmap_margins,
)
from voting_metrics_main_code.replication import ROOT


def build_boost_table(
    district: str, boost_df: pd.DataFrame, limit: float, *, show_numbers: bool = False
) -> TikzTable:
    """Build a LaTeX heatmap using the boost plotter's colors, typography, and geometry.

    Rows are mentioned candidates and columns are conditioning candidates. Colors use
    unrounded boosts on the PRGn scale and saturate outside [-limit, limit]. Undefined
    entries, including the diagonal, are blank white cells.

    Args:
        district (str): Portland district identifier used to select label font sizes.
        boost_df (pd.DataFrame): Square boost matrix with a (Slate, Candidate) row index.
            Slates 1 and 2 must appear in that order, with columns matching the row candidates.
        limit (float): Positive magnitude of the symmetric color scale.
        show_numbers (bool, optional): Display boosts to two decimal places with contrasting
            text. Defaults to False.

    Returns:
        TikzTable: Standalone table configured for TeX export and PDF/PNG rendering.

    Raises:
        ValueError: Rows and columns do not follow the same slate and candidate order.
        KeyError: A required slate or the district's font sizes are missing.
    """
    slates = [list(boost_df.xs(slate, level="Slate").index) for slate in (1, 2)]
    candidates = [candidate for slate in slates for candidate in slate]
    expected_index = [
        (slate_index, candidate)
        for slate_index, slate in enumerate(slates, 1)
        for candidate in slate
    ]
    if list(boost_df.index) != expected_index or list(boost_df.columns) != candidates:
        raise ValueError(
            "Boost matrix rows and columns must use the same ordered slate candidates."
        )

    candidate_count = len(candidates)
    first_slate_size = len(slates[0])
    table = TikzTable(boost_df.droplevel("Slate"), use_defaults=False)
    table.set_table_name(f"boost-{district}-{'numbers' if show_numbers else 'plain'}")
    table.remove_all_headers()
    configure_boost_cells(table, candidate_count, limit, show_numbers=show_numbers)
    add_candidate_labels(table, candidates, first_slate_size, district)
    add_matrix_grid(table, candidate_count, first_slate_size)

    document = table.document
    document.engine_preference_order = ("xelatex", "lualatex")
    document.add_packages(["fontspec", "graphicx"])
    document.add_color("slateone", SLATE_COLORS[0])
    document.add_color("slatetwo", SLATE_COLORS[1])
    document.add_command(r"\setmainfont{DejaVu Sans}")
    document.add_command(r"\setlength{\tabcolsep}{0pt}")
    margins = " ".join(f"{margin:.9f}in" for margin in measure_heatmap_margins(slates, district))
    document.add_command(rf"\standaloneconfig{{border={{{margins}}}}}")
    return table


def configure_boost_cells(
    table: TikzTable, candidate_count: int, limit: float, *, show_numbers: bool
) -> None:
    """Configure square PRGn cells with optional numbers and blank undefined entries."""
    cell_size_inches = HEATMAP_SIZE_INCHES / candidate_count
    cell_box = rf"\parbox[c][{cell_size_inches:.9f}in][c]{{{cell_size_inches:.9f}in}}"

    # An explicit empty box preserves the width of blank cells.
    blank_cell = rf"{cell_box}{{\centering\strut\mbox{{}}}}"
    colormap = colormaps[BOOST_COLORMAP]
    norm = Normalize(vmin=-limit, vmax=limit, clip=True)

    def format_boost(value: Real) -> str:
        boost = float(value)
        rgb = colormap(norm(boost), bytes=True)[:3]
        color = "#" + "".join(f"{channel:02x}" for channel in rgb)
        cell_content = r"\mbox{}"

        if show_numbers:
            brightness = np.dot(rgb, [0.2126, 0.7152, 0.0722])
            text_color = "white" if brightness < 128 else "black"
            cell_content = (
                rf"\textcolor{{{text_color}}}{{\fontsize{{18bp}}{{18bp}}"
                rf"\selectfont {boost:z.2f}}}"
            )

        rendered_cell = rf"{cell_box}{{\centering\strut{cell_content}}}"
        return highlight_between(boost, boost, color=color)(value, rendered_cell)[1]

    table.set_cell_space_limits("0pt")
    table.set_nan_string(blank_cell)
    table.set_number_formatter(format_boost)


def add_candidate_labels(
    table: TikzTable, candidates: list[str], first_slate_size: int, district: str
) -> None:
    """Place full row names and rotated column surnames at cell centers."""
    row_fontsize, column_fontsize = LABEL_FONT_SIZES[district]
    row_style = rf"\fontsize{{{row_fontsize}bp}}{{{row_fontsize}bp}}\selectfont\bfseries"
    column_style = rf"\fontsize{{{column_fontsize}bp}}{{{column_fontsize}bp}}\selectfont\bfseries"

    for index, candidate in enumerate(candidates, start=1):
        color = "slateone" if index <= first_slate_size else "slatetwo"
        full_name = latex_escape(candidate)
        surname = latex_escape(" ".join(candidate.split()[1:]))

        table.add_draw(
            rf"\node[anchor=east, inner sep=0pt, outer sep=0pt, text={color}] at "
            rf"($(row-{index}-|col-1)!0.5!(row-{index + 1}-|col-1)+(-8bp,0)$) "
            rf"{{{row_style} {full_name}}};"
        )
        # Anchor the rotated bounding box, as Matplotlib's default rotation mode does.
        table.add_draw(
            rf"\node[anchor=south west, inner sep=0pt, outer sep=0pt, text={color}] at "
            rf"($(row-1-|col-{index})!0.5!(row-1-|col-{index + 1})+(0,8bp)$) "
            rf"{{\rotatebox{{45}}{{{column_style} {surname}}}}};"
        )


def add_matrix_grid(table: TikzTable, candidate_count: int, first_slate_size: int) -> None:
    """Draw white cell borders, a black frame, and the two slate separators."""
    for index in range(2, candidate_count + 1):
        table.add_draw(
            rf"\draw[white, line width=1bp] (row-{index}-|col-1) -- "
            rf"(row-{index}-|col-{candidate_count + 1});"
        )
        table.add_draw(
            rf"\draw[white, line width=1bp] (row-1-|col-{index}) -- "
            rf"(row-{candidate_count + 1}-|col-{index});"
        )

    table.add_draw(
        rf"\draw[line width=1bp] (row-1-|col-1) rectangle "
        rf"(row-{candidate_count + 1}-|col-{candidate_count + 1});"
    )
    table.add_draw(
        rf"\draw[line width=6bp] (row-{first_slate_size + 1}-|col-1) -- "
        rf"(row-{first_slate_size + 1}-|col-{candidate_count + 1});"
    )
    table.add_draw(
        rf"\draw[line width=6bp] (row-1-|col-{first_slate_size + 1}) -- "
        rf"(row-{candidate_count + 1}-|col-{first_slate_size + 1});"
    )


def main() -> None:
    """Save standalone TeX sources and rendered tables from the exported boost matrices."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--district", choices=[*FOCUS_CANDIDATES, "all"], default="all")
    parser.add_argument("--stats-dir", type=Path, default=ROOT / "stats")
    parser.add_argument("--output-dir", type=Path, default=ROOT)
    parser.add_argument("--limit", type=float, default=0.21)
    args = parser.parse_args()

    if not np.isfinite(args.limit) or args.limit <= 0:
        parser.error("--limit must be finite and positive")

    output = args.output_dir.resolve() / "plots/portland/boost_tables"
    output.mkdir(parents=True, exist_ok=True)
    districts = list(FOCUS_CANDIDATES) if args.district == "all" else [args.district]

    for district in districts:
        boost_df = pd.read_csv(
            args.stats_dir / "portland_boost_matrices" / f"boost_matrix_{district}.csv",
            index_col=[0, 1],
        )

        for show_numbers, filename in (
            (False, f"TEX_{district}_boost_matrix"),
            (True, f"TEX_with_nums_{district}_boost_matrix"),
        ):
            table = build_boost_table(district, boost_df, args.limit, show_numbers=show_numbers)
            document = table.document
            destination = output / filename
            destination.with_suffix(".tex").write_text(document.to_tex(), encoding="utf-8")
            document.save_pdf(destination.with_suffix(".pdf"))
            document.save_png(destination.with_suffix(".png"))
            print(f"Saved {district} boost table: {destination}.{{tex,pdf,png}}")


if __name__ == "__main__":
    main()
