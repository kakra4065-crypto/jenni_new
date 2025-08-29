import sys
import pandas as pd
import os
import re
import glob
from collections import Counter

# === Script 1: 2nd and 4th latest prediction ===
def run_2nd_and_4th_latest(data_all, input_file):
    def sanitize_prediction(pred):
        return [min(90, max(1, int(round(x)))) for x in pred]

    def get_conditions(machine_nums):
        conditions = []
        if any(num in machine_nums for num in [2, 50]):
            conditions.append("Accurate")
        if any(num in machine_nums for num in [26, 74]):
            conditions.append("Super Accurate")
        return conditions

    results = data_all.get(input_file)
    if not results or len(results) < 1:
        return []

    outputs = []

    for code in [1, 2]:
        row = results[-1]
        if code == 1:
            value1 = row[0] + row[1] - 1
        else:
            value1 = row[1] + row[3]
        value2 = row[2] + 10

        for src_file, data in data_all.items():
            for i, ref_row in enumerate(data):
                if len(ref_row) < 10:
                    continue
                if ref_row[0] == value1 and ref_row[3] == value2:
                    pred = sanitize_prediction(ref_row[5:10])
                    conds = []
                    if i + 2 < len(data):
                        conds = get_conditions(data[i + 2][5:10])
                    if conds:  # Only show if conditions found
                        outputs.append(f"Script 2nd and 4th code {code}: Prediction {pred} from {src_file} (event {i+1}), Conditions: {conds}")
    return outputs

# === Script 2: AA.NEW latest prediction ===
def run_AA_NEW_latest(data, number_df):
    def is_double(n):
        return n in {11,22,33,44,55,66,77,88}

    def turn_mac0(m0):
        if 10 <= m0 <= 99 and not is_double(m0):
            rev = int(str(m0)[::-1])
        elif 1 <= m0 <= 9:
            rev = m0 * 10
        else:
            return None
        return rev if 1 <= rev <= 90 else None

    if len(data) < 3:
        return []

    i = len(data) - 1
    row = data.iloc[i]
    win = list(map(int, row[:5]))
    mac = list(map(int, row[5:10]))

    win_sum = win[3] + win[4]
    prev = data.iloc[i-2] if i-2 >= 0 else None
    prev_mac_sum = (int(prev[5]) + int(prev[6])) if prev is not None else 0
    total_sum = win_sum + mac[2] + mac[3] + prev_mac_sum

    src_idx = max(0, min(total_sum - 1, len(data) - 1))
    src = data.iloc[src_idx]
    src_prev = data.iloc[src_idx - 1] if src_idx - 1 >= 0 else None
    src_next = data.iloc[src_idx + 1] if src_idx + 1 < len(data) else None

    two_sure = [int(src[0]), int(src[1])]
    conds = []

    if i - 1 >= 0 and int(data.iloc[i - 1, 3]) == 35:
        two_sure.append(15)
        conds.append("cond1")

    if src_prev is not None and int(src[0]) == int(src_prev[1]):
        two_sure.append(int(src[0]))
        conds.append("cond2")

    if src_next is not None and int(src_next[4]) == 9 and is_double(int(src_next[0])):
        two_sure.append(int(src_next[0]))
        conds.append("cond3")

    if src_prev is not None and int(src[0]) + 1 == int(src_prev[1]) and 50 in [int(x) for x in src_prev[:5]]:
        two_sure.append(int(src[0]) + 1)
        conds.append("cond4")

    if prev is not None and mac[1] == int(prev[7]):
        turned = turn_mac0(mac[0])
        if turned is not None:
            two_sure.append(turned)
            conds.append("cond5")

    if int(src[1]) == win[1]:
        two_sure.append(win[1])
        conds.append("cond6")

    if src_prev is not None and int(src[1]) == 50 and is_double(int(src_prev[0])):
        two_sure.append(50)
        conds.append("cond7")

    if src_next is not None and int(src_next[2]) == 25 and mac[4] == 35:
        two_sure.append(25)
        conds.append("cond8")

    if not conds:
        return []

    if len(conds) > 1:
        a, b = two_sure[0], two_sure[1]
        two_sure = [a, b, f"({a}-{b})"] + two_sure[2:]

    base = two_sure[0]
    if base not in number_df["Number"].values:
        return []

    cp = int(number_df.loc[number_df["Number"] == base, "Counterpart"].iat[0])
    sk = number_df.loc[number_df["Number"] == cp, "StringKey"].iat[0]

    prediction = two_sure + [cp, sk, str(total_sum)]

    output_str = f"Script A A. NEW: Two-sure {two_sure[:2]}, Full Prediction: {prediction}, Conditions: {conds}"

    return [output_str]

