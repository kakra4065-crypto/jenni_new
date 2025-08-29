import os
from collections import Counter
import pyttsx3

# ========= Load Data ========= #
def load_data(file_path):
    with open(file_path, 'r') as f:
        return [list(map(int, line.split())) for line in f if line.strip()]

# ========= COMPLETE Formula ========= #
def complete(results, event_number, include_debug=False):
    try:
        current = results[event_number - 1]
        previous = results[event_number - 2]
        third_win = current[2]
        fourth_win_prev = previous[3]
        second_mac = current[6]
        idx = max(0, event_number - (third_win + fourth_win_prev + second_mac) - 1)
        if idx < 2 or idx + 2 >= len(results):
            return None, 0, None

        source = results[idx]
        source_event = idx
        two_sure = [source[0], source[4]]
        conditions_met = 0

        src = results[source_event][:5]
        src_mac = results[source_event][5:10]
        sm1 = results[source_event - 1][:5]
        sm2 = results[source_event - 2][:5]
        sp1 = results[source_event + 1][:5]
        sp2 = results[source_event + 2][:5]
        sp1_mac = results[source_event + 1][5:10]
        curr_mac = current[5:10]
        pm1 = results[event_number - 2][:5]

        def is_turning(a, b):
            return str(a).zfill(2)[::-1] == str(b).zfill(2)

        try:
            if sm2[2] == 23 or 19 in sm2: conditions_met += 1
            if sm1[0] == 23 and sm1[1] == 19:
                d = abs(sp1[1] - sp1[2])
                if d == 10 and max(sp1[1], sp1[2]) == sp1[1] and min(sp1[1], sp1[2]) == sp1[2]:
                    conditions_met += 1
            if src[3] == 2: conditions_met += 1
            if abs(sp1[2] - sp1[3]) == 10 and sp1[2] < sp1[3]: conditions_met += 1
            s_diffs = [abs(sm1[i] - sm1[j]) for i in range(5) for j in range(i+1, 5)]
            if 1 in s_diffs and 10 in s_diffs: conditions_met += 1
            if sm1[3] == 43: conditions_met += 1
            if sp1[3] == 44 and sp1[4] == 68: conditions_met += 1
            if src[1] in [21, 29]: conditions_met += 1
            if is_turning(src[4], src[3]): conditions_met += 1
            if src[4] - 1 == sm1[4]: conditions_met += 1
            if src[4] - 1 == src[3]: conditions_met += 1
            if src_mac[:3] == [90, 74, 10]: conditions_met += 1
            if sp1_mac[:2] == [70, 71]: conditions_met += 1
            mac_sums = [curr_mac[i] + curr_mac[j] for i in range(5) for j in range(i+1, 5)]
            if 84 in mac_sums and 22 in pm1: conditions_met += 1
            if src[3] == 34: conditions_met += 1
            if src[1] in sp1[:2]: conditions_met += 1
            if abs(sp1[0] - sp1[1]) == 1: conditions_met += 1
            if sp1[0] == sp2[2]: conditions_met += 1
            if src[3] == 21: conditions_met += 1
            if abs(sm1[2] - sm1[3]) == 10 and sm1[2] < sm1[3]: conditions_met += 1
        except:
            pass

        extra = []
        if conditions_met >= 1:
            extra.append(current[3])
        if include_debug:
            print(f"[COMPLETE] Source Event: {source_event + 1}")

        return sorted(set(two_sure + extra)), conditions_met, source_event + 1
    except:
        return None, 0, None

# ─── Main ──────────────────────────────────────────────────────────────────────
if __name__=="__main__":
    engine = pyttsx3.init()

    if not os.path.exists("a.code,counter.txt"):
        print("[X] Missing a.code,counter.txt"); exit(1)

    files = [f for f in os.listdir() if f.lower().endswith(".txt") and f!="a.code,counter.txt"]
    print("[FILES] Available .txt files:")
    for i,f in enumerate(files,1): print(f"  {i}: {f}")
    sel = int(input("Select a file: ")) - 1
    fname = files[sel]

    results = load_data(fname)
    event_number = len(results)

    print(f"\n📊 Running prediction on: {fname} | Latest Event: {event_number}")

    pred, conds, src_event = complete(results, event_number, include_debug=True)

    if pred:
        percentage = min(15 * conds, 100)
        message = f"Prediction from event {src_event}: {pred}. {conds} condition{'s' if conds != 1 else ''} met. Confidence: {percentage} percent."
        print(f"\n📌 {message}")
        engine.say(message)
        engine.runAndWait()
    else:
        print("[X] Prediction failed.")
        engine.say("Prediction failed.")
        engine.runAndWait()

    input("\nPress Enter to close...")
