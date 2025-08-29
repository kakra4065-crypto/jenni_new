import os
import sys
import pyttsx3
from math import sqrt
from collections import Counter
from scipy.stats import f_oneway
from sklearn.metrics import pairwise_distances

# ─── Text-to-speech setup ───────────────────────────────────────────────────────
tts = pyttsx3.init()
tts.setProperty('rate', 160)
def speak(msg: str):
    """
    Prints and speaks the given message.
    """
    print("🗣️", msg)
    try:
        tts.say(msg)
        tts.runAndWait()
    except:
        pass

# ─── DATA LOADING HELPERS ────────────────────────────────────────────────────────
def load_lotto_file(path: str):
    """
    Reads a lottery .txt file (space- or tab-delimited).
    Returns a list of rows, each a list of ints. Skips any line with fewer than 10 ints.
    """
    data = []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            parts = line.strip().split()
            try:
                nums = list(map(int, parts))
            except:
                continue
            if len(nums) >= 10:
                data.append(nums)
    return data

def load_family_map_full(path: str):
    """
    Loads a.code,counter.txt into a dict for A.bestest4 logic:
      { number: {"counter": int, "bonanza": int, "string": int, "turning": int} }
    Only lines with exactly 10 ints are used.
    """
    fam = {}
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) != 10:
                continue
            try:
                nums = list(map(int, parts))
            except:
                continue
            key = nums[0]
            fam[key] = {
                "counter": nums[1],
                "bonanza": nums[2],
                "string": nums[3],
                "turning": nums[4]
            }
    return fam

def load_family_map_simple(path: str):
    """
    Loads a.code,counter.txt into a dict for A.bestest3 logic:
      { number: turning } (the 5th column).
    """
    fam = {}
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) != 10:
                continue
            try:
                nums = list(map(int, parts))
            except:
                continue
            key = nums[0]
            fam[key] = nums[4]
    return fam

def get_context_set(data: list, event_index: int, window: int = 9):
    """
    Collects all numbers (5 wins + 5 macs) from the `window` events preceding event_index.
    Returns a set of ints. If fewer than `window` draws exist, takes what's available.
    """
    ctx = []
    for d in range(1, window + 1):
        idx = event_index - d
        if idx < 0:
            break
        row = data[idx]
        ctx.extend(row[0:5])
        ctx.extend(row[5:10])
    return set(ctx)

# ─── SHARED CONDITIONS AROUND “two_sure” ─────────────────────────────────────────
def compute_shared_conditions(src_idx: int, data: list):
    """
    Three shared conditions, evaluated around the “source” event (src_idx, zero-based):
      S1: (src_idx - 1)th event’s 3rd win == src event’s 5th win
      S2: (src_idx + 1)th event’s 2nd win == 61
      S3: src event’s 3rd mac (index 7) == 13

    Returns (score:int, flags:dict) where flags = {"S1":bool, "S2":bool, "S3":bool}.
    """
    flags = {"S1": False, "S2": False, "S3": False}
    n = len(data)

    # S1: previous event’s 3rd win equals this event’s 5th win
    if src_idx - 1 >= 0:
        prev = data[src_idx - 1]
        cur = data[src_idx]
        if len(prev) >= 3 and len(cur) >= 5 and prev[2] == cur[4]:
            flags["S1"] = True

    # S2: next event’s 2nd win == 61
    if src_idx + 1 < n:
        nxt = data[src_idx + 1]
        if len(nxt) >= 2 and nxt[1] == 61:
            flags["S2"] = True

    # S3: this event’s 3rd mac (index 7) == 13
    cur = data[src_idx]
    if len(cur) >= 8 and cur[7] == 13:
        flags["S3"] = True

    score = sum(1 for v in flags.values() if v)
    return score, flags

