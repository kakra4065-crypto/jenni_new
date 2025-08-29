import os
import pandas as pd
import numpy as np
from math import sqrt
from collections import Counter, defaultdict
from scipy.stats import f_oneway
from sklearn.metrics import pairwise_distances

# === LOADERS ===

def load_number_file():
    """
    Loads number.txt into a pandas DataFrame, indexed by the first column.
    """
    df = pd.read_csv("number.txt", sep="\t", header=None)
    return df.set_index(0)

def load_family_data():
    """
    Loads a.code,counter.txt into a dict for A_BEST.
    """
    headers = ['number', 'counter', 'bonanza', 'string', 'turning',
               'malta', 'partner', 'equivalent', 'shadow', 'code']
    family = {}
    with open("a.code,counter.txt", "r") as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) == 10 and parts[0].isdigit():
                nums = list(map(int, parts))
                family[nums[0]] = dict(zip(headers[1:], nums[1:]))
    return family

def get_user_selected_txt():
    """
    Lists all *.txt files (except “a.code,counter.txt”), asks the user to pick one,
    and returns its filename.
    """
    txt_files = [f for f in os.listdir() if f.lower().endswith(".txt") and f != "a.code,counter.txt"]
    print("\n📂 Available .txt files:")
    for i, fname in enumerate(txt_files, 1):
        print(f"{i}: {fname}")
    choice = int(input("Select file number: "))
    return txt_files[choice - 1]

# === ANAT “LATEST ONLY” PREDICTION ===

def get_ANAT_latest(lines, number_df):
    """
    Returns the 4‐number set that ANAT would predict for the last row of 'lines'.
    """
    def transform(n):
        row = number_df.loc[n]
        return int(row.iloc[0]) + int(row.iloc[1]) + int(row.iloc[2])

    def formula_block(win, mac):
        return list({
            (win[0] + win[1] + win[2]) % 90 + 1,
            (mac[0] * 2 + mac[1] * 3) % 90 + 1,
            abs(win[2] - mac[2]) % 90 + 1,
            (transform(win[0]) + transform(mac[0])) % 90 + 1,
            (win[3] * mac[3]) % 90 + 1,
            (win[4] + mac[4] + transform(win[4])) % 90 + 1
        })

    def source_based(event_idx):
        if event_idx < 5 or event_idx >= len(lines) - 1:
            return []
        src = lines[event_idx - 1]
        win = src[:5]
        mac = src[5:]
        return list({
            (win[0] + win[2]) % 90 + 1,
            (mac[1] + mac[3]) % 90 + 1,
            (win[1] * 2 - mac[2]) % 90 + 1,
            (transform(mac[0]) + transform(win[4])) % 90 + 1
        })

    idx = len(lines) - 1
    current = lines[idx]
    win = current[:5]
    mac = current[5:]
    fp = formula_block(win, mac)
    sp = source_based(idx)
    final_preds = list(dict.fromkeys(fp + sp))[:4]
    return set(int(x) for x in final_preds)

# === OTHER PREDICTORS ===

def predict_from_AA_NEW(lines, number_df):
    event_df = pd.DataFrame(lines)
    final_idx = len(event_df) - 1
    try:
        cur = event_df.iloc[final_idx]
        prev = event_df.iloc[final_idx - 2]
        src_idx = min(
            (cur[3] + cur[4] + cur[7] + cur[8] + prev[5] + prev[6]) - 1,
            len(event_df) - 1
        )
        src = event_df.iloc[src_idx]
        sure = [int(src[0]), int(src[1])]
        base = sure[0]
        cp = int(number_df.loc[base, 1])
        sk = int(number_df.loc[cp, 3])
        return {sure[0], sure[1], cp, sk}
    except:
        return set()

def predict_from_A_BEST(data, family_map):
    df = pd.DataFrame(data)
    current_idx = len(df) - 1
    try:
        mac2 = df.iloc[current_idx, 6]
        mac4_prev = df.iloc[current_idx - 5, 8]
        diff = abs(mac2 - mac4_prev)
        src_event = current_idx - diff - 4
        banker = df.iloc[src_event, 6]
        third_win = df.iloc[src_event, 2]
        counter = family_map.get(third_win, {}).get("counter", 0)
        target_idx = src_event - (counter + 3)
        win_ref = df.iloc[target_idx, :5]
        check_win = df.iloc[current_idx - 18, :5]
        matches = set(win_ref).intersection(set(check_win))
        return set(int(x) for x in matches.union({banker}))
    except:
        return set()

