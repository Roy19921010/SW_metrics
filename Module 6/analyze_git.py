#!/usr/bin/env python3
"""
Git metrics: 
1) Code Churn
2) Bug Fix Rate
3) Ownership
4) Review Participation
"""

from datetime import datetime, timedelta
from collections import defaultdict
from pathlib import Path
import csv
from pydriller import Repository
import sys

def analyze_git(repo_path: str, days=90, include_java_only=True):
    since = datetime.now() - timedelta(days=days)
    print(f"🔍 Git analysis window: {since.date()} → today ({days} days)")
    
    file_churn = defaultdict(lambda: {'added': 0, 'deleted': 0})
    file_authors = defaultdict(set)
    file_author_added = defaultdict(lambda: defaultdict(int))
    file_commits_flags = defaultdict(list)
    commits_list = []

    bug_kws = {'fix', 'bug', 'error', 'fail', 'crash', 'issue', 'defect', 'hotfix'}
    review_kws = {'review', 'cr:', 'r=', 'code review', 'reviewed'}

    try:
        repo = Repository(repo_path, since=since)
        for commit in repo.traverse_commits():
            commits_list.append(commit)
            msg = (commit.msg or "").lower()
            is_bug = any(k in msg for k in bug_kws)
            is_review = any(k in msg for k in review_kws)

            for mfile in commit.modified_files:
                if not mfile.filename:
                    continue
                if include_java_only and not mfile.filename.endswith('.java'):
                    continue

                fname = str(Path(mfile.filename).as_posix())
                added = mfile.added_lines or 0
                deleted = mfile.deleted_lines or 0

                file_churn[fname]['added'] += added
                file_churn[fname]['deleted'] += max(deleted - added, 0)
                file_authors[fname].add(commit.author.name)
                file_author_added[fname][commit.author.name] += added
                file_commits_flags[fname].append({
                    'is_bug': is_bug,
                    'is_review': is_review,
                    'date': commit.author_date
                })
    except Exception as e:
        print(f"❌ PyDriller error: {e}", file=sys.stderr)
        return {}

    print(f"✅ Found {len(commits_list)} commits, {len(file_churn)} modified files")

    # Repo-wide avg commit interval
    commits_sorted = sorted(commits_list, key=lambda c: c.author_date)
    repo_intervals = [(commits_sorted[i].author_date - commits_sorted[i-1].author_date).total_seconds()/3600
                      for i in range(1, len(commits_sorted))]
    repo_avg_interval = sum(repo_intervals)/len(repo_intervals) if repo_intervals else 0.0
    print(f"⏱ Repo-wide avg commit interval: {repo_avg_interval:.2f} hours")

    # Compute per-file avg commit interval
    file_intervals = {}
    for f, commits in file_commits_flags.items():
        sorted_dates = sorted(c['date'] for c in commits)
        intervals = [(sorted_dates[i] - sorted_dates[i-1]).total_seconds()/3600
                     for i in range(1, len(sorted_dates))]
        file_intervals[f] = sum(intervals)/len(intervals) if intervals else 0.0
        # Debug: print timestamps and intervals
        print(f"\n🗂 File: {f}")
        print(f"   Commits: {[d.strftime('%Y-%m-%d %H:%M') for d in sorted_dates]}")
        print(f"   Intervals (hours): {['{:.2f}'.format(iv) for iv in intervals]}")
        print(f"   Avg interval: {file_intervals[f]:.2f} hours")

    churn = {f: v['added'] + v['deleted'] for f, v in file_churn.items()}
    authors = {f: len(file_authors[f]) for f in file_authors}
    bug_ratio = {}
    review_ratio = {}
    ownership_ratio = {}

    for f in file_commits_flags:
        commits = file_commits_flags[f]
        if commits:
            bug_ratio[f] = sum(c['is_bug'] for c in commits) / len(commits)
            review_ratio[f] = sum(c['is_review'] for c in commits) / len(commits)

    for f, amap in file_author_added.items():
        total = sum(amap.values())
        if total > 0:
            ownership_ratio[f] = max(amap.values()) / total

    return {
        'churn': churn,
        'authors': authors,
        'bug_ratio': bug_ratio,
        'review_ratio': review_ratio,
        'ownership_ratio': ownership_ratio,
        'avg_commit_interval_hours': file_intervals,  # per-file
        'total_commits': len(commits_list)
    }

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("-r", "--repo", default="/home/eiinluj/phd/courses/test_metrics_course/final/rdi-datastream-dump-archiver")
    parser.add_argument("-o", "--output", default="git_metrics.csv")
    parser.add_argument("-d", "--days", type=int, default=90)
    parser.add_argument("--all-files", action="store_true", help="Include non-Java files")
    args = parser.parse_args()

    print(f"Repo: {args.repo}")
    data = analyze_git(args.repo, args.days, include_java_only=not args.all_files)
    
    if data.get('total_commits', 0) == 0:
        print("No commits found in the time window. Try --days 365 or --all-files.")
        return

    all_files = set(data['churn'].keys()) | set(data['authors'].keys())
    print(f"Files with metrics: {len(all_files)}")

    rows = []
    for f in sorted(all_files):
        row = {
            'filename': f,
            'code_churn': data['churn'].get(f, 0),
            'author_count': data['authors'].get(f, 0),
            'bug_commit_ratio': data['bug_ratio'].get(f, 0.0),
            'review_participation_ratio': data['review_ratio'].get(f, 0.0),
            'ownership_ratio_top_author': data['ownership_ratio'].get(f, 0.0),
            'avg_commit_interval_hours': data['avg_commit_interval_hours'].get(f, 0.0)  # now per-file
        }
        rows.append(row)
        print(f"{f} → churn:{row['code_churn']} authors:{row['author_count']} "
              f"bugs:{row['bug_commit_ratio']:.2f} reviews:{row['review_participation_ratio']:.2f} "
              f"owner:{row['ownership_ratio_top_author']:.2f} interval:{row['avg_commit_interval_hours']:.2f}")

    if not rows:
        print("No files matched criteria. Try --all-files to include XML/config files.")
        # Still write header-only CSV
        rows = [{'filename': 'N/A', 'code_churn': 0, 'author_count': 0,
                 'bug_commit_ratio': 0.0, 'review_participation_ratio': 0.0,
                 'ownership_ratio_top_author': 0.0, 'avg_commit_interval_hours': 0.0}]

    with open(args.output, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    print(f"Git metrics saved to {args.output}")

if __name__ == "__main__":
    main()