# ─── A.bestest4.py LOGIC ─────────────────────────────────────────────────────────
def evaluate_event_best4(idx: int, data: list, fam_map: dict):
    """
    Returns {"event", "src", "two_sure", "extras", "pred"} or None.
    Always forms prediction = two_sure (first two wins at src) + extras (macs[0,2,4] from src+158).
    """
    row = data[idx]
    if len(row) < 10:
        return None
    mac_weighted = row[5]*2 + row[6]*4 + row[7]*6
    fam1 = fam_map.get(row[0])
    fam2 = fam_map.get(row[1])
    fam3 = fam_map.get(row[2])
    if fam1 is None or fam2 is None or fam3 is None:
        return None
    transformed_sum = fam1["counter"] + fam2["bonanza"] + fam3["string"]
    win_total = sum(row[0:5]) * 2
    mac_total = sum(row[5:10])
    combined = mac_weighted + transformed_sum + win_total + mac_total
    src = int(combined / 6) + row[5]
    if not (1 <= src <= len(data)):
        return None
    win_src = data[src - 1][0:5]
    two_sure = win_src[0:2]
    ev2 = src + 158
    extras = []
    if 1 <= ev2 <= len(data):
        ev2_row = data[ev2 - 1]
        if len(ev2_row) >= 10:
            macs2 = ev2_row[5:10]
            # Always extract the three extras, regardless of conditions
            extras = [macs2[0], macs2[2], macs2[4]]
    pred = sorted(set(two_sure + extras))
    return {
        "event": idx + 1,
        "src": src,
        "two_sure": two_sure,
        "extras": extras,
        "pred": pred
    }

def check_conditions_best4(src_idx: int, data: list):
    """
    Returns (score:int, flags:dict) for best4’s +158 source index.
    cond4: previous event's 9th column == 32
    cond5a: event+2's 8th column in [24,79]
    cond5b: event+1's first-5 contains 17 or 87
    cond6: in prev row, adjacent win differ by 1 and that number appears in next1's macs
    cond7: in event-3, wins[2] and wins[3] differ by 1 ascending
    """
    flags = {"cond4": False, "cond5a": False, "cond5b": False, "cond6": False, "cond7": False}
    n = len(data)
    if src_idx - 1 >= 0:
        prev = data[src_idx - 1]
        if len(prev) >= 9 and prev[8] == 32:
            flags["cond4"] = True
    next1 = data[src_idx + 1] if src_idx + 1 < n else None
    next2 = data[src_idx + 2] if src_idx + 2 < n else None
    if next2 and len(next2) >= 8 and next2[7] in [24, 79]:
        flags["cond5a"] = True
    if next1 and len(next1) >= 5 and any(x in [17, 87] for x in next1[0:5]):
        flags["cond5b"] = True
    if src_idx - 1 >= 0 and next1:
        prev = data[src_idx - 1]
        if len(prev) >= 5 and len(next1) >= 10:
            mac_next1 = set(next1[5:10])
            for i in range(4):
                if abs(prev[i] - prev[i + 1]) == 1:
                    if prev[i] in mac_next1 or prev[i + 1] in mac_next1:
                        flags["cond6"] = True
                        break
    if src_idx - 3 >= 0:
        back3 = data[src_idx - 3]
        if len(back3) >= 4:
            third, fourth = back3[2], back3[3]
            if abs(third - fourth) == 1 and third < fourth:
                flags["cond7"] = True
    score = sum(1 for v in flags.values() if v)
    return score, flags

