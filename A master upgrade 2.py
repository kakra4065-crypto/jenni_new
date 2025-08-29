import os
import math
import pandas as pd
from collections import Counter

# ───── Utility Helpers ─────

def clamp(vals):
    out = []
    for v in vals:
        try:
            iv = int(round(v))
        except:
            iv = 0
        out.append(max(1, min(90, iv)))
    return out

def ensure_unique(vals):
    vals = clamp(vals)
    for i in range(len(vals)):
        offset = (i+1)*13
        while vals.count(vals[i]) > 1:
            vals[i] = (vals[i] + offset) % 90 + 1
    return vals

def list_txt_files():
    return [f for f in os.listdir() if f.lower().endswith('.txt')]

# ───── Predictor Functions (each returns 3 values) ─────

def predict_navier_stokes6(win0, mac0, winL, macL, winM, macM):
    u = (win0[1] - winM[3]) / (macM[2] + 1)
    v = (winM[2] - winL[0]) / (macL[4] + 1)
    w = (win0[4] - macL[1]) / (macM[1] + 1)
    x = (mac0[2] - winM[1]) / (winL[3] + 1)
    y = (win0[3] - macL[3]) / (mac0[4] + 1)
    return ensure_unique([u, v, w, x, y])

def predict_einstein6(win0, mac0, winL, macL, winM, macM):
    e1 = (winM[0] - macM[3]) / (winL[3] + 1)
    e2 = (mac0[2] - winM[2]) / (macL[3] + 1)
    e3 = (winL[1] - mac0[0]) / (win0[2] + 1)
    e4 = (macM[2] - win0[3]) / (macL[1] + 1)
    e5 = (win0[4] - macL[2]) / (mac0[1] + 1)
    return ensure_unique([e1, e2, e3, e4, e5])

def predict_riemann6(win0, mac0, winL, macL, winM, macM):
    def pi(n):
        return sum(1 for x in range(2, n+1) if all(x % j for j in range(2, int(x**0.5) + 1)))
    p1 = pi(winM[1]) - pi(win0[0])
    p2 = pi(macL[2]) - pi(macM[0])
    p3 = pi(winL[2]) - pi(mac0[3])
    p4 = pi(win0[3]) - pi(macL[3])
    p5 = pi(macM[1]) - pi(winL[1])
    return ensure_unique([p1, p2, p3, p4, p5])

def predict_quintic6(win0, mac0, winL, macL, winM, macM):
    a = macM[3] - winL[0]
    b = win0[2] - winM[2]
    c = mac0[1] - macL[3]
    d = macL[0] - win0[0]
    e = winM[4] - mac0[2]
    return ensure_unique([
        (abs(a)**5 - b**2) % 90 + 1,
        (abs(b)**5 - c**2) % 90 + 1,
        (abs(c)**5 - d**2) % 90 + 1,
        (abs(d)**5 - e**2) % 90 + 1,
        (abs(e)**5 - a**2) % 90 + 1
    ])

def predict_gaussian_curvature6(win0, mac0, winL, macL, winM, macM):
    g1 = (winM[0] * mac0[0] - winL[0] * macL[0]) / (macM[1] + 1)
    g2 = (mac0[1] * winL[1] - macL[1] * winM[1]) / (win0[1] + 1)
    g3 = (win0[2] * macM[2] - winM[2] * macL[2]) / (mac0[2] + 1)
    g4 = (macL[3] - win0[3]) / (macM[3] + 1)
    g5 = (winM[4] - mac0[4]) / (winL[4] + 1)
    return ensure_unique([g1, g2, g3, g4, g5])

def predict_schrodinger6(win0, mac0, winL, macL, winM, macM):
    s1 = ((winM[2]+1) / (macM[2]+1)) * 1.5
    s2 = ((mac0[1]+2) / (win0[0]+2)) * 0.8
    s3 = ((winL[1]+3) / (macL[0]+3)) * 1.2
    s4 = ((macM[3] + 4) / (winM[3] + 1)) * 0.9
    s5 = ((macL[4] + 5) / (win0[4] + 1)) * 1.1
    return ensure_unique([s1, s2, s3, s4, s5])

