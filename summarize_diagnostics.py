import pandas as pd

def safe_excel_writer(xlsx_path):
    """Try xlsxwriter first, fall back to openpyxl if missing."""
    try:
        return pd.ExcelWriter(xlsx_path, engine="xlsxwriter")
    except ImportError:
        print("[warn] xlsxwriter not installed, falling back to openpyxl")
        return pd.ExcelWriter(xlsx_path, engine="openpyxl")

def main():
    # ... your existing logic up to where you write Excel ...
    
    xlsx_path = "eval/results/diagnostics_summary.xlsx"

    with safe_excel_writer(xlsx_path) as xl:
        # write your dataframes, e.g.
        # df.to_excel(xl, sheet_name="summary")
        pass  # <-- replace with your actual code

if __name__ == "__main__":
    main()
