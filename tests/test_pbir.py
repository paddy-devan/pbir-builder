import json
import tempfile
import unittest
from pathlib import Path

from pbir_builder import GeneralFormatting, Report, TextBox, write_report


class PbirWriterTests(unittest.TestCase):
    def test_writes_basic_report_layout(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            background_path = Path(temp_dir) / "background.png"
            background_path.write_bytes(b"not really a png")

            report = Report("My Report", dataset_path="../Model")
            page = report.add_page("Overview", name="page1")
            background = page.set_background(background_path)
            line_chart = page.add_line_chart(
                10,
                20,
                300,
                200,
                name="visual1",
                general_formatting=GeneralFormatting(
                    title="Admissions",
                    title_show=True,
                    title_font_size=12,
                    background_color="#FFFFFF",
                    background_transparency=49,
                    border_show=True,
                    border_color="#000000",
                    border_radius=12,
                    padding_right=20,
                ),
            )
            line_chart.position.width = 320
            line_chart.update_general_formatting(title_font_color="#111111")
            page.add_text_box(
                10,
                240,
                300,
                80,
                "Summary commentary",
                name="textbox1",
                typeface="Segoe UI",
                font_size=14,
                text_color="#FFFFFF",
                general_formatting=GeneralFormatting(
                    background_show=False,
                    border_show=False,
                ),
            )

            project_dir = write_report(report, Path(temp_dir) / "out")

            self.assertTrue((project_dir / "My_Report.pbip").exists())
            self.assertTrue((project_dir / "My_Report.Report" / "definition.pbir").exists())
            self.assertTrue(
                (
                    project_dir
                    / "My_Report.Report"
                    / "StaticResources"
                    / "SharedResources"
                    / "BaseThemes"
                    / "CY26SU04.json"
                ).exists()
            )
            self.assertTrue(
                (
                    project_dir
                    / "My_Report.Report"
                    / "StaticResources"
                    / "RegisteredResources"
                    / background.registered_name
                ).exists()
            )
            self.assertTrue(
                (
                    project_dir
                    / "My_Report.Report"
                    / "definition"
                    / "pages"
                    / "page1"
                    / "visuals"
                    / "visual1"
                    / "visual.json"
                ).exists()
            )
            self.assertTrue(
                (
                    project_dir
                    / "My_Report.Report"
                    / "definition"
                    / "pages"
                    / "page1"
                    / "visuals"
                    / "textbox1"
                    / "visual.json"
                ).exists()
            )

            pages = _read_json(
                project_dir / "My_Report.Report" / "definition" / "pages" / "pages.json"
            )
            self.assertEqual(pages["pageOrder"], ["page1"])
            self.assertEqual(pages["activePageName"], "page1")

            report_json = _read_json(
                project_dir / "My_Report.Report" / "definition" / "report.json"
            )
            self.assertEqual(report_json["themeCollection"]["baseTheme"]["name"], "CY26SU04")
            self.assertEqual(
                report_json["resourcePackages"][0]["items"][0]["path"],
                "BaseThemes/CY26SU04.json",
            )
            self.assertEqual(report_json["resourcePackages"][1]["name"], "RegisteredResources")
            self.assertEqual(
                report_json["resourcePackages"][1]["items"][0],
                {
                    "name": background.registered_name,
                    "path": background.registered_name,
                    "type": "Image",
                },
            )

            page_json = _read_json(
                project_dir / "My_Report.Report" / "definition" / "pages" / "page1" / "page.json"
            )
            background_properties = page_json["objects"]["background"][0]["properties"]
            self.assertEqual(
                background_properties["image"]["image"]["name"]["expr"]["Literal"]["Value"],
                "'background.png'",
            )
            self.assertEqual(
                background_properties["image"]["image"]["url"]["expr"]["ResourcePackageItem"][
                    "ItemName"
                ],
                background.registered_name,
            )
            self.assertEqual(
                background_properties["image"]["image"]["scaling"]["expr"]["Literal"]["Value"],
                "'Fill'",
            )
            self.assertEqual(
                background_properties["transparency"]["expr"]["Literal"]["Value"],
                "0D",
            )

            visual = _read_json(
                project_dir
                / "My_Report.Report"
                / "definition"
                / "pages"
                / "page1"
                / "visuals"
                / "visual1"
                / "visual.json"
            )
            self.assertEqual(visual["visual"]["visualType"], "lineChart")
            self.assertEqual(visual["position"]["tabOrder"], 0)
            self.assertEqual(visual["position"]["width"], 320)
            visual_container_objects = visual["visual"]["visualContainerObjects"]
            title_properties = visual_container_objects["title"][0]["properties"]
            self.assertEqual(title_properties["show"]["expr"]["Literal"]["Value"], "true")
            self.assertEqual(title_properties["text"]["expr"]["Literal"]["Value"], "'Admissions'")
            self.assertEqual(title_properties["fontSize"]["expr"]["Literal"]["Value"], "12D")
            self.assertEqual(
                title_properties["fontColor"]["solid"]["color"]["expr"]["Literal"]["Value"],
                "'#111111'",
            )
            background_properties = visual_container_objects["background"][0]["properties"]
            self.assertEqual(
                background_properties["color"]["solid"]["color"]["expr"]["Literal"]["Value"],
                "'#FFFFFF'",
            )
            self.assertEqual(
                background_properties["transparency"]["expr"]["Literal"]["Value"],
                "49D",
            )
            border_properties = visual_container_objects["border"][0]["properties"]
            self.assertEqual(border_properties["show"]["expr"]["Literal"]["Value"], "true")
            self.assertEqual(
                border_properties["color"]["solid"]["color"]["expr"]["Literal"]["Value"],
                "'#000000'",
            )
            self.assertEqual(border_properties["radius"]["expr"]["Literal"]["Value"], "12D")
            padding_properties = visual_container_objects["padding"][0]["properties"]
            self.assertEqual(padding_properties["right"]["expr"]["Literal"]["Value"], "20D")

            text_box = _read_json(
                project_dir
                / "My_Report.Report"
                / "definition"
                / "pages"
                / "page1"
                / "visuals"
                / "textbox1"
                / "visual.json"
            )
            self.assertEqual(text_box["visual"]["visualType"], "textbox")
            self.assertEqual(text_box["position"]["tabOrder"], 1)
            text_run = text_box["visual"]["objects"]["general"][0]["properties"]["paragraphs"][0][
                "textRuns"
            ][0]
            self.assertEqual(text_run["value"], "Summary commentary")
            self.assertEqual(text_run["textStyle"]["fontFamily"], "Segoe UI")
            self.assertEqual(text_run["textStyle"]["fontSize"], "14pt")
            self.assertEqual(text_run["textStyle"]["color"], "#FFFFFF")
            text_box_background = text_box["visual"]["visualContainerObjects"]["background"][0][
                "properties"
            ]
            self.assertEqual(text_box_background["show"]["expr"]["Literal"]["Value"], "false")
            text_box_border = text_box["visual"]["visualContainerObjects"]["border"][0][
                "properties"
            ]
            self.assertEqual(text_box_border["show"]["expr"]["Literal"]["Value"], "false")

            self.assertIsInstance(page.visuals[1], TextBox)


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
