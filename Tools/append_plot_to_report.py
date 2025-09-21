# Tools/append_plot_to_report.py
import pathlib, re
ROOT = pathlib.Path(__file__).resolve().parents[1]
report = ROOT / "REPORT.md"
png    = ROOT / "fig_composite_by_year.png"
if not report.exists():
    raise SystemExit("REPORT.md not found")
txt = report.read_text(encoding="utf-8")

# Ensure "Composite Mean by Year" section exists; then add the figure below it once.
header = "## Composite Mean by Year"
if header not in txt:
    txt += f"\n\n{header}\n\n_(table will be generated separately)_\n"

block = "\n![Composite Mean by Year](fig_composite_by_year.png)\n"
pattern = re.compile(r"(## Composite Mean by Year.*?)(\n!\[Composite Mean by Year\]\(fig_composite_by_year\.png\)\n)?", re.S)
if pattern.search(txt):
    txt = pattern.sub(lambda m: (m.group(1) + block), txt, count=1)
else:
    txt += block
report.write_text(txt, encoding="utf-8")
print(f"[report] embedded plot -> {report}")