# ─── A.bestest3_final.py LOGIC ──────────────────────────────────────────────────
def evaluate_event_best3(idx: int, data: list, fam_map: dict):
    """
    Returns {"event", "src", "two_sure", "extras", "pred", "conds", "grade"} or None.
    Always forms pred = two_sure + extras (from +158), regardless of conditions.
    Removed the “72 or 35” check; cond2 now checks two_sure vs. 9-event surroundings.
    """
    row = data[idx]
    if len(row) < 10:
        return None
    mac1, mac2, win3 = row[5], row[6], row[2]
    diff = abs(mac1 - mac2)
    turned = fam_map.get(diff)
    if turned is None:
        return None
    src = turned * 2 + (win3 - 1)
    if not (1 <= src <= len(data)):
        return None
    win_src = data[src - 1][0:5]
    two_sure = win_src[0:2]

    # cond2: check if either two_sure number appears in 9-event surroundings around src
    src_idx = src - 1
    ctx = get_context_set(data, src_idx, window=9)
    cond2 = any(num in ctx for num in two_sure)

    ev2 = src + 158
    cond3 = cond4 = False
    extras = []
    if 1 <= ev2 <= len(data):
        ev2_row = data[ev2 - 1]
        # Always extract extras from +158
        if len(ev2_row) >= 10:
            macs2 = ev2_row[5:10]
            extras = [macs2[0], macs2[2], macs2[4]]
        # Then compute cond3 and cond4:
        if ev2 > 1 and abs(data[ev2 - 2][0] - ev2_row[0]) == 1:
            cond3 = True
        if ev2 < len(data):
            nxt = data[ev2][0:5]
            if 17 in nxt and 87 in nxt:
                cond4 = True

    pred = sorted(set(two_sure + extras))
    conds = {"C2": cond2, "C3": cond3, "C4": cond4}
    grade_map = {1: "16%", 2: "45%", 3: "79%", 4: "100%"}
    grade = grade_map.get(sum(conds.values()), "0%")

    return {
        "event": idx + 1,
        "src": src,
        "two_sure": two_sure,
        "extras": extras,
        "pred": pred,
        "conds": conds,
        "grade": grade
    }

# ─── A.bestest 5.py LOGIC ────────────────────────────────────────────────────────
def evaluate_latest_best5(data: list):
    """
    Returns {"current_event", "ref_event", "two_sure", "extras", "prediction", "conds", "grade"} or None.
    Always forms prediction = two_sure + extras (from +158), regardless of conditions.
    """
    idx = len(data) - 1
    row = data[idx]
    if len(row) < 10:
        return None
    wins = row[0:5]
    macs = row[5:10]
    current_event = idx + 1
    total_win = sum(wins) * 2
    total_macs = sum(macs)
    second_win = wins[1]
    ref = abs(total_win + total_macs + second_win - current_event)
    if not (1 <= ref <= len(data)):
        return None
    win_ref = data[ref - 1][0:5]
    two_sure = win_ref[0:2]
    cond1 = False
    if ref > 1 and data[ref - 2][2] in win_ref:
        cond1 = True
    ev2 = ref + 158
    cond3 = cond4 = cond5 = cond6 = False
    extras = []
    if 1 <= ev2 <= len(data):
        row2 = data[ev2 - 1]
        # Always extract extras from +158
        if len(row2) >= 10:
            extras = [row2[5], row2[7], row2[9]]
        # Then compute cond3–cond6:
        if ev2 > 1 and abs(data[ev2 - 2][0] - row2[0]) == 1:
            cond3 = True
        if ev2 < len(data):
            wins_next2 = data[ev2][0:5]
            if 17 in wins_next2 and 87 in wins_next2:
                cond4 = True
        if ev2 > 3:
            wb3 = data[ev2 - 4][0:5]
            third, fourth = wb3[2], wb3[3]
            if abs(third - fourth) == 1 and third < fourth:
                cond5 = True
        if ev2 + 2 <= len(data):
            mac_check = data[ev2 + 1][7]
            if mac_check in (24, 79):
                cond6 = True

    pred = sorted(set(two_sure + extras))
    conds = {"C1": cond1, "C3": cond3, "C4": cond4, "C5": cond5, "C6": cond6}
    grade_map = {1: "16%", 2: "45%", 3: "79%", 4: "100%"}
    grade = grade_map.get(sum(conds.values()), "0%")

    return {
        "current_event": current_event,
        "ref_event": ref,
        "two_sure": two_sure,
        "extras": extras,
        "prediction": pred,
        "conds": conds,
        "grade": grade
    }

