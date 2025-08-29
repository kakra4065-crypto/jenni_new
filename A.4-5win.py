import os
import pandas as pd
import pyttsx3

# Initialize text-to-speech engine
tts = pyttsx3.init()
tts.setProperty('rate', 160)

def speak(msg):
    tts.say(msg)
    tts.runAndWait()

def load_all_txt_files():
    return {f: pd.read_csv(f, sep="\t", header=None) for f in os.listdir() if f.endswith(".txt")}

def apply_prediction_logic(event_idx, input_df, ref_df, ref_file):
    try:
        mac_4th = input_df.iloc[event_idx, 8]
        win_2nd = input_df.iloc[event_idx, 1]
    except IndexError:
        return None

    candidates = ref_df[(ref_df[3] == mac_4th) & (ref_df[4] == win_2nd)]
    if candidates.empty:
        return None

    source_idx = candidates.index[0]
    two_sure = []
    if source_idx + 1 < len(ref_df):
        two_sure = [ref_df.iloc[source_idx + 1, 3], ref_df.iloc[source_idx + 1, 4]]

    add_third = None
    if source_idx + 2 < len(ref_df):
        mac2_next = ref_df.iloc[source_idx + 1, 6]
        win2_next2 = ref_df.iloc[source_idx + 2, 1]
        if mac2_next == win2_next2:
            add_third = mac2_next

    banker = None
    condition_met = False
    if source_idx - 1 >= 0:
        if ref_df.iloc[source_idx - 1, 7] == 4:
            mac2_now = ref_df.iloc[source_idx, 6]
            banker = mac2_now + 1
            condition_met = True

    prediction = []
    if banker is not None:
        prediction.append(banker)
    if add_third is not None:
        prediction.append(add_third)
    prediction.extend(two_sure)

    return {
        "event": event_idx + 1,
        "ref_file": ref_file,
        "ref_event": source_idx + 1,
        "banker": banker,
        "two_sure": two_sure,
        "add_third": add_third,
        "condition_met": condition_met,
        "final_prediction": sorted(set(prediction))
    }

def run_prediction(input_file_name, all_data):
    input_df = all_data[input_file_name]
    other_files = {k: v for k, v in all_data.items() if k != input_file_name}
    latest_idx = len(input_df) - 1

    matches = []
    for ref_file, ref_df in other_files.items():
        result = apply_prediction_logic(latest_idx, input_df, ref_df, ref_file)
        if result:
            matches.append(result)
    return matches

if __name__ == "__main__":
    all_data = load_all_txt_files()
    txt_files = list(all_data.keys())

    print("\n📂 Available .txt files:")
    for i, name in enumerate(txt_files):
        print(f"{i + 1}: {name}")
    selected = int(input("\nSelect input file by number: ")) - 1
    input_file = txt_files[selected]

    print(f"\n🔍 Checking predictions for: {input_file}")
    matches = run_prediction(input_file, all_data)

    if not matches:
        print("❌ No prediction matches found in any file.")
    else:
        for m in matches:
            print(f"\n📄 Reference File: {m['ref_file']} (Event {m['ref_event']})")
            print(f"Banker: ({m['banker']})" if m['banker'] is not None else "Banker: ()")
            print(f"Two Sure: ({', '.join(map(str, m['two_sure']))})")
            all_nums = []
            if m['banker'] is not None:
                all_nums.append(m['banker'])
            if m['add_third'] is not None:
                all_nums.append(m['add_third'])
            all_nums.extend(m['two_sure'])
            print(f"All Together: ({', '.join(map(str, sorted(set(all_nums))) )})")

            if m['condition_met']:
                speak(f"Hello Professor Alema, your next prediction from {m['ref_file']} has met conditions and is so accurate to match the next draw.")

input("\nPress Enter to close...")