# === Script 3: a.best.py latest prediction ===
def run_a_best_latest(data, family_map):
    def get_event_numbers(df, event_idx):
        if 0 <= event_idx < len(df):
            row = df.iloc[event_idx]
            if len(row.dropna()) >= 10:
                win = list(row[:5])
                mac = list(row[5:10])
                return win, mac
        return [], []

    current_event_num = len(data)
    try:
        current_idx = current_event_num - 1
        _, mac_current = get_event_numbers(data, current_idx)
        if len(mac_current) < 4:
            return []

        mac2_current = mac_current[1]

        _, mac_prev = get_event_numbers(data, current_idx - 5)
        if len(mac_prev) < 4:
            return []

        mac4_prev = mac_prev[3]

        diff = abs(mac2_current - mac4_prev)
        source_event_from = current_event_num - diff
        true_source_event = source_event_from - 4
        true_source_idx = true_source_event - 1

        _, mac_source = get_event_numbers(data, true_source_idx)
        if len(mac_source) < 2:
            return []

        banker = mac_source[1]

        _, mac_plus2 = get_event_numbers(data, true_source_idx + 2)
        if len(mac_plus2) < 2:
            return []

        mac2_plus2 = mac_plus2[1]
        condition_met = mac2_plus2 in [72, 35]

        if not condition_met:
            return []

        win_source, _ = get_event_numbers(data, true_source_idx)
        if len(win_source) < 3:
            return []

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

        return [f"Script a. best.py: Prediction {final_prediction}, Banker: {banker}, Condition Met: {condition_met}"]
    except Exception:
        return []

# === Script 4: A.4-5win.py latest prediction ===
def run_4_5win_latest(input_file):
    all_data = {}
    for f in os.listdir():
        if f.lower().endswith(".txt"):
            try:
                df = pd.read_csv(f, sep="\t", header=None)
                all_data[f] = df
            except:
                pass
    if not all_data:
        return []

    input_df = all_data.get(input_file)
    if input_df is None or input_df.shape[0] < 1:
        return []

    latest_idx = input_df.shape[0] - 1
    results = []

    for ref_file, ref_df in all_data.items():
        if ref_file == input_file:
            continue

        try:
            mac_4th = int(input_df.iat[latest_idx, 8])
            win_2nd = int(input_df.iat[latest_idx, 1])
        except (IndexError, ValueError):
            continue

        candidates = ref_df[(ref_df[3] == mac_4th) & (ref_df[4] == win_2nd)]
        if candidates.empty:
            continue
        source_idx = candidates.index[0]

        banker = None
        cond_bank = False
        if source_idx - 1 >= 0:
            try:
                if int(ref_df.iat[source_idx - 1, 7]) == 4:
                    banker = int(ref_df.iat[source_idx, 6]) + 1
                    cond_bank = True
            except:
                pass

        two_sure = []
        if source_idx + 1 < ref_df.shape[0]:
            try:
                two_sure = [
                    int(ref_df.iat[source_idx + 1, 3]),
                    int(ref_df.iat[source_idx + 1, 4])
                ]
            except:
                pass

        add_third = None
        if source_idx + 2 < ref_df.shape[0]:
            try:
                mac2n  = int(ref_df.iat[source_idx + 1, 6])
                win2n2 = int(ref_df.iat[source_idx + 2, 1])
                if mac2n == win2n2:
                    add_third = mac2n
            except:
                pass

        conds = []
        if cond_bank:
            conds.append("Banker")
        if two_sure:
            conds.append("TwoSure")
        if add_third is not None:
            conds.append("AddThird")

        if not conds:
            continue

        prediction = []
        if banker   is not None:
            prediction.append(banker)
        if add_third is not None:
            prediction.append(add_third)
        prediction.extend(two_sure)

        results.append(
            f"Script A.4-5win.py: Prediction {sorted(set(prediction))} "
            f"from {ref_file} (source event {source_idx+1}), Conditions: {conds}"
        )

    return results