def predict_differential6(win0, mac0, winL, macL, winM, macM):
    d1 = (win0[0] - winM[0] - mac0[0]) * 1.1
    d2 = (winM[1] - winL[1] - macL[1]) * 1.1
    d3 = (macM[2] - macL[2] - win0[2]) * 0.9
    d4 = (winL[3] - winM[3] - mac0[3]) * 1.0
    d5 = (macL[4] - macM[4] - win0[4]) * 1.2
    return ensure_unique([d1, d2, d3, d4, d5])

def predict_black_scholes6(win0, mac0, winL, macL, winM, macM):
    S = win0[4]
    K = winM[4]
    vol = ((mac0[3] + macL[3] + macM[3]) / 3 + 1)
    c1 = ((S - K) / vol) * 1.2
    c2 = ((S + K) / (vol + 1)) * 0.9
    c3 = ((S * K) / (vol + 2)) * 1.1
    c4 = ((S + macL[2]) / (macM[1] + 1)) * 0.95
    c5 = ((K - mac0[1]) / (macL[1] + 1)) * 1.05
    return ensure_unique([c1, c2, c3, c4, c5])

def predict_lotka_volterra6(win0, mac0, winL, macL, winM, macM):
    a, b, c = winM[0], macM[0], winL[0]
    x1 = (a - b / (c + 1)) * 1.1
    x2 = (b - c / (a + 1)) * 0.95
    x3 = (c - a / (b + 1)) * 1.05
    x4 = (win0[2] - macL[2]) / (mac0[2] + 1)
    x5 = (winL[3] - winM[3]) / (macM[3] + 1)
    return ensure_unique([x1, x2, x3, x4, x5])

def predict_topology_geometry6(win0, mac0, winL, macL, winM, macM):
    p1 = (win0[1] - macM[3] + winM[1]) / (macL[4] + 1)
    p2 = (macL[3] - winL[3] + mac0[1]) / (winM[2] + 1)
    p3 = (winL[0] - mac0[2] + win0[2]) / (macM[2] + 1)
    p4 = (macM[0] - winM[0] + macL[0]) / (win0[0] + 1)
    p5 = (winM[3] - mac0[3] + winL[3]) / (macL[3] + 1)
    return ensure_unique([p1, p2, p3, p4, p5])

def predict_poincare6(win0, mac0, winL, macL, winM, macM):
    p1 = (win0[0] - macM[1]) / (macL[1] + 1)
    p2 = (mac0[0] - winM[1]) / (winL[1] + 1)
    p3 = (winL[2] - mac0[4]) / (macM[2] + 1)
    p4 = (macL[3] - win0[3]) / (winM[3] + 1)
    p5 = (macM[4] - winL[4]) / (mac0[4] + 1)
    return ensure_unique([p1, p2, p3, p4, p5])

def predict_calabi_yau6(win0, mac0, winL, macL, winM, macM):
    p1 = (winM[0] * winL[0]) / (mac0[0] + 1)
    p2 = (macM[1] * macL[1]) / (win0[1] + 1)
    p3 = (win0[2] * mac0[2]) / (macM[2] + 1)
    p4 = (mac0[3] * winM[3]) / (macL[3] + 1)
    p5 = (winL[4] * macM[4]) / (mac0[4] + 1)
    return ensure_unique([p1, p2, p3, p4, p5])

def predict_bayesian6(win0, mac0, winL, macL, winM, macM):
    l1 = (mac0[0] / (macM[0] + 1)) * 40
    l2 = (win0[1] / (winM[1] + 1)) * 30
    l3 = (macL[2] / (winL[2] + 1)) * 35
    l4 = (mac0[3] / (macL[3] + 1)) * 25
    l5 = (win0[4] / (winL[4] + 1)) * 20
    return ensure_unique([l1, l2, l3, l4, l5])

def predict_stochastic6(win0, mac0, winL, macL, winM, macM):
    s1 = (win0[0] - macM[0] - winL[0]) * 1.05
    s2 = (win0[1] - mac0[1] - winM[1]) * 1.05
    s3 = (win0[2] - macL[2] - winL[2]) * 0.95
    s4 = (win0[3] - macM[3] - winM[3]) * 1.1
    s5 = (win0[4] - macL[4] - winL[4]) * 0.9
    return ensure_unique([s1, s2, s3, s4, s5])

