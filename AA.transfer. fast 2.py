import os
import time
import pandas as pd
import pyttsx3

# === CONFIG ===
VOICE_MODE = True

# Initialize text-to-speech engine
engine = pyttsx3.init()
engine.setProperty('rate', 160)
engine.setProperty('volume', 1.0)

# --- Load Data ---
def load_data(file_path):
    try:
        return pd.read_csv(file_path, sep="\t", header=None)
    except Exception as e:
        print(f"[WARN] Could not read {file_path}: {e}")
        return pd.DataFrame()

# --- Find Source Events ---
def find_source_events(data, first_machine, third_winning):
    return [
        i for i in range(len(data))
        if len(data.columns) >= 10 and data.iloc[i, 8] == first_machine and data.iloc[i, 9] == third_winning
    ]

# --- Check Conditions ---
def check_conditions(data, event_idx):
    if event_idx + 1 >= len(data) or event_idx - 2 < 0:
        return False, []

    passed_conditions = 0
    met_conditions = []

    # Condition 1
    third_mac = data.iloc[event_idx, 7]
    if third_mac - 1 == data.iloc[event_idx + 1, 8]:
        passed_conditions += 1
        met_conditions.append("4th machine next = current 3rd machine - 1")

    # Condition 2 (original + difference-of-1 for first two)
    two_back = data.iloc[event_idx - 2, :5].values
    if (
        (two_back[0] == 75 and two_back[1] == 74)
        or two_back[0] == 75
        or two_back[1] == 8
        or two_back[2] == 8
    ):
        passed_conditions += 1
        met_conditions.append("Two back fixed number check")
    elif abs(two_back[0] - two_back[1]) == 1:
        passed_conditions += 1
        met_conditions.append("Two back first & second differ by 1")

    # Condition 3
    next_event = data.iloc[event_idx + 1, :5].values
    if set([89, 8]).issubset(next_event) or set([8, 44]).issubset(next_event):
        passed_conditions += 1
        met_conditions.append("Next event contains (89,8) or (8,44)")

    # Condition 4
    if event_idx - 1 >= 0:
        back1_machine = data.iloc[event_idx - 1, 5:10].values
        if back1_machine[2] == 30 or back1_machine[3] == 34:
            passed_conditions += 1
            met_conditions.append("Prev machine has 30 in center or 34 in 4th")

    # Condition 5
    back2 = data.iloc[event_idx - 2, :5].values
    if 83 in (back2[1], back2[3]):
        passed_conditions += 1
        met_conditions.append("Two back has 83 in 2nd or 4th")

    # Condition 6
    if event_idx - 1 >= 0:
        prev_win = data.iloc[event_idx - 1, :5].values
        if any(abs(prev_win[i] - prev_win[j]) == 1 for i in range(5) for j in range(i + 1, 5)):
            passed_conditions += 1
            met_conditions.append("Prev win has two numbers diff of 1")

    return passed_conditions >= 1, met_conditions

# --- Check Last Event ---
def check_last_event_conditions(selected_data, reference_datasets):
    last_event_index = len(selected_data) - 1
    first_machine = selected_data.iloc[last_event_index, 5]
    third_winning = selected_data.iloc[last_event_index, 2]
    matched_details = []
    for ref_name, ref_data in reference_datasets.items():
        for src_idx in find_source_events(ref_data, first_machine, third_winning):
            passed, met_conditions = check_conditions(ref_data, src_idx)
            if passed:
                prediction = ref_data.iloc[src_idx, :5].values.tolist()
                matched_details.append({
                    "file": ref_name,
                    "source_event": src_idx + 1,
                    "prediction": prediction,
                    "conditions": met_conditions
                })
    return matched_details

# --- Main ---
def main():
    txt_files = [f for f in os.listdir() if f.lower().endswith('.txt')]
    if not txt_files:
        print("[X] No .txt files found.")
        return

    print("\n[FILES] Available .txt files:")
    for idx, file in enumerate(txt_files):
        print(f"{idx + 1}: {file}")

    try:
        choice = int(input(f"\nSelect a file by number (1-{len(txt_files)}): ")) - 1
        selected_file = txt_files[choice]
    except (ValueError, IndexError):
        print("[X] Invalid selection.")
        return

    print(f"\n🚀 Checking latest event in: {selected_file}")
    start_time = time.time()

    selected_data = load_data(selected_file)
    if selected_data.empty:
        print(f"[X] Selected file is empty or unreadable.")
        return

    reference_datasets = {}
    for ref_file in txt_files:
        data = load_data(ref_file)
        if not data.empty:
            reference_datasets[ref_file] = data

    matched_files = check_last_event_conditions(selected_data, reference_datasets)
    if matched_files:
        print("\n📌 Matches found for latest event with conditions:")
        for match in matched_files:
            print(f"- {match['file']} (Event {match['source_event']}) => Prediction: {match['prediction']}")
            print(f"   Conditions met: {', '.join(match['conditions'])}")
        if VOICE_MODE:
            engine.say("Predictions found for the latest event.")
            engine.runAndWait()
    else:
        print("[X] No matches found for latest event.")

    print(f"\n⏱️ Total processing time: {time.time() - start_time:.2f} seconds")
    print("\n📌 Developed by Alema Samuel Odame Junior")
    input("\nPress Enter to close...")

if __name__ == "__main__":
    main()
