#!/usr/bin/env python3
"""
combine_wrapper.py

A script that runs two existing prediction scripts ('A master upgrade 2.py' and 'GENERAL_COMBO.py.py') on the same .txt file selection,
captures their final predictions, and outputs:
  1. ((duplicates))
  2. ((top3 duplicates by combined frequency))
  3. ((banker: top of top3))

Usage:
  python combine_wrapper.py

The script will list all .txt files in the current directory and prompt you to select one by its number.
"""
import subprocess
import re
from collections import Counter
import glob
import sys

def list_txt_files():
    files = sorted(glob.glob("*.txt"))
    if not files:
        print("No .txt files found in the current directory.")
        sys.exit(1)
    for idx, fname in enumerate(files, start=1):
        print(f"{idx}. {fname}")
    return files


def run_script_and_get_preds(script_path, file_index, keyword):
    """
    Runs a script, feeds it the file_index and newline to exit, and parses
    the prediction line containing 'keyword'. Returns list of ints.
    """
    proc = subprocess.Popen(
        [sys.executable, script_path],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    inputs = f"{file_index}\n\n"
    out, err = proc.communicate(inputs)

    for line in out.splitlines():
        if keyword in line:
            return [int(x) for x in re.findall(r"\d+", line)]
    raise RuntimeError(f"Could not find predictions in output of {script_path}")


def combine_predictions(preds1, preds2):
    """
    Given two lists of numeric predictions, compute:
      duplicates: sorted list of numbers in both
      top3: three numbers among those duplicates with highest combined frequency
      banker: the single number among top3 with highest frequency
    """
    dup_set = set(preds1) & set(preds2)
    duplicates = sorted(dup_set)

    freq = Counter(preds1 + preds2)
    top3 = [num for num, _ in freq.most_common() if num in dup_set][:3]
    banker = top3[0] if top3 else None
    return duplicates, top3, banker

if __name__ == "__main__":
    # List and select .txt file
    print("Select the .txt file to process:")
    files = list_txt_files()
    choice = input("Enter file number: ")
    try:
        idx = int(choice)
        if idx < 1 or idx > len(files):
            raise ValueError
    except ValueError:
        print("Invalid selection.")
        sys.exit(1)
    file_index = str(idx)

    # Run both scripts
    preds1 = run_script_and_get_preds(
        "A master upgrade 2.py",
        file_index,
        "Final 5-number prediction"
    )
    preds2 = run_script_and_get_preds(
        "GENERAL_COMBO.py.py",
        file_index,
        "FINAL COMBINED PREDICTION"
    )

    duplicates, top3, banker = combine_predictions(preds1, preds2)

    # Output only what was requested
    print(f"((({', '.join(map(str, duplicates))})))")
    print(f"((({', '.join(map(str, top3))})))")
    print(f"((({banker})))")
