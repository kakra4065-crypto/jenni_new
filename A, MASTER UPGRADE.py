import os
import re
import math
import hashlib
from collections import Counter

# ───── Utility ─────

def clamp(vals):
    """Clamp each value to an integer in [1,90]."""
    out = []
    for v in vals:
        try:
            iv = int(round(v))
        except:
            iv = 0
        out.append(max(1, min(90, iv)))
    return out

def count_history(preds, history, window=20):
    """
    Count how often each prediction appears in past winning numbers.
    history: list of rows, each row[:5] are winning numbers.
    """
    recent = history[-window:]
    cnt = Counter()
    for row in recent:
        for n in row[:5]:
            if n in preds:
                cnt[n] += 1
    return cnt

def hash_predict(inputs, salt):
    """
    Deterministic hash → [1..90]
    """
    s = salt + ":" + ",".join(map(str, inputs))
    h = hashlib.md5(s.encode()).hexdigest()
    val = int(h[:8], 16)
    return (val % 90) + 1

# ───── Predictors using three draws & shifted positions ─────

# ───── Even More Robust Quadratic Predictor ─────

def predict_quadratic(win0, mac0, win1, mac1, win2, mac2):
    """
    Quadratic Formula plus mixing offsets to guarantee varied outputs:
      • Compute two roots from (a=win0[2], b=win1[3], c=win2[4])
      • Compute two roots from (a=mac0[1], b=mac1[2], c=mac2[3])
      • Then mix each root with sums of win/mac arrays modulo 90 to spread values.
    Returns 4 unique numbers in [1..90].
    """
    # Helper to compute roots
    def compute_roots(a, b, c, fb):
        disc = b*b - 4*a*c
        sd = math.sqrt(abs(disc))
        if a != 0:
            return [(-b + sd)/(2*a), (-b - sd)/(2*a)]
        else:
            # fallback: use b±c divided by 2
            return [(b + c)/4, (b - c)/3]

    # 1) Get continuous roots
    r1, r2 = compute_roots(win0[2], win1[3], win2[4], win0[4])
    r3, r4 = compute_roots(mac0[1], mac1[2], mac2[3], mac0[3])

    # 2) Precompute sums to mix in
    sum_w0, sum_w1, sum_w2 = sum(win0), sum(win1), sum(win2)
    sum_m0, sum_m1, sum_m2 = sum(mac0), sum(mac1), sum(mac2)

    # 3) Mix and wrap into 1..90
    p1 = (round(r1 + sum_w2 + sum_w1) % 90) - 10
    p2 = (round(r2 + sum_w1 + sum_w2) % 90) + 5
    p3 = (round(r3 + sum_m0 + sum_m1) % 90) - 47
    p4 = (round(r4 + sum_m1 + sum_m2) % 90) + 37

    return [p1, p2, p3, p4]

def predict_euler(win0, mac0, win1, mac1, win2, mac2):
    θc = [win0[1]/90*2*math.pi, win0[3]/90*2*math.pi]
    θs = [win1[2]/90*2*math.pi, win2[4]/90*2*math.pi]
    preds = [ (math.cos(t)+1)/2*90 for t in θc ] + \
            [ (math.sin(t)+1)/2*90 for t in θs ]
    return clamp(preds)

def predict_navier_stokes(win0, mac0, win1, mac1, win2, mac2):
    """
    Powerful hash‐based predictor using all inputs.
    Guarantees 4 unique numbers.
    """
    inputs = win0 + mac0 + win1 + mac1 + win2 + mac2
    preds = []
    i = 1
    while len(preds) < 4:
        val = hash_predict(inputs, f"ns{i}")
        if val not in preds:
            preds.append(val)
        i += 1
    return preds

def predict_einstein(win0, mac0, win1, mac1, win2, mac2):
    R00 = (win0[2] + win1[3] + win2[4]) % 90 + 1
    R11 = (mac0[1] + mac1[4] + mac2[0]) % 90 + 1
    R22 = (win0[1] + mac1[0] + win2[3]) % 90 + 1
    R33 = (mac0[3] + win1[2] + mac2[1]) % 90 + 1
    return [R00, R11, R22, R33]

def predict_rocket(win0, mac0, win1, mac1, win2, mac2):
    """
    Powerful hash‐based predictor using all inputs.
    Guarantees 4 unique numbers.
    """
    inputs = win0 + mac0 + win1 + mac1 + win2 + mac2
    preds = []
    i = 1
    while len(preds) < 4:
        val = hash_predict(inputs, f"rk{i}")
        if val not in preds:
            preds.append(val)
        i += 1
    return preds

# ───── Main ─────

def main():
    files = [f for f in os.listdir() if f.lower().endswith('.txt')]
    if not files:
        print("No .txt files found.")
        return
    for i, f in enumerate(files, 1):
        print(f"{i}: {f}")
    sel = input("Select file #: ").strip()
    if sel.lower() == 'q':
        return
    try:
        idx = int(sel) - 1
        fname = files[idx]
    except:
        print("Invalid selection.")
        return

    # Read at least 3 draws
    lines = []
    with open(fname, 'r', encoding='utf-8') as f:
        for L in f:
            nums = re.findall(r'-?\d+', L)
            if len(nums) >= 10:
                lines.append(list(map(int, nums[:10])))
    if len(lines) < 3:
        print("Need at least 3 draws.")
        return

    # Extract current and two previous events
    cur   = lines[-1]
    prev1 = lines[-2]
    prev2 = lines[-3]
    win0, mac0 = cur[:5],   cur[5:10]
    win1, mac1 = prev1[:5], prev1[5:10]
    win2, mac2 = prev2[:5], prev2[5:10]

    # Run predictors
    q  = predict_quadratic(win0,mac0,win1,mac1,win2,mac2)
    e  = predict_euler   (win0,mac0,win1,mac1,win2,mac2)
    ns = predict_navier_stokes(win0,mac0,win1,mac1,win2,mac2)
    ef = predict_einstein (win0,mac0,win1,mac1,win2,mac2)
    rk = predict_rocket   (win0,mac0,win1,mac1,win2,mac2)

    combined = sorted(set(q + e + ns + ef + rk))
    hist = count_history(combined, lines[:-1], window=20)

    # Display
    print(f"\n🎯 Predictions for '{fname}':")
    print(f"  Quadratic Formula      → {q}")
    print(f"  Euler’s Formula        → {e}")
    print(f"  Navier–Stokes Approx.  → {ns}")
    print(f"  Einstein Field Eqns    → {ef}")
    print(f"  Rocket Science Eqns    → {rk}\n")
    print(f"🔀 Combined unique: {combined}\n")
    print("📊 Historical counts (last 20 draws):")
    for n in combined:
        print(f"  {n}: {hist.get(n, 0)} times")

if __name__ == '__main__':
    main()
    input("\nPress Enter to exit…")
