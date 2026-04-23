from __future__ import annotations

import json
import re
import secrets
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


PBIP_SCHEMA = (
    "https://developer.microsoft.com/json-schemas/fabric/pbip/"
    "pbipProperties/1.0.0/schema.json"
)
PBIR_SCHEMA = (
    "https://developer.microsoft.com/json-schemas/fabric/item/report/"
    "definitionProperties/2.0.0/schema.json"
)
REPORT_SCHEMA = (
    "https://developer.microsoft.com/json-schemas/fabric/item/report/"
    "definition/report/3.2.0/schema.json"
)
VERSION_SCHEMA = (
    "https://developer.microsoft.com/json-schemas/fabric/item/report/"
    "definition/versionMetadata/1.0.0/schema.json"
)
PAGES_SCHEMA = (
    "https://developer.microsoft.com/json-schemas/fabric/item/report/"
    "definition/pagesMetadata/1.0.0/schema.json"
)
PAGE_SCHEMA = (
    "https://developer.microsoft.com/json-schemas/fabric/item/report/"
    "definition/page/2.1.0/schema.json"
)
VISUAL_SCHEMA = (
    "https://developer.microsoft.com/json-schemas/fabric/item/report/"
    "definition/visualContainer/2.8.0/schema.json"
)
DEFAULT_THEME_NAME = "CY26SU04"
DEFAULT_THEME_SOURCE = None


def _new_name() -> str:
    """Return a Power BI-style opaque object name."""
    return secrets.token_hex(10)


def _artifact_name(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "_", value.strip()).strip("_")
    return cleaned or "Report"


def _literal(value: str | int | float) -> dict[str, Any]:
    if isinstance(value, str):
        literal_value = f"'{value}'"
    elif isinstance(value, float):
        literal_value = f"{value}D"
    else:
        literal_value = str(value)
    return {"expr": {"Literal": {"Value": literal_value}}}


def _numeric_literal(value: str | int | float) -> dict[str, Any]:
    if isinstance(value, str):
        literal_value = value
    else:
        literal_value = f"{value}D"
    return {"expr": {"Literal": {"Value": literal_value}}}


def _bool_literal(value: bool) -> dict[str, Any]:
    return {"expr": {"Literal": {"Value": str(value).lower()}}}


def _solid_color(value: str) -> dict[str, Any]:
    return {"solid": {"color": _literal(value)}}


def _resource_package_item(registered_name: str) -> dict[str, Any]:
    return {
        "expr": {
            "ResourcePackageItem": {
                "PackageName": "RegisteredResources",
                "PackageType": 1,
                "ItemName": registered_name,
            }
        }
    }


def _resource_image(
    display_name: str,
    registered_name: str,
    scaling: str,
) -> dict[str, Any]:
    return {
        "name": _literal(display_name),
        "url": _resource_package_item(registered_name),
        "scaling": _literal(scaling),
    }


def _new_resource_name(path: Path) -> str:
    stem = _artifact_name(path.stem)
    return f"{stem}{secrets.randbelow(10**16)}{path.suffix}"


@dataclass(frozen=True)
class FieldRef:
    entity: str
    property: str


@dataclass(frozen=True)
class MeasureRef:
    entity: str
    property: str


@dataclass(frozen=True)
class VisualBinding:
    """Base type for future visual binding models."""


@dataclass(frozen=True)
class CartesianBinding(VisualBinding):
    category: FieldRef | None = None
    values: tuple[MeasureRef, ...] = ()
    series: FieldRef | None = None
    tooltips: tuple[FieldRef | MeasureRef, ...] = ()


@dataclass(frozen=True)
class SummaryBinding(VisualBinding):
    value: MeasureRef | None = None
    target: MeasureRef | None = None
    trend: FieldRef | None = None
    tooltips: tuple[FieldRef | MeasureRef, ...] = ()


@dataclass(frozen=True)
class TabularBinding(VisualBinding):
    rows: tuple[FieldRef, ...] = ()
    columns: tuple[FieldRef, ...] = ()
    values: tuple[FieldRef | MeasureRef, ...] = ()
    tooltips: tuple[FieldRef | MeasureRef, ...] = ()