# === Script X: Transfer Logic (requires ≥2 conditions) ===
def run_transfer_logic_latest(input_file):
    def load_data(fpath):
        return pd.read_csv(fpath, sep="\t", header=None)

    def find_source_events(data, first_machine, third_winning):
        return [
            i for i in range(len(data))
            if data.shape[1] >= 10
               and data.iat[i, 8] == first_machine
               and data.iat[i, 9] == third_winning
        ]

    def check_conditions(data, idx):
        if idx + 1 >= len(data) or idx - 2 < 0:
            return False
        passed = 0

        if data.iat[idx, 7] - 1 == data.iat[idx + 1, 8]:
            passed += 1

        two_back = data.iloc[idx - 2, :5].values
        if (
            (two_back[0] == 75 and two_back[1] == 74)
            or two_back[0] == 75
            or two_back[1] == 8
            or two_back[2] == 8
        ):
            passed += 1

        nxt = data.iloc[idx + 1, :5].values
        if set((89, 8)).issubset(nxt) or set((8, 44)).issubset(nxt):
            passed += 1

        back1m = data.iloc[idx - 1, 5:10].values
        if back1m[2] == 30 or back1m[3] == 34:
            passed += 1

        if 83 in (two_back[1], two_back[3]):
            passed += 1

        prev_w = data.iloc[idx - 1, :5].values
        if any(
            abs(prev_w[i] - prev_w[j]) == 1
            for i in range(5) for j in range(i+1, 5)
        ):
            passed += 1

        return passed >= 2

    selected_df = load_data(input_file)
    if selected_df.shape[0] < 1:
        return []

    last_idx = selected_df.shape[0] - 1
    try:
        first_machine = int(selected_df.iat[last_idx, 5])
        third_winning = int(selected_df.iat[last_idx, 2])
    except:
        return []

    results = []

    for fname in os.listdir():
        if not fname.lower().endswith(".txt") or fname == input_file:
            continue
        ref_df = load_data(fname)
        src_idxs = find_source_events(ref_df, first_machine, third_winning)
        for src in src_idxs:
            if not check_conditions(ref_df, src):
                continue
            try:
                pred = ref_df.iloc[src, :5].astype(int).tolist()
            except:
                continue
            results.append(
                f"Script Transfer Logic: Prediction {pred} "
                f"from {fname} (source event {src+1})"
            )

    return results

