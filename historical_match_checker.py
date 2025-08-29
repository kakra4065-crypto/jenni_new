import sys, os, re, tempfile, subprocess
from collections import Counter

# Helper: extract groups from script output
def extract_groups(text):
    pattern = r'\[(?:\s*\d+\s*[,\s]+)+\d+\s*\]'
    return [[int(n) for n in re.findall(r'\d+', m.group())] for m in re.finditer(pattern, text)]

# Helper: compute predictions
def compute_predictions(g1, g2):
    c1, c2 = Counter(), Counter()
    for g in g1: c1.update(set(g))
    for g in g2: c2.update(set(g))
    shared, tot = [], {}
    for n in set(c1) | set(c2):
        t = c1[n] + c2[n]
        if t >= 2 and not (c1[n] == c2[n] == 1):
            shared.append(n)
            tot[n] = t
    ranked = sorted(shared, key=lambda n: (-tot[n], n))
    return sorted(shared), ranked[:14]

# Parse events from file
def parse_events(fp):
    events = []
    with open(fp) as f:
        for ln in f:
            m = re.search(r'Event\s+(\d+):\s*((?:\d+\s+){5})\|', ln)
            if m:
                events.append((int(m.group(1)), ln))
    events.sort(key=lambda x: x[0])  # ascending
    return events

# Run prediction script
def run_and_capture(script, txt_file):
    import shutil
    import sys
    import os
    name = os.path.basename(script)
    path = os.path.abspath(script)
    with tempfile.TemporaryDirectory() as tmp:
        shutil.copy(txt_file, tmp)
        if os.path.exists('number.txt'): shutil.copy('number.txt', tmp)
        for d in ['a.code', 'counter.txt']:
            if os.path.exists(d): shutil.copy(d, tmp)
        env = os.environ.copy(); env['PYTHONIOENCODING'] = 'utf-8'
        p = subprocess.Popen([sys.executable, path], cwd=tmp, stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             text=True, errors='ignore', env=env)
        out, _ = p.communicate('1\n\n')
    return out

def simulate_last20(fp, window=20):
    ev = parse_events(fp)
    if len(ev) < 2: return []
    matches = []; start = max(0, len(ev) - (window + 1))
    for i in range(start, len(ev) - 1):
        ev_no, line = ev[i]
        next_nums = [int(x) for x in re.findall(r'\d+', ev[i+1][1])][1:6]
        with tempfile.NamedTemporaryFile('w+', delete=False) as tmp:
            tmp.writelines([ln for _, ln in ev[:i+1]])
            tmp_name = tmp.name
        gC = extract_groups(run_and_capture('GENERAL_COMBO.py', tmp_name))
        gM = extract_groups(run_and_capture('A master upgrade 2.py', tmp_name))
        shared, topX = compute_predictions(gM, gC)
        top_hit = sorted(set(topX) & set(next_nums))
        sh_hit = sorted(set(shared) & set(next_nums))
        if top_hit or sh_hit:
            seg = []
            if top_hit: seg.append(f"TopX {top_hit} ({len(top_hit)})")
            if sh_hit:  seg.append(f"Shared {sh_hit} ({len(sh_hit)})")
            matches.append(f"Event {ev_no}: " + "; ".join(seg))
        os.unlink(tmp_name)
    return matches[-window:]

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python historical_match_checker.py <draw_file.txt>")
        sys.exit(1)
    draw_file = sys.argv[1]
    results = simulate_last20(draw_file, 20)
    for line in results:
        print(line)