@dataclass(frozen=True)
class SlicerBinding(VisualBinding):
    values: tuple[FieldRef, ...] = ()


@dataclass
class Position:
    x: float
    y: float
    width: float
    height: float
    z: int = 0
    tab_order: int = 0

    def to_pbir(self) -> dict[str, Any]:
        return {
            "x": self.x,
            "y": self.y,
            "z": self.z,
            "height": self.height,
            "width": self.width,
            "tabOrder": self.tab_order,
        }


@dataclass
class PageBackground:
    image_path: Path
    registered_name: str
    scaling: str = "Fill"
    transparency: str | int | float = "0D"

    @property
    def display_name(self) -> str:
        return self.image_path.name

    def to_pbir_properties(self) -> dict[str, Any]:
        return {
            "image": {
                "image": _resource_image(
                    self.display_name,
                    self.registered_name,
                    self.scaling,
                )
            },
            "transparency": _numeric_literal(self.transparency),
        }


@dataclass
class GeneralFormatting:
    padding: str | int | float | None = None
    padding_top: str | int | float | None = None
    padding_right: str | int | float | None = None
    padding_bottom: str | int | float | None = None
    padding_left: str | int | float | None = None
    title: str | None = None
    title_show: bool | None = None
    title_font_size: str | int | float | None = None
    title_font_family: str | None = None
    title_font_color: str | None = None
    background_show: bool | None = None
    background_color: str | None = None
    background_transparency: str | int | float | None = None
    border_show: bool | None = None
    border_color: str | None = None
    border_radius: str | int | float | None = None

    def to_visual_container_objects(self) -> dict[str, Any]:
        objects: dict[str, Any] = {}

        title_properties = self._title_properties()
        if title_properties:
            objects["title"] = [{"properties": title_properties}]

        background_properties = self._background_properties()
        if background_properties:
            objects["background"] = [{"properties": background_properties}]

        padding_properties = self._padding_properties()
        if padding_properties:
            objects["padding"] = [{"properties": padding_properties}]

        border_properties = self._border_properties()
        if border_properties:
            objects["border"] = [{"properties": border_properties}]

        return objects

    def update(self, **kwargs: Any) -> None:
        for key, value in kwargs.items():
            if not hasattr(self, key):
                raise AttributeError(f"Unknown general formatting property: {key}")
            setattr(self, key, value)

    def _title_properties(self) -> dict[str, Any]:
        properties: dict[str, Any] = {}
        if self.title_show is not None:
            properties["show"] = _bool_literal(self.title_show)
        if self.title is not None:
            properties["text"] = _literal(self.title)
        if self.title_font_size is not None:
            properties["fontSize"] = _numeric_literal(self.title_font_size)
        if self.title_font_family is not None:
            properties["fontFamily"] = _literal(self.title_font_family)
        if self.title_font_color is not None:
            properties["fontColor"] = _solid_color(self.title_font_color)
        return properties

    def _background_properties(self) -> dict[str, Any]:
        properties: dict[str, Any] = {}
        if self.background_show is not None:
            properties["show"] = _bool_literal(self.background_show)
        if self.background_color is not None:
            properties["color"] = _solid_color(self.background_color)
        if self.background_transparency is not None:
            properties["transparency"] = _numeric_literal(self.background_transparency)
        return properties

    def _padding_properties(self) -> dict[str, Any]:
        values = {
            "top": self.padding_top,
            "right": self.padding_right,
            "bottom": self.padding_bottom,
            "left": self.padding_left,
        }
        if self.padding is not None:
            values = {
                key: self.padding if value is None else value
                for key, value in values.items()
            }
        return {
            key: _numeric_literal(value)
            for key, value in values.items()
            if value is not None
        }

    def _border_properties(self) -> dict[str, Any]:
        properties: dict[str, Any] = {}
        if self.border_show is not None:
            properties["show"] = _bool_literal(self.border_show)
        if self.border_color is not None:
            properties["color"] = _solid_color(self.border_color)
        if self.border_radius is not None:
            properties["radius"] = _numeric_literal(self.border_radius)
        return properties


