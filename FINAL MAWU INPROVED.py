import os
from collections import Counter

# ========= Load Data ========= #
def load_data(file_path):
    with open(file_path, 'r') as f:
        return [list(map(int, line.split())) for line in f if line.strip()]

# ========= Formula Implementations ========= #
formulas = []

def mawusi_1(results, event_number):
    try:
        current = results[event_number - 1]
        previous = results[event_number - 2]
        idx = max(0, event_number - (current[6] + previous[8] + current[9]) - 14)
        row = results[idx]
        return [row[9], row[6]]
    except: return None
formulas.append(("MAWUSI 1", mawusi_1))

def mawusi_2(results, event_number):
    try:
        current = results[event_number - 1]
        previous = results[event_number - 2]
        idx = max(0, event_number - (current[6] + previous[8] + current[9]) - 9)
        row = results[idx]
        return [row[3], row[0]]
    except: return None
formulas.append(("MAWUSI 2", mawusi_2))

def mawusi_4(results, event_number):
    try:
        current = results[event_number - 1]
        win = current[:5]
        mac = current[5:10]
        base = win[3] + mac[2]
        bonus = 0
        if win[4] > 70: bonus += 7
        if win[4] % 17 == 0: bonus += 5
        if win[4] in [13,17,19,23,29,31,37,41,43,47]: bonus += 3
        weighted = win[2]*2 + mac[4]
        source_event = event_number - ((base + bonus + weighted) % 40 + 2)
        if source_event + 1 >= len(results) or source_event < 1:
            return None
        triple_pick = results[source_event + 1][:5]
        combined_set = set(triple_pick)
        confirmed_sources = set()
        for i in range(1, len(results) - 2):
            if len([n for n in results[i + 1][:5] if n in results[i + 2][:5]]) >= 2:
                confirmed_sources.add(i)
        if source_event in confirmed_sources:
            combined_set.update(triple_pick)
        return sorted(combined_set)
    except:
        return None
formulas.append(("MAWUSI 4", mawusi_4))

def mawusi_5(results, event_number):
    try:
        current = results[event_number - 1]
        previous = results[event_number - 2]
        idx = max(0, event_number - (current[4] + previous[9] + current[9]) - 1)
        row = results[idx]
        return [row[0], row[4]]
    except: return None
formulas.append(("MAWUSI 5", mawusi_5))

def mawusi(results, event_number):
    try:
        current = results[event_number - 1]
        previous = results[event_number - 2]
        idx = max(0, event_number - (current[6] + previous[4] + current[3]) - 1)
        row = results[idx]
        return [row[0], row[4]]
    except: return None
formulas.append(("MAWUSI", mawusi))

def complete(results, event_number):
    try:
        current = results[event_number - 1]
        previous = results[event_number - 2]
        idx = max(0, event_number - (current[2] + previous[3] + current[6]) - 1)
        row = results[idx]
        return [row[0], row[4]]
    except: return None
formulas.append(("COMPLETE", complete))

def mawusi_b(results, event_number):
    try:
        current = results[event_number - 1]
        previous = results[event_number - 2]
        idx = max(0, event_number - (current[6] + previous[4] + current[3]) - 1)
        row = results[idx]
        return [row[1], row[3]]
    except: return None
formulas.append(("MAWUSI B", mawusi_b))

def mawusi_bc(results, event_number):
    try:
        current = results[event_number - 1]
        previous = results[event_number - 2]
        idx = max(0, event_number - (current[2] + previous[8] + current[7]) - 3)
        row = results[idx]
        return [row[0], row[4]]
    except: return None
formulas.append(("MAWUSI BC", mawusi_bc))

# ========= MAIN FUNCTION ========= #
def main():
    # Always scan current folder for .txt files
    txt_files = sorted([
        f for f in os.listdir(os.getcwd())
        if os.path.isfile(f) and f.lower().endswith(".txt") and "a.code,counter.txt" not in f.lower()
    ])

    if not txt_files:
        print("[X] No .txt files found.")
        return

    print("\n📂 Available .txt files:")
    for i, file in enumerate(txt_files):
        print(f"{i+1}: {file}")

    try:
        idx = int(input("\nEnter file number: ")) - 1
        file_path = txt_files[idx]
    except (ValueError, IndexError):
        print("[X] Invalid selection.")
        return

    results = load_data(file_path)
    event_number = len(results)

    print(f"\n📊 Running all predictions on: {file_path} | Latest Event: {event_number}")
    flat_all = []
    print("\n--- INDIVIDUAL FORMULA OUTPUTS ---")

    for name, func in formulas:
        pred = func(results, event_number)
        print(f"{name}: {pred}")
        if pred:
            flat_all.extend(pred)

        # Historical accuracy
        two_sure_hits = []
        banker_hits = []
        for i in range(1, len(results) - 1):
            past = func(results, i)
            if not past: continue
            next_win = results[i + 1][:5]
            if (name == "MAWUSI 4" and len([n for n in past if n in next_win]) >= 2) or \
               (name != "MAWUSI 4" and any(n in next_win for n in past)):
                two_sure_hits.append(i + 1)
            if past[0] in next_win:
                banker_hits.append(i + 1)

        print(f"    ➤ Total Checked: {len(results) - 2}")
        print(f"    [OK] Two Sure Matches: {len(two_sure_hits)}")
        print(f"        Events: {', '.join(map(str, two_sure_hits[:10]))}{'...' if len(two_sure_hits) > 10 else ''}")
        print(f"    ☑️  Banker Matches: {len(banker_hits)}")
        print(f"        Events: {', '.join(map(str, banker_hits[:10]))}{'...' if len(banker_hits) > 10 else ''}")

    final = list(dict.fromkeys(flat_all))
    final_output = '-'.join(map(str, final))
    repeated = [str(n) for n, c in Counter(flat_all).items() if c > 1]

    print(f"\n📌 Final Prediction: {final_output}")
    if repeated:
        print(f"\n📌 Repeated Numbers Across Formulas: (({' '.join(repeated)}))")

    # MAWUSI 4 confirmation
    current = results[event_number - 1]
    win = current[:5]
    mac = current[5:10]
    base = win[3] + mac[2]
    bonus = 0
    if win[4] > 70: bonus += 7
    if win[4] % 17 == 0: bonus += 5
    if win[4] in [13,17,19,23,29,31,37,41,43,47]: bonus += 3
    weighted = win[2]*2 + mac[4]
    source_event = event_number - ((base + bonus + weighted) % 40 + 2)

    confirmed_sources = set()
    for i in range(1, len(results) - 2):
        if len([n for n in results[i + 1][:5] if n in results[i + 2][:5]]) >= 2:
            confirmed_sources.add(i)

    if source_event in confirmed_sources:
        print(f"\n[BRAIN] MAWUSI 4 ➤ NEXT PREDICTION IS HISTORICALLY CONFIRMED [OK]")
    else:
        print(f"\n[BRAIN] MAWUSI 4 ➤ NEXT PREDICTION IS NOT HISTORICALLY CONFIRMED [X]")

    os.system("pause")  # Keeps the terminal open on Windows

if __name__ == "__main__":
    main()
    input("\nPress Enter to close...")
