import logging
logging.basicConfig(filename='./information_quality.log', 
                    filemode='w',
                    format='%(asctime)s;%(name)s;%(levelname)s;%(message)s',
                    level=logging.DEBUG)

logger = logging.getLogger('IQ_info')

logger.info('Configuration started')
iq_results = []  # Store check results for summary and visualization
# ---- Package importation check ----
try:
    import requests, json
    import pandas as pd
    from datetime import datetime, timedelta
    import matplotlib.pyplot as plt
    import numpy as np
    from scipy.interpolate import CubicSpline
    import ast
    import json
    import re
    import os
    logger.info(f"✅ All pacages loaded successfully.")
    iq_results.append({"Package importation check": "✅Pass"})
except Exception as e:
    logger.warning(f'Exception caught when importing libraries: {e.msg}')
    iq_results.append({"Package importation check": "❌Fail"})
PROD_URL =  "https://nosa.internal.ericsson.com"
PROD_AUTH = "Bearer "+"" # Fill in your appliaction token
url =  PROD_URL+ "/nosa-service-metadata/metadata/query"
headers = {'Content-type': 'application/json', 'Accept': 'application/json', 'Authorization': PROD_AUTH}

# ---- Date format check ----
try:
    # ---- USER INPUTS ----
    start_year=2025
    start_month=10
    start_day=1
    start_date = datetime(start_year, start_month, start_day, 10, 0, 0)

    end_year=2025
    end_month=10
    end_day=6
    end_date = datetime(end_year, end_month, end_day, 10, 0, 0)
    future_days = 5
    if end_date <= start_date:
        raise ValueError("End date must be after start date.")

    days_to_collect = (end_date - start_date).days
    iq_results.append({"Date format check": "✅Pass"})
except ValueError as e:
    logger.warning(f"Invalid date input: {e}")
    iq_results.append({"Date format check": "❌Fail"})

    

# ---- DATA COLLECTION ----
all_data = []
daily_counts = []

for i in range(days_to_collect):
    gte = (start_date + timedelta(days=i)).isoformat() + "Z"
    lte = (start_date + timedelta(days=i+1)).isoformat() + "Z"

    data = {
        "query": {
            "bool": {
                "must": [
                    {"query_string": {"query": "ESID0002", "time_zone": "Europe/Stockholm"}},
                    {"range": {"Created_Time": {"format": "strict_date_optional_time", "gte": gte, "lte": lte}}}
                ]
            }
        },
        "size": 9999
    }
    # ---- Json format check ----
    try:
        json.dumps(data)
        logger.info("✅ : Valid JSON string.")
        iq_results.append({"Json format check": "✅Pass"})
    except json.JSONDecodeError:
        logger.warning(f"❌ Invalid JSON. Error: {e}")
        iq_results.append({"Json format check": "❌Fail"})
    # ---- Database response check ----
    try:
        r = requests.post(url, data=json.dumps(data), headers=headers, verify=False)
        if r.status_code != 200:
            logger.warning(f"PROD_URL responded with status {r.status_code}")
        iq_results.append({"Database response check": "✅Pass"})
    except Exception as e:
        logger.warning(f"Unable to reach PROD_URL ({PROD_URL}): {e}")
        #raise SystemExit("❌ Cannot reach PROD_URL. Check VPN, URL, or token.")
        iq_results.append({"Database response check": "❌Fail"})
    content = json.loads(r.text)
    # ---- Response content non-empty check ----
    if 'results' in content:
        df_day = pd.json_normalize(content['results'])
        all_data.append(df_day)
        daily_counts.append({"date": gte[:10], "count": len(df_day)})
        print(f"✅ {gte[:10]} → {len(df_day)} rows")
        iq_results.append({"Response content non-empty check": "✅Pass"})
    else:
        print(f"⚠️ No data for {gte[:10]}")
        iq_results.append({"Response content non-empty check": "❌Fail"})


# ---- Dataframe concatenation check ----
try:
    # ---- Combine all results ----
    if all_data:
        df_all = pd.concat(all_data, ignore_index=True)
        print(f"\nTotal collected rows: {len(df_all)}")
    df_all.to_csv("all_data.csv")
    print("💾 Saved 'all_data.csv'")
    df_counts = pd.DataFrame(daily_counts)
    iq_results.append({"Dataframe concatenation check": "✅Pass"})
except Exception as e:
    logger.warning(f'Exception caught when combining dataframes: {e.msg}')
    iq_results.append({"Dataframe concatenation check": "❌Fail"})


# ---- Define status function ----
def get_status(count):
    if count == 0:
        return "Pass"
    elif count <= 100:
        return "Warning"
    else:
        return "Error"