@dataclass
class Visual:
    position: Position
    name: str = field(default_factory=_new_name)
    general_formatting: GeneralFormatting = field(default_factory=GeneralFormatting)
    drill_filter_other_visuals: bool = True
    visual_type = "visual"

    @classmethod
    def line_chart(
        cls,
        x: float,
        y: float,
        width: float,
        height: float,
        *,
        name: str | None = None,
        binding: VisualBinding | None = None,
        general_formatting: GeneralFormatting | None = None,
        z: int = 0,
        tab_order: int = 0,
    ) -> "Visual":
        return LineChart(
            name=name or _new_name(),
            position=_position(x, y, width, height, z=z, tab_order=tab_order),
            general_formatting=general_formatting or GeneralFormatting(),
            binding=binding,
        )

    @classmethod
    def bar_chart(
        cls,
        x: float,
        y: float,
        width: float,
        height: float,
        *,
        name: str | None = None,
        binding: VisualBinding | None = None,
        general_formatting: GeneralFormatting | None = None,
        z: int = 0,
        tab_order: int = 0,
    ) -> "Visual":
        return BarChart(
            name=name or _new_name(),
            position=_position(x, y, width, height, z=z, tab_order=tab_order),
            general_formatting=general_formatting or GeneralFormatting(),
            binding=binding,
        )

    @classmethod
    def clustered_column_chart(
        cls,
        x: float,
        y: float,
        width: float,
        height: float,
        *,
        name: str | None = None,
        binding: VisualBinding | None = None,
        general_formatting: GeneralFormatting | None = None,
        z: int = 0,
        tab_order: int = 0,
    ) -> "Visual":
        return ClusteredColumnChart(
            name=name or _new_name(),
            position=_position(x, y, width, height, z=z, tab_order=tab_order),
            general_formatting=general_formatting or GeneralFormatting(),
            binding=binding,
        )

    @classmethod
    def card(
        cls,
        x: float,
        y: float,
        width: float,
        height: float,
        *,
        name: str | None = None,
        binding: VisualBinding | None = None,
        general_formatting: GeneralFormatting | None = None,
        z: int = 0,
        tab_order: int = 0,
    ) -> "Visual":
        return Card(
            name=name or _new_name(),
            position=_position(x, y, width, height, z=z, tab_order=tab_order),
            general_formatting=general_formatting or GeneralFormatting(),
            binding=binding,
        )

    @classmethod
    def slicer(
        cls,
        x: float,
        y: float,
        width: float,
        height: float,
        *,
        name: str | None = None,
        mode: str = "Basic",
        binding: VisualBinding | None = None,
        general_formatting: GeneralFormatting | None = None,
        z: int = 0,
        tab_order: int = 0,
    ) -> "Visual":
        return Slicer(
            name=name or _new_name(),
            position=_position(x, y, width, height, z=z, tab_order=tab_order),
            general_formatting=general_formatting or GeneralFormatting(),
            binding=binding,
            mode=mode,
        )

    @classmethod
    def table(
        cls,
        x: float,
        y: float,
        width: float,
        height: float,
        *,
        name: str | None = None,
        binding: VisualBinding | None = None,
        general_formatting: GeneralFormatting | None = None,
        z: int = 0,
        tab_order: int = 0,
    ) -> "Visual":
        return Table(
            name=name or _new_name(),
            position=_position(x, y, width, height, z=z, tab_order=tab_order),
            general_formatting=general_formatting or GeneralFormatting(),
            binding=binding,
        )

    @classmethod
    def matrix(
        cls,
        x: float,
        y: float,
        width: float,
        height: float,
        *,
        name: str | None = None,
        binding: VisualBinding | None = None,
        general_formatting: GeneralFormatting | None = None,
        z: int = 0,
        tab_order: int = 0,
    ) -> "Visual":
        return Matrix(
            name=name or _new_name(),
            position=_position(x, y, width, height, z=z, tab_order=tab_order),
            general_formatting=general_formatting or GeneralFormatting(),
            binding=binding,
        )

    @classmethod
    def shape(
        cls,
        x: float,
        y: float,
        width: float,
        height: float,
        *,
        name: str | None = None,
        shape_type: str = "rectangleRounded",
        rotation: str | int | float = "0L",
        general_formatting: GeneralFormatting | None = None,
        z: int = 0,
        tab_order: int = 0,
    ) -> "Visual":
        return Shape(
            name=name or _new_name(),
            position=_position(x, y, width, height, z=z, tab_order=tab_order),
            general_formatting=general_formatting or GeneralFormatting(),
            shape_type=shape_type,
            rotation=rotation,
        )

    @classmethod
    def image(
        cls,
        x: float,
        y: float,
        width: float,
        height: float,
        image_path: str | Path,
        *,
        name: str | None = None,
        scaling: str = "Normal",
        general_formatting: GeneralFormatting | None = None,
        z: int = 0,
        tab_order: int = 0,
    ) -> "Visual":
        image_source = Path(image_path)
        return ImageVisual(
            name=name or _new_name(),
            position=_position(x, y, width, height, z=z, tab_order=tab_order),
            general_formatting=general_formatting or GeneralFormatting(),
            image_path=image_source,
            registered_name=_new_resource_name(image_source),
            scaling=scaling,
        )

    @classmethod
    def text_box(
        cls,
        x: float,
        y: float,
        width: float,
        height: float,
        text: str,
        *,
        name: str | None = None,
        typeface: str | None = None,
        font_size: str | int | float | None = None,
        text_color: str | None = None,
        general_formatting: GeneralFormatting | None = None,
        z: int = 0,
        tab_order: int = 0,
    ) -> "Visual":
        return TextBox(
            name=name or _new_name(),
            position=_position(x, y, width, height, z=z, tab_order=tab_order),
            general_formatting=general_formatting or GeneralFormatting(),
            text=text,
            typeface=typeface,
            font_size=font_size,
            text_color=text_color,
        )

    def update_general_formatting(self, **kwargs: Any) -> "Visual":
        self.general_formatting.update(**kwargs)
        return self

    def to_pbir(self) -> dict[str, Any]:
        return {
            "$schema": VISUAL_SCHEMA,
            "name": self.name,
            "position": self.position.to_pbir(),
            "visual": self._visual_document(),
        }

    def _visual_document(self) -> dict[str, Any]:
        document: dict[str, Any] = {
            "visualType": self.visual_type,
            "drillFilterOtherVisuals": self.drill_filter_other_visuals,
        }
        objects = self._visual_objects()
        if objects:
            document["objects"] = objects
        visual_container_objects = self.general_formatting.to_visual_container_objects()
        if visual_container_objects:
            document["visualContainerObjects"] = visual_container_objects
        return document

    def _visual_objects(self) -> dict[str, Any]:
        return {}

    def validate(self) -> None:
        return None


