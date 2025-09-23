import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os
import argparse

# ------------------------------
# Parse command-line arguments
# ------------------------------
parser = argparse.ArgumentParser(description="Generate plots from software metrics CSVs")
parser.add_argument('--results_dir', required=True, help='Path to the folder containing per_file.csv, per_function.csv, per_module.csv')
parser.add_argument('--out_dir', default='plots', help='Folder to save generated plots')
args = parser.parse_args()

results_dir = args.results_dir
out_dir = args.out_dir
os.makedirs(out_dir, exist_ok=True)

# ------------------------------
# 1. Total LOC per module
# ------------------------------
df_module = pd.read_csv(os.path.join(results_dir, 'per_module.csv'))
df_module_sorted = df_module.sort_values('loc_physical', ascending=False)

plt.figure(figsize=(12,6))
df_module_sorted.plot.bar(x='module', y=['loc_physical', 'loc_logical'], figsize=(12,6))
plt.title('Physical vs Logical LOC per Module')
plt.ylabel('Lines of Code')
plt.xticks(rotation=45, ha='right')
plt.tight_layout()
plt.savefig(os.path.join(out_dir, 'loc_per_module.png'))
plt.close()

# ------------------------------
# 2. Cyclomatic Complexity per module
# ------------------------------
plt.figure(figsize=(12,6))
df_module_sorted.plot.bar(x='module', y='cc_total', color='orange')
plt.title('Total Cyclomatic Complexity per Module')
plt.ylabel('Cyclomatic Complexity')
plt.xticks(rotation=45, ha='right')
plt.tight_layout()
plt.savefig(os.path.join(out_dir, 'cc_per_module.png'))
plt.close()

# ------------------------------
# 3. Histogram of Cyclomatic Complexity per function
# ------------------------------
df_func = pd.read_csv(os.path.join(results_dir, 'per_function.csv'))
plt.figure(figsize=(10,6))
sns.histplot(df_func['cc'], bins=50, kde=False)
plt.title('Distribution of Cyclomatic Complexity per Function')
plt.xlabel('Cyclomatic Complexity')
plt.ylabel('Number of Functions')
plt.tight_layout()
plt.savefig(os.path.join(out_dir, 'cc_histogram.png'))
plt.close()

# ------------------------------
# 4. Scatter plot: CC vs Fan-out
# ------------------------------
plt.figure(figsize=(10,6))
sns.scatterplot(data=df_func, x='fan_out', y='cc')
plt.title('Cyclomatic Complexity vs Fan-out per Function')
plt.xlabel('Fan-out')
plt.ylabel('Cyclomatic Complexity')
plt.tight_layout()
plt.savefig(os.path.join(out_dir, 'cc_vs_fanout.png'))
plt.close()

# ------------------------------
# 5. Scatter plot: CC vs Fan-in
# ------------------------------
plt.figure(figsize=(10,6))
sns.scatterplot(data=df_func, x='fan_in', y='cc')
plt.title('Cyclomatic Complexity vs Fan-in per Function')
plt.xlabel('Fan-in')
plt.ylabel('Cyclomatic Complexity')
plt.tight_layout()
plt.savefig(os.path.join(out_dir, 'cc_vs_fanin.png'))
plt.close()

# ------------------------------
# 6. Heatmap of fan-in vs fan-out per module
# ------------------------------
df_module_heat = df_module.set_index('module')[['fan_in_total','fan_out_total']]
plt.figure(figsize=(10,6))
sns.heatmap(df_module_heat, annot=True, fmt='d', cmap='YlGnBu')
plt.title('Fan-in / Fan-out per Module')
plt.tight_layout()
plt.savefig(os.path.join(out_dir, 'fanin_fanout_per_module.png'))
plt.close()

print(f"All plots saved in '{out_dir}/' folder.")
