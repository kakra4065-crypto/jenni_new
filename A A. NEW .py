import os
import pandas as pd
import sys


if __name__ == "__main__" and len(sys.argv) >= 2:
    path = sys.argv[1]
    event_df = pd.read_csv(path, sep="\t", header=None)
    # Replace the line below with your script’s actual prediction call:
    # e.g. preds = main(event_df) or preds = process_event_batch(event_df)
    preds = run_predictions(event_df)
    print(preds)  # must output exactly one list like [a, b, c, d]
    sys.exit(0)

# ───── AA.NEW CONDITION Helpers ─────

def is_double(n):
    """Return True if n is one of 11,22,…,88."""
    return n in {11,22,33,44,55,66,77,88}

def turn_mac0(m0):
    """
    Turn logic for machine[0]:
      - If 10 ≤ m0 ≤ 99 and not a double, reverse digits (e.g. 23→32, 54→45).
      - Else if 1 ≤ m0 ≤ 9, multiply by 10 (e.g. 2→20, 9→90).
      - Doubles do not turn.
      - Ensure result in 1–90.
    """
    if 10 <= m0 <= 99 and not is_double(m0):
        rev = int(str(m0)[::-1])
    elif 1 <= m0 <= 9:
        rev = m0 * 10
    else:
        return None
    return rev if 1 <= rev <= 90 else None

def list_txt_files():
    return [f for f in os.listdir() if f.lower().endswith('.txt')]

def load_number_file():
    df = pd.read_csv("number.txt", sep="\t", header=None)
    df.columns = ["Number","Counterpart","Bonanza","StringKey",
                  "Extra1","Extra2","Extra3","Extra4","Extra5","Extra6"]
    return df

# ───── Core Logic ─────

def process_event(event_df, number_df, i):
    """
    For event index i, apply original logic + AA.NEW CONDITION checks.
    Returns (prediction_list, conditions_list, source_idx).
    """
    row = event_df.iloc[i]
    win = list(map(int, row[:5]))
    mac = list(map(int, row[5:10]))

    # original index math
    win_sum      = win[3] + win[4]
    mac_sum      = mac[2] + mac[3]
    prev = event_df.iloc[i-2] if i-2 >= 0 else None
    prev_mac_sum = (int(prev[5]) + int(prev[6])) if prev is not None else 0
    total_sum    = win_sum + mac_sum + prev_mac_sum

    src_idx = max(0, min(total_sum-1, len(event_df)-1))
    src      = event_df.iloc[src_idx]
    src_prev = event_df.iloc[src_idx-1] if src_idx-1 >= 0 else None
    src_next = event_df.iloc[src_idx+1] if src_idx+1 < len(event_df) else None

    two_sure = [int(src[0]), int(src[1])]
    conds = []

    # 1) previous draw’s 4th win == 35
    if i-1 >= 0 and int(event_df.iloc[i-1,3]) == 35:
        two_sure.append(15); conds.append("cond1")
    # 2) src 1st win == src_prev 2nd win
    if src_prev is not None and int(src[0]) == int(src_prev[1]):
        two_sure.append(int(src[0])); conds.append("cond2")
    # 3) src_next 5th win == 9 and 1st win is double
    if src_next is not None and int(src_next[4]) == 9 and is_double(int(src_next[0])):
        two_sure.append(int(src_next[0])); conds.append("cond3")
    # 4) src 1st+1 == src_prev 2nd AND 50 in src_prev wins
    if src_prev is not None and int(src[0])+1 == int(src_prev[1]) and 50 in [int(x) for x in src_prev[:5]]:
        two_sure.append(int(src[0])+1); conds.append("cond4")
    # 5) mac[1] == prev draw’s mac[2] → turn mac[0]
    if prev is not None and mac[1] == int(prev[7]):
        turned = turn_mac0(mac[0])
        if turned is not None:
            two_sure.append(turned); conds.append("cond5")
    # 6) current win[1] == src win[1]
    if int(src[1]) == win[1]:
        two_sure.append(win[1]); conds.append("cond6")

    # wrap first two if multiple conditions
    if len(conds) > 1:
        a, b = two_sure[0], two_sure[1]
        two_sure = [a, b, f"({a}-{b})"] + two_sure[2:]

    # lookup counterpart & string key
    base = two_sure[0]
    cp   = int(number_df.loc[number_df["Number"]==base,      "Counterpart"].iat[0])
    sk   =   number_df.loc[number_df["Number"]==cp,          "StringKey"].iat[0]

    prediction = two_sure + [cp, sk, str(total_sum)]
    return prediction, conds, src_idx

# ───── Main ─────

def main():
    files = sorted(list_txt_files())
    print("📂 Available .txt files:")
    for idx, f in enumerate(files, 1):
        print(f"  {idx}: {f}")
    try:
        sel  = int(input("Select file #: ")) - 1
        path = files[sel]
    except:
        print("❌ Invalid selection."); return

    event_df  = pd.read_csv(path, sep="\t", header=None)
    number_df = load_number_file()

    print(f"\n🔍 Historical Matches for '{path}':\n")
    for i in range(2, len(event_df)-1):
        pred, conds, src_idx = process_event(event_df, number_df, i)
        next_wins = set(map(int, event_df.iloc[i+1, :5]))
        matches = [p for p in pred if isinstance(p,int) and p in next_wins]
        if matches:
            print(f" Event {i+1} (Src {src_idx+1}): matches={matches}, conditions={conds}")

    # Next‐Draw Prediction
    last = len(event_df)-1
    print(f"\n🎯 Next‐Draw Prediction for '{path}' (Event {last+1}):\n")
    pred, conds, src_idx = process_event(event_df, number_df, last)

    two_sure = pred[:2]
    seen = set(); uniq = []
    for x in pred:
        if isinstance(x,int) and x not in seen:
            uniq.append(x); seen.add(x)
    full_str = "-".join(map(str, uniq)) + f" src event: '{pred[-1]}'"
    accuracy = f"{len(conds)*15}%"

    print(f"  Two‐Sure Hits: {two_sure}")
    print(f"  Full Prediction({full_str})")
    print(f"  Conditions Satisfied: {conds}")
    print(f"  Accuracy: {accuracy}")

if __name__ == "__main__":
    main()
    input("\nPress Enter to exit…")
