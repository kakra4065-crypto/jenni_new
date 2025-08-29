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
# --- Find and replace your AI_THRESHOLDS dictionary:
AI_THRESHOLDS = {
    "Monday": {"C8": 25.0, "C9": 6, "C10": 5},
    "Tuesday": {"C8": 26.32, "C9": 7, "C10": 4},
    "Midweek": {"C8": 26.25, "C9": 7, "C10": 4},
    "Thursday": {"C8": 26.43, "C9": 7, "C10": 4},
    "Friday": {"C8": 26.37, "C9": 7, "C10": 4},
    "National": {"C8": 24.95, "C9": 5, "C10": 1}
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
        # --- C8–C10: AI day-specific logic (Monday–Friday thresholds) ---
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
        hits = []
        grouped = defaultdict(list)
        pair_groups = defaultdict(lambda: defaultdict(set))
        triplet_groups = defaultdict(lambda: defaultdict(set))
        global_pairs = defaultdict(set)
        global_trips = defaultdict(set)
        seen_39_by_pos = defaultdict(set)
        seen_39_all = set()
        condition_summary = defaultdict(list)

        for i in range(5, latest):
            src, pred = self.predict_event(i)
            if not (src and pred and (i+1) in e): continue
            if pred in e[i+1].event[:5]:
                pos = e[i+1].event.index(pred) + 1
                conds = self.evaluate_conditions(src)
                plus2 = i + 3
                nums = e[plus2].event[:5] if plus2 in e else []
                hits.append((i+1, pred, src, pos, plus2, conds, nums))
                for pair in combinations(nums, 2):
                    pair_groups[pos][pair].add(plus2)
                    global_pairs[pair].add(plus2)
                for trip in combinations(nums, 3):
                    triplet_groups[pos][trip].add(plus2)
                    global_trips[trip].add(plus2)
                for cond in conds:
                    condition_summary[cond].append(i+1)
                if 39 in nums:
                    seen_39_by_pos[pos].add(plus2)
                    seen_39_all.add(plus2)

        print("\n📈 Historical Matches:")
        for ev, pred, src, pos, p2, conds, nums in hits:
            print(f"🔁 {pred} from source event {src} matched at event {ev}")
            print(f"   📍 Matched at: {ordinal(pos)} win")
            print(f"   🧠 Conditions: {conds}")
            print(f"   ➕ Event+2: {p2}")
            if 39 in nums:
                print(f"   🔢 Contains 39: ✅")

        print("\n📊 Global Shared Patterns (Match+2s):")
        for pair, evs in global_pairs.items():
            if len(evs) > 1:
                print(f"   🔁 Pair {pair} seen in events: {sorted(evs)}")
        for trip, evs in global_trips.items():
            if len(evs) > 1:
                print(f"   🔁 Triplet {trip} seen in events: {sorted(evs)}")

        print("\n🧠 Condition Match Events Summary:")
        for cond, events in sorted(condition_summary.items()):
            tag = "🔵" if cond in ["C1","C2","C3","C4","C5","C6","C7"] else "🟡"
            label = "your logic" if tag == "🔵" else "AI logic"
            print(f"   {tag} {cond} ({label}): matched in events {sorted(events)}")

        all_hits = set(ev for ev, *_ in hits)
        your_matched = set(e for c, evs in condition_summary.items() if c in ["C1","C2","C3","C4","C5","C6","C7"] for e in evs)
        ai_matched = set(e for c, evs in condition_summary.items() if c in ["C8","C9","C10"] for e in evs)
        both = your_matched & ai_matched
        only_your = your_matched - ai_matched
        only_ai = ai_matched - your_matched
        neither = all_hits - (your_matched | ai_matched)

        print("\n📋 Detailed Matches:")
        for ev, pred, _, pos, _, _, _ in hits:
            tag = "⚪ No condition"
            if ev in both:
                tag = "✅ Both logics"
            elif ev in only_your:
                tag = "🔵 Your logic only"
            elif ev in only_ai:
                tag = "🟡 AI logic only"
            print(f"   {tag}: Event {ev} ➜ Predicted W3: {pred} matched at W{pos}")

        print("\n📊 Match Summary:")
        print(f"   ✅ Both logics matched: {sorted(both)}")
        print(f"   🔵 Your conditions only: {sorted(only_your)}")
        print(f"   🟡 AI conditions only: {sorted(only_ai)}")
        print(f"   ⚪ No condition matched: {sorted(neither)}")
        print("\n📊 Global Repeated Pairs and Triplets in Matched+2 Events")

        pair_counts = defaultdict(set)
        triplet_counts = defaultdict(set)

        for _, _, _, _, p2, _, _ in hits:
            if p2 in e:
                nums = e[p2].event[:5]
                for pair in combinations(nums, 2):
                    pair_counts[tuple(sorted(pair))].add(p2)
                for triplet in combinations(nums, 3):
                    triplet_counts[tuple(sorted(triplet))].add(p2)

        repeated_pairs = {p: evs for p, evs in pair_counts.items() if len(evs) > 1}
        repeated_triplets = {t: evs for t, evs in triplet_counts.items() if len(evs) > 1}

        print("\n🔁 Repeated Pairs (2+ appearances):")
        if repeated_pairs:
            for pair, evs in sorted(repeated_pairs.items(), key=lambda x: (-len(x[1]), x[0])):
                print(f"- Pair {pair} appeared {len(evs)} times — events: {sorted(evs)}")
        else:
            print("⚠️ No repeated pairs found.")

        print("\n🔁 Repeated Triplets (2+ appearances):")
        if repeated_triplets:
            for triplet, evs in sorted(repeated_triplets.items(), key=lambda x: (-len(x[1]), x[0])):
                print(f"- Triplet {triplet} appeared {len(evs)} times — events: {sorted(evs)}")
        else:
            print("⚠️ No repeated triplets found.")

        print("\n🧠 Deep Dive: AI-Only Logic Matches (C8–C10 without C1–C7)")
        ai_conditions = {"C8", "C9", "C10"}
        your_conditions = {"C1", "C2", "C3", "C4", "C5", "C6", "C7"}

        ai_matched = set(e for c, evs in condition_summary.items() if c in ai_conditions for e in evs)
        your_matched = set(e for c, evs in condition_summary.items() if c in your_conditions for e in evs)

        ai_only = ai_matched - your_matched

        ai_pair_counter = defaultdict(int)
        ai_triplet_counter = defaultdict(int)
        ai_pair_sources = defaultdict(set)
        ai_triplet_sources = defaultdict(set)

        for ev, pred, src, pos, p2, conds, nums in hits:
            if ev in ai_only and p2 in e:
                nums_p2 = e[p2].event[:5]
                for pair in combinations(nums_p2, 2):
                    ai_pair_counter[pair] += 1
                    ai_pair_sources[pair].add(p2)
                for triplet in combinations(nums_p2, 3):
                    ai_triplet_counter[triplet] += 1
                    ai_triplet_sources[triplet].add(p2)

        shared_ai_pairs = [p for p, cnt in ai_pair_counter.items() if cnt > 1]
        shared_ai_triplets = [t for t, cnt in ai_triplet_counter.items() if cnt > 1]

        print(f"🔍 AI-only matched events: {sorted(ai_only)}")
        if shared_ai_pairs:
            print("\n🔁 Shared Pairs from AI-only logic:")
            for p in shared_ai_pairs:
                print(f"   Pair {p} appeared in +2 of events: {sorted(ai_pair_sources[p])}")
        else:
            print("⚠️ No shared pairs found in AI-only logic matches.")

        if shared_ai_triplets:
            print("\n🔁 Shared Triplets from AI-only logic:")
            for t in shared_ai_triplets:
                print(f"   Triplet {t} appeared in +2 of events: {sorted(ai_triplet_sources[t])}")
        else:
            print("⚠️ No shared triplets found in AI-only logic matches.")
        print("\n🌐 Global Pattern Matches Without Any Condition Logic")

        all_condition_events = your_matched.union(ai_matched)
        global_only_events = set(ev for ev, *_ in hits) - all_condition_events

        global_pair_counter = defaultdict(int)
        global_triplet_counter = defaultdict(int)
        global_pair_events = defaultdict(set)
        global_triplet_events = defaultdict(set)

        for ev, pred, src, pos, p2, conds, nums in hits:
            if ev in global_only_events and p2 in e:
                nums_p2 = e[p2].event[:5]
                for pair in combinations(nums_p2, 2):
                    global_pair_counter[pair] += 1
                    global_pair_events[pair].add(p2)
                for triplet in combinations(nums_p2, 3):
                    global_triplet_counter[triplet] += 1
                    global_triplet_events[triplet].add(p2)

        shared_global_pairs = [p for p, cnt in global_pair_counter.items() if cnt > 1]
        shared_global_triplets = [t for t, cnt in global_triplet_counter.items() if cnt > 1]

        print(f"🧩 Events where match occurred without C1–C10: {sorted(global_only_events)}")

        if shared_global_pairs:
            print("\n🔁 Shared Global Pairs (No Logic):")
            for p in shared_global_pairs:
                print(f"   Pair {p} appeared in events: {sorted(global_pair_events[p])}")
        else:
            print("⚠️ No shared pairs found in global-only matches.")

        if shared_global_triplets:
            print("\n🔁 Shared Global Triplets (No Logic):")
            for t in shared_global_triplets:
                print(f"   Triplet {t} appeared in events: {sorted(global_triplet_events[t])}")
        else:
            print("⚠️ No shared triplets found in global-only matches.")

        src, pred = self.predict_event(latest)
        if src:
            conds = self.evaluate_conditions(src)
            print("\n📌 Next Prediction Based on Historical Data:")
            print(f"🎯 Latest Event: {latest}")
            print(f"📍 Source Event: {src}")
            print(f"🔢 Predicted W3: ((({pred})))")
            print(f"✅ Conditions Met: {conds}")
            if not conds:
                print("🧠 No conditions met — likely to play from global triplets/pairs or 39")
            self.speak(f"{len(conds)} conditions matched. Confidence {len(conds)*15} percent.")

        # FINAL: Show your overlap forecast strength
        src, pred = self.predict_event(latest)
        if src:
            conds = self.evaluate_conditions(src)
            self.forecast_strength_overlap(src, conds)

        # FINAL: Show the BOS overlap forecast strength, for side-by-side comparison
        self.bos_overlap_report()

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

    # === BOS stand-alone overlap logic using pandas, for true A.A BOS result
    def bos_overlap_report(self, window=5):
        df = pd.read_csv(self.file_path, sep="\t", header=None)
        num_df = pd.read_csv("number.txt", sep="\t", header=None)
        lookup = {}
        for _, row in num_df.iterrows():
            if row[0] not in lookup:
                lookup[int(row[0])] = {"Cumpt": int(row[1]), "Bonaz": int(row[2]), "Strin": int(row[3])}
        day = os.path.splitext(os.path.basename(self.file_path))[0].capitalize()
        ai_thresholds = AI_THRESHOLDS
        latest = len(df)
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
