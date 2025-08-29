import pandas as pd
import pyttsx3
import os

# === VOICE SETUP ===
engine = pyttsx3.init()
def speak(text):
    print("\n🗣 " + text)
    engine.say(text)
    engine.runAndWait()

# === MAIN PREDICTION FUNCTION ===
def run_combined_prediction(file_path):
    df = pd.read_csv(file_path, delimiter='\t', header=None)
    latest_event_idx = len(df) - 1
    start_event_number = latest_event_idx + 1
    history_depth = 550

    print(f"\n🗣 Processing file: {file_path} (Last Event: {start_event_number})")

    def predict_at_event(event_idx):
        try:
            if event_idx < 4:
                return [], [], None

            ref_numbers = [
                int(df.iloc[event_idx, 0]),
                int(df.iloc[event_idx - 1, 1]),
                int(df.iloc[event_idx - 2, 2]),
                int(df.iloc[event_idx - 3, 3]),
                int(df.iloc[event_idx - 4, 4]),
            ]
            reference_sum = sum(ref_numbers)

            if reference_sum >= len(df):
                return [], [], None

            event_ref = df.iloc[reference_sum - 1]
            sum_ref = int(event_ref[2]) + int(event_ref[3]) + int(event_ref[4])
            difference = abs(sum_ref - reference_sum)
            source_event_number = difference

            if source_event_number < 3 or source_event_number >= len(df):
                return [], [], None

            banker = None
            if source_event_number - 2 > 0:
                nums = df.iloc[source_event_number - 3, 0:5].dropna().astype(int).tolist()
                close_pairs = [(a, b) for i, a in enumerate(nums) for b in nums[i+1:] if abs(a - b) == 1]
                if close_pairs:
                    banker = max(max(pair) for pair in close_pairs)

            event_source = df.iloc[source_event_number - 1]
            main_predictions = [int(event_source[0]), int(event_source[2]), int(event_source[4])]
            if banker and banker not in main_predictions:
                main_predictions.append(banker)

            event_third_pred = reference_sum + sum_ref + 2
            third_prediction = []
            if event_third_pred < len(df):
                event_third = df.iloc[event_third_pred - 1]
                third_prediction = [int(event_third[0]), int(event_third[4])]

            original_final_predictions = sorted(set(main_predictions + third_prediction))

            mac_predictions = []
            try:
                mac_sum = sum([
                    int(df.iloc[event_idx, 6]),
                    int(df.iloc[event_idx, 7]),
                    int(df.iloc[event_idx, 8]),
                    int(df.iloc[event_idx - 1, 7]),
                    int(df.iloc[event_idx - 2, 7]),
                    int(df.iloc[event_idx - 4, 7]),
                ])
                combined_sum = mac_sum + reference_sum
                reference_event_mac = abs(combined_sum - (event_idx + 1))

                if 2 <= reference_event_mac + 1 < len(df):
                    mac_plus = df.iloc[reference_event_mac, 5:10].dropna().astype(int).tolist()
                    mac_minus = df.iloc[reference_event_mac - 2, 5:10].dropna().astype(int).tolist()
                    mac_predictions = sorted(set(num for num in mac_plus if num in mac_minus))
            except:
                pass

            return original_final_predictions, mac_predictions, banker

        except:
            return [], [], None

    # === STEP 1: CURRENT PREDICTION ===
    original_predictions, mac_predictions, banker_number = predict_at_event(latest_event_idx)

    if not original_predictions and not mac_predictions:
        print("[X] Unable to make a prediction for the latest event.")
        return

    print(f"\n🎯 Original System Predictions: {original_predictions}")
    if banker_number:
        print(f"🔹 Banker: {banker_number}")
    print(f"🎯 MAC System Predictions: {mac_predictions}")

    combined_all = sorted(set(original_predictions + mac_predictions))
    print(f"\n🎯 FINAL COMBINED PREDICTIONS for Event {start_event_number}: {combined_all}")
    speak("Combined predictions are ready.")
    speak(f"Prediction numbers are {', '.join(str(num) for num in combined_all)}")

    # === STEP 2: HISTORICAL CHECKING ===
    print("\n--- Historical Checking over Past 550 Events ---")
    historical_matches = []

    for event_number in range(start_event_number, start_event_number - history_depth, -1):
        idx = event_number - 1
        if idx < 0 or idx >= latest_event_idx:
            continue

        old_preds, mac_preds, _ = predict_at_event(idx)
        predictions = sorted(set(old_preds + mac_preds))
        if not predictions:
            continue

        next_idx = idx + 1
        if next_idx >= len(df):
            continue

        try:
            next_wins = df.iloc[next_idx, 0:5].dropna().astype(int).tolist()
            matched = [n for n in predictions if n in next_wins]
            if len(matched) >= 2:
                historical_matches.append((event_number, event_number+1, matched))
        except:
            continue

    if historical_matches:
        for orig_ev, match_ev, nums in historical_matches:
            print(f"[OK] Event {orig_ev} matched Event {match_ev}: {nums}")
    else:
        print("[X] No strong historical matches found across 550 events.")

    print(f"\n[OK] Total Matches Found: {len(historical_matches)} matches")


# === FILE SELECTION ===
def main():
    txt_files = [
        f for f in os.listdir()
        if os.path.isfile(f) and f.lower().endswith(".txt") and f.lower() != "a.code,counter.txt"
    ]

    if not txt_files:
        print("[X] No .txt files found.")
        return

    print("\n📂 Available .txt files:")
    for idx, f in enumerate(txt_files, 1):
        print(f"{idx}. {f}")

    try:
        choice = int(input("\nEnter file number to process: "))
        selected_file = txt_files[choice - 1]
    except (ValueError, IndexError):
        print("[X] Invalid selection.")
        return

    speak(f"Processing file: {selected_file}")
    run_combined_prediction(selected_file)

if __name__ == "__main__":
    main()
    input("\nPress Enter to close...")