# ---- INTERPOLATION + TREND FORECAST ----
df_counts["date"] = pd.to_datetime(df_counts["date"])
df_counts.set_index("date", inplace=True)
# ---- Prediction check ----
try:
    df_daily = df_counts.resample('D').asfreq()
    df_daily["count"] = df_daily["count"].interpolate(method='linear')
    iq_results.append({"Prediction check": "✅Pass"})
except Exception as e:
    logger.warning(f'Exception caught when doing interpolation: {e.msg}')
    iq_results.append({"Prediction check": "❌Fail"})

# Add status for actual counts
df_daily["status"] = df_daily["count"].apply(get_status)
df_daily.to_csv("daily_counts_with_status.csv")
print("💾 Saved 'daily_counts_with_status.csv'")

# Historical data for cubic spline
y = df_daily["count"].dropna().values
x = np.arange(len(y))
cs = CubicSpline(x, y, bc_type='natural')

total_days = len(df_daily) + future_days
x_full = np.arange(total_days)
full_counts = cs(x_full)

# Non-negative integers
full_counts = np.maximum(full_counts, 0)
full_counts = np.round(full_counts).astype(int)

full_index = pd.date_range(df_daily.index[0], periods=total_days)
full_df = pd.DataFrame({"count": full_counts}, index=full_index)

full_df_reset = full_df.reset_index()
full_df_reset.rename(columns={"index": "date"}, inplace=True)
full_df_reset["status"] = full_df_reset["count"].apply(get_status)
full_df_reset.to_csv("trend_forecast_with_status.csv", index=False)


# ---- Plotting check ----
try:
    # ---- PLOT WITH INDICATORS (actual + forecast) ----
    plt.figure(figsize=(10,5))

    # Plot actual line (solid)
    plt.plot(df_daily.index, df_daily["count"], "-", color='black', alpha=1.0, label="Actual")

    # Color-coded actual points
    for i, val in enumerate(df_daily["count"].values):
        date = df_daily.index[i]
        if val == 0:
            color = 'green'
        elif val <= 100:
            color = 'yellow'
        else:
            color = 'red'
        plt.scatter(date, val, color=color, label="_nolegend_")

    # Plot forecast line (dashed)
    plt.plot(full_df.index, full_df["count"], "--", color='blue', alpha=0.5, label="Forecast")

    # Color-coded forecast points with black edge
    for i, val in enumerate(full_counts):
        date = full_index[i]
        if val == 0:
            color = 'green'
        elif val <= 100:
            color = 'yellow'
        else:
            color = 'red'
        plt.scatter(date, val, color=color, edgecolor='black', label="_nolegend_")

    plt.title("Fan toggling count with predictions")
    plt.xlabel("Date")
    plt.ylabel("Fan toggling Count")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.savefig("trend_forecast_with_indicators.png", dpi=300)
    plt.close()
    print("📈 Saved 'trend_forecast_with_indicators.png'")
    iq_results.append({"Plotting check": "✅Pass"})
except Exception as e:
    logger.warning(f'Exception caught when plotting: {e.msg}')
    iq_results.append({"Plotting check": "❌ Fail"})

# ---- COMPLETENESS CHECKs----
# Output file existense check & content check

required_files = [
    "all_data.csv",
    "daily_counts_with_status.csv",
    "trend_forecast_with_status.csv",
    "trend_forecast_with_indicators.png"
]

logger.info("Starting completeness checks for output files...")

for file in required_files:
    try:
        if os.path.exists(file):
            iq_results.append({f"File existence check for {file}": "✅Pass"})
            size = os.path.getsize(file)
            if file.endswith(".csv"):
                if size > 0:
                    logger.info(f"✅ File check passed: {file} (non-empty CSV, {size} bytes)")
                    iq_results.append({f"File emptiness check for {file}": "✅Pass"})
                else:
                    logger.warning(f"⚠️ File exists but is empty: {file}")
                    iq_results.append({f"File emptiness check for {file}": "❌Fail"})
            else:
                logger.info(f"✅ File check passed: {file} (non-CSV file present)")
        else:
            logger.warning(f"❌ File missing: {file}")
            iq_results.append({f"File existence check for {file}": "❌Fail"})
    except Exception as e:
        logger.exception(f"Exception during file completeness check for {file}: {e}")

logger.info("Completeness checks completed.")

# ---- IQ check report ----
report_file = "iq_check_report.txt"

# Print each element and save to text file
with open(report_file, "w") as f:
    for item in iq_results:
        print(item)
        f.write(str(item) + "\n")

print(f"\n💾 IQ report saved to {report_file}")
logger.info(f"💾 IQ report saved to {report_file}")