@dataclass
class DataVisual(Visual):
    binding: VisualBinding | None = None

    def validate(self) -> None:
        if self.binding is not None:
            raise ValueError(
                f"Bindings are not written to PBIR yet for {self.visual_type} visual '{self.name}'"
            )


@dataclass
class LineChart(DataVisual):
    visual_type = "lineChart"


@dataclass
class BarChart(DataVisual):
    visual_type = "barChart"


@dataclass
class ClusteredColumnChart(DataVisual):
    visual_type = "clusteredColumnChart"


@dataclass
class Card(DataVisual):
    visual_type = "cardVisual"


@dataclass
class Slicer(DataVisual):
    visual_type = "slicer"
    mode: str = "Basic"

    def _visual_objects(self) -> dict[str, Any]:
        return {
            "data": [
                {
                    "properties": {
                        "mode": _literal(self.mode),
                    }
                }
            ]
        }


@dataclass
class Table(DataVisual):
    visual_type = "tableEx"


@dataclass
class Matrix(DataVisual):
    visual_type = "pivotTable"


@dataclass
class Shape(Visual):
    visual_type = "shape"
    shape_type: str = "rectangleRounded"
    rotation: str | int | float = "0L"

    def _visual_objects(self) -> dict[str, Any]:
        return {
            "shape": [
                {
                    "properties": {
                        "tileShape": _literal(self.shape_type),
                    }
                }
            ],
            "rotation": [
                {
                    "properties": {
                        "shapeAngle": _numeric_literal(self.rotation),
                    }
                }
            ],
        }


