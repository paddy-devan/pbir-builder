from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from .layout import Frame
from .layout_tree import GridNode, HStackNode, VStackNode, VisualPlacement, apply_layout
from .pbir import Visual

if TYPE_CHECKING:
    from .layout import Padding
    from .pbir import Page, Report


@dataclass
class RootLayout:
    node: HStackNode | VStackNode | GridNode
    frame: Frame


@dataclass
class LayoutState:
    roots: list[RootLayout] = field(default_factory=list)


class LayoutContainerFacade:
    def __init__(self, page: "Page", node: HStackNode | VStackNode | GridNode):
        self._page = page
        self._node = node

    def add_hstack(self, gap: float = 0, padding: "Padding | float" = 0) -> "LayoutContainerFacade":
        node = HStackNode(gap=gap, padding=padding)
        self._node.add(node)
        return LayoutContainerFacade(self._page, node)

    def add_vstack(self, gap: float = 0, padding: "Padding | float" = 0) -> "LayoutContainerFacade":
        node = VStackNode(gap=gap, padding=padding)
        self._node.add(node)
        return LayoutContainerFacade(self._page, node)

    def add_grid(
        self,
        rows: int,
        columns: int,
        *,
        gap: float = 0,
        padding: "Padding | float" = 0,
    ) -> "LayoutContainerFacade":
        node = GridNode(rows=rows, columns=columns, gap=gap, padding=padding)
        self._node.add(node)
        return LayoutContainerFacade(self._page, node)

    def add_visual(self, factory: Any, *args: Any, **kwargs: Any) -> VisualPlacement:
        placement = VisualPlacement(factory, args=args, kwargs=kwargs)
        self._node.add(placement)
        return placement

    def add_line_chart(self, **kwargs: Any) -> VisualPlacement:
        return self.add_visual(Visual.line_chart, **kwargs)

    def add_bar_chart(self, **kwargs: Any) -> VisualPlacement:
        return self.add_visual(Visual.bar_chart, **kwargs)

    def add_clustered_column_chart(self, **kwargs: Any) -> VisualPlacement:
        return self.add_visual(Visual.clustered_column_chart, **kwargs)

    def add_card(self, **kwargs: Any) -> VisualPlacement:
        return self.add_visual(Visual.card, **kwargs)

    def add_slicer(self, **kwargs: Any) -> VisualPlacement:
        return self.add_visual(Visual.slicer, **kwargs)

    def add_table(self, **kwargs: Any) -> VisualPlacement:
        return self.add_visual(Visual.table, **kwargs)

    def add_matrix(self, **kwargs: Any) -> VisualPlacement:
        return self.add_visual(Visual.matrix, **kwargs)

    def add_shape(self, **kwargs: Any) -> VisualPlacement:
        return self.add_visual(Visual.shape, **kwargs)

    def add_image(self, image_path: str, **kwargs: Any) -> VisualPlacement:
        return self.add_visual(Visual.image, image_path, **kwargs)

    def add_text_box(self, text: str, **kwargs: Any) -> VisualPlacement:
        return self.add_visual(Visual.text_box, text, **kwargs)


def page_add_hstack(
    page: "Page",
    gap: float = 0,
    padding: "Padding | float" = 0,
    *,
    frame: Frame | None = None,
    x: float = 0,
    y: float = 0,
    width: float | None = None,
    height: float | None = None,
) -> LayoutContainerFacade:
    return _add_root_container(
        page,
        HStackNode(gap=gap, padding=padding),
        frame=frame,
        x=x,
        y=y,
        width=width,
        height=height,
    )


def page_add_vstack(
    page: "Page",
    gap: float = 0,
    padding: "Padding | float" = 0,
    *,
    frame: Frame | None = None,
    x: float = 0,
    y: float = 0,
    width: float | None = None,
    height: float | None = None,
) -> LayoutContainerFacade:
    return _add_root_container(
        page,
        VStackNode(gap=gap, padding=padding),
        frame=frame,
        x=x,
        y=y,
        width=width,
        height=height,
    )


def page_add_grid(
    page: "Page",
    rows: int,
    columns: int,
    *,
    gap: float = 0,
    padding: "Padding | float" = 0,
    frame: Frame | None = None,
    x: float = 0,
    y: float = 0,
    width: float | None = None,
    height: float | None = None,
) -> LayoutContainerFacade:
    return _add_root_container(
        page,
        GridNode(rows=rows, columns=columns, gap=gap, padding=padding),
        frame=frame,
        x=x,
        y=y,
        width=width,
        height=height,
    )


def materialize_report_layouts(report: "Report") -> None:
    for page in report.pages:
        _materialize_page_layouts(page)


def _add_root_container(
    page: "Page",
    node: HStackNode | VStackNode | GridNode,
    *,
    frame: Frame | None,
    x: float,
    y: float,
    width: float | None,
    height: float | None,
) -> LayoutContainerFacade:
    layout_frame = frame or Frame(
        x=x,
        y=y,
        width=page.width if width is None else width,
        height=page.height if height is None else height,
    )
    _get_layout_state(page).roots.append(RootLayout(node=node, frame=layout_frame))
    return LayoutContainerFacade(page, node)


def _materialize_page_layouts(page: "Page") -> None:
    state = getattr(page, "_layout_state", None)
    if state is None:
        return

    page.visuals = [
        visual for visual in page.visuals if not getattr(visual, "_from_layout_facade", False)
    ]
    for root in state.roots:
        start_index = len(page.visuals)
        apply_layout(page, root.node, root.frame)
        for visual in page.visuals[start_index:]:
            visual._from_layout_facade = True


def _get_layout_state(page: "Page") -> LayoutState:
    state = getattr(page, "_layout_state", None)
    if state is None:
        state = LayoutState()
        page._layout_state = state
    return state