# === Script A OLIVIA latest ===
def run_A_OLIVIA_latest(data):
    def safe_get(df, row_idx, col_idx):
        if 0 <= row_idx < len(df) and 0 <= col_idx < df.shape[1]:
            try:
                v = df.iat[row_idx, col_idx]
                return None if pd.isna(v) else int(v)
            except:
                return None
        return None

    def evaluate_custom_conditions(df, source_idx):
        res = {}

        mac1 = safe_get(df, len(df) - 1, 5)
        mac2 = safe_get(df, len(df) - 1, 6)
        res['1st mac -10 == 2nd mac'] = (mac1 is not None and mac2 is not None and (mac1 - 10 == mac2))

        win4       = safe_get(df, source_idx,   3)
        win4_prev  = safe_get(df, source_idx-1, 3)
        def bonanza(x): return int(str(x).zfill(2)[::-1]) if x is not None else None
        res['Source 4th win bonanza == prev 4th win'] = (
            win4 is not None and win4_prev is not None and bonanza(win4) == win4_prev)

        idx3 = source_idx - 2
        w1   = safe_get(df, idx3, 0)
        w3   = safe_get(df, idx3, 2)
        all5 = [safe_get(df, idx3, i) for i in range(5)]
        res['Source-2: 1st==7 & 3rd==10 or any==10'] = ((w1 == 7 and w3 == 10) or 10 in all5)

        src5 = safe_get(df, source_idx, 4)
        nxt4 = safe_get(df, source_idx+1, 3)
        res['Source 5th win == +1 event 4th win'] = (src5 is not None and nxt4 is not None and src5 == nxt4)

        nxt_wins = [safe_get(df, source_idx+1, i) for i in range(5)]
        cond5   = [n for n in nxt_wins if n in (3,34,7,32,9)]
        res['Source+1 win has 2+ of (3,34,7,32,9)'] = len([x for x in cond5 if x is not None]) >= 2

        src1p4    = safe_get(df, source_idx+1, 3)
        src2_wins = [safe_get(df, source_idx+2, i) for i in range(5)]
        res['Source+1 4th win in +2 any win'] = src1p4 in src2_wins if src1p4 is not None else False

        def is_turning(n1, n2): return (n1 != n2 and str(n1).zfill(2)[::-1] == str(n2).zfill(2))
        found = any(is_turning(w1, w2) for w1 in src2_wins for w2 in src2_wins if w1 is not None and w2 is not None)
        res['Source+2 any win and its turning'] = found

        win1_3 = safe_get(df, source_idx+3, 0)
        win2_3 = safe_get(df, source_idx+3, 1)
        res['Source+3: 1st-2nd diff=1 & 1st>2nd'] = (
            win1_3 is not None and win2_3 is not None and abs(win1_3 - win2_3) == 1 and win1_3 > win2_3)

        win2_3 = safe_get(df, source_idx+3, 1)
        win4_4 = safe_get(df, source_idx+4, 3)
        res['Source+3 2nd win == +4 4th win'] = (win2_3 is not None and win4_4 is not None and win2_3 == win4_4)

        res['Source+1 4th win == +2 3rd mac'] = (
            src1p4 is not None and safe_get(df, source_idx+2, 7) == src1p4)

        res['Source-1 4th win == 44'] = (safe_get(df, source_idx-1, 3) == 44)

        win1   = safe_get(df, source_idx, 0)
        win2   = safe_get(df, source_idx, 1)
        res['Source: 2nd win - 1st win == 10'] = (
            win1 is not None and win2 is not None and (win2 - win1 == 10))

        score = sum(1 for v in res.values() if v)
        return res, score

    if len(data) < 6:
        return []

    last_idx = len(data) - 1
    third_win = safe_get(data, last_idx, 2)
    third_mac = safe_get(data, last_idx, 7)
    if third_win is None or third_mac is None:
        return []

    abs_diff = abs(third_win - third_mac)
    adjusted = 45 - abs_diff
    source_idx = int(last_idx + 2 - adjusted)
    if not (0 <= source_idx + 4 < len(data)):
        return []

    cond_results, cond_score = evaluate_custom_conditions(data, source_idx)
    if cond_score == 0:
        return []

    src_event = data.iloc[source_idx]
    plus4_event= data.iloc[source_idx + 4]
    prediction_set = {
        int(src_event[3]),
        int(src_event[3] - 2),
        int(src_event[9]),
        int(plus4_event[0])
    }
    prediction_list = sorted(prediction_set)

    pred_str = "(" + "-".join(str(x) for x in prediction_list) + ")"

    cond_lines = []
    for name, passed in cond_results.items():
        mark = "✔️" if passed else "❌"
        cond_lines.append(f"{name}: {mark}")
    cond_summary = "\n".join(cond_lines)

    out1 = f"Script A OLIVIA.PY: Prediction {pred_str}"
    out2 = f"Conditions matched ({cond_score}/12):\n{cond_summary}"

    return [out1, out2]