@dataclass
class ImageVisual(Visual):
    visual_type = "image"
    image_path: Path = field(default_factory=lambda: Path("."))
    registered_name: str = ""
    scaling: str = "Normal"

    @property
    def display_name(self) -> str:
        return self.image_path.name

    def _visual_objects(self) -> dict[str, Any]:
        return {
            "image": [
                {
                    "properties": {
                        "sourceFile": {
                            "image": _resource_image(
                                self.display_name,
                                self.registered_name,
                                self.scaling,
                            )
                        }
                    }
                }
            ]
        }


@dataclass
class TextBox(Visual):
    visual_type = "textbox"
    text: str = ""
    typeface: str | None = None
    font_size: str | int | float | None = None
    text_color: str | None = None

    def _visual_objects(self) -> dict[str, Any]:
        return {"general": [{"properties": {"paragraphs": self._text_paragraphs()}}]}

    def _text_paragraphs(self) -> list[dict[str, Any]]:
        lines = (self.text or "").splitlines() or [""]
        return [{"textRuns": [self._text_run(line)]} for line in lines]

    def _text_run(self, value: str) -> dict[str, Any]:
        text_run: dict[str, Any] = {"value": value}
        text_style = _text_style(self.typeface, self.font_size, self.text_color)
        if text_style:
            text_run["textStyle"] = text_style
        return text_run


