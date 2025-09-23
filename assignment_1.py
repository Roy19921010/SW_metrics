#!/usr/bin/env python3
"""
Simple measurement instrument for repositories.
Usage:
  python assignment_1.py --repo /path/to/repo --langs c,c++,java,py --outdir results

Outputs:
  - results/summary.json, this file has the overall summary including McCabe Complexity, fan-in/out
  - results/per_file.csv, this tells you the locs info per file
  - results/per_module.csv
  - results/callgraph.json, this is the overall callgraph for the repo

Notes: to run analysis on a single file, considering putting the file in a folder and run the script on that folder path
"""
import os, sys, json, argparse, subprocess, multiprocessing
from pathlib import Path
from collections import defaultdict
import csv

try:
    import lizard
except Exception:
    lizard = None

# minimal helpers
LANG_EXT = {
    'c': ['.c', '.h'],
    'cpp': ['.cpp', '.cc', '.cxx', '.hpp', '.hh', '.hxx'],
    'java': ['.java'],
    'py': ['.py'],
    'js': ['.js', '.jsx'],
    'ts': ['.ts', '.tsx']
}

def walk_source_files(root, exts):
    for dirpath, dirnames, filenames in os.walk(root):
        for fn in filenames:
            if any(fn.endswith(e) for e in exts):
                yield os.path.join(dirpath, fn)

def count_physical_loc_file(path):
    ext = Path(path).suffix
    loc = 0
    try:
        with open(path, 'r', errors='ignore') as f:
            for line in f:
                s = line.strip()
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
                if not s or s.startswith(('#', '//')):  # skip blanks & comments
                    continue
                if ext in ('.c', '.cpp', '.java', '.js', '.ts', '.hpp', '.cc'):
                    # heuristic: count semicolons
                    lloc += s.count(';')
                    # add decision/control keywords if present
                    if any(kw in s for kw in ['if', 'for', 'while', 'case', 'else']):
                        lloc += 1
                elif ext == '.py':
                    # Python: count non-comment, non-blank lines
                    # for future proofness keep it like this first
                    if s.startswith(('def ', 'class ', 'if ', 'for ', 'while ', 'elif ', 'else')):
                        lloc += 1
                    else:
                        lloc += 1
    except Exception:
        return 0
    return lloc


def measure_with_lizard(paths):
    # paths: list of files
    if lizard is None:
        return None
    analysis = lizard.analyze_files(paths)
    per_file = []
    for f in analysis:
        per_file.append({
            'filename': f.filename,
            'nloc': f.nloc,  # physical NLOC from lizard
            'cyclomatic_complexity': sum(func.cyclomatic_complexity for func in f.function_list) if f.function_list else 0,
            'function_count': len(f.function_list)
        })
    return per_file

# Call-graph naive heuristics
import re
from pathlib import Path

# Regex for C/C++/Java-style function definitions & calls
FUNC_DEF_RE_C = re.compile(r"\b([A-Za-z_][A-Za-z0-9_:<>]*)\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(")
FUNC_CALL_RE_C = re.compile(r"\b([A-Za-z_][A-Za-z0-9_:<>]*)\s*\(")

# Regex for Python function definitions
FUNC_DEF_RE_PY = re.compile(r"^\s*def\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(")
# Python function calls (simple heuristic)
FUNC_CALL_RE_PY = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(")

def extract_functions_and_calls(file_path):
    funcs = []
    calls = []

    ext = Path(file_path).suffix.lower()
    try:
        with open(file_path, 'r', errors='ignore') as f:
            text = f.read()
            
            if ext in ('.c', '.cpp', '.java', '.js', '.ts', '.hpp', '.cc'):
                # C/C++/Java-like files
                for m in FUNC_DEF_RE_C.finditer(text):
                    name = m.group(2)
                    funcs.append(name)
                for m in FUNC_CALL_RE_C.finditer(text):
                    name = m.group(1)
                    calls.append(name)

            elif ext == '.py':
                # Python files
                for m in FUNC_DEF_RE_PY.finditer(text, re.MULTILINE):
                    name = m.group(1)
                    funcs.append(name)
                for m in FUNC_CALL_RE_PY.finditer(text):
                    name = m.group(1)
                    calls.append(name)

    except Exception:
        pass

    return funcs, calls



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
    total_loc = 0
    total_lloc = 0
    # streaming pass: physical LOC + collect files for lizard in batches
    for i, fpath in enumerate(files):
        loc = count_physical_loc_file(fpath)
        lloc = count_logical_loc_file(fpath)
        total_loc += loc
        total_lloc += lloc
        per_file_rows.append({'file': fpath, 'loc_physical': loc, 'loc_logical': lloc})
        if i % 10000 == 0 and i>0:
            print(f"... processed {i} files, total_loc ~ {total_loc}")

    os.makedirs(args.outdir, exist_ok=True)
    per_file_csv = os.path.join(args.outdir, 'per_file.csv')
    with open(per_file_csv, 'w', newline='', encoding='utf-8') as csvf:
        writer = csv.DictWriter(csvf, fieldnames=['file','loc_physical', 'loc_logical'])
        writer.writeheader()
        writer.writerows(per_file_rows)

    summary = {
        'repo': repo,
        'file_count': len(files),
        'total_loc_physical': total_loc,
        'total_loc_logical': total_lloc
    }

    # try lizard for CC
    lizard_res = measure_with_lizard(files)
    if lizard_res is not None:
        # write simple aggregation
        cc_total = 0
        func_count = 0
        for r in lizard_res:
            cc_total += r['cyclomatic_complexity']
            func_count += r['function_count']
        summary['cc_total'] = cc_total
        summary['function_count'] = func_count

    # simple call graph pass (naive)
    callgraph = defaultdict(set)
    for fpath in files:
        funcs, calls = extract_functions_and_calls(fpath)
        for func in funcs:
            # opportunistically set the owner file
            caller = func
            for c in calls:
                callgraph[caller].add(c)

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
    fan_in, fan_out = compute_fan_in_out(callgraph)
    summary['fan_in'] = fan_in
    summary['fan_out'] = fan_out
    per_func_metrics = []
    for func in callgraph:
        per_func_metrics.append({
            "function": func,
            "fan_in": fan_in.get(func, 0),
            "fan_out": fan_out.get(func, 0)
        })


    # write callgraph
    cg_out = os.path.join(args.outdir, 'callgraph.json')
    with open(cg_out, 'w') as f:
        json.dump({k: list(v) for k,v in callgraph.items()}, f)

    summary_out = os.path.join(args.outdir, 'summary.json')
    with open(summary_out, 'w') as f:
        json.dump(summary, f, indent=2)
    print('Wrote results to', args.outdir)

if __name__ == '__main__':
    main()