# === Combined A best family 3 predictor helpers and main function ===

def get_context_set(data, event_index, window=9):
    ctx = []
    for d in range(1, window + 1):
        idx = event_index - d
        if idx < 0:
            break
        row = data[idx]
        ctx.extend(row[0:5])
        ctx.extend(row[5:10])
    return set(ctx)

def compute_shared_conditions(src_idx, data):
    flags = {"S1": False, "S2": False, "S3": False}
    n = len(data)

    if src_idx - 1 >= 0:
        prev = data[src_idx - 1]
        cur = data[src_idx]
        if len(prev) >= 3 and len(cur) >= 5 and prev[2] == cur[4]:
            flags["S1"] = True

    if src_idx + 1 < n:
        nxt = data[src_idx + 1]
        if len(nxt) >= 2 and nxt[1] == 61:
            flags["S2"] = True

    cur = data[src_idx]
    if len(cur) >= 8 and cur[7] == 13:
        flags["S3"] = True

    score = sum(1 for v in flags.values() if v)
    return score, flags

def evaluate_event_best4(idx, data, fam_map):
    if idx < 0 or idx >= len(data):
        return None
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
            extras = [ev2_row[5], ev2_row[7], ev2_row[9]]
    pred = sorted(set(two_sure + extras))
    return {
        "event": idx + 1,
        "src": src,
        "two_sure": two_sure,
        "extras": extras,
        "pred": pred
    }

def check_conditions_best4(src_idx, data):
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

def evaluate_event_best3(idx, data, fam_map):
    if idx < 0 or idx >= len(data):
        return None
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

    src_idx = src - 1
    ctx = get_context_set(data, src_idx, window=9)
    cond2 = any(num in ctx for num in two_sure)

    ev2 = src + 158
    cond3 = cond4 = False
    extras = []
    if 1 <= ev2 <= len(data):
        ev2_row = data[ev2 - 1]
        if len(ev2_row) >= 10:
            extras = [ev2_row[5], ev2_row[7], ev2_row[9]]
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

def evaluate_latest_best5(data):
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
        if len(row2) >= 10:
            extras = [row2[5], row2[7], row2[9]]
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

# --- Family map loaders ---
def load_family_map_full(path):
    fam = {}
    if not os.path.exists(path):
        return fam
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

def load_family_map_simple(path):
    fam = {}
    if not os.path.exists(path):
        return fam
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

# === FINAL MAWU INPROVED 2 logic ===
def run_final_mawu_improved(data_list):
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

    pred, conds, src_event = complete(data_list, len(data_list), include_debug=False)
    if pred and conds > 0:
        percentage = min(15 * conds, 100)
        msg = (
            f"FINAL MAWU INPROVED 2: Prediction from event {src_event}: {pred}. "
            f"{conds} condition{'s' if conds != 1 else ''} met. Confidence: {percentage} percent."
        )
        return [msg]
    return []

# === Combined A best family 3 predictor main function ===
def run_A_best_3_family_latest(data, fam_map_full, fam_map_simple):
    num_events = len(data)
    idx_latest = num_events - 1

    res4 = evaluate_event_best4(idx_latest, data, fam_map_full)
    res3 = evaluate_event_best3(idx_latest, data, fam_map_simple)
    res5 = evaluate_latest_best5(data)

    combined_preds = set()

    cond4_met = False
    if res4:
        src_idx = res4["src"] - 1
        shared_score, shared_flags = compute_shared_conditions(src_idx, data)
        ev2 = src_idx + 158
        cond4_score, cond4_flags = check_conditions_best4(ev2, data)
        cond4_met = (shared_score >= 1) or (cond4_score >= 3)
        if cond4_met:
            combined_preds |= set(res4["pred"])
            print(f"A.bestest4 prediction: {sorted(res4['pred'])} Conditions met: True")

    cond3_met = False
    if res3:
        cond3_score = sum(res3["conds"].values())
        cond3_met = cond3_score > 0
        if cond3_met:
            combined_preds |= set(res3["pred"])
            print(f"A.bestest3_final prediction: {sorted(res3['pred'])} Conditions met: True")

    cond5_met = False
    if res5:
        cond5_score = sum(res5["conds"].values())
        cond5_met = cond5_score > 0
        if cond5_met:
            combined_preds |= set(res5["prediction"])
            print(f"A.bestest5 prediction: {sorted(res5['prediction'])} Conditions met: True")

    if not (cond4_met or cond3_met or cond5_met):
        print("\nNo conditions found. No predictions to show.\n")
        return []

    final_pred_sorted = sorted(combined_preds)
    print(f"\n🎯 FINAL combined prediction set: {final_pred_sorted}\n")

    return final_pred_sorted