def predict_from_ABOTH(df):
    latest_idx = len(df) - 1
    try:
        ref_numbers = [
            int(df.iloc[latest_idx, 0]),
            int(df.iloc[latest_idx - 1, 1]),
            int(df.iloc[latest_idx - 2, 2]),
            int(df.iloc[latest_idx - 3, 3]),
            int(df.iloc[latest_idx - 4, 4]),
        ]
        reference_sum = sum(ref_numbers)
        if reference_sum >= len(df):
            return set()

        event_ref = df.iloc[reference_sum - 1]
        sum_ref = int(event_ref[2]) + int(event_ref[3]) + int(event_ref[4])
        difference = abs(sum_ref - reference_sum)
        source_event_number = difference
        if source_event_number < 3 or source_event_number >= len(df):
            return set()

        banker = None
        nums = df.iloc[source_event_number - 3, 0:5].dropna().astype(int).tolist()
        close_pairs = [
            (a, b)
            for i, a in enumerate(nums)
            for b in nums[i+1:]
            if abs(a - b) == 1
        ]
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

        return set(int(x) for x in (main_predictions + third_prediction))
    except:
        return set()

def predict_from_AAA1(lines, number_dict):
    try:
        cur = lines[-1]
        total = (
            int(number_dict[cur[0]][1]) +   # 'bonanza'
            int(number_dict[cur[1]][2]) +   # 'stringKey'
            int(number_dict[cur[2]][3]) +   # 'extra1'
            cur[5] * 2 + cur[6] * 4 + cur[7] * 6
        )
        src = int(abs((total / 4) - len(lines)))
        if 0 <= src < len(lines):
            return {int(lines[src][2])}
        return set()
    except:
        return set()

def predict_from_FINAL_MAWU(lines):
    try:
        cur = lines[-1]
        prev = lines[-2]
        idx = len(lines) - (cur[2] + prev[3] + cur[6]) - 1
        if idx < 2:
            return set()
        src = lines[idx]
        extra = [cur[3]] if idx > 0 else []
        return set(int(x) for x in ([src[0], src[4]] + extra))
    except:
        return set()

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

def complete(results, event_number):
    try:
        current = results[event_number - 1]
        previous = results[event_number - 2]
        third_win = current[2]
        fourth_win_prev = previous[3]
        second_mac = current[6]
        idx = max(0, event_number - (third_win + fourth_win_prev + second_mac) - 1)
        row = results[idx]
        return [int(row[0]), int(row[4])]
    except:
        return None

# === RECENCY‐WEIGHTED HELPER ===

def recency_score(combined_set, lines, current_index, window=9):
    """
    For each number x in combined_set, look back up to 'window' events
    (not including current_index itself). If x appeared 'd' draws ago (1 ≤ d ≤ window),
    weight = 1/d. Sum weights. If not seen in last 'window', contributes 0.
    """
    score = 0.0
    last_seen = {}
    for d in range(1, window + 1):
        idx = current_index - d
        if idx < 0:
            break
        for num in lines[idx][:5] + lines[idx][5:]:
            if num not in last_seen:
                last_seen[num] = d

    for x in combined_set:
        if x in last_seen:
            score += 1.0 / last_seen[x]
    return score

# === CONTEXT BUILDER ===

def get_context_set(lines, event_index, window=9):
    """
    Return a set of all numbers (win + mac) from the 'window' events
    immediately preceding `event_index`. If there are fewer than `window`
    draws before event_index, we just take whatever is available.
    """
    context = []
    for d in range(1, window + 1):
        idx = event_index - d
        if idx < 0:
            break
        row = lines[idx]
        context += row[:5] + row[5:]
    return set(context)

# === FORMULAS (MATCHING final_full_combo.py EXACTLY) ===

def sanitize(predictions):
    seen = set()
    cleaned = []
    for x in predictions:
        num = max(1, min(90, int(round(x))))
        if num not in seen:
            cleaned.append(num)
            seen.add(num)
    return cleaned[:4]

