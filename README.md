# pbir-builder

`pbir-builder` is a Python package for programmatically generating Power BI report
layouts using the PBIR report format.

## Installation

Install from a local checkout:

```bash
pip install .
```

For editable development installs:

```bash
pip install -e .
```

## Usage

```python
from pbir_builder import GeneralFormatting, Report, write_report

report = Report("Example Report", dataset_path="../Model")
page = report.add_page("Overview")

page.add_text_box(
    20,
    20,
    300,
    80,
    "Executive summary",
    general_formatting=GeneralFormatting(
        background_show=False,
        border_show=False,
        title_show=False,
    ),
)

page.add_line_chart(
    20,
    120,
    400,
    240,
    general_formatting=GeneralFormatting(
        title="Admissions",
        title_show=True,
        title_font_size=12,
    ),
)

write_report(report, "generated-report", overwrite=True)
```