# === Formatting and printing output in the style you want ===
def format_and_print_outputs(outputs, filename, event_num):
    predictions_map = {
        '24': [],
        'AA': [],
        'AB': [],
        '45': [],
        'OL': [],
        'TR': [],
        'MA': [],
    }
    conditions_map = {
        '24': set(),
        'AA': set(),
        'AB': set(),
        '45': set(),
        'OL': set(),
        'TR': set(),
        'MA': set(),
    }

    for line in outputs:
        m24 = re.match(r"Script 2nd and 4th code (\d+): Prediction (\[.*?\]) from (.*?) \(event (\d+)\), Conditions: (\[.*\])", line)
        if m24:
            code = m24.group(1)
            pred_str = m24.group(2)
            conds_str = m24.group(5)
            preds = eval(pred_str)
            conditions = eval(conds_str)
            predictions_map['24'].append(tuple(preds))
            conditions_map['24'].update(conditions)
            continue

        mAA = re.match(r"Script A A\. NEW: Two-sure .*Full Prediction: (\[.*?\]), Conditions: (\[.*\])", line)
        if mAA:
            pred_str = mAA.group(1)
            conds_str = mAA.group(2)
            preds = eval(pred_str)
            conditions = eval(conds_str)
            predictions_map['AA'].append(tuple(preds))
            conditions_map['AA'].update(conditions)
            continue

        mAB = re.match(r"Script a\. best\.py: Prediction (\[.*?\]), Banker: (\d+), Condition Met: (True|False)", line)
        if mAB:
            pred_str = mAB.group(1)
            cond_met = mAB.group(3) == 'True'
            preds = eval(pred_str)
            predictions_map['AB'].append(tuple(preds))
            if cond_met:
                conditions_map['AB'].add("Condition Met")
            continue

        m45 = re.match(r"Script A\.4-5win\.py: Prediction (\[.*?\]) from (.*?) \(source event (\d+)\), Conditions: (\[.*\])", line)
        if m45:
            pred_str = m45.group(1)
            conds_str = m45.group(4)
            preds = eval(pred_str)
            conditions = eval(conds_str)
            predictions_map['45'].append(tuple(preds))
            conditions_map['45'].update(conditions)
            continue

        if line.startswith("Script A OLIVIA.PY: Prediction"):
            pred_match = re.search(r"Prediction \((.*?)\)", line)
            if pred_match:
                pred_nums = tuple(map(int, pred_match.group(1).split("-")))
                predictions_map['OL'].append(pred_nums)
            continue
        if line.startswith("Conditions matched"):
            conditions_map['OL'].add("1st mac -10 == 2nd mac")
            conditions_map['OL'].add("Source+1 4th win in +2 any win")
            continue

        if line.startswith("Script Transfer Logic: Prediction"):
            mTR = re.match(r"Script Transfer Logic: Prediction (\[.*?\]) from (.*?) \(source event (\d+)\)", line)
            if mTR:
                pred_str = mTR.group(1)
                preds = eval(pred_str)
                predictions_map['TR'].append(tuple(preds))
                conditions_map['TR'].add("Transfer Logic Condition")
            continue

        if line.startswith("FINAL MAWU INPROVED 2:"):
            mMA = re.search(r"Prediction from event (\d+): (\[.*?\]). (\d+) condition", line)
            if mMA:
                preds = eval(mMA.group(2))
                conds_count = int(mMA.group(3))
                predictions_map['MA'].append(tuple(preds))
                conditions_map['MA'].add(f"{conds_count} conditions met")
            continue

        if line.startswith("A best 3 family combined prediction:"):
            mB3 = re.search(r"A best 3 family combined prediction: \[(.*?)\]", line)
            if mB3:
                preds_str = mB3.group(1)
                preds = tuple(int(x.strip()) for x in preds_str.split(",") if x.strip().isdigit())
                predictions_map['MA'].append(preds)
            continue

    print(f"=== Predictions from all scripts (conditions met only) === {filename} event {event_num}\n")

    label_map = {
        '24': "[24]",
        'AA': "[AA]",
        'AB': "[AB]",
        '45': "[45]",
        'OL': "[OL]",
        'TR': "[TR]",
        'MA': "[MA]",
    }

    for key in ['24','AA','AB','45','OL','TR','MA']:
        preds_list = predictions_map[key]
        for pred in preds_list:
            if pred:
                sorted_pred = sorted(pred)
                print(f"🎯 {label_map[key]}: ({', '.join(map(str, sorted_pred))})")

    print()
    print("A b3 :", end=" ")
    if predictions_map['MA']:
        flat_preds = set()
        for tup in predictions_map['MA']:
            flat_preds.update(tup)
        flat_preds = sorted(flat_preds)
        print(flat_preds)
    else:
        print("[]")

    print("\n=== Conditions met per script ===")
    for key in ['24','AA','AB','45','OL','TR','MA']:
        conds = conditions_map[key]
        if conds:
            if key == '24':
                sconds = []
                if "Super Accurate" in conds:
                    sconds.append("Super Accurate")
                if "Accurate" in conds:
                    sconds.append("Accurate")
                print(f"{label_map[key]}: {', '.join(sconds)}")
            elif key == 'AA':
                print(f"{label_map[key]}: {', '.join(sorted(conds))}")
            elif key == 'AB':
                print(f"{label_map[key]}: Condition Met")
            elif key == '45':
                print(f"{label_map[key]}: {', '.join(sorted(conds))}")
            elif key == 'OL':
                print(f"{label_map[key]}: 1st mac -10 == 2nd mac, Source+1 4th win in +2 any win")
            elif key == 'TR':
                print(f"{label_map[key]}: Transfer Logic Condition")
            elif key == 'MA':
                conds_str = ', '.join(conds)
                print(f"{label_map[key]}: {conds_str}")

    print("\n🗣️ Predictions generated for all scripts.\n")

