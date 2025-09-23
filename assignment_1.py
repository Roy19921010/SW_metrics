import os, sys, json, argparse
from pathlib import Path
from collections import defaultdict
import csv
import re

# ----------------------------
# Language extension mapping
# ----------------------------
LANG_EXT = {
    'c': ['.c', '.h'],
    'cpp': ['.cpp', '.cc', '.cxx', '.hpp', '.hh', '.hxx'],
    'java': ['.java'],
    'py': ['.py'],
    'js': ['.js', '.jsx'],
    'ts': ['.ts', '.tsx']
}

# ----------------------------
# File walker
# ----------------------------
def walk_source_files(root, exts):
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            if any(fn.endswith(e) for e in exts):
                yield os.path.join(dirpath, fn)

# ----------------------------
# LOC counters
# ----------------------------
def count_physical_loc_file(path):
    loc = 0
    try:
        with open(path, 'r', errors='ignore') as f:
            for _ in f:
                loc += 1
    except Exception:
        return 0
    return loc

def count_logical_loc_file(path):
    ext = Path(path).suffix
    lloc = 0
    try:
        with open(path, 'r', errors='ignore') as f:
            for line in f:
                s = line.strip()
                if not s or s.startswith(('#', '//')):
                    continue
                if ext in ('.c', '.cpp', '.java', '.js', '.ts', '.hpp', '.cc'):
                    lloc += s.count(';')
                    if any(kw in s for kw in ['if', 'for', 'while', 'case', 'else']):
                        lloc += 1
                elif ext == '.py':
                    if s.startswith(('def ', 'class ', 'if ', 'for ', 'while ', 'elif ', 'else')):
                        lloc += 1
                    else:
                        lloc += 1
    except Exception:
        return 0
    return lloc

# ----------------------------
# Cyclomatic complexity
# ----------------------------
def compute_cyclomatic_complexity(path):
    ext = Path(path).suffix.lower()
    cc_per_func = {}
    cc_total = 0
    try:
        with open(path, 'r', errors='ignore') as f:
            lines = f.readlines()

        func_name = None
        cc = 0

        for line in lines:
            s = line.strip()

            # Detect function starts
            if ext in ('.c', '.cpp', '.java', '.js', '.ts', '.hpp', '.cc'):
                if re.match(r".*\w+\s+\w+\s*\(.*\)\s*{?", s):
                    if func_name:
                        cc_per_func[func_name] = cc
                        cc_total += cc
                    func_name = re.findall(r"(\w+)\s*\(", s)
                    func_name = func_name[0] if func_name else "anon_func"
                    cc = 1

            elif ext == '.py':
                if s.startswith("def "):
                    if func_name:
                        cc_per_func[func_name] = cc
                        cc_total += cc
                    func_name = re.findall(r"def\s+(\w+)\s*\(", s)
                    func_name = func_name[0] if func_name else "anon_func"
                    cc = 1

            # Count decision points
            if any(kw in s for kw in ["if", "for", "while", "case", "elif", "else if"]):
                cc += 1
            if "&&" in s or "||" in s:
                cc += 1
            if ext == '.py' and "except" in s:
                cc += 1

        if func_name:
            cc_per_func[func_name] = cc
            cc_total += cc

    except Exception:
        pass

    return cc_per_func, cc_total

