"""
pptx_lib.grid — Grid-based layout system for consistent alignment.

ContentGrid divides a rectangular region into rows and columns with explicit
gaps.  Every element on the slide fetches its position from the grid, so
cards, banners, and connectors are guaranteed to align.

Usage:
    from .grid import ContentGrid
    from .constants import FREE_LEFT, FREE_TOP, FREE_WIDTH, FREE_HEIGHT

    grid = ContentGrid(
        left=FREE_LEFT, top=FREE_TOP,
        width=FREE_WIDTH, height=FREE_HEIGHT,
        cols=2, rows=2,
        col_gap=Cm(0.5), row_gap=Cm(0.5),
        banner_height=Cm(2.1), banner_gap=Cm(0.3),
    )

    # Get a single cell (col, row) — 0-indexed
    left, top, w, h = grid.cell(0, 0)

    # Get a merged region spanning multiple cells
    left, top, w, h = grid.region(col=0, row=0, colspan=2, rowspan=1)

    # Get the banner region — always matches the grid's outer edges
    left, top, w, h = grid.banner()

    # Get a gap chevron position between two columns
    center_x, center_y, gap_width = grid.col_gap_center(col_left=0, row=0)
"""

from __future__ import annotations

from pptx.util import Cm, Emu


class ContentGrid:
    """Divide a content region into an aligned grid of cells.

    Parameters
    ----------
    left, top, width, height : EMU-compatible
        Outer bounds of the content area (typically FREE_LEFT/TOP/WIDTH/HEIGHT).
    cols, rows : int
        Number of columns and rows.
    col_gap, row_gap : EMU-compatible
        Gap between adjacent columns / rows.
    banner_height : EMU-compatible or None
        If set, reserve space at the bottom for a banner/takeaway box.
        The grid cells shrink accordingly.
    banner_gap : EMU-compatible
        Vertical gap between the last row and the banner.
    padding : EMU-compatible
        Inner padding on all four sides of the grid (shrinks the usable area
        symmetrically).  Default ``Cm(0)`` — no extra padding beyond what
        ``left``/``top`` already define.
    """

    def __init__(
        self,
        left,
        top,
        width,
        height,
        cols: int = 1,
        rows: int = 1,
        col_gap=Cm(0.5),
        row_gap=Cm(0.5),
        banner_height=None,
        banner_gap=Cm(0.3),
        padding=Cm(0),
    ):
        self._outer_left = int(left)
        self._outer_top = int(top)
        self._outer_width = int(width)
        self._outer_height = int(height)

        pad = int(padding)
        self._left = self._outer_left + pad
        self._top = self._outer_top + pad
        self._width = self._outer_width - 2 * pad
        self._total_height = self._outer_height - 2 * pad

        self.cols = max(cols, 1)
        self.rows = max(rows, 1)
        self._col_gap = int(col_gap)
        self._row_gap = int(row_gap)

        # Banner reservation
        self._banner_h = int(banner_height) if banner_height else 0
        self._banner_gap = int(banner_gap) if self._banner_h else 0
        self._grid_height = self._total_height - self._banner_h - self._banner_gap

        # Pre-compute column geometry
        total_col_gaps = self._col_gap * (self.cols - 1)
        self._col_w = (self._width - total_col_gaps) // self.cols

        # Pre-compute row geometry
        total_row_gaps = self._row_gap * (self.rows - 1)
        self._row_h = (self._grid_height - total_row_gaps) // self.rows

    # ── Accessors ──────────────────────────────────────────────────────────

    @property
    def grid_left(self) -> int:
        """Left edge of the grid (EMU)."""
        return self._left

    @property
    def grid_top(self) -> int:
        """Top edge of the grid (EMU)."""
        return self._top

    @property
    def grid_width(self) -> int:
        """Total width of the grid (EMU)."""
        return self._width

    @property
    def grid_height(self) -> int:
        """Height of the grid area *excluding* the banner (EMU)."""
        return self._grid_height

    @property
    def col_width(self) -> int:
        """Width of a single column (EMU)."""
        return self._col_w

    @property
    def row_height(self) -> int:
        """Height of a single row (EMU)."""
        return self._row_h

    # ── Cell / Region ──────────────────────────────────────────────────────

    def _col_left(self, col: int) -> int:
        return self._left + col * (self._col_w + self._col_gap)

    def _row_top(self, row: int) -> int:
        return self._top + row * (self._row_h + self._row_gap)

    def cell(self, col: int, row: int) -> tuple[int, int, int, int]:
        """Return (left, top, width, height) in EMU for a single cell."""
        if col < 0 or col >= self.cols:
            raise IndexError(f"col {col} out of range 0..{self.cols - 1}")
        if row < 0 or row >= self.rows:
            raise IndexError(f"row {row} out of range 0..{self.rows - 1}")
        return (
            Emu(self._col_left(col)),
            Emu(self._row_top(row)),
            Emu(self._col_w),
            Emu(self._row_h),
        )

    def region(
        self,
        col: int = 0,
        row: int = 0,
        colspan: int = 1,
        rowspan: int = 1,
    ) -> tuple[int, int, int, int]:
        """Return (left, top, width, height) for a merged multi-cell area."""
        end_col = col + colspan - 1
        end_row = row + rowspan - 1
        if end_col >= self.cols:
            raise IndexError(f"colspan {colspan} at col {col} exceeds {self.cols} columns")
        if end_row >= self.rows:
            raise IndexError(f"rowspan {rowspan} at row {row} exceeds {self.rows} rows")
        left = self._col_left(col)
        top = self._row_top(row)
        right = self._col_left(end_col) + self._col_w
        bottom = self._row_top(end_row) + self._row_h
        return Emu(left), Emu(top), Emu(right - left), Emu(bottom - top)

    # ── Banner ─────────────────────────────────────────────────────────────

    def banner(self) -> tuple[int, int, int, int]:
        """Return (left, top, width, height) for the bottom banner.

        Raises ValueError if no banner_height was configured.
        """
        if not self._banner_h:
            raise ValueError("No banner_height configured for this grid.")
        banner_top = self._top + self._grid_height + self._banner_gap
        return (
            Emu(self._left),
            Emu(banner_top),
            Emu(self._width),
            Emu(self._banner_h),
        )

    def has_banner(self) -> bool:
        return self._banner_h > 0

    # ── Gap helpers ────────────────────────────────────────────────────────

    def col_gap_center(
        self,
        col_left: int,
        row: int = 0,
        rowspan: int = 1,
    ) -> tuple[int, int, int]:
        """Center point and width of the gap between col_left and col_left+1.

        Returns (center_x, center_y, gap_width) in EMU.
        Useful for placing chevron connectors between columns.
        """
        if col_left < 0 or col_left >= self.cols - 1:
            raise IndexError(f"col_left {col_left} invalid for {self.cols}-column grid")
        right_edge = self._col_left(col_left) + self._col_w
        next_left = self._col_left(col_left + 1)
        cx = right_edge + (next_left - right_edge) // 2

        row_t = self._row_top(row)
        end_row = row + rowspan - 1
        row_b = self._row_top(end_row) + self._row_h
        cy = row_t + (row_b - row_t) // 2

        return Emu(cx), Emu(cy), Emu(self._col_gap)

    def row_gap_center(
        self,
        row_top: int,
        col: int = 0,
        colspan: int = 1,
    ) -> tuple[int, int, int]:
        """Center point and height of the gap between row_top and row_top+1.

        Returns (center_x, center_y, gap_height) in EMU.
        """
        if row_top < 0 or row_top >= self.rows - 1:
            raise IndexError(f"row_top {row_top} invalid for {self.rows}-row grid")
        bottom_edge = self._row_top(row_top) + self._row_h
        next_top = self._row_top(row_top + 1)
        cy = bottom_edge + (next_top - bottom_edge) // 2

        col_l = self._col_left(col)
        end_col = col + colspan - 1
        col_r = self._col_left(end_col) + self._col_w
        cx = col_l + (col_r - col_l) // 2

        return Emu(cx), Emu(cy), Emu(self._row_gap)

    # ── Label row helpers ──────────────────────────────────────────────────

    def label_column(
        self,
        width=Cm(2.0),
        align: str = "left",
    ) -> tuple[int, int, int]:
        """Return (left, width, remaining_grid_left) for a label column
        placed outside the grid on the specified side.

        Useful for "Before" / "After" row labels that sit left of the cards.
        After calling this, shift grid left/width to start after the label.
        """
        if align == "left":
            lbl_left = self._left
            new_left = self._left + int(width) + self._col_gap
            return Emu(lbl_left), Emu(int(width)), Emu(new_left)
        else:
            lbl_left = self._left + self._width - int(width)
            return Emu(lbl_left), Emu(int(width)), Emu(self._left)

    # ── String repr ────────────────────────────────────────────────────────

    def __repr__(self) -> str:
        return (
            f"ContentGrid({self.cols}x{self.rows}, "
            f"cell={self._col_w}x{self._row_h} EMU, "
            f"gaps={self._col_gap}/{self._row_gap}, "
            f"banner={'yes' if self._banner_h else 'no'})"
        )