@dataclass
class Page:
    display_name: str
    name: str = field(default_factory=_new_name)
    width: int = 794
    height: int = 1123
    display_option: str = "ActualSize"
    background: PageBackground | None = None
    visuals: list[Visual] = field(default_factory=list)

    def add_visual(self, visual: Visual) -> Visual:
        self.visuals.append(visual)
        return visual

    def add_hstack(
        self,
        gap: float = 0,
        padding: Any = 0,
        *,
        frame: Any = None,
        x: float = 0,
        y: float = 0,
        width: float | None = None,
        height: float | None = None,
    ) -> Any:
        from .layout_authoring import page_add_hstack

        return page_add_hstack(
            self,
            gap=gap,
            padding=padding,
            frame=frame,
            x=x,
            y=y,
            width=width,
            height=height,
        )

    def add_vstack(
        self,
        gap: float = 0,
        padding: Any = 0,
        *,
        frame: Any = None,
        x: float = 0,
        y: float = 0,
        width: float | None = None,
        height: float | None = None,
    ) -> Any:
        from .layout_authoring import page_add_vstack

        return page_add_vstack(
            self,
            gap=gap,
            padding=padding,
            frame=frame,
            x=x,
            y=y,
            width=width,
            height=height,
        )

    def add_grid(
        self,
        rows: int,
        columns: int,
        *,
        gap: float = 0,
        padding: Any = 0,
        frame: Any = None,
        x: float = 0,
        y: float = 0,
        width: float | None = None,
        height: float | None = None,
    ) -> Any:
        from .layout_authoring import page_add_grid

        return page_add_grid(
            self,
            rows=rows,
            columns=columns,
            gap=gap,
            padding=padding,
            frame=frame,
            x=x,
            y=y,
            width=width,
            height=height,
        )

    def set_background(
        self,
        image_path: str | Path,
        *,
        scaling: str = "Fill",
        transparency: str | int | float = "0D",
    ) -> PageBackground:
        background = PageBackground(
            image_path=Path(image_path),
            registered_name=_new_resource_name(Path(image_path)),
            scaling=scaling,
            transparency=transparency,
        )
        self.background = background
        return background

    def add_line_chart(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        *,
        name: str | None = None,
        binding: VisualBinding | None = None,
        general_formatting: GeneralFormatting | None = None,
    ) -> Visual:
        return self.add_visual(
            Visual.line_chart(
                x=x,
                y=y,
                width=width,
                height=height,
                name=name,
                binding=binding,
                general_formatting=general_formatting,
                tab_order=len(self.visuals),
            )
        )

    def add_bar_chart(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        *,
        name: str | None = None,
        binding: VisualBinding | None = None,
        general_formatting: GeneralFormatting | None = None,
    ) -> Visual:
        return self.add_visual(
            Visual.bar_chart(
                x=x,
                y=y,
                width=width,
                height=height,
                name=name,
                binding=binding,
                general_formatting=general_formatting,
                z=len(self.visuals),
                tab_order=len(self.visuals),
            )
        )

    def add_clustered_column_chart(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        *,
        name: str | None = None,
        binding: VisualBinding | None = None,
        general_formatting: GeneralFormatting | None = None,
    ) -> Visual:
        return self.add_visual(
            Visual.clustered_column_chart(
                x=x,
                y=y,
                width=width,
                height=height,
                name=name,
                binding=binding,
                general_formatting=general_formatting,
                z=len(self.visuals),
                tab_order=len(self.visuals),
            )
        )

    def add_card(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        *,
        name: str | None = None,
        binding: VisualBinding | None = None,
        general_formatting: GeneralFormatting | None = None,
    ) -> Visual:
        return self.add_visual(
            Visual.card(
                x=x,
                y=y,
                width=width,
                height=height,
                name=name,
                binding=binding,
                general_formatting=general_formatting,
                z=len(self.visuals),
                tab_order=len(self.visuals),
            )
        )

    def add_slicer(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        *,
        name: str | None = None,
        mode: str = "Basic",
        binding: VisualBinding | None = None,
        general_formatting: GeneralFormatting | None = None,
    ) -> Visual:
        return self.add_visual(
            Visual.slicer(
                x=x,
                y=y,
                width=width,
                height=height,
                name=name,
                mode=mode,
                binding=binding,
                general_formatting=general_formatting,
                z=len(self.visuals),
                tab_order=len(self.visuals),
            )
        )

    def add_table(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        *,
        name: str | None = None,
        binding: VisualBinding | None = None,
        general_formatting: GeneralFormatting | None = None,
    ) -> Visual:
        return self.add_visual(
            Visual.table(
                x=x,
                y=y,
                width=width,
                height=height,
                name=name,
                binding=binding,
                general_formatting=general_formatting,
                z=len(self.visuals),
                tab_order=len(self.visuals),
            )
        )

    def add_matrix(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        *,
        name: str | None = None,
        binding: VisualBinding | None = None,
        general_formatting: GeneralFormatting | None = None,
    ) -> Visual:
        return self.add_visual(
            Visual.matrix(
                x=x,
                y=y,
                width=width,
                height=height,
                name=name,
                binding=binding,
                general_formatting=general_formatting,
                z=len(self.visuals),
                tab_order=len(self.visuals),
            )
        )

    def add_shape(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        *,
        name: str | None = None,
        shape_type: str = "rectangleRounded",
        rotation: str | int | float = "0L",
        general_formatting: GeneralFormatting | None = None,
    ) -> Visual:
        return self.add_visual(
            Visual.shape(
                x=x,
                y=y,
                width=width,
                height=height,
                name=name,
                shape_type=shape_type,
                rotation=rotation,
                general_formatting=general_formatting,
                z=len(self.visuals),
                tab_order=len(self.visuals),
            )
        )

    def add_image(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        image_path: str | Path,
        *,
        name: str | None = None,
        scaling: str = "Normal",
        general_formatting: GeneralFormatting | None = None,
    ) -> Visual:
        return self.add_visual(
            Visual.image(
                x=x,
                y=y,
                width=width,
                height=height,
                image_path=image_path,
                name=name,
                scaling=scaling,
                general_formatting=general_formatting,
                z=len(self.visuals),
                tab_order=len(self.visuals),
            )
        )

    def add_text_box(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        text: str,
        *,
        name: str | None = None,
        typeface: str | None = None,
        font_size: str | int | float | None = None,
        text_color: str | None = None,
        general_formatting: GeneralFormatting | None = None,
    ) -> Visual:
        return self.add_visual(
            Visual.text_box(
                x=x,
                y=y,
                width=width,
                height=height,
                text=text,
                name=name,
                typeface=typeface,
                font_size=font_size,
                text_color=text_color,
                general_formatting=general_formatting,
                z=len(self.visuals),
                tab_order=len(self.visuals),
            )
        )

    def to_pbir(self) -> dict[str, Any]:
        document: dict[str, Any] = {
            "$schema": PAGE_SCHEMA,
            "name": self.name,
            "displayName": self.display_name,
            "displayOption": self.display_option,
            "height": self.height,
            "width": self.width,
        }
        if self.background is not None:
            document["objects"] = {
                "background": [{"properties": self.background.to_pbir_properties()}]
            }
        return document


