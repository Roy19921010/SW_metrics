"""
Static analysis:
1) Physical LOC
2) Cyclomatic Complexity
3) Halstead Volume (manual computation)
4) Maintainability Index
5) Code Smells
6) Comment Percentage
"""

from pathlib import Path
import lizard
import math
import csv
import sys
import re

# -------------------
# Manual Halstead Function
# -------------------
JAVA_OPERATORS = [
    '=', '+', '-', '*', '/', '%', '++', '--', '==', '!=', '>', '<', '>=', '<=',
    '&&', '||', '!', '+=', '-=', '*=', '/=', '%=', '&', '|', '^', '<<', '>>',
    '>>>', '?', ':', '->', '::'
]

def compute_halstead(file_path: Path):
    """Compute Halstead metrics manually"""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            code = f.read()
    except Exception as e:
        print(f"File read error ({file_path}): {e}", file=sys.stderr)
        return {'halstead_volume': 0}

    # Remove comments
    code_nocomments = re.sub(r'//.*', '', code)
    code_nocomments = re.sub(r'/\*.*?\*/', '', code_nocomments, flags=re.DOTALL)

    # Tokenize
    tokens = re.findall(r'\b\w+\b|[^\s\w]', code_nocomments)

    # Count operators and operands
    operators = [t for t in tokens if t in JAVA_OPERATORS]
    operands = [t for t in tokens if t not in JAVA_OPERATORS and re.match(r'\w+', t)]

    n1 = len(set(operators))
    n2 = len(set(operands))
    N1 = len(operators)
    N2 = len(operands)

    if n1 + n2 == 0:
        volume = 0
    else:
        volume = (N1 + N2) * math.log2(n1 + n2)

    return {'halstead_volume': volume}


# -------------------
# Physical LOC + Comment Percentage
# -------------------
def compute_loc_and_comments(filepath: Path):
    """Compute physical LOC and comment percentage"""
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
    except:
        return 0, 0.0

    total_lines = len(lines)
    if total_lines == 0:
        return 0, 0.0

    single_comment = sum(1 for line in lines if re.match(r'\s*//', line))
    
    # Multiline comments
    code = "".join(lines)
    multi_comments = re.findall(r'/\*.*?\*/', code, flags=re.DOTALL)
    multi_comment_lines = sum(mc.count("\n") + 1 for mc in multi_comments)

    comment_lines = single_comment + multi_comment_lines
    comment_percentage = (comment_lines / total_lines) * 100.0

    return total_lines, comment_percentage


# -------------------
# Analyze Java File
# -------------------
def analyze_java_file(filepath: Path):
    """Compute all static metrics for a single Java file"""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            code = f.read()
    except Exception as e:
        print(f"File read error ({filepath}): {e}", file=sys.stderr)
        return {}

    try:
        analysis = lizard.analyze_file.analyze_source_code(filepath.name, code)
    except Exception as e:
        print(f"Lizard parse error ({filepath}): {e}", file=sys.stderr)
        return {}

    # Cyclomatic Complexity
    ccs = [f.cyclomatic_complexity for f in analysis.function_list] if analysis.function_list else []
    cc_max = int(max(ccs)) if ccs else 1
    cc_avg = float(sum(ccs) / len(ccs)) if ccs else 1.0

    # Halstead
    hal_vol = compute_halstead(filepath)['halstead_volume']

    # Maintainability Index
    nloc = int(analysis.nloc) if hasattr(analysis, 'nloc') and analysis.nloc else 1
    hv = hal_vol if hal_vol > 0 else 1.0
    cc_val = cc_avg if cc_avg > 0 else 1.0
    mi = 171 - 5.2 * math.log(abs(hv) + 1) - 0.23 * cc_val - 16.2 * math.log(abs(nloc) + 1)
    mi = float(max(0, min(100, mi)))

    # Code Smells
    smells = 0
    for f in analysis.function_list:
        if getattr(f, 'length', 0) > 50: smells += 1
        if getattr(f, 'max_nested_depth', 0) > 3: smells += 1
    if nloc > 400: smells += 1

    # NEW: Physical LOC + Comment %
    loc, comment_pct = compute_loc_and_comments(filepath)

    return {
        'cc_max': cc_max,
        'cc_avg': cc_avg,
        'halstead_volume': hal_vol,
        'nloc': nloc,
        'physical_loc': loc,
        'comment_percentage': comment_pct,
        'maintainability_index': mi,
        'code_smells': smells,
        'n_methods': len(analysis.function_list) if analysis.function_list else 0
    }


# -------------------
# Main Script
# -------------------
def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("-r", "--repo", default="/home/eiinluj/phd/rdi-datastream-dump-archiver")
    parser.add_argument("-o", "--output", default="static_metrics.csv")
    args = parser.parse_args()

    repo_path = Path(args.repo).resolve()
    java_files = list(repo_path.rglob("*.java"))
    print(f"Found {len(java_files)} Java files")

    rows = []
    for f in java_files:
        rel = str(f.relative_to(repo_path))
        res = analyze_java_file(f)
        if res:
            print(
                f"{rel} → "
                f"CC:{res['cc_max']} "
                f"Hal:{res['halstead_volume']:.1f} "
                f"MI:{res['maintainability_index']:.1f} "
                f"Smells:{res['code_smells']} "
                f"NLOC:{res['nloc']} "
                f"LOC:{res['physical_loc']} "
                f"Comments:{res['comment_percentage']:.1f}%"
            )
            rows.append({'filename': rel, **res})

    if rows:
        keys = rows[0].keys()
        with open(args.output, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(rows)
        print(f"Static metrics saved to {args.output}")

if __name__ == "__main__":
    main()
