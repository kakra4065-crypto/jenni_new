import os
import pandas as pd

# --- Recursively Find All .txt Files ---
def find_txt_files():
    txt_files = []
    for root, _, files in os.walk("."):
        for f in files:
            if f.lower().endswith(".txt"):
                txt_files.append(os.path.join(root, f))
    return txt_files

# --- Load Lotto Data Safely ---
def load_data(file_path):
    try:
        data = pd.read_csv(file_path, sep="\t", header=None)
        if data.shape[0] < 10 or data.shape[1] < 10:
            return None, "❌ File doesn't contain enough rows or columns."
        return data, None
    except Exception as e:
        return None, f"❌ Error loading file: {e}"

# --- Prediction Formula ---
def generate_prediction(source_event, plus4_event):
    fourth_win = source_event[3]
    return {
        "full_set": [fourth_win, fourth_win - 2, source_event[9], plus4_event[0]]
    }

# --- Get Latest Prediction ---
def get_latest_prediction(data):
    try:
        last_idx = len(data) - 1
        third_win = data.iloc[last_idx, 2]
        third_mac = data.iloc[last_idx, 7]
        abs_diff = abs(third_win - third_mac)
        adjusted = 45 - abs_diff
        source_idx = int(last_idx + 2 - adjusted)

        if 0 <= source_idx + 4 < len(data):
            source = data.iloc[source_idx]
            plus4 = data.iloc[source_idx + 4]
            pred = generate_prediction(source, plus4)
            return {
                "prediction_numbers": sorted(set(pred["full_set"]), reverse=True),
                "source_idx": source_idx,
                "plus4_idx": source_idx + 4,
                "latest_idx": last_idx
            }
    except:
        return None
    return None

# --- 12 Custom Condition Checks ---
def evaluate_custom_conditions(data, source_idx):
    try:
        last_idx = len(data) - 1
        res = {}

        def safe_get(row_idx, col_idx):
            if 0 <= row_idx < len(data) and 0 <= col_idx < data.shape[1]:
                try:
                    v = data.iloc[row_idx, col_idx]
                    return None if pd.isna(v) else int(v)
                except:
                    return None
            return None

        mac1 = safe_get(last_idx, 5)
        mac2 = safe_get(last_idx, 6)
        res['1st mac -10 == 2nd mac'] = (mac1 is not None and mac2 is not None and (mac1 - 10 == mac2))

        win4 = safe_get(source_idx, 3)
        win4_prev = safe_get(source_idx - 1, 3)
        def bonanza(x): return int(str(int(x)).zfill(2)[::-1]) if x is not None else None
        res['Source 4th win bonanza == prev 4th win'] = (
            win4 is not None and win4_prev is not None and bonanza(win4) == win4_prev)

        idx3 = source_idx - 2
        w1 = safe_get(idx3, 0)
        w3 = safe_get(idx3, 2)
        all5 = [safe_get(idx3, i) for i in range(5)]
        res['Source-2: 1st==7 & 3rd==10 or any==10'] = ((w1 == 7 and w3 == 10) or 10 in all5)

        src5 = safe_get(source_idx, 4)
        nxt4 = safe_get(source_idx + 1, 3)
        res['Source 5th win == +1 event 4th win'] = (src5 is not None and nxt4 is not None and src5 == nxt4)

        nxt_wins = [safe_get(source_idx + 1, i) for i in range(5)]
        cond5 = [n for n in nxt_wins if n in (3, 34, 7, 32, 9)]
        res['Source+1 win has 2+ of (3,34,7,32,9)'] = len([x for x in cond5 if x is not None]) >= 2

        src1p4 = safe_get(source_idx + 1, 3)
        src2_wins = [safe_get(source_idx + 2, i) for i in range(5)]
        res['Source+1 4th win in +2 any win'] = src1p4 in src2_wins if src1p4 is not None else False

        def is_turning(n1, n2): return n1 != n2 and str(n1).zfill(2)[::-1] == str(n2).zfill(2)
        found = any(is_turning(w1, w2) for w1 in src2_wins for w2 in src2_wins if w1 and w2)
        res['Source+2 any win and its turning'] = found

        win1 = safe_get(source_idx + 3, 0)
        win2 = safe_get(source_idx + 3, 1)
        res['Source+3: 1st-2nd diff=1 & 1st>2nd'] = (
            win1 is not None and win2 is not None and abs(win1 - win2) == 1 and win1 > win2)

        win2_3 = safe_get(source_idx + 3, 1)
        win4_4 = safe_get(source_idx + 4, 3)
        res['Source+3 2nd win == +4 4th win'] = (win2_3 is not None and win4_4 is not None and win2_3 == win4_4)

        src1p4 = safe_get(source_idx + 1, 3)
        mac3_2 = safe_get(source_idx + 2, 7)
        res['Source+1 4th win == +2 3rd mac'] = (src1p4 is not None and mac3_2 is not None and src1p4 == mac3_2)

        win4_m1 = safe_get(source_idx - 1, 3)
        res['Source-1 4th win == 44'] = (win4_m1 == 44)

        win1 = safe_get(source_idx, 0)
        win2 = safe_get(source_idx, 1)
        res['Source: 2nd win - 1st win == 10'] = (
            win1 is not None and win2 is not None and (win2 - win1 == 10))

        score = sum(1 for v in res.values() if v)
        percent = round(score * 100 / 12)
        return res, score, percent

    except Exception as e:
        return {"ERROR": str(e)}, 0, 0

# --- Main Execution ---
def main():
    txt_files = find_txt_files()
    if not txt_files:
        print("❌ No .txt files found in folder or subfolders.")
        return

    print("📂 Lotto Files Found:")
    for idx, file in enumerate(txt_files, 1):
        print(f"{idx}: {file}")

    try:
        choice = int(input(f"\nSelect file to process (1-{len(txt_files)}): ")) - 1
        file_path = txt_files[choice]
        file_name = os.path.basename(file_path)
    except:
        print("❌ Invalid selection.")
        return

    data, error = load_data(file_path)
    if error:
        print(error)
        return

    print(f"\n📥 Analyzing File: {file_name}")

    latest = get_latest_prediction(data)
    if latest:
        formatted = f"({', '.join(str(n) for n in latest['prediction_numbers'])})"
        print(f"\n📌 LATEST PREDICTION BEING PROCESSED: {file_name.upper()}, Event {latest['source_idx'] + 1}")
        print(f"Prediction Numbers: {formatted}")
    else:
        print("❌ Could not compute latest prediction.")
        return

    print("\n==== CUSTOM CONDITIONS EVALUATION ====")
    cond_result, cond_score, cond_percent = evaluate_custom_conditions(data, latest["source_idx"])
    for label, ok in cond_result.items():
        print(f"{label}: {'✔️' if ok else '❌'}")
    print(f"\nMatched {cond_score}/12 conditions ({cond_percent}%)")
    print(f"Accuracy Score: {cond_percent}%")

    print("\n📌 Script by Alema Samuel Odame Junior")
    input("\nPress Enter to close...")

if __name__ == "__main__":
    main()