def chebyshev(numbers):
    mean = np.mean(numbers)
    stddev = np.std(numbers)
    return sanitize([mean - stddev, mean + stddev, mean - 2*stddev, mean + 2*stddev])

def elijah(numbers):
    return sanitize([sum(numbers)/len(numbers), max(numbers), min(numbers), (max(numbers)+min(numbers))/2])

def time_series(numbers):
    return sanitize([numbers[-1], numbers[-2], (numbers[-1]+numbers[-2])/2, np.mean(numbers)])

def improved_F3(numbers):
    try:
        a, b, c = numbers[0], numbers[1], numbers[2]
        root_term = b**2 - 4*a*c
        if root_term < 0: root_term = 0
        x1 = (-b + sqrt(root_term)) / (2*a) if a != 0 else 1
        x2 = (-b - sqrt(root_term)) / (2*a) if a != 0 else 1
        log_avg = np.log1p(np.mean(numbers))
        poly_sum = a**2 + b**2 + c**2
        return sanitize([x1, x2, log_avg, poly_sum % 90])
    except:
        return sanitize([1,2,3,4])

def F1(numbers):
    return sanitize([(numbers[0]+numbers[2])/2, (numbers[1]+numbers[3])/2, (numbers[2]+numbers[4])/2, (numbers[3]+numbers[5])/2])

def F2(numbers):
    a, b, c, d = numbers[0], numbers[1], numbers[2], numbers[3]
    return sanitize([a + b - c, b + c - d, c + d - a, (a + d) / 2])

def simultaneous_eq(numbers):
    a, b, c = numbers[0], numbers[1], numbers[2]
    x = (a + b + c) / 3
    y = (a * b - c) / 2
    return sanitize([x, y, abs(x-y), (x+y)/2])

def anova(numbers):
    try:
        mid = len(numbers) // 2
        group_1 = numbers[:mid]
        group_2 = numbers[mid:]
        f_stat, _ = f_oneway(group_1, group_2)
        predictions = [np.mean(group_1), np.mean(group_2), np.var(group_1), np.var(group_2), f_stat]
        return sanitize(predictions)
    except:
        return sanitize([1,2,3,4])

def hausdorff(numbers, base, comp):
    try:
        distances = pairwise_distances([base], [comp], metric='euclidean')
        return sanitize([np.mean(distances), np.max(distances)])
    except:
        return sanitize([1,2,3,4])

def hybrid_prediction(numbers, base, comp):
    hybrid = []
    hybrid.extend(elijah(numbers))
    hybrid.extend(chebyshev(numbers))
    hybrid.extend(time_series(numbers))
    hybrid.extend(improved_F3(numbers))
    counts = Counter(hybrid)
    most_common = [num for num, _ in counts.most_common(4)]
    return sanitize(most_common)

# Map names to functions exactly as in final_full_combo.py
formulas = {
    "chebyshev":     lambda x, b2, b1: chebyshev(x),
    "anova":         lambda x, b2, b1: anova(x),
    "hausdorff":     lambda x, b2, b1: hausdorff(x, b2, b1),
    "F1":            lambda x, b2, b1: F1(x),
    "F2":            lambda x, b2, b1: F2(x),
    "F3 (improved)": lambda x, b2, b1: improved_F3(x),
    "elijah":        lambda x, b2, b1: elijah(x),
    "time_series":   lambda x, b2, b1: time_series(x),
    "sim_eq":        lambda x, b2, b1: simultaneous_eq(x),
    "hybrid":        lambda x, b2, b1: hybrid_prediction(x, b2, b1),
}

# === COMPOSITE CONFIDENCE (Recency + Context‐Overlap) ===