@dataclass
class Report:
    display_name: str
    dataset_path: str | None = None
    artifact_name: str | None = None
    base_theme_name: str = DEFAULT_THEME_NAME
    base_theme_source: str | Path | None = DEFAULT_THEME_SOURCE
    pages: list[Page] = field(default_factory=list)

    def add_page(
        self,
        display_name: str,
        *,
        name: str | None = None,
        width: int = 794,
        height: int = 1123,
    ) -> Page:
        page = Page(
            name=name or _new_name(),
            display_name=display_name,
            width=width,
            height=height,
        )
        self.pages.append(page)
        return page

    @property
    def pbip_artifact_name(self) -> str:
        return self.artifact_name or _artifact_name(self.display_name)


def write_report(report: Report, output_dir: str | Path, *, overwrite: bool = False) -> Path:
    """Write a report as a PBIP project and return the project directory."""
    from .layout_authoring import materialize_report_layouts

    materialize_report_layouts(report)
    _validate_report(report)
    output_path = Path(output_dir)
    if output_path.exists():
        if not overwrite:
            raise FileExistsError(f"{output_path} already exists")
        shutil.rmtree(output_path)

    artifact_name = report.pbip_artifact_name
    report_dir = output_path / f"{artifact_name}.Report"
    definition_dir = report_dir / "definition"
    pages_dir = definition_dir / "pages"

    pages_dir.mkdir(parents=True)
    _write_base_theme(report, report_dir)
    _write_registered_resources(report, report_dir)

    _write_json(
        output_path / f"{artifact_name}.pbip",
        {
            "$schema": PBIP_SCHEMA,
            "version": "1.0",
            "artifacts": [{"report": {"path": f"{artifact_name}.Report"}}],
            "settings": {"enableAutoRecovery": True},
        },
    )

    definition_pbir: dict[str, Any] = {"$schema": PBIR_SCHEMA, "version": "4.0"}
    if report.dataset_path:
        definition_pbir["datasetReference"] = {"byPath": {"path": report.dataset_path}}
    _write_json(report_dir / "definition.pbir", definition_pbir)

    _write_json(definition_dir / "version.json", {"$schema": VERSION_SCHEMA, "version": "2.0.0"})
    _write_json(
        definition_dir / "report.json",
        _report_document(report.base_theme_name, _registered_resource_items(report)),
    )
    _write_json(definition_dir / "pages" / "pages.json", _pages_document(report.pages))

    for page in report.pages:
        page_dir = pages_dir / page.name
        visuals_dir = page_dir / "visuals"
        visuals_dir.mkdir(parents=True)
        _write_json(page_dir / "page.json", page.to_pbir())

        for visual in page.visuals:
            visual_dir = visuals_dir / visual.name
            visual_dir.mkdir()
            _write_json(visual_dir / "visual.json", visual.to_pbir())

    return output_path


