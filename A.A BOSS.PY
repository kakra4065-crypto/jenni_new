import os
import pandas as pd
import numpy as np
import pyttsx3
from collections import defaultdict, Counter
from itertools import combinations

# AI logic thresholds per file
AI_THRESHOLDS = {
    "Monday": {"C8": 25.0, "C9": 6, "C10": 5},
    "Tuesday": {"C8": 26.32, "C9": 7, "C10": 4},
    "Midweek": {"C8": 26.25, "C9": 7, "C10": 4},
    "Thursday": {"C8": 26.43, "C9": 7, "C10": 4},
    "Friday": {"C8": 26.37, "C9": 7, "C10": 4}
}

def speak(msg):
    try:
        tts = pyttsx3.init()
        tts.setProperty('rate', 160)
        tts.say(msg)
        tts.runAndWait()
    except:
        print(f"(voice disabled) {msg}")

def evaluate_conditions(day, idx, df):
    logic = AI_THRESHOLDS.get(day, {})
    if not logic or idx < 1 or idx > len(df):
        return []

    row = df.iloc[idx - 1]
    nums = row[:5].tolist() + row[5:10].tolist()
    std = np.std(nums)
    evens = sum(1 for x in nums if x % 2 == 0)
    overlap = 0
    if idx > 1:
        prev = df.iloc[idx - 2, :5].tolist() + df.iloc[idx - 2, 5:10].tolist()
        overlap = len(set(nums) & set(prev))

    conds = []
    if std > logic["C8"]: conds.append("C8")
    if evens >= logic["C9"]: conds.append("C9")
    if overlap >= logic["C10"]: conds.append("C10")
    return conds

def safe_get(lookup, n, col):
    try:
        return lookup.loc[n, col]
    except:
        return 0

def run_prediction(filename):
    print(f"\n📂 Processing file: {filename}")
    day = os.path.splitext(os.path.basename(filename))[0].capitalize()

    df = pd.read_csv(filename, sep="\t", header=None)
    number_df = pd.read_csv("number.txt", sep="\t", header=None)
    number_df.columns = ["Num", "Cumpt", "Bonaz", "Strin"] + [f"X{i}" for i in range(6)]
    lookup = number_df.set_index("Num")[["Cumpt", "Bonaz", "Strin"]].fillna(0).astype(int)

    latest = len(df)
    win = df.iloc[-1, :5].tolist()
    mach = df.iloc[-1, 5:10].tolist()
    score = (
        safe_get(lookup, win[0], "Cumpt") +
        safe_get(lookup, win[1], "Bonaz") +
        safe_get(lookup, win[2], "Strin") +
        mach[0]*2 + mach[1]*4 + mach[2]*6
    )
    source = int(abs((score / 4) - latest))
    pred = df.iloc[source - 1, 2] if 0 <= source - 1 < len(df) else None

    print(f"🎯 Predicted W3: {pred} from source event {source}")

    latest_conds = evaluate_conditions(day, source, df)
    print(f"🧠 Triggered AI Conditions: {latest_conds}")

    # Build surroundings for similarity scoring
    latest_sur = []
    for j in range(latest - 5, latest + 6):
        if 0 <= j - 1 < len(df):
            latest_sur += df.iloc[j - 1, :5].tolist() + df.iloc[j - 1, 5:10].tolist()

    # Compare to past matches with same logic and position
    matches = []
    for i in range(40, latest - 1):
        row = df.iloc[i]
        w = row[:5].tolist()
        m = row[5:10].tolist()
        t = (
            safe_get(lookup, w[0], "Cumpt") +
            safe_get(lookup, w[1], "Bonaz") +
            safe_get(lookup, w[2], "Strin") +
            m[0]*2 + m[1]*4 + m[2]*6
        )
        src_i = int(abs((t / 4) - (i + 1)))
        if 0 <= src_i - 1 < len(df):
            pred_i = df.iloc[src_i - 1, 2]
        else:
            continue

        if pred_i in df.iloc[i + 1, :5].tolist():
            pos = df.iloc[i + 1, :5].tolist().index(pred_i) + 1
            conds_i = evaluate_conditions(day, src_i, df)
            if pos == 3 and set(conds_i) == set(latest_conds):
                hist_sur = []
                for j in range(i - 5, i + 6):
                    if 0 <= j < len(df):
                        hist_sur += df.iloc[j, :5].tolist() + df.iloc[j, 5:10].tolist()
                overlap = len(set(latest_sur) & set(hist_sur))
                matches.append((i + 1, overlap))

    if matches:
        top = sorted(matches, key=lambda x: -x[1])[0]
        print(f"✅ {len(matches)} past matches with same logic + W3")
        print(f"📊 Best overlap: {top[1]} numbers (Event {top[0]})")
        if top[1] >= 14:
            print("📈 Forecast Strength: STRONG")
            speak("Forecast strength is strong")
        elif top[1] >= 10:
            print("⚠️ Forecast Strength: MODERATE")
            speak("Forecast strength is moderate")
        else:
            print("❌ Forecast Strength: WEAK")
            speak("Forecast strength is weak")
    else:
        print("⚠️ No similar historical matches found.")
        speak("No matching history")

if __name__ == "__main__":
    print("📁 Available .txt files:")
    files = [f for f in os.listdir() if f.endswith(".txt")]
    for i, f in enumerate(files):
        print(f"{i+1}: {f}")
    try:
        choice = int(input("Select a file number to analyze: ")) - 1
        if 0 <= choice < len(files):
            run_prediction(files[choice])
        else:
            print("❌ Invalid selection.")
    except Exception as e:
        print(f"❌ Error: {e}")

    input("\nPress Enter to close...")
