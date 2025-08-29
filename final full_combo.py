import os
import numpy as np
from math import sqrt
from collections import Counter, defaultdict
from scipy.stats import f_oneway
from sklearn.metrics import pairwise_distances

# === FORMULAS ===

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
    return sanitize([
        sum(numbers) / len(numbers),
        max(numbers),
        min(numbers),
        (max(numbers) + min(numbers)) / 2
    ])

def time_series(numbers):
    return sanitize([
        numbers[-1],
        numbers[-2],
        (numbers[-1] + numbers[-2]) / 2,
        np.mean(numbers)
    ])

def improved_F3(numbers):
    try:
        a, b, c = numbers[0], numbers[1], numbers[2]
        root_term = b**2 - 4 * a * c
        if root_term < 0:
            root_term = 0
        x1 = (-b + sqrt(root_term)) / (2 * a) if a != 0 else 1
        x2 = (-b - sqrt(root_term)) / (2 * a) if a != 0 else 1
        log_avg = np.log1p(np.mean(numbers))
        poly_sum = a**2 + b**2 + c**2
        return sanitize([x1, x2, log_avg, poly_sum % 90])
    except:
        return sanitize([1, 2, 3, 4])

def F1(numbers):
    return sanitize([
        (numbers[0] + numbers[2]) / 2,
        (numbers[1] + numbers[3]) / 2,
        (numbers[2] + numbers[4]) / 2,
        (numbers[3] + numbers[5]) / 2
    ])

def F2(numbers):
    a, b, c, d = numbers[0], numbers[1], numbers[2], numbers[3]
    return sanitize([a + b - c, b + c - d, c + d - a, (a + d) / 2])

def simultaneous_eq(numbers):
    a, b, c = numbers[0], numbers[1], numbers[2]
    x = (a + b + c) / 3
    y = (a * b - c) / 2
    return sanitize([x, y, abs(x - y), (x + y) / 2])

def anova(numbers):
    try:
        mid = len(numbers) // 2
        group_1 = numbers[:mid]
        group_2 = numbers[mid:]
        f_stat, _ = f_oneway(group_1, group_2)
        predictions = [
            np.mean(group_1),
            np.mean(group_2),
            np.var(group_1),
            np.var(group_2),
            f_stat
        ]
        return sanitize(predictions)
    except:
        return sanitize([1, 2, 3, 4])

def hausdorff(numbers, base, comp):
    try:
        distances = pairwise_distances([base], [comp], metric='euclidean')
        return sanitize([np.mean(distances), np.max(distances)])
    except:
        return sanitize([1, 2, 3, 4])

def hybrid_prediction(numbers, base, comp):
    hybrid = []
    hybrid.extend(elijah(numbers))
    hybrid.extend(chebyshev(numbers))
    hybrid.extend(time_series(numbers))
    hybrid.extend(improved_F3(numbers))
    counts = Counter(hybrid)
    most_common = [num for num, _ in counts.most_common(4)]
    return sanitize(most_common)

# === FORMULA MAP ===

formulas = {
    "chebyshev": chebyshev,
    "anova": anova,
    "hausdorff": lambda x, b, c: hausdorff(x, b, c),
    "F1": F1,
    "F2": F2,
    "F3 (improved)": improved_F3,
    "elijah": elijah,
    "time_series": time_series,
    "sim_eq": simultaneous_eq,
    "hybrid": lambda x, b, c: hybrid_prediction(x, b, c),
}

# === HELPER TO GET CONTEXT SET ===

def get_context_set(data, event_index, window=9):
    """
    Return a set of all numbers (win + mac) from the `window` events
    immediately preceding `event_index`. If fewer than `window` draws
    exist before `event_index`, take what's available.
    """
    context = []
    for d in range(1, window + 1):
        idx = event_index - d
        if idx < 0:
            break
        row = data[idx]
        context += row[:5] + row[5:]
    return set(context)

# === TXT FILE SELECTION ===

txt_files = [f for f in os.listdir() if f.lower().endswith(".txt")]
if not txt_files:
    print("[X] No .txt files found.")
    exit()

print("\n[FILES] Available .txt files:")
for idx, file in enumerate(txt_files):
    print(f"{idx + 1}: {file}")

try:
    choice = int(input("\nSelect file number: ")) - 1
    selected_file = txt_files[choice]
except (ValueError, IndexError):
    print("[X] Invalid selection.")
    exit()

# === LOAD DATA ===

with open(selected_file, "r", encoding="utf-8") as f:
    lines = f.readlines()

data = []
for line in lines:
    parts = line.strip().split()
    if len(parts) >= 5:
        try:
            numbers = list(map(int, parts))
            data.append(numbers)
        except:
            continue

if len(data) < 5:
    print("[X] File doesn't have enough events.")
    exit()

# === HISTORICAL MATCH CHECK FOR UNION ONLY ===

print(f"\n🔎 Historical summary of Union‐based predictions for file: {selected_file}\n")

# We'll record events where the union of all formula predictions matched ≥2 numbers
historical_matches = []  # list of tuples (event_number, matched_list)
num_events = len(data)

for i in range(3, num_events - 1):
    current = data[i][:10]
    before_1 = data[i - 1][:5]
    before_2 = data[i - 2][:5]
    next_draw = set(data[i + 1][:5])

    # Build union of this event's predictions from all formulas
    union_preds = set()
    for name, func in formulas.items():
        try:
            if name in ["hausdorff", "hybrid"]:
                preds = func(current, before_2, before_1)
            else:
                preds = func(current)
            union_preds.update(preds)
        except:
            continue

    matched = sorted(union_preds.intersection(next_draw))
    if len(matched) >= 2:
        historical_matches.append((i + 1, matched))

# Print only matched numbers and their event numbers
if historical_matches:
    for evt, matched_nums in historical_matches:
        print(f"📌 Event {evt}: Matched Numbers: {matched_nums}")
else:
    print("⚠️ No historical events where Union matched ≥2 numbers.\n")

# === NEXT PREDICTION FROM LATEST EVENT (with UNION) ===

last_idx = num_events - 1
print(f"\n📄 Processing File: {selected_file}")
print(f"📌 Next Prediction Based on Latest Event: Event {num_events}")

latest = data[last_idx][:10]
before_1 = data[last_idx - 1][:5]
before_2 = data[last_idx - 2][:5]

all_predicted_nums = []
next_union = set()

for name, func in formulas.items():
    try:
        if name in ["hausdorff", "hybrid"]:
            preds = func(latest, before_2, before_1)
        else:
            preds = func(latest)
        next_union.update(preds)
        all_predicted_nums.extend(preds)
        print(f"{name:>15}: {preds}")
    except:
        print(f"{name:>15}: []  (failed)")

next_union = sorted(next_union)
print(f"\n🎯 COMBINED UNION PREDICTION (All Formulas): {next_union}")

# === OVERLAP LOGIC: LATEST UNION vs. LATEST CONTEXT ===

latest_context = get_context_set(data, last_idx, window=9)
overlap_count = len(set(next_union).intersection(latest_context))

# Label strength based on overlap_count
if overlap_count >= 14:
    strength = "📈 STRONG"
elif overlap_count >= 10:
    strength = "⚠️ MODERATE"
else:
    strength = "❌ WEAK"

print(f"\n🔗 Overlap between next union ({len(next_union)} numbers) "
      f"and the last 9‐draw context ({len(latest_context)} numbers): {overlap_count}")
print(f"🔰 Prediction Strength: {strength}\n")

input("Press Enter to exit...")
