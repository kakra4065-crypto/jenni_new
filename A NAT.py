import os
from collections import defaultdict
import numpy as np

import os
from collections import defaultdict

def transform(n, number_data):
    return sum(number_data.get(n, [0, 0, 0, 0])[1:4])

def formula_block(win, mac, number_data):
    f = []
    f.append((win[0] + win[1] + win[2]) % 90 + 1)
    f.append((mac[0] * 2 + mac[1] * 3) % 90 + 1)
    f.append(abs(win[2] - mac[2]) % 90 + 1)
    f.append((transform(win[0], number_data) + transform(mac[0], number_data)) % 90 + 1)
    f.append((win[3] * mac[3]) % 90 + 1)
    f.append((win[4] + mac[4] + transform(win[4], number_data)) % 90 + 1)
    return list(set(f))

def source_based(event_idx, lines, number_data):
    if event_idx < 5 or event_idx >= len(lines) - 1:
        return []
    src_event = lines[event_idx - 1]
    win = src_event[:5]
    mac = src_event[5:]
    return list(set([
        (win[0] + win[2]) % 90 + 1,
        (mac[1] + mac[3]) % 90 + 1,
        (win[1] * 2 - mac[2]) % 90 + 1,
        (transform(mac[0], number_data) + transform(win[4], number_data)) % 90 + 1
    ]))

def main():
    txt_files = [f for f in os.listdir() if f.lower().endswith('.txt')]
    if not txt_files:
        print("❌ No .txt files found.")
        return

    print("📂 Available .txt files:")
    for i, file in enumerate(txt_files):
        print(f"{i+1}: {file}")

    try:
        choice = int(input("Select a file number: ")) - 1
        file_path = txt_files[choice]
    except:
        print("❌ Invalid selection.")
        return

    try:
        with open(file_path) as f:
            lines = [list(map(int, line.strip().split())) for line in f if len(line.strip().split()) >= 10]
    except FileNotFoundError:
        print("❌ Selected file not found.")
        return

    try:
        with open("number.txt") as f:
            number_data = {
                int(line.split("\t")[0]): list(map(int, line.strip().split("\t")))
                for line in f if line.strip()
            }
    except FileNotFoundError:
        print("❌ number.txt not found.")
        return

    results = []
    for i in range(10, len(lines) - 1):
        actual_next = lines[i + 1][:5]
        formula_preds = formula_block(lines[i][:5], lines[i][5:], number_data)
        src_preds = source_based(i, lines, number_data)
        final_preds = list(dict.fromkeys(formula_preds + src_preds))[:4]
        match_count = len(set(final_preds) & set(actual_next))

        surrounding = []
        for j in range(i - 5, i + 6):
            if 0 <= j < len(lines):
                surrounding += lines[j][:5] + lines[j][5:]
        overlap_score = len(set(final_preds) & set(surrounding))

        results.append({
            "event": i + 1,
            "predictions": final_preds,
            "actual": actual_next,
            "match": match_count,
            "overlap": overlap_score
        })

    # Historical match reporting
    hits_2plus = [r for r in results if r['match'] >= 2]
    hits_3plus = [r for r in results if r['match'] == 3]

    print(f"\n✅ 2+ Matches: {len(hits_2plus)} / {len(results)} = {(len(hits_2plus)/len(results))*100:.2f}%")
    print(f"🎯 3 Matches:  {len(hits_3plus)} / {len(results)} = {(len(hits_3plus)/len(results))*100:.2f}%\n")

    for r in hits_2plus:
        print(f"📌 Event {r['event']}: Pred {r['predictions']} | Actual {r['actual']} | Matches: {r['match']} | Overlap: {r['overlap']}")

    # 🔮 Latest Prediction
    latest_input = lines[-1]
    formula_preds = formula_block(latest_input[:5], latest_input[5:], number_data)
    src_preds = source_based(len(lines) - 1, lines, number_data)
    final_preds = list(dict.fromkeys(formula_preds + src_preds))[:4]

    surrounding = []
    for j in range(len(lines) - 6, len(lines)):
        surrounding += lines[j][:5] + lines[j][5:]
    overlap_score = len(set(final_preds) & set(surrounding))

    # Strength label
    if overlap_score >= 14:
        strength = "📈 STRONG"
    elif overlap_score >= 10:
        strength = "⚠️ MODERATE"
    else:
        strength = "❌ WEAK"

    print("\n📌 Next Event Based on Historical Data:")
    print(f"Event {len(lines)}: Predicted: {final_preds}")
    print(f"Prediction Strength: {strength} (Overlap: {overlap_score}/20)")

if __name__ == "__main__":
    main()
    input("\nPress Enter to close...")