# --- Main entry point ---
def main():
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

    try:
        data_df = pd.read_csv(filename, sep="\t", header=None)
    except Exception as e:
        print(f"[X] Failed to load file {filename} with pandas: {e}")
        sys.exit(1)

    data_list = []
    try:
        with open(filename, encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) >= 10:
                    try:
                        nums = list(map(int, parts))
                        data_list.append(nums)
                    except:
                        continue
    except Exception as e:
        print(f"[X] Failed to load file {filename} as list: {e}")
        sys.exit(1)

    if len(data_list) < 44:
        print(f"[X] Need at least 44 events; file has only {len(data_list)}")
        sys.exit(1)

    fam_map_full = load_family_map_full("a.code,counter.txt")
    fam_map_simple = load_family_map_simple("a.code,counter.txt")
    if not fam_map_full or not fam_map_simple:
        print("[X] Family map file 'a.code,counter.txt' missing or invalid.")
        sys.exit(1)

    number_df = None
    if os.path.exists("number.txt"):
        try:
            number_df = pd.read_csv("number.txt", sep="\t", header=None)
            number_df.columns = ["Number","Counterpart","Bonanza","StringKey",
                                 "Extra1","Extra2","Extra3","Extra4","Extra5","Extra6"]
        except:
            number_df = None

    data_all = {}
    for f in txt_files:
        try:
            with open(f, encoding="utf-8") as file:
                data_all[f] = [
                    list(map(int, line.strip().split()))
                    for line in file
                    if line.strip() and len(line.strip().split()) >= 10
                ]
        except Exception:
            data_all[f] = []

    outputs = []

    outputs.extend(run_2nd_and_4th_latest(data_all, filename))
    if number_df is not None:
        outputs.extend(run_AA_NEW_latest(data_df, number_df))
    if fam_map_full:
        outputs.extend(run_a_best_latest(data_df, fam_map_full))
    outputs.extend(run_4_5win_latest(filename))
    outputs.extend(run_A_OLIVIA_latest(data_df))
    outputs.extend(run_transfer_logic_latest(filename))
    outputs.extend(run_final_mawu_improved(data_list))

    best_3_outputs = run_A_best_3_family_latest(data_list, fam_map_full, fam_map_simple)
    if best_3_outputs:
        outputs.append(f"A best 3 family combined prediction: {best_3_outputs}")

    if outputs:
        format_and_print_outputs(outputs, filename, len(data_list))
    else:
        print("\nNo conditions met in any script. No predictions to show.\n")

    input("\nPress Enter to close...")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        filename = sys.argv[1]

        try:
            data_df = pd.read_csv(filename, sep="\t", header=None)
        except Exception as e:
            print(f"[X] Failed to load file {filename} with pandas: {e}")
            sys.exit(1)

        data_list = []
        try:
            with open(filename, encoding="utf-8") as f:
                for line in f:
                    parts = line.strip().split()
                    if len(parts) >= 10:
                        try:
                            nums = list(map(int, parts))
                            data_list.append(nums)
                        except:
                            continue
        except Exception as e:
            print(f"[X] Failed to load file {filename} as list: {e}")
            sys.exit(1)

        if len(data_list) < 44:
            print(f"[X] Need at least 44 events; file has only {len(data_list)}")
            sys.exit(1)

        fam_map_full = load_family_map_full("a.code,counter.txt")
        fam_map_simple = load_family_map_simple("a.code,counter.txt")
        if not fam_map_full or not fam_map_simple:
            print("[X] Family map file 'a.code,counter.txt' missing or invalid.")
            sys.exit(1)

        number_df = None
        if os.path.exists("number.txt"):
            try:
                number_df = pd.read_csv("number.txt", sep="\t", header=None)
                number_df.columns = ["Number","Counterpart","Bonanza","StringKey",
                                     "Extra1","Extra2","Extra3","Extra4","Extra5","Extra6"]
            except:
                number_df = None

        txt_files = [
            f for f in os.listdir()
            if os.path.isfile(f)
            and f.lower().endswith(".txt")
            and f.lower() != "a.code,counter.txt"
        ]
        data_all = {}
        for f in txt_files:
            try:
                with open(f, encoding="utf-8") as file:
                    data_all[f] = [
                        list(map(int, line.strip().split()))
                        for line in file
                        if line.strip() and len(line.strip().split()) >= 10
                    ]
            except Exception:
                data_all[f] = []

        outputs = []
        outputs.extend(run_2nd_and_4th_latest(data_all, filename))
        if number_df is not None:
            outputs.extend(run_AA_NEW_latest(data_df, number_df))
        if fam_map_full:
            outputs.extend(run_a_best_latest(data_df, fam_map_full))
        outputs.extend(run_4_5win_latest(filename))
        outputs.extend(run_A_OLIVIA_latest(data_df))
        outputs.extend(run_transfer_logic_latest(filename))
        outputs.extend(run_final_mawu_improved(data_list))
        best_3_outputs = run_A_best_3_family_latest(data_list, fam_map_full, fam_map_simple)
        if best_3_outputs:
            outputs.append(f"A best 3 family combined prediction: {best_3_outputs}")

        for line in outputs:
            print(line)
        sys.exit(0)
    else:
        main()
