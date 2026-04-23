import tempfile
import unittest
from pathlib import Path

from pbir_builder import (
    Frame,
    Grid,
    GridNode,
    HStack,
    HStackNode,
    LayoutDebugStyle,
    Padding,
    Report,
    VStack,
    VStackNode,
    Visual,
    VisualPlacement,
    apply_layout,
    write_report,
)


class LayoutContainerTests(unittest.TestCase):
    def test_hstack_resolves_equal_width_frames(self) -> None:
        frames = HStack(
            x=10,
            y=20,
            width=320,
            height=120,
            gap=10,
            padding=Padding.all(5),
        ).resolve(3)

        self.assertEqual(len(frames), 3)
        self.assertEqual(frames[0].x, 15)
        self.assertEqual(frames[0].y, 25)
        self.assertEqual(frames[0].width, 96.66666666666667)
        self.assertEqual(frames[0].height, 110)
        self.assertEqual(frames[1].x, 121.66666666666667)
        self.assertEqual(frames[2].x, 228.33333333333334)

    def test_vstack_resolves_equal_height_frames(self) -> None:
        frames = VStack(
            x=30,
            y=40,
            width=180,
            height=260,
            gap=12,
            padding=Padding.symmetric(horizontal=10, vertical=8),
        ).resolve(2)

        self.assertEqual(len(frames), 2)
        self.assertEqual(frames[0].x, 40)
        self.assertEqual(frames[0].y, 48)
        self.assertEqual(frames[0].width, 160)
        self.assertEqual(frames[0].height, 116)
        self.assertEqual(frames[1].y, 176)

    def test_grid_resolves_row_major_cells(self) -> None:
        frames = Grid(
            x=0,
            y=0,
            width=420,
            height=240,
            rows=2,
            columns=3,
            gap=10,
            padding=Padding.all(10),
        ).resolve(5)

        self.assertEqual(len(frames), 5)
        self.assertEqual(frames[0].x, 10)
        self.assertEqual(frames[0].y, 10)
        self.assertEqual(frames[0].width, 126.66666666666667)
        self.assertEqual(frames[0].height, 105)
        self.assertEqual(frames[1].x, 146.66666666666669)
        self.assertEqual(frames[3].x, 10)
        self.assertEqual(frames[3].y, 125)

    def test_grid_rejects_over_capacity_layout(self) -> None:
        grid = Grid(x=0, y=0, width=100, height=100, rows=1, columns=2)

        with self.assertRaisesRegex(ValueError, "Grid capacity exceeded"):
            grid.resolve(3)

    def test_nested_layout_nodes_resolve_to_visuals(self) -> None:
        node = HStackNode(
            gap=20,
            children=[
                VisualPlacement(Visual.card),
                VStackNode(
                    gap=10,
                    children=[
                        VisualPlacement(Visual.text_box, args=("Top",)),
                        VisualPlacement(Visual.text_box, args=("Bottom",)),
                    ],
                ),
            ],
        )

        visuals = node.resolve_visuals(Frame(10, 20, 330, 180))

        self.assertEqual(len(visuals), 3)
        self.assertEqual(visuals[0].visual_type, "cardVisual")
        self.assertEqual(visuals[0].position.x, 10)
        self.assertEqual(visuals[0].position.width, 155)
        self.assertEqual(visuals[1].position.x, 185)
        self.assertEqual(visuals[1].position.y, 20)
        self.assertEqual(visuals[1].position.height, 85)
        self.assertEqual(visuals[2].position.y, 115)

    def test_apply_layout_adds_resolved_visuals_to_page(self) -> None:
        report = Report("Layout Test")
        page = report.add_page("Overview")
        node = GridNode(
            rows=1,
            columns=2,
            gap=12,
            children=[
                VisualPlacement(Visual.line_chart),
                VisualPlacement(Visual.bar_chart),
            ],
        )

        apply_layout(page, node, Frame(40, 60, 420, 180))

        self.assertEqual(len(page.visuals), 2)
        self.assertEqual(page.visuals[0].visual_type, "lineChart")
        self.assertEqual(page.visuals[0].position.tab_order, 0)
        self.assertEqual(page.visuals[1].visual_type, "barChart")
        self.assertEqual(page.visuals[1].position.x, 256)
        self.assertEqual(page.visuals[1].position.tab_order, 1)

    def test_page_layout_facade_supports_nested_container_authoring(self) -> None:
        report = Report("Facade Test")
        page = report.add_page("Overview", width=600, height=400)

        outer = page.add_vstack(12, 8, frame=Frame(20, 30, 560, 300))
        top_row = outer.add_hstack(10)
        bottom_row = outer.add_hstack(16)
        top_row.add_card()
        top_row.add_text_box("Summary", font_size=14)
        bottom_row.add_slicer()

        page_json_before = len(page.visuals)
        self.assertEqual(page_json_before, 0)

        with tempfile.TemporaryDirectory() as temp_dir:
            from pbir_builder import write_report

            write_report(report, Path(temp_dir) / "out")

        self.assertEqual(len(page.visuals), 3)
        self.assertEqual(page.visuals[0].visual_type, "cardVisual")
        self.assertEqual(page.visuals[1].visual_type, "textbox")
        self.assertEqual(page.visuals[2].visual_type, "slicer")
        self.assertEqual(page.visuals[0].position.x, 28)
        self.assertEqual(page.visuals[2].position.y, 186.0)

    def test_per_container_debug_adds_border_only_shape_for_that_container(self) -> None:
        report = Report("Per Container Debug")
        page = report.add_page("Overview", width=400, height=300)

        row = page.add_hstack(10, frame=Frame(20, 30, 360, 120), debug=True)
        row.add_card()
        row.add_text_box("Summary")

        with tempfile.TemporaryDirectory() as temp_dir:
            write_report(report, Path(temp_dir) / "out")

        self.assertEqual(len(page.visuals), 3)
        debug_visuals = [visual for visual in page.visuals if getattr(visual, "_from_layout_debug", False)]
        self.assertEqual(len(debug_visuals), 1)
        debug_visual = debug_visuals[0]
        self.assertEqual(debug_visual.visual_type, "shape")
        self.assertEqual(debug_visual.position.x, 20)
        self.assertEqual(debug_visual.position.width, 360)
        debug_shape_objects = debug_visual._visual_objects()
        self.assertEqual(debug_shape_objects["fill"][0]["properties"]["show"]["expr"]["Literal"]["Value"], "false")
        self.assertEqual(
            debug_shape_objects["outline"][0]["properties"]["show"]["expr"]["Literal"]["Value"],
            "false",
        )
        debug_objects = debug_visual.general_formatting.to_visual_container_objects()
        self.assertEqual(
            debug_objects["background"][0]["properties"]["show"]["expr"]["Literal"]["Value"],
            "false",
        )
        self.assertEqual(
            debug_objects["border"][0]["properties"]["color"]["solid"]["color"]["expr"]["Literal"]["Value"],
            "'#FF6A00'",
        )
        self.assertEqual(
            debug_objects["border"][0]["properties"]["width"]["expr"]["Literal"]["Value"],
            "4D",
        )

    def test_global_layout_debug_adds_overlays_for_all_containers(self) -> None:
        report = Report("Global Debug")
        page = report.add_page("Overview", width=500, height=300)

        outer = page.add_vstack(12, frame=Frame(20, 20, 460, 240))
        top = outer.add_hstack(10)
        bottom = outer.add_hstack(10)
        top.add_card()
        bottom.add_text_box("Bottom")

        with tempfile.TemporaryDirectory() as temp_dir:
            write_report(
                report,
                Path(temp_dir) / "out",
                layout_debug=True,
                layout_debug_style=LayoutDebugStyle(border_color="#00A3FF"),
            )

        debug_visuals = [visual for visual in page.visuals if getattr(visual, "_from_layout_debug", False)]
        self.assertEqual(len(debug_visuals), 3)
        border_objects = [
            visual.general_formatting.to_visual_container_objects()["border"][0]["properties"]
            for visual in debug_visuals
        ]
        self.assertEqual(
            [props["color"]["solid"]["color"]["expr"]["Literal"]["Value"] for props in border_objects],
            ["'#00A3FF'"] * 3,
        )
        self.assertEqual(
            [props["width"]["expr"]["Literal"]["Value"] for props in border_objects],
            ["4D"] * 3,
        )


if __name__ == "__main__":
    unittest.main()
