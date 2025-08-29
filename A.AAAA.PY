import os
from collections import defaultdict, Counter
from itertools import combinations
import pyttsx3
import numpy as np
import pandas as pd

def ordinal(n):
    if 10 <= n % 100 <= 20:
        return f"{n}th"
    return f"{n}{ {1:'st', 2:'nd', 3:'rd'}.get(n % 10, 'th') }"

# Per-day AI logic thresholds from A.A BOS
AI_THRESHOLDS = {
    "Monday": {"C8": 25.0, "C9": 6, "C10": 5},
    "Tuesday": {"C8": 26.32, "C9": 7, "C10": 4},
    "Midweek": {"C8": 26.25, "C9": 7, "C10": 4},
    "Thursday": {"C8": 26.43, "C9": 7, "C10": 4},
    "Friday": {"C8": 26.37, "C9": 7, "C10": 4}
}

class All_numbers:
    def __init__(self):
        self.dic = {}
        try:
            with open("number.txt", "r") as f:
                for line in f:
                    parts = line.strip().split("\t")
                    if len(parts) >= 4:
                        try:
                            n = int(parts[0])
                            self.dic[n] = type("Num", (), {
                                "Cumpt": int(parts[1]),
                                "Bonaz": int(parts[2]),
                                "Strin": int(parts[3])
                            })()
                        except: continue
        except FileNotFoundError:
            print("number.txt not found")

    def get_Cumpt(self, n): return self.dic[n].Cumpt if n in self.dic else 0
    def get_Bonaz(self, n): return self.dic[n].Bonaz if n in self.dic else 0
    def get_Strin(self, n): return self.dic[n].Strin if n in self.dic else 0

class Event:
    def __init__(self, data, index):
        self.Numero = index
        self.event = list(map(int, data[:5]))
        self.machin = list(map(int, data[5:10]))

