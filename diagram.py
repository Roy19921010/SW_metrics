import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os
import argparse

# ------------------------------
# Parse command-line arguments
# ------------------------------
parser = argparse.ArgumentParser(description="Generate per-module plots with totals")
parser.add_argument('--results_dir', required=True, help='Path to folder containing per_module.csv')
parser.add_argument('--out_dir', default='plots', help='Folder to save generated plots')
args = parser.parse_args()

results_dir = args.results_dir
out_dir = args.out_dir
os.makedirs(out_dir, exist_ok=True)

# ------------------------------
# Load per-module CSV
# ------------------------------
df_module = pd.read_csv(os.path.join(results_dir, 'per_module.csv'))

# Truncate module names to 10 characters
df_module['module_short'] = df_module['module'].apply(lambda x: x[:10])

# ------------------------------
# Compute totals
# ------------------------------
total_loc_physical = df_module['loc_physical'].sum()
total_loc_logical = df_module['loc_logical'].sum()
total_cc = df_module['cc_total'].sum()
total_fan_in = df_module['fan_in_total'].sum()
total_fan_out = df_module['fan_out_total'].sum()

print("=== Total values for the repo ===")
print(f"Physical LOC: {total_loc_physical}")
print(f"Logical LOC: {total_loc_logical}")
print(f"Cyclomatic Complexity: {total_cc}")
print(f"Fan-in: {total_fan_in}")
print(f"Fan-out: {total_fan_out}")

# ------------------------------
# 1. LOC per module (physical vs logical)
# ------------------------------
plt.figure(figsize=(14,6))
ax = df_module.plot.bar(x='module_short', y=['loc_physical', 'loc_logical'])
plt.ylabel('Lines of Code')
plt.xticks(rotation=45, ha='right')
# Set y-axis max slightly above the max LOC
ymax = df_module[['loc_physical', 'loc_logical']].max().max()
print("ymax is:", ymax)
plt.ylim(0, ymax)
# Add total as text box
plt.text(0.95, 0.95,
         f'Total Pysical LOC: {total_loc_physical}\nTotal Logical LOC: {total_loc_logical}',
         horizontalalignment='right',
         verticalalignment='top',
         transform=ax.transAxes,
         bbox=dict(facecolor='white', alpha=0.7, edgecolor='gray'))
plt.tight_layout()
plt.savefig(os.path.join(out_dir, 'loc_per_module.png'))
plt.close()

# ------------------------------
# 2. Cyclomatic Complexity per module
# ------------------------------
plt.figure(figsize=(14,6))
ax = df_module.plot.bar(x='module_short', y='cc_total', color='orange')
plt.ylabel('Cyclomatic Complexity')
plt.xticks(rotation=45, ha='right')
# Add total as text box
plt.text(0.95, 0.95,
         f'Total CC: {total_cc}',
         horizontalalignment='right',
         verticalalignment='top',
         transform=ax.transAxes,
         bbox=dict(facecolor='white', alpha=0.7, edgecolor='gray'))
plt.tight_layout()
plt.savefig(os.path.join(out_dir, 'cc_per_module.png'))
plt.close()

# ------------------------------
# 3. Fan-in and Fan-out per module (stacked)
# ------------------------------
plt.figure(figsize=(14,6))
ax = df_module.plot.bar(x='module_short', y=['fan_in_total', 'fan_out_total'], stacked=True)
plt.ylabel('Count')
plt.xticks(rotation=45, ha='right')
# Add totals as text box
plt.text(0.95, 0.95,
         f'Total Fan-in: {total_fan_in}\nTotal Fan-out: {total_fan_out}',
         horizontalalignment='right',
         verticalalignment='top',
         transform=ax.transAxes,
         bbox=dict(facecolor='white', alpha=0.7, edgecolor='gray'))
plt.tight_layout()
plt.savefig(os.path.join(out_dir, 'fanin_fanout_per_module.png'))
plt.close()

print(f"All per-module plots saved in '{out_dir}/'")
