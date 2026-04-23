from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from .layout import Frame, Grid as FrameGrid
from .layout import HStack as FrameHStack
from .layout import Padding
from .layout import VStack as FrameVStack
from .pbir import Page, Visual


@dataclass
class LayoutNode:
    """Base type for nodes that compile into positioned visuals."""

    def resolve_visuals(self, frame: Frame) -> list[Visual]:
        raise NotImplementedError

    def apply_to(self, page: Page, frame: Frame) -> None:
        apply_layout(page, self, frame)


@dataclass
class VisualPlacement(LayoutNode):
    factory: Callable[..., Visual]
    args: tuple[Any, ...] = ()
    kwargs: dict[str, Any] = field(default_factory=dict)

    def resolve_visuals(self, frame: Frame) -> list[Visual]:
        visual = self.factory(
            frame.x,
            frame.y,
            frame.width,
            frame.height,
            *self.args,
            **self.kwargs,
        )
        return [visual]


@dataclass
class ContainerNode(LayoutNode):
    gap: float = 0
    padding: Padding | float = field(default_factory=Padding)
    children: list[LayoutNode] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.gap < 0:
            raise ValueError("Container gap must be non-negative")
        self.padding = _coerce_padding(self.padding)

    def add(self, child: LayoutNode) -> LayoutNode:
        self.children.append(child)
        return child

    def resolve_visuals(self, frame: Frame) -> list[Visual]:
        child_frames = self._child_frames(frame)
        visuals: list[Visual] = []
        for child, child_frame in zip(self.children, child_frames):
            visuals.extend(child.resolve_visuals(child_frame))
        return visuals

    def _child_frames(self, frame: Frame) -> list[Frame]:
        raise NotImplementedError


@dataclass
class HStackNode(ContainerNode):
    def _child_frames(self, frame: Frame) -> list[Frame]:
        return FrameHStack(
            x=frame.x,
            y=frame.y,
            width=frame.width,
            height=frame.height,
            gap=self.gap,
            padding=self.padding,
        ).resolve(len(self.children))


@dataclass
class VStackNode(ContainerNode):
    def _child_frames(self, frame: Frame) -> list[Frame]:
        return FrameVStack(
            x=frame.x,
            y=frame.y,
            width=frame.width,
            height=frame.height,
            gap=self.gap,
            padding=self.padding,
        ).resolve(len(self.children))


@dataclass
class GridNode(ContainerNode):
    rows: int = 1
    columns: int = 1

    def __post_init__(self) -> None:
        super().__post_init__()
        if self.rows <= 0 or self.columns <= 0:
            raise ValueError("Grid rows and columns must be positive")

    def _child_frames(self, frame: Frame) -> list[Frame]:
        return FrameGrid(
            x=frame.x,
            y=frame.y,
            width=frame.width,
            height=frame.height,
            rows=self.rows,
            columns=self.columns,
            gap=self.gap,
            padding=self.padding,
        ).resolve(len(self.children))


def apply_layout(page: Page, node: LayoutNode, frame: Frame) -> None:
    for visual in node.resolve_visuals(frame):
        visual.position.z = len(page.visuals)
        visual.position.tab_order = len(page.visuals)
        page.add_visual(visual)


def _coerce_padding(value: Padding | float) -> Padding:
    if isinstance(value, Padding):
        return value
    return Padding.all(value)