def evaluate_combined_full(lines, number_df, number_dict, family_map, alpha=0.5):
    total_events = 0
    count_exact_1 = 0
    count_exact_2 = 0
    count_exact_3 = 0
    count_exact_4 = 0
    count_exact_5 = 0

    hist_indices = []
    hist_matched = []
    hist_recency = []
    hist_contexts = []
    hist_match_count = []

    for i in range(10, len(lines) - 1):
        sub_lines = lines[: i + 1]
        df_sub = pd.DataFrame(sub_lines)

        an_set = get_ANAT_latest(sub_lines, number_df)
        aa_set = predict_from_AA_NEW(sub_lines, number_df)
        best_set = predict_from_A_BEST(sub_lines, family_map)
        both_set = predict_from_ABOTH(df_sub)
        aaa1_set = predict_from_AAA1(sub_lines, number_dict)
        mawu_set = predict_from_FINAL_MAWU(sub_lines)
        maw1_list = mawusi_1(sub_lines, i + 1)
        maw1_set = set(maw1_list) if maw1_list else set()
        maw2_list = mawusi_2(sub_lines, i + 1)
        maw2_set = set(maw2_list) if maw2_list else set()
        maw5_list = mawusi_5(sub_lines, i + 1)
        maw5_set = set(maw5_list) if maw5_list else set()
        comp_list = complete(sub_lines, i + 1)
        comp_set = set(comp_list) if comp_list else set()

        current = lines[i]
        before_1 = lines[i - 1][:5]
        before_2 = lines[i - 2][:5]
        formula_sets = []
        for name, func in formulas.items():
            try:
                preds = func(current, before_2, before_1)
                formula_sets.append({int(x) for x in preds})
            except:
                formula_sets.append(set())

        combined_set = (
            an_set | aa_set | best_set | both_set |
            aaa1_set | mawu_set |
            maw1_set | maw2_set | maw5_set | comp_set
        )
        for fs in formula_sets:
            combined_set |= fs

        Ri = recency_score(combined_set, lines, i, window=9)
        actual_next = set(lines[i + 1][:5])
        matched_numbers = combined_set.intersection(actual_next)
        match_count = len(matched_numbers)

        total_events += 1
        if match_count == 1:
            count_exact_1 += 1
        elif match_count == 2:
            count_exact_2 += 1
        elif match_count == 3:
            count_exact_3 += 1
        elif match_count == 4:
            count_exact_4 += 1
        elif match_count == 5:
            count_exact_5 += 1

        if match_count >= 2:
            hist_indices.append(i)
            hist_matched.append((i + 1, sorted(matched_numbers)))
            hist_recency.append(Ri)
            hist_contexts.append(get_context_set(lines, i, window=9))
            hist_match_count.append(match_count)

    for (evt, matched_nums) in hist_matched:
        print(f"📌 Event {evt}: Matched Numbers: {matched_nums}")

    print(f"\n🔹 Combined 1 Match only: {count_exact_1} / {total_events} = "
          f"{(count_exact_1/total_events)*100:.2f}%")
    print(f"✅ Combined 2 Matches: {count_exact_2} / {total_events} = "
          f"{(count_exact_2/total_events)*100:.2f}%")
    print(f"🎯 Combined 3 Matches: {count_exact_3} / {total_events} = "
          f"{(count_exact_3/total_events)*100:.2f}%")
    print(f"🔸 Combined 4 Matches: {count_exact_4} / {total_events} = "
          f"{(count_exact_4/total_events)*100:.2f}%")
    print(f"⭐ Combined 5 Matches: {count_exact_5} / {total_events} = "
          f"{(count_exact_5/total_events)*100:.2f}%\n")

    if not hist_indices:
        print("⚠️ No historical events with ≥2 matches. Cannot compute composite confidence.")
        return

    last_idx = len(lines) - 1
    latest_context = get_context_set(lines, last_idx, window=9)

    C_overlaps = [len(latest_context.intersection(ctx)) for ctx in hist_contexts]
    max_R = max(hist_recency) if hist_recency else 1.0
    max_C = max(C_overlaps) if C_overlaps else 1.0

    hist_S = []
    hist_S_by_bucket = {2: [], 3: [], 4: [], 5: []}

    for Ri, Ci, mc in zip(hist_recency, C_overlaps, hist_match_count):
        Rn = Ri / max_R
        Cn = Ci / max_C
        Si = alpha * Rn + (1 - alpha) * Cn
        hist_S.append(Si)
        hist_S_by_bucket[mc].append(Si)

    avg_S_by_bucket = {}
    for k in [2, 3, 4, 5]:
        lst = hist_S_by_bucket[k]
        avg_S_by_bucket[k] = (sum(lst) / len(lst)) if lst else 0.0

    p25_S = float(np.percentile(hist_S, 25))
    p75_S = float(np.percentile(hist_S, 75))
    max_S = max(hist_S)

    # --- Today's metrics ---
    df_full = pd.DataFrame(lines)
    latest_sets = [
        get_ANAT_latest(lines, number_df),
        predict_from_AA_NEW(lines, number_df),
        predict_from_A_BEST(lines, family_map),
        predict_from_ABOTH(df_full),
        predict_from_AAA1(lines, number_dict),
        predict_from_FINAL_MAWU(lines),
    ]
    lmaw1 = mawusi_1(lines, len(lines))
    latest_sets.append(set(lmaw1) if lmaw1 else set())
    lmaw2 = mawusi_2(lines, len(lines))
    latest_sets.append(set(lmaw2) if lmaw2 else set())
    lmaw5 = mawusi_5(lines, len(lines))
    latest_sets.append(set(lmaw5) if lmaw5 else set())
    lcomp = complete(lines, len(lines))
    latest_sets.append(set(lcomp) if lcomp else set())

    cur_latest = lines[-1]
    b1_latest = lines[-2][:5]
    b2_latest = lines[-3][:5]
    for name, func in formulas.items():
        try:
            preds = func(cur_latest, b2_latest, b1_latest)
            latest_sets.append({int(x) for x in preds})
        except:
            pass

    latest_combined = set().union(*latest_sets)
    R_latest = recency_score(latest_combined, lines, last_idx, window=9)
    C_latest = float(np.mean(C_overlaps))

    Rn_latest = R_latest / max_R
    Cn_latest = C_latest / max_C
    S_latest = alpha * Rn_latest + (1 - alpha) * Cn_latest

    likely_k = min(avg_S_by_bucket.keys(),
                   key=lambda k: abs(avg_S_by_bucket[k] - S_latest))

    if S_latest >= p75_S:
        strength_label = "STRONG"
    elif S_latest >= p25_S:
        strength_label = "MODERATE"
    else:
        strength_label = "WEAK"

    print("📊 Historical Recency & Context Overlap (≥2 match events):")
    print(f"    • max(R_i) = {max_R:.2f}")
    print(f"    • max(C_i) = {max_C:.2f}")
    print(f"    • 25th percentile of S_i = {p25_S:.3f}")
    print(f"    • 75th percentile of S_i = {p75_S:.3f}")
    print(f"    • max(S_i) = {max_S:.3f}\n")

    print("📊 Average Composite S̄_k by match‐count bucket k:")
    for k in [2, 3, 4, 5]:
        print(f"    • k = {k} → avg S̄_{k} = {avg_S_by_bucket[k]:.3f}")
    print()

    print(f"📊 Today’s recency R_latest = {R_latest:.3f}  (normalized = {Rn_latest:.3f})")
    print(f"📊 Today’s context‐mean C_latest = {C_latest:.3f}  (normalized = {Cn_latest:.3f})")
    print(f"📊 Today’s composite S_latest = {S_latest:.3f}\n")

    print(f"👉 Based on composite score, likely matches = {likely_k}  ({strength_label} confidence)\n")

