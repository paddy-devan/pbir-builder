from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Padding:
    top: float = 0
    right: float = 0
    bottom: float = 0
    left: float = 0

    def __post_init__(self) -> None:
        for value in (self.top, self.right, self.bottom, self.left):
            if value < 0:
                raise ValueError("Padding values must be non-negative")

    @classmethod
    def all(cls, value: float) -> "Padding":
        return cls(top=value, right=value, bottom=value, left=value)

    @classmethod
    def symmetric(cls, *, horizontal: float = 0, vertical: float = 0) -> "Padding":
        return cls(
            top=vertical,
            right=horizontal,
            bottom=vertical,
            left=horizontal,
        )

    @property
    def horizontal(self) -> float:
        return self.left + self.right

    @property
    def vertical(self) -> float:
        return self.top + self.bottom


@dataclass(frozen=True)
class Frame:
    x: float
    y: float
    width: float
    height: float

    def __post_init__(self) -> None:
        if self.width < 0 or self.height < 0:
            raise ValueError("Frame dimensions must be non-negative")


@dataclass
class LayoutContainer:
    x: float
    y: float
    width: float
    height: float
    gap: float = 0
    padding: Padding | float = field(default_factory=Padding)

    def __post_init__(self) -> None:
        if self.width < 0 or self.height < 0:
            raise ValueError("Container dimensions must be non-negative")
        if self.gap < 0:
            raise ValueError("Container gap must be non-negative")
        self.padding = _coerce_padding(self.padding)

    @property
    def frame(self) -> Frame:
        return Frame(self.x, self.y, self.width, self.height)

    @property
    def inner_frame(self) -> Frame:
        padding = self.padding
        inner_width = self.width - padding.horizontal
        inner_height = self.height - padding.vertical
        if inner_width < 0 or inner_height < 0:
            raise ValueError("Padding exceeds the available container size")
        return Frame(
            x=self.x + padding.left,
            y=self.y + padding.top,
            width=inner_width,
            height=inner_height,
        )

    def resolve(self, item_count: int) -> list[Frame]:
        raise NotImplementedError

    def _resolve_grid(
        self,
        *,
        item_count: int,
        rows: int,
        columns: int,
        name: str,
    ) -> list[Frame]:
        _validate_item_count(item_count)
        _validate_grid_shape(rows, columns)

        capacity = rows * columns
        if item_count > capacity:
            raise ValueError(f"{name} capacity exceeded: got {item_count} items for {rows}x{columns}")
        if item_count == 0:
            return []

        inner = self.inner_frame
        available_width = inner.width - self.gap * (columns - 1)
        available_height = inner.height - self.gap * (rows - 1)
        if available_width < 0 or available_height < 0:
            raise ValueError(f"Gap exceeds the available size for this {name}")

        cell_width = available_width / columns
        cell_height = available_height / rows
        frames = []
        for index in range(item_count):
            row = index // columns
            column = index % columns
            frames.append(
                Frame(
                    x=inner.x + column * (cell_width + self.gap),
                    y=inner.y + row * (cell_height + self.gap),
                    width=cell_width,
                    height=cell_height,
                )
            )
        return frames


@dataclass
class HStack(LayoutContainer):
    def resolve(self, item_count: int) -> list[Frame]:
        return self._resolve_grid(item_count=item_count, rows=1, columns=max(1, item_count), name="HStack")


@dataclass
class VStack(LayoutContainer):
    def resolve(self, item_count: int) -> list[Frame]:
        return self._resolve_grid(item_count=item_count, rows=max(1, item_count), columns=1, name="VStack")


@dataclass
class Grid(LayoutContainer):
    rows: int = 1
    columns: int = 1

    def __post_init__(self) -> None:
        super().__post_init__()
        _validate_grid_shape(self.rows, self.columns)

    def resolve(self, item_count: int) -> list[Frame]:
        return self._resolve_grid(
            item_count=item_count,
            rows=self.rows,
            columns=self.columns,
            name="Grid",
        )


def _coerce_padding(value: Padding | float) -> Padding:
    if isinstance(value, Padding):
        return value
    return Padding.all(value)


def _validate_item_count(item_count: int) -> None:
    if item_count < 0:
        raise ValueError("Item count must be non-negative")


def _validate_grid_shape(rows: int, columns: int) -> None:
    if rows <= 0 or columns <= 0:
        raise ValueError("Grid rows and columns must be positive")
