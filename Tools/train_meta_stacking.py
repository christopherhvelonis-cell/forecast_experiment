import csv, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
ENS  = ROOT / "ensemble"
ENS.mkdir(exist_ok=True, parents=True)

# In a real FFORMA you’d learn weights by series/horizon features.
# For now we emit equal weights as a placeholder.
def main():
    outp = ENS / "weights_equal.csv"
    with outp.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["model","weight"])
        # Update this list when you add more models
        for m in ["HSM_chatgpt","FSM_chatgpt","HSM_grok","FSM_grok","HSM_equal_weight","FSM_equal_weight","HSM_baseline","FSM_baseline","HSM_naive","FSM_naive"]:
            w.writerow([m, "0.10"])  # will renormalize later as needed
    print(f"[stacking] wrote {outp}")
if __name__ == "__main__":
    main()