# === MAIN EXECUTION ===

def combined_predictions():
    selected_file = get_user_selected_txt()
    with open(selected_file) as f:
        lines = [
            list(map(int, l.strip().split()))
            for l in f
            if len(l.strip().split()) >= 10
        ]

    number_df = load_number_file()
    number_dict = number_df.to_dict("index")
    family_map = load_family_data()

    # 1) Historical matched‐events + composite confidence
    evaluate_combined_full(lines, number_df, number_dict, family_map, alpha=0.5)

    # 2) FINAL COMBINED PREDICTION

    df_full = pd.DataFrame(lines)
    last_idx = len(lines) - 1

    print(f"📄 Processing File: {selected_file}")
    print(f"🔢 Last Event Number: {last_idx + 1}\n")
    print("🎯 INDIVIDUAL PREDICTIONS:")

    final_union = set()

    # ANAT
    anat = get_ANAT_latest(lines, number_df)
    print(f"ANAT: {sorted(anat)}")
    final_union |= anat

    # AA_NEW
    aa = predict_from_AA_NEW(lines, number_df)
    print(f"AA_NEW: {sorted(aa)}")
    final_union |= aa

    # A_BEST
    best = predict_from_A_BEST(lines, family_map)
    print(f"A_BEST: {sorted(best)}")
    final_union |= best


    # A_BOTH (updated to include MAC system + Banker logic from A.BOTH 6.py)
    def predict_aboth_mac_banker(df, idx):
        try:
            if idx < 4:
                return [], [], None

            ref_numbers = [
                int(df.iloc[idx, 0]),
                int(df.iloc[idx - 1, 1]),
                int(df.iloc[idx - 2, 2]),
                int(df.iloc[idx - 3, 3]),
                int(df.iloc[idx - 4, 4]),
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
                    int(df.iloc[idx, 6]),
                    int(df.iloc[idx, 7]),
                    int(df.iloc[idx, 8]),
                    int(df.iloc[idx - 1, 7]),
                    int(df.iloc[idx - 2, 7]),
                    int(df.iloc[idx - 4, 7]),
                ])
                combined_sum = mac_sum + reference_sum
                reference_event_mac = abs(combined_sum - (idx + 1))

                if 2 <= reference_event_mac + 1 < len(df):
                    mac_plus = df.iloc[reference_event_mac, 5:10].dropna().astype(int).tolist()
                    mac_minus = df.iloc[reference_event_mac - 2, 5:10].dropna().astype(int).tolist()
                    mac_predictions = sorted(set(num for num in mac_plus if num in mac_minus))
            except:
                pass

            return original_final_predictions, mac_predictions, banker

        except:
            return [], [], None

    aboth_preds, mac_preds, banker = predict_aboth_mac_banker(df_full, last_idx)
    print(f"A_BOTH: {sorted(aboth_preds)}")
    if banker:
        print(f"🔹 Banker: {banker}")
    print(f"🎯 MAC System Predictions: {sorted(mac_preds)}")

    final_union |= set(aboth_preds)
    final_union |= set(mac_preds)
    if banker:
        final_union.add(banker)
    # AAA1
    aaa1 = predict_from_AAA1(lines, number_dict)
    print(f"AAA1: {sorted(aaa1)}")
    final_union |= aaa1

    # FINAL_MAWU
    mawu = predict_from_FINAL_MAWU(lines)
    print(f"FINAL_MAWU: {sorted(mawu)}")
    final_union |= mawu

    # MAWUSI1
    maw1 = mawusi_1(lines, len(lines))
    maw1_set = set(maw1) if maw1 else set()
    print(f"MAWUSI1: {sorted(maw1_set)}")
    final_union |= maw1_set

    # MAWUSI2
    maw2 = mawusi_2(lines, len(lines))
    maw2_set = set(maw2) if maw2 else set()
    print(f"MAWUSI2: {sorted(maw2_set)}")
    final_union |= maw2_set

    # MAWUSI5
    maw5 = mawusi_5(lines, len(lines))
    maw5_set = set(maw5) if maw5 else set()
    print(f"MAWUSI5: {sorted(maw5_set)}")
    final_union |= maw5_set

    # COMPLETE
    comp = complete(lines, len(lines))
    comp_set = set(comp) if comp else set()
    print(f"COMPLETE: {sorted(comp_set)}")
    final_union |= comp_set

    print("\nFORMULAS:")
    cur_latest = lines[-1]
    b1_latest = lines[-2][:5]
    b2_latest = lines[-3][:5]

    for name, func in formulas.items():
        try:
            preds = func(cur_latest, b2_latest, b1_latest)
            preds_int = {int(x) for x in preds}
            preds_sorted = sorted(preds_int)
            print(f"{name:>15}: {preds_sorted}")
            final_union |= preds_int
        except:
            print(f"{name:>15}: []  (failed)")

    # Print final union
    sorted_union = sorted(final_union)
    print(f"\n🎯 FINAL COMBINED PREDICTION (All Systems & Formulas): {sorted_union}\n")

if __name__ == "__main__":
    combined_predictions()
    input("Press Enter to close...")