def predict_merton6(win0, mac0, winL, macL, winM, macM):
    m1 = (winM[2] * mac0[2] - winL[2]) / (macL[2] + 1)
    m2 = (win0[3] * macM[3] - winM[3]) / (macL[3] + 1)
    m3 = (winL[4] * mac0[4] - win0[4]) / (macM[4] + 1)
    m4 = (win0[0] * macL[0] - winL[0]) / (mac0[0] + 1)
    m5 = (macM[1] * winM[1] - mac0[1]) / (winL[1] + 1)
    return ensure_unique([m1, m2, m3, m4, m5])

def predict_arbitrage6(win0, mac0, winL, macL, winM, macM):
    a1 = abs(mac0[0] - macM[0])
    a2 = abs(win0[1] - winM[1])
    a3 = abs(macL[2] - winL[2])
    a4 = abs(winM[3] - mac0[3])
    a5 = abs(macL[4] - win0[4])
    return ensure_unique([a1, a2, a3, a4, a5])

# ───── Lags per formula ─────

LAGS = {
    "Navier–Stokes":   1,
    "Einstein FE":     2,
    "Riemann Hyp.":    3,
    "Quintic Eqn":     4,
    "Gaussian K":      5,
    "Schrödinger":     6,
    "Differential":    7,
    "Black–Scholes":   8,
    "Lotka–Volterra":  9,
    "Topology/Geom":  10,
    "Poincaré":        1,
    "Calabi–Yau":      2,
    "Bayesian Inf":    3,
    "Stochastic":      4,
    "Merton Proc.":    5,
    "Arbitrage":       6,
}

# ───── Main Function ─────

def main():
    files = list_txt_files()
    if not files:
        print("[X] No .txt files found.")
        return

    print("📂 Available .txt files:")
    for idx, f in enumerate(files, 1):
        print(f"  {idx}: {f}")
    choice = input("Select a file #: ").strip()
    if not choice.isdigit():
        print("[X] Invalid selection.")
        return
    path = files[int(choice) - 1]

    df = pd.read_csv(path, sep="\t", header=None)
    n = len(df)
    max_lag = max(LAGS.values())
    if n < max_lag + 2:
        print(f"[X] Need ≥{max_lag+2} draws; only {n} in file.")
        return

    print(f"\n🎯 Next-Draw Predictions for '{path}' (draw {n}):\n")

    all_preds = []
    for name, fn in [
        ("Navier–Stokes",   predict_navier_stokes6),
        ("Einstein FE",     predict_einstein6),
        ("Riemann Hyp.",    predict_riemann6),
        ("Quintic Eqn",     predict_quintic6),
        ("Gaussian K",      predict_gaussian_curvature6),
        ("Schrödinger",     predict_schrodinger6),
        ("Differential",    predict_differential6),
        ("Black–Scholes",   predict_black_scholes6),
        ("Lotka–Volterra",  predict_lotka_volterra6),
        ("Topology/Geom",   predict_topology_geometry6),
        ("Poincaré",        predict_poincare6),
        ("Calabi–Yau",      predict_calabi_yau6),
        ("Bayesian Inf",    predict_bayesian6),
        ("Stochastic",      predict_stochastic6),
        ("Merton Proc.",    predict_merton6),
        ("Arbitrage",       predict_arbitrage6),
    ]:
        lag = LAGS[name]
        win0 = list(df.iloc[-1, :5])
        mac0 = list(df.iloc[-1, 5:10])
        winM = list(df.iloc[-2, :5])
        macM = list(df.iloc[-2, 5:10])
        winL = list(df.iloc[-1 - lag, :5])
        macL = list(df.iloc[-1 - lag, 5:10])
        preds = fn(win0, mac0, winL, macL, winM, macM)
        print(f"  {name:<15}→ {preds}")
        all_preds.extend(preds)

    mode5 = [num for num, _ in Counter(all_preds).most_common(5)]
    print(f"\n📊 Final 5-number prediction (mode across formulas): {mode5}")
    input("\nPress Enter to exit…")

if __name__ == "__main__":
    main()