# ----------------------------
# Call graph extraction
# ----------------------------
FUNC_DEF_RE_C = re.compile(r"\b([A-Za-z_][A-Za-z0-9_:<>]*)\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(")
FUNC_CALL_RE_C = re.compile(r"\b([A-Za-z_][A-Za-z0-9_:<>]*)\s*\(")
FUNC_DEF_RE_PY = re.compile(r"^\s*def\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(")
FUNC_CALL_RE_PY = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(")

def extract_functions_and_calls(file_path):
    funcs = []
    calls = []
    ext = Path(file_path).suffix.lower()
    try:
        with open(file_path, 'r', errors='ignore') as f:
            text = f.read()
            if ext in ('.c', '.cpp', '.java', '.js', '.ts', '.hpp', '.cc'):
                for m in FUNC_DEF_RE_C.finditer(text):
                    funcs.append(m.group(2))
                for m in FUNC_CALL_RE_C.finditer(text):
                    calls.append(m.group(1))
            elif ext == '.py':
                for m in FUNC_DEF_RE_PY.finditer(text, re.MULTILINE):
                    funcs.append(m.group(1))
                for m in FUNC_CALL_RE_PY.finditer(text):
                    calls.append(m.group(1))
    except Exception:
        pass
    return funcs, calls

def compute_fan_in_out(callgraph):
    fan_in = {f: 0 for f in callgraph}
    fan_out = {f: len(set(callees)) for f, callees in callgraph.items()}
    for caller, callees in callgraph.items():
        for callee in set(callees):
            if callee in fan_in:
                fan_in[callee] += 1
            else:
                fan_in[callee] = 1
    return fan_in, fan_out

# ----------------------------
# Main
# ----------------------------
def main():
    p = argparse.ArgumentParser()
    p.add_argument('--repo', required=True)
    p.add_argument('--langs', default='c,cpp')
    p.add_argument('--outdir', default='results')
    args = p.parse_args()
    repo = args.repo
    exts = []
    for L in args.langs.split(','):
        exts += LANG_EXT.get(L, [])
    files = list(walk_source_files(repo, exts))
    print(f"Found {len(files)} files matching extensions.")

    per_file_rows = []
    per_func_rows = []
    total_loc = total_lloc = total_cc = 0

    callgraph = defaultdict(set)

    for i, fpath in enumerate(files):
        loc = count_physical_loc_file(fpath)
        lloc = count_logical_loc_file(fpath)
        cc_per_func, cc_total_file = compute_cyclomatic_complexity(fpath)

        total_loc += loc
        total_lloc += lloc
        total_cc += cc_total_file

        per_file_rows.append({
            'file': fpath,
            'loc_physical': loc,
            'loc_logical': lloc,
            'cc_total': cc_total_file
        })

        for func, cc in cc_per_func.items():
            per_func_rows.append({
                'file': fpath,
                'function': func,
                'cc': cc,
                'fan_in': 0,   # fill later
                'fan_out': 0   # fill later
            })

        funcs, calls = extract_functions_and_calls(fpath)
        for func in funcs:
            for c in calls:
                callgraph[func].add(c)

    fan_in, fan_out = compute_fan_in_out(callgraph)

    # update per-function rows with fan-in/out
    for row in per_func_rows:
        fn = row['function']
        row['fan_in'] = fan_in.get(fn, 0)
        row['fan_out'] = fan_out.get(fn, 0)

    os.makedirs(args.outdir, exist_ok=True)

    # per-file CSV
    with open(os.path.join(args.outdir, 'per_file.csv'), 'w', newline='', encoding='utf-8') as csvf:
        writer = csv.DictWriter(csvf, fieldnames=['file','loc_physical','loc_logical','cc_total'])
        writer.writeheader()
        writer.writerows(per_file_rows)

    # per-function CSV
    with open(os.path.join(args.outdir, 'per_function.csv'), 'w', newline='', encoding='utf-8') as csvf:
        writer = csv.DictWriter(csvf, fieldnames=['file','function','cc','fan_in','fan_out'])
        writer.writeheader()
        writer.writerows(per_func_rows)

    summary = {
        'repo': repo,
        'file_count': len(files),
        'total_loc_physical': total_loc,
        'total_loc_logical': total_lloc,
        'total_cc': total_cc,
        'function_count': len(per_func_rows)
    }

    with open(os.path.join(args.outdir, 'summary.json'), 'w') as f:
        json.dump(summary, f, indent=2)

    with open(os.path.join(args.outdir, 'callgraph.json'), 'w') as f:
        json.dump({k: list(v) for k, v in callgraph.items()}, f)

    print('Wrote results to', args.outdir)

if __name__ == '__main__':
    main()
