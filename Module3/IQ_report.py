import ast
import matplotlib.pyplot as plt

report_file = "iq_check_report.txt"

# ---- Load list from txt ----
iq_results = []
with open(report_file, "r") as f:
    for line in f:
        line = line.strip()
        if line:  # skip empty lines
            try:
                # Convert string dict back to actual dict
                iq_results.append(ast.literal_eval(line))
            except Exception as e:
                print(f"Skipping line due to parse error: {line}\nError: {e}")

# ---- Prepare data for plotting ----
checks = [list(d.keys())[0] for d in iq_results]
statuses = [list(d.values())[0] for d in iq_results]
colors = ['green' if 'Pass' in s else 'red' for s in statuses]

# Overall status
overall_status = 'Pass' if all('Pass' in s for s in statuses) else 'Fail'
overall_color = 'green' if overall_status == 'Pass' else 'red'

# ---- Plot ----
plt.figure(figsize=(10, len(checks)*0.4 + 1))
plt.barh(checks, [1]*len(checks), color=colors)
plt.title(f"Information Quality Checks - Overall Status: {overall_status}", color=overall_color, fontsize=14)
plt.xlim(0, 1)
plt.xticks([])
plt.tight_layout()

# Save figure
plt.savefig("iq_checks_summary_from_txt.png", dpi=300)
plt.close()
print(f"📊 IQ summary figure saved as 'iq_checks_summary_from_txt.png'")