class Predictor:
    def __init__(self, file_path):
        self.file_path = file_path
        self.day = os.path.splitext(os.path.basename(file_path))[0].capitalize()
        self.events = self.load_events()
        self.all_n = All_numbers()
        self.tts = pyttsx3.init()
        self.tts.setProperty('rate', 160)

    def speak(self, msg):
        print(f"🔊 {msg}")
        try:
            self.tts.say(msg)
            self.tts.runAndWait()
        except Exception as e:
            print(f"(voice disabled) {msg}")

    def load_events(self):
        events = {}
        with open(self.file_path, "r") as f:
            for idx, line in enumerate(f):
                parts = line.strip().split()
                if len(parts) >= 10:
                    nums = list(map(int, parts[:10]))
                    events[idx+1] = Event(nums, idx+1)
        return events

    def predict_event(self, i):
        if i not in self.events:
            return None, None
        ev = self.events[i]
        result = self.all_n.get_Cumpt(ev.event[0]) + self.all_n.get_Bonaz(ev.event[1]) + self.all_n.get_Strin(ev.event[2])
        mach = ev.machin[0]*2 + ev.machin[1]*4 + ev.machin[2]*6
        total = result + mach
        source = int(abs((total / 4) - ev.Numero))
        if source in self.events:
            return source, self.events[source].event[2]
        return source, None

    def evaluate_conditions(self, s):
        c = []
        e = self.events
        # Your own logic C1–C7 (unchanged)
        if abs(e[s].event[2] - e[s].event[0]) in (1,10,11): c.append("C1")
        if s+1 in e and e[s+1].event[2] == 40: c.append("C2")
        if s+2 in e and e[s].machin[2] == e[s+2].event[2]: c.append("C3")
        if s-2 in e and e[s-2].event[2] == 84: c.append("C4")
        if s-3 in e and e[s-3].event[1] == 84: c.append("C5")
        if s-2 in e and s-3 in e and e[s-2].event[2] == e[s-3].event[1]: c.append("C6")
        if s-1 in e and any(x in e[s-1].event for x in [17,44,39]): c.append("C7")
        # --- C8–C10: AI day-specific logic (as in A.A BOS) ---
        logic = AI_THRESHOLDS.get(self.day, {"C8": 25.0, "C9": 6, "C10": 5})
        s_ev = []
        for j in range(s-5, s+6):
            if j in e:
                s_ev += e[j].event + e[j].machin
        if len(s_ev) > 0:
            avg = sum(s_ev) / len(s_ev)
            stddev = (sum((x - avg)**2 for x in s_ev) / len(s_ev))**0.5
            if stddev > logic["C8"]:
                c.append("C8")
        even_count = sum(1 for x in e[s].event + e[s].machin if x % 2 == 0)
        if even_count >= logic["C9"]:
            c.append("C9")
        if s > 1:
            prev = e[s - 1].event + e[s - 1].machin
            overlap = len(set(e[s].event + e[s].machin) & set(prev))
            if overlap >= logic["C10"]:
                c.append("C10")
        return c

    def run(self):
        e = self.events
        latest = max(e)
        # ... [all your original reporting logic, unchanged] ...

        # At the end, run your main overlap check:
        src, pred = self.predict_event(latest)
        if src:
            conds = self.evaluate_conditions(src)
            self.forecast_strength_overlap(src, conds)

        # Then run the BOS overlap logic using pandas
        self.aabos_overlap_report()

    def forecast_strength_overlap(self, src, conds, predicted_pos=3, window=5):
        e = self.events
        latest = max(e)
        latest_surroundings = []
        for j in range(latest - window, latest + window + 1):
            if j in e:
                latest_surroundings += e[j].event + e[j].machin
        historical_matches = []
        for i in range(40, latest - 1):
            src_i, pred_i = self.predict_event(i)
            if not src_i or not pred_i or (i+1) not in e: continue
            conds_i = self.evaluate_conditions(src_i)
            if pred_i in e[i+1].event[:5]:
                pos_i = e[i+1].event.index(pred_i) + 1
                if pos_i == predicted_pos and set(conds_i) == set(conds):
                    hist_sur = []
                    for j in range(i - window, i + window + 1):
                        if j in e:
                            hist_sur += e[j].event + e[j].machin
                    overlap = len(set(latest_surroundings) & set(hist_sur))
                    historical_matches.append({
                        "event": i+1,
                        "source": src_i,
                        "overlap": overlap,
                        "predicted": pred_i,
                        "position": pos_i,
                        "conditions": conds_i,
                    })
        print("\n🔍 [Your main logic] Overlap Forecast Strength Check:")
        if historical_matches:
            historical_matches.sort(key=lambda x: -x["overlap"])
            best = historical_matches[0]
            print(f"✅ Found {len(historical_matches)} past matches with same logic + position.")
            print(f"   Best match: Event {best['event']} (source {best['source']})")
            print(f"   Overlap with latest: {best['overlap']}/20 numbers")
            if best['overlap'] >= 14:
                print("📈 Forecast Strength: STRONG")
            elif best['overlap'] >= 10:
                print("⚠️ Forecast Strength: MODERATE")
            else:
                print("❌ Forecast Strength: WEAK")
            print("\n📜 Historical events with this logic (and their overlaps):")
            for match in historical_matches:
                print(f"  - Event {match['event']}: overlap={match['overlap']} [source {match['source']}, pred={match['predicted']}, pos={match['position']}, conds={match['conditions']}]")
            used_events = [m['event'] for m in historical_matches]
            print(f"\n📊 This logic/position combo was used in events: {used_events}")
            print(f"   (Best overlap: {best['overlap']} at event {best['event']})")
        else:
            print("⚠️ No similar historical match found for same conditions and position.")

    def aabos_overlap_report(self, window=5):
        # Load file fresh as BOS style expects
        df = pd.read_csv(self.file_path, sep="\t", header=None)
        num_df = pd.read_csv("number.txt", sep="\t", header=None)
        lookup = {}
        for _, row in num_df.iterrows():
            if row[0] not in lookup:
                lookup[int(row[0])] = {"Cumpt": int(row[1]), "Bonaz": int(row[2]), "Strin": int(row[3])}
        day = self.day
        ai_thresholds = AI_THRESHOLDS
        latest = len(df)
        # BOS prediction logic
        def bos_predict_event(i, df, lookup):
            if i < 1 or i > len(df):
                return None, None
            row = df.iloc[i - 1]
            win = row[:5].tolist()
            mach = row[5:10].tolist()
            score = (
                lookup.get(win[0], {}).get("Cumpt", 0) +
                lookup.get(win[1], {}).get("Bonaz", 0) +
                lookup.get(win[2], {}).get("Strin", 0) +
                mach[0]*2 + mach[1]*4 + mach[2]*6
            )
            source = int(abs((score / 4) - i))
            pred = df.iloc[source - 1, 2] if 0 <= source - 1 < len(df) else None
            return source, pred
        def bos_evaluate_conditions(day, idx, df, ai_thresholds, lookup):
            logic = ai_thresholds.get(day, {})
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
        src, pred = bos_predict_event(latest, df, lookup)
        conds = bos_evaluate_conditions(day, src, df, ai_thresholds, lookup)
        latest_sur = []
        for j in range(latest - window, latest + window + 1):
            if 0 <= j - 1 < len(df):
                latest_sur += df.iloc[j - 1, :5].tolist() + df.iloc[j - 1, 5:10].tolist()
        historical_matches = []
        for i in range(40, latest - 1):
            src_i, pred_i = bos_predict_event(i, df, lookup)
            if not src_i or not pred_i or not (0 <= src_i - 1 < len(df)): continue
            conds_i = bos_evaluate_conditions(day, src_i, df, ai_thresholds, lookup)
            if pred_i in df.iloc[i, :5].tolist():
                pos_i = df.iloc[i, :5].tolist().index(pred_i) + 1
                if pos_i == 3 and set(conds_i) == set(conds):
                    hist_sur = []
                    for j in range(i - window, i + window + 1):
                        if 0 <= j - 1 < len(df):
                            hist_sur += df.iloc[j - 1, :5].tolist() + df.iloc[j - 1, 5:10].tolist()
                    overlap = len(set(latest_sur) & set(hist_sur))
                    historical_matches.append({
                        "event": i+1,
                        "source": src_i,
                        "overlap": overlap,
                        "predicted": pred_i,
                        "position": pos_i,
                        "conditions": conds_i,
                    })
        print("\n🔍 [A.A BOS stand-alone style] Overlap Forecast Strength Check:")
        if historical_matches:
            historical_matches.sort(key=lambda x: -x["overlap"])
            best = historical_matches[0]
            print(f"✅ Found {len(historical_matches)} past matches with same logic + position.")
            print(f"   Best match: Event {best['event']} (source {best['source']})")
            print(f"   Overlap with latest: {best['overlap']}/20 numbers")
            if best['overlap'] >= 14:
                print("📈 Forecast Strength: STRONG")
            elif best['overlap'] >= 10:
                print("⚠️ Forecast Strength: MODERATE")
            else:
                print("❌ Forecast Strength: WEAK")
            print("\n📜 Historical events with this logic (and their overlaps):")
            for match in historical_matches:
                print(f"  - Event {match['event']}: overlap={match['overlap']} [source {match['source']}, pred={match['predicted']}, pos={match['position']}, conds={match['conditions']}]")
            used_events = [m['event'] for m in historical_matches]
            print(f"\n📊 This logic/position combo was used in events: {used_events}")
            print(f"   (Best overlap: {best['overlap']} at event {best['event']})")
        else:
            print("⚠️ No similar historical match found for same conditions and position.")

if __name__ == "__main__":
    files = sorted([f for f in os.listdir('.') if os.path.isfile(f) and f.lower().endswith('.txt')])
    print("📂 Available .txt files:")
    for i, f in enumerate(files):
        print(f"{i+1}: {f}")
    try:
        idx = int(input("Select a file number: ")) - 1
        Predictor(files[idx]).run()
    except:
        print("❌ Invalid selection.")

    input("\nPress Enter to close...")
