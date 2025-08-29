import os
import pandas as pd

# === MAWUSI 1, 2, 5 LOGIC from GENERAL_COMBO ===
def mawusi_1(results, event_number):
    try:
        current = results[event_number - 1]
        previous = results[event_number - 2]
        third_win = current[6]
        fifth_win_prev = previous[8]
        second_mac = current[9]
        idx = max(0, event_number - (third_win + fifth_win_prev + second_mac) - 14)
        row = results[idx]
        return [int(row[9]), int(row[6])]
    except:
        return None

def mawusi_2(results, event_number):
    try:
        current = results[event_number - 1]
        previous = results[event_number - 2]
        third_win = current[6]
        fifth_win_prev = previous[8]
        second_mac = current[9]
        idx = max(0, event_number - (third_win + fifth_win_prev + second_mac) - 9)
        row = results[idx]
        return [int(row[3]), int(row[0])]
    except:
        return None

def mawusi_5(results, event_number):
    try:
        current = results[event_number - 1]
        previous = results[event_number - 2]
        third_win = current[4]
        fifth_win_prev = previous[9]
        second_mac = current[9]
        idx = max(0, event_number - (third_win + fifth_win_prev + second_mac) - 1)
        row = results[idx]
        return [int(row[0]), int(row[4])]
    except:
        return None

# === AAA1 MASTER LOGIC (C1-C10 ONLY, PRINT IF ANY CONDITION FOUND) ===
def aaa1_master_predict(file_path):
    AI_THRESHOLDS = {
        "Monday": {"C8": 25.0, "C9": 6, "C10": 5},
        "Tuesday": {"C8": 26.32, "C9": 7, "C10": 4},
        "Midweek": {"C8": 26.25, "C9": 7, "C10": 4},
        "Thursday": {"C8": 26.43, "C9": 7, "C10": 4},
        "Friday": {"C8": 26.37, "C9": 7, "C10": 4},
        "National": {"C8": 24.95, "C9": 5, "C10": 1}
    }

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
            pred = ev.event[2]
            return i, pred

        def evaluate_conditions(self, s):
            c = []
            e = self.events
            if abs(e[s].event[2] - e[s].event[0]) in (1,10,11): c.append("C1")
            if s+1 in e and e[s+1].event[2] == 40: c.append("C2")
            if s+2 in e and e[s].machin[2] == e[s+2].event[2]: c.append("C3")
            if s-2 in e and e[s-2].event[2] == 84: c.append("C4")
            if s-3 in e and e[s-3].event[1] == 84: c.append("C5")
            if s-2 in e and s-3 in e and e[s-2].event[2] == e[s-3].event[1]: c.append("C6")
            if s-1 in e and any(x in e[s-1].event for x in [17,44,39]): c.append("C7")
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

        def run_latest(self):
            e = self.events
            latest = max(e)
            src, pred = self.predict_event(latest)
            conds = self.evaluate_conditions(src)
            if conds:
                print(f"\n📢 [AAA1 MASTER] Latest Event: {latest}")
                print(f"   ➡️ Prediction (W3): {pred}")
                print(f"   ✅ Conditions found: {conds}")
            else:
                print("\n[AAA1 MASTER] No C1–C10 conditions found for latest event. No prediction shown.")

    Predictor(file_path).run_latest()

# === ABOTH 6 LOGIC (PRINT ONLY IF BANKER OR MAC OR BOTH) ===
def aboth6_predict(file_path):
    df = pd.read_csv(file_path, delimiter='\t', header=None)
    latest_event_idx = len(df) - 1

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

    original_predictions, mac_predictions, banker_number = predict_at_event(latest_event_idx)
    show = False
    if banker_number or mac_predictions:
        show = True
    if show:
        print(f"\n📢 [ABOTH 6] Latest Event: {latest_event_idx + 1}")
        print(f"   🎯 Original System Predictions: {original_predictions}")
        if banker_number:
            print(f"   🔹 Banker: {banker_number}")
        if mac_predictions:
            print(f"   🎯 MAC System Predictions: {mac_predictions}")
        combined_all = sorted(set(original_predictions + mac_predictions))
        print(f"   🏆 FINAL COMBINED PREDICTIONS: {combined_all}")
    else:
        print("\n[ABOTH 6] No banker or MAC predictions for latest event.")

# === FILE SELECTION & MAIN ===
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

    # --- Read .txt file as rows of at least 10 ints ---
    with open(selected_file) as f:
        lines = [list(map(int, l.strip().split())) for l in f if len(l.strip().split()) >= 10]
    n_events = len(lines)

    print("\n━━━━━━━━━━ MAWUSI SYSTEMS ━━━━━━━━━━")
    out1 = mawusi_1(lines, n_events)
    out2 = mawusi_2(lines, n_events)
    out5 = mawusi_5(lines, n_events)
    print(f"MAWUSI 1: {out1}")
    print(f"MAWUSI 2: {out2}")
    print(f"MAWUSI 5: {out5}")

    print("\n━━━━━━━━━━ AAA1 MASTER ━━━━━━━━━━")
    aaa1_master_predict(selected_file)

    print("\n━━━━━━━━━━ ABOTH 6 ━━━━━━━━━━")
    aboth6_predict(selected_file)

    input("\nPress Enter to close...")

if __name__ == "__main__":
    main()