# ─── MAIN COMBINED SCRIPT ───────────────────────────────────────────────────────
if __name__ == "__main__":
    # 1) Ensure a.code,counter.txt exists
    if not os.path.exists("a.code,counter.txt"):
        print("[X] Missing 'a.code,counter.txt'.")
        sys.exit(1)

    # 2) Let user select a .txt data file
    txt_files = [
        f for f in os.listdir()
        if os.path.isfile(f)
        and f.lower().endswith(".txt")
        and f.lower() != "a.code,counter.txt"
    ]
    if not txt_files:
        print("[X] No .txt files found.")
        sys.exit(1)

    print("\n📂 Available .txt files:")
    for i, fname in enumerate(txt_files, start=1):
        print(f"  {i}: {fname}")
    try:
        sel = int(input(f"\nSelect a file by number (1-{len(txt_files)}): ")) - 1
        filename = txt_files[sel]
    except (ValueError, IndexError):
        print("[X] Invalid selection.")
        sys.exit(1)

    # 3) Load data
    data = load_lotto_file(filename)
    if len(data) < 44:
        print("[X] Need ≥44 events; file has only", len(data))
        sys.exit(1)

    # 4) Load family maps
    fam_map_full = load_family_map_full("a.code,counter.txt")
    fam_map_simple = load_family_map_simple("a.code,counter.txt")

    num_events = len(data)
    print(f"\n🔎 Historical summary for file: {filename}\n")

    # ── Historical best4 (≥2 matches) ──────────────────────────────────────────────
    print("— A.bestest4.py logic (≥2-match events) —")
    history4 = []
    for i in range(43, num_events - 1):
        r4 = evaluate_event_best4(i, data, fam_map_full)
        if not r4:
            continue
        next_win = set(data[i + 1][0:5])
        matched4 = sorted(set(r4["pred"]) & next_win)
        if len(matched4) >= 2:
            history4.append((r4["event"], matched4))
            print(f"📌 Event {r4['event']} → Matched: {matched4}")
    print(f"📊 Total A.bestest4 matches (≥2): {len(history4)}\n")

    # ── Historical best3 (≥2 matches) ──────────────────────────────────────────────
    print("— A.bestest3_final.py logic (≥2-match events) —")
    history3 = []
    for i in range(43, num_events - 1):
        r3 = evaluate_event_best3(i, data, fam_map_simple)
        if not r3:
            continue
        next_win = set(data[i + 1][0:5])
        matched3 = sorted(set(r3["pred"]) & next_win)
        if len(matched3) >= 2:
            history3.append((r3["event"], matched3))
            print(f"📌 Event {r3['event']} → Matched: {matched3}")
    print(f"📊 Total A.bestest3_final matches (≥2): {len(history3)}\n")

    # ── Historical union (best4 ∪ best3) matched events ────────────────────────────
    print("— Union (best4 ∪ best3) logic (at least one match) —")
    history_union = []
    for i in range(43, num_events - 1):
        r4 = evaluate_event_best4(i, data, fam_map_full)
        r3 = evaluate_event_best3(i, data, fam_map_simple)
        if not r4 and not r3:
            continue
        pred_union = set()
        if r4:
            pred_union |= set(r4["pred"])
        if r3:
            pred_union |= set(r3["pred"])
        next_win = set(data[i + 1][0:5])
        matched_union = sorted(pred_union & next_win)
        if matched_union:
            history_union.append((i + 1, matched_union))
            print(f"📌 Event {i+1} → Matched: {matched_union}")
    print(f"📊 Total Union matches: {len(history_union)}\n")

    # ── Latest predictions for each script ─────────────────────────────────────────
    print(f"\n[⏳] Generating ‘latest’ predictions for file: {filename}\n")

    idx_latest = num_events - 1
    print(f"🔄 Processing Event: {idx_latest + 1}\n")

    # A.bestest4 “latest”
    res4_latest = evaluate_event_best4(idx_latest, data, fam_map_full)
    shared_flags = {}
    shared_score = 0
    cond4_flags = {}
    cond4_score = 0
    if res4_latest:
        src_idx = res4_latest["src"] - 1
        # Shared conditions around two_sure
        shared_score, shared_flags = compute_shared_conditions(src_idx, data)
        # +158 conditions for best4
        src2 = src_idx + 158
        if 0 <= src2 < num_events:
            cond4_score, cond4_flags = check_conditions_best4(src2, data)

        print("— A.bestest4.py Latest —")
        print(f"  Event (current):       {res4_latest['event']}")
        print(f"  Source event (src):    {res4_latest['src']}  →  +158 event: {res4_latest['src'] + 158 if res4_latest['src'] + 158 <= num_events else 'N/A'}")
        print(f"  Two-sure at src:       {tuple(res4_latest['two_sure'])}")
        print(f"  Surrounding Score:     {shared_flags}   → {shared_score}/3")
        print(f"  Extras from +158:      {tuple(res4_latest['extras'])}")
        print(f"  +158 Conditions:       {cond4_flags}   → Score: {cond4_score * 15}%")
        print(f"  Full 5-number pred:    {tuple(res4_latest['pred'])}\n")

        if shared_score >= 1 or cond4_score >= 1:
            speak(
                f"A.bestest4 prediction from {filename}: "
                f"{', '.join(map(str, res4_latest['pred']))}."
            )
    else:
        print("— A.bestest4.py Latest: No valid prediction.\n")

    # A.bestest3_final “latest”
    res3_latest = evaluate_event_best3(idx_latest, data, fam_map_simple)
    if res3_latest:
        cond3_score = sum(res3_latest["conds"].values())
        print("— A.bestest3_final.py Latest —")
        print(f"  Event (current):       {res3_latest['event']}")
        print(f"  Source event (src):    {res3_latest['src']}")
        print(f"  Two-sure at src:       {tuple(res3_latest['two_sure'])}")
        print(f"  Surrounding Score:     {shared_flags}   → {shared_score}/3")
        print(f"  Extras from +158:      {tuple(res3_latest['extras'])}")
        print(f"  +158 Conditions:       {res3_latest['conds']}   → Grade: {res3_latest['grade']}")
        print(f"  Full 5-number pred:    {tuple(res3_latest['pred'])}\n")

        if shared_score >= 1 or cond3_score >= 1:
            speak(
                f"A.bestest3_final prediction from {filename}: "
                f"{', '.join(map(str, res3_latest['pred']))}."
            )
    else:
        print("— A.bestest3_final.py Latest: No valid prediction.\n")

    # A.bestest 5 “latest”
    res5_latest = evaluate_latest_best5(data)
    if res5_latest:
        cond5_score = sum(res5_latest["conds"].values())
        print("— A.bestest 5.py Latest —")
        print(f"  Current Event:         {res5_latest['current_event']}")
        print(f"  Reference event (ref): {res5_latest['ref_event']}")
        print(f"  Two-sure at ref:       {res5_latest['two_sure']}")
        print(f"  Surrounding Score:     {shared_flags}   → {shared_score}/3")
        print(f"  Extras from +158:      {res5_latest['extras']}")
        print(f"  +158 Conditions:       {res5_latest['conds']}   → Grade: {res5_latest['grade']}")
        print(f"  Full 5-number pred:    {tuple(res5_latest['prediction'])}\n")

        if shared_score >= 1 or cond5_score >= 1:
            speak(
                f"A.bestest5 prediction from {filename}: "
                f"{', '.join(map(str, res5_latest['prediction']))}."
            )
    else:
        print("— A.bestest 5.py Latest: No valid prediction.\n")

    # ── Combined union of all latest predictions ───────────────────────────────────
    all_preds = set()
    if res4_latest:
        all_preds |= set(res4_latest["pred"])
    if res3_latest:
        all_preds |= set(res3_latest["pred"])
    if res5_latest:
        all_preds |= set(res5_latest["prediction"])
    combined_latest = tuple(sorted(all_preds))
    print(f"🎯 FINAL COMBINED PREDICTION (All Systems):\n({', '.join(map(str, combined_latest))})\n")

    input("Press Enter to close…")
