import os
import pandas as pd

# --- Load Family Data ---
def load_family_data(family_file):
    headers = ['number', 'counter', 'bonanza', 'string', 'turning',
               'malta', 'partner', 'equivalent', 'shadow', 'code']
    family_dict = {}
    if not os.path.exists(family_file):
        print("[X] Family file not found.")
        return {}
    with open(family_file, 'r') as file:
        for line in file:
            parts = line.strip().split()
            if len(parts) != 10 or parts[0] == 'N':
                continue
            values = list(map(int, parts))
            num = values[0]
            family_dict[num] = {headers[i]: values[i] for i in range(1, 10)}
    return family_dict

# --- Get Win & MAC ---
def get_event_numbers(df, event_idx):
    if 0 <= event_idx < len(df):
        row = df.iloc[event_idx]
        if len(row.dropna()) >= 10:
            win = list(row[:5])
            mac = list(row[5:10])
            return win, mac
    return [], []

# --- Main Formula Logic ---
def process_event(data, family_map, current_event_num):
    try:
        current_idx = current_event_num - 1
        _, mac_current = get_event_numbers(data, current_idx)
        if len(mac_current) < 4:
            return None
        mac2_current = mac_current[1]

        _, mac_prev = get_event_numbers(data, current_idx - 5)
        if len(mac_prev) < 4:
            return None
        mac4_prev = mac_prev[3]

        diff = abs(mac2_current - mac4_prev)
        source_event_from = current_event_num - diff
        true_source_event = source_event_from - 4
        true_source_idx = true_source_event - 1

        _, mac_source = get_event_numbers(data, true_source_idx)
        if len(mac_source) < 2:
            return None
        banker = mac_source[1]

        _, mac_plus2 = get_event_numbers(data, true_source_idx + 2)
        if len(mac_plus2) < 2:
            return None
        mac2_plus2 = mac_plus2[1]
        condition_met = mac2_plus2 in [72, 35]

        win_source, _ = get_event_numbers(data, true_source_idx)
        if len(win_source) < 3:
            return None
        third_win = win_source[2]
        counter_of_third = family_map.get(third_win, {}).get("counter", 0)
        calc_value = counter_of_third + 3

        target_event = true_source_event - calc_value
        target_idx = target_event - 1
        win_reference, _ = get_event_numbers(data, target_idx)
        check_event = current_event_num - 18
        check_idx = check_event - 1
        win_check, _ = get_event_numbers(data, check_idx)

        main_two = sorted(list(set(win_reference) & set(win_check)))
        final_prediction = sorted(set(main_two + [banker]))

        return {
            "current_event": current_event_num,
            "banker": banker,
            "source_event": true_source_event,
            "condition_met": condition_met,
            "main_two_matches": main_two,
            "final_prediction": final_prediction,
            "reference_event": target_event,
            "reference_win_numbers": win_reference,
            "check_event": check_event,
            "check_win_numbers": win_check
        }
    except Exception:
        return None

# --- Evaluate prediction accuracy ---
def evaluate_prediction(hit_event_win_numbers, predicted_numbers, banker):
    hits = set(predicted_numbers) & set(hit_event_win_numbers)
    banker_hit = banker in hit_event_win_numbers
    return {
        "hits": list(hits),
        "hit_count": len(hits),
        "banker_hit": banker_hit
    }

# === MAIN SCRIPT ===
if __name__ == "__main__":
    # Select file from current folder (case-insensitive)
    all_txts = [f for f in os.listdir() if os.path.isfile(f) and f.lower().endswith(".txt")]
    if not all_txts:
        print("[X] No .txt files found in the current folder.")
        exit(1)

    print("\n📂 Available .txt files:")
    for idx, name in enumerate(all_txts):
        print(f"{idx + 1}: {name}")

    try:
        choice = int(input("\nSelect a file number: ")) - 1
        selected_file = all_txts[choice]
    except (ValueError, IndexError):
        print("[X] Invalid selection.")
        exit(1)

    family_file = "a.code,counter.txt"
    family_map = load_family_data(family_file)
    if not family_map:
        exit(1)

    data = pd.read_csv(selected_file, sep="\t", header=None)

    # --- Next Prediction (based on last event) ---
    last_event = len(data)
    next_result = process_event(data, family_map, last_event)

    if next_result:
        print(f"\n🔮 [CRYSTAL] NEXT PREDICTION for Event {last_event + 1}")
        for k, v in next_result.items():
            print(f"{k}: {v}")
    else:
        print("[X] Could not generate prediction for next event.")

    # --- Historical tracking ---
    history_results = []
    for event_num in range(50, len(data) - 1):
        result = process_event(data, family_map, event_num)
        if result:
            next_win, _ = get_event_numbers(data, event_num)
            eval_result = evaluate_prediction(next_win, result["final_prediction"], result["banker"])
            result.update(eval_result)
            result["evaluated_against_event"] = event_num + 1
            history_results.append(result)

    # Summary
    total_predictions = len(history_results)
    with_hits = [r for r in history_results if r["hit_count"] > 0]
    with_condition = [r for r in with_hits if r["condition_met"]]
    without_condition = [r for r in with_hits if not r["condition_met"]]

    print(f"\n📊 [CHART] HISTORICAL SUMMARY")
    print(f"🔢 Total Predictions: {total_predictions}")
    print(f"✅ Hits WITH Condition Met: {len(with_condition)}")
    print(f"➖ Hits WITHOUT Condition: {len(without_condition)}\n")

    print("🎯 Matches WITH Condition:")
    for r in with_condition[-3:]:
        print(f"Event {r['current_event']} → Event {r['evaluated_against_event']} | "
              f"Prediction: {r['final_prediction']} | Hits: {r['hits']} | "
              f"Banker: {r['banker']} {'✔' if r['banker_hit'] else '✘'} | Condition: [OK]")

    print("\n🎯 Matches WITHOUT Condition:")
    for r in without_condition[-3:]:
        print(f"Event {r['current_event']} → Event {r['evaluated_against_event']} | "
              f"Prediction: {r['final_prediction']} | Hits: {r['hits']} | "
              f"Banker: {r['banker']} {'✔' if r['banker_hit'] else '✘'} | Condition: [X]")

    input("\nPress Enter to close...")