def _report_document(
    base_theme_name: str,
    registered_resources: list[dict[str, str]],
) -> dict[str, Any]:
    resource_packages = [
        {
            "name": "SharedResources",
            "type": "SharedResources",
            "items": [
                {
                    "name": base_theme_name,
                    "path": f"BaseThemes/{base_theme_name}.json",
                    "type": "BaseTheme",
                }
            ],
        }
    ]
    if registered_resources:
        resource_packages.append(
            {
                "name": "RegisteredResources",
                "type": "RegisteredResources",
                "items": registered_resources,
            }
        )

    return {
        "$schema": REPORT_SCHEMA,
        "themeCollection": {
            "baseTheme": {
                "name": base_theme_name,
                "reportVersionAtImport": {
                    "visual": "2.8.0",
                    "report": "3.2.0",
                    "page": "2.3.1",
                },
                "type": "SharedResources",
            }
        },
        "objects": {
            "section": [
                {
                    "properties": {
                        "verticalAlignment": _literal("Top"),
                    }
                }
            ]
        },
        "resourcePackages": resource_packages,
        "settings": {
            "useStylableVisualContainerHeader": True,
            "exportDataMode": "AllowSummarized",
            "defaultDrillFilterOtherVisuals": True,
            "allowChangeFilterTypes": True,
            "useEnhancedTooltips": True,
            "useDefaultAggregateDisplayName": True,
        },
    }


def _pages_document(pages: list[Page]) -> dict[str, Any]:
    page_order = [page.name for page in pages]
    document: dict[str, Any] = {
        "$schema": PAGES_SCHEMA,
        "pageOrder": page_order,
    }
    if page_order:
        document["activePageName"] = page_order[0]
    return document


def _validate_report(report: Report) -> None:
    for page in report.pages:
        for visual in page.visuals:
            visual.validate()


def _write_base_theme(report: Report, report_dir: Path) -> None:
    theme_dir = report_dir / "StaticResources" / "SharedResources" / "BaseThemes"
    theme_dir.mkdir(parents=True)

    destination = theme_dir / f"{report.base_theme_name}.json"
    if report.base_theme_source is not None:
        source = Path(report.base_theme_source)
        if source.exists():
            shutil.copyfile(source, destination)
            return

    _write_json(destination, {"name": report.base_theme_name})


def _write_registered_resources(report: Report, report_dir: Path) -> None:
    resources = _unique_registered_resources(report)
    if not resources:
        return

    resource_dir = report_dir / "StaticResources" / "RegisteredResources"
    resource_dir.mkdir(parents=True)
    for resource in resources.values():
        source = resource.image_path
        if not source.exists():
            raise FileNotFoundError(f"Registered image not found: {source}")
        shutil.copyfile(source, resource_dir / resource.registered_name)


def _registered_resource_items(report: Report) -> list[dict[str, str]]:
    items = []
    for resource in _unique_registered_resources(report).values():
        items.append(
            {
                "name": resource.registered_name,
                "path": resource.registered_name,
                "type": "Image",
            }
        )
    return items


def _unique_registered_resources(report: Report) -> dict[Path, PageBackground | ImageVisual]:
    resources: dict[Path, PageBackground | ImageVisual] = {}
    for page in report.pages:
        if page.background is not None:
            _register_resource(resources, page.background)
        for visual in page.visuals:
            if isinstance(visual, ImageVisual):
                _register_resource(resources, visual)
    return resources


def _register_resource(
    resources: dict[Path, PageBackground | ImageVisual],
    resource: PageBackground | ImageVisual,
) -> None:
    key = resource.image_path.resolve()
    if key in resources:
        resource.registered_name = resources[key].registered_name
    else:
        resources[key] = resource


def _position(
    x: float,
    y: float,
    width: float,
    height: float,
    *,
    z: int = 0,
    tab_order: int = 0,
) -> Position:
    return Position(
        x=x,
        y=y,
        width=width,
        height=height,
        z=z,
        tab_order=tab_order,
    )


def _text_style(
    typeface: str | None,
    font_size: str | int | float | None,
    text_color: str | None = None,
) -> dict[str, str]:
    style: dict[str, str] = {}
    if typeface is not None:
        style["fontFamily"] = typeface
    if font_size is not None:
        style["fontSize"] = _font_size_value(font_size)
    if text_color is not None:
        style["color"] = text_color
    return style


def _font_size_value(font_size: str | int | float) -> str:
    if isinstance(font_size, str):
        return font_size
    return f"{font_size:g}pt"


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
