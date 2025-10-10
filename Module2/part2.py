# -*- coding: utf-8 -*-
import os
import git
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

# ---- USER INPUTS ----
REPO_PATH = "/home/eiinluj/phd/courses/test_metrics_course/week2/rdi-datastream-dump-archiver"
SRC_PATH_IDENTIFIER = "src/main"
TEST_PATH_IDENTIFIER = "src/test"
NUM_COMMITS = 22

# ---- INITIALIZE REPO ----
repo = git.Repo(REPO_PATH)
BRANCH_NAME = repo.active_branch.name
commits = list(repo.iter_commits(BRANCH_NAME, max_count=NUM_COMMITS))
commits.reverse()

results = []

# ---- SCAN COMMITS ----
for i in range(len(commits) - 1):
    commit_old = commits[i]
    commit_new = commits[i + 1]
    diff_index = commit_new.diff(commit_old, create_patch=True)

    src_added, src_deleted = 0, 0
    test_added, test_deleted = 0, 0

    for diff in diff_index:
        if diff.b_blob is None or diff.diff is None:
            continue
        diff_text = diff.diff.decode("utf-8", errors="ignore")
        lines_added = sum(1 for line in diff_text.split("\n") if line.startswith("+") and not line.startswith("+++"))
        lines_deleted = sum(1 for line in diff_text.split("\n") if line.startswith("-") and not line.startswith("---"))
        file_path = diff.b_path or diff.a_path or ""
        if TEST_PATH_IDENTIFIER in file_path:
            test_added += lines_added
            test_deleted += lines_deleted
        elif SRC_PATH_IDENTIFIER in file_path:
            src_added += lines_added
            src_deleted += lines_deleted

    results.append({
        "commit_hash": commit_new.hexsha[:8],
        "commit_date": commit_new.committed_datetime.strftime("%Y-%m-%d %H:%M:%S"),
        "src_added": src_added,
        "src_deleted": src_deleted,
        "test_added": test_added,
        "test_deleted": test_deleted,
        "src_total_change": src_added + src_deleted,
        "test_total_change": test_added + test_deleted
    })

# ---- SAVE RESULTS ----
df = pd.DataFrame(results)
df["ratio_src_vs_test"] = df["src_total_change"] / df["test_total_change"].replace(0, 1)
df["balance_status"] = df["ratio_src_vs_test"].apply(lambda r: "Balanced" if 0.2 <= r <= 5 else "Unbalanced")

csv_path = os.path.join(REPO_PATH, "commit_loc_changes.csv")
df.to_csv(csv_path, index=False)
print(f"✅ Saved LOC change statistics with balance info to: {csv_path}")

# ---- PLOT FIGURE 1: LOC Changes ----
plt.figure(figsize=(12,5))
plt.plot(df["commit_hash"], df["src_total_change"], marker='o', label="Source LOC change")
plt.plot(df["commit_hash"], df["test_total_change"], marker='o', label="Test LOC change")
plt.xticks(rotation=45)
plt.xlabel("Commit")
plt.ylabel("Lines of Code Changed")
plt.title("Source vs Test LOC Changes per Commit")
plt.grid(True)
plt.legend()
plt.tight_layout()
plt.savefig(os.path.join(REPO_PATH, "loc_changes.png"), dpi=300)
plt.close()
print(f"📈 Saved LOC changes figure to: {os.path.join(REPO_PATH, 'loc_changes.png')}")

# ---- PLOT FIGURE 2: Ratio with color, labels, and legend ----
plt.figure(figsize=(12,5))

for i, (commit, ratio) in enumerate(zip(df["commit_hash"], df["ratio_src_vs_test"])):
    color = "green" if 0.2 <= ratio <= 5 else "red"
    plt.scatter(commit, ratio, color=color, s=80, edgecolor='black', zorder=3)
    plt.text(commit, ratio + 0.1, f"{ratio:.2f}", ha='center', va='bottom', fontsize=8)

plt.plot(df["commit_hash"], df["ratio_src_vs_test"], linestyle='--', color='gray', alpha=0.5)
plt.xticks(rotation=45)
plt.xlabel("Commit")
plt.ylabel("Source/Test LOC Change Ratio")
plt.title("Ratio of Source to Test LOC Changes per Commit")

# Custom legend for color meaning
legend_elements = [
    Line2D([0], [0], marker='o', color='w', label='Balanced (0.2–5)', markerfacecolor='green', markersize=10, markeredgecolor='black'),
    Line2D([0], [0], marker='o', color='w', label='Unbalanced (<0.2 or >5)', markerfacecolor='red', markersize=10, markeredgecolor='black')
]
plt.legend(handles=legend_elements, loc="best")

plt.grid(True)
plt.tight_layout()
plt.savefig(os.path.join(REPO_PATH, "loc_ratio_colored.png"), dpi=300)
plt.close()
print(f"📊 Saved LOC ratio figure to: {os.path.join(REPO_PATH, 'loc_ratio_colored.png')}")

# ---- PRINT DATAFRAME ----
print(df)
