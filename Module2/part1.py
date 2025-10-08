# -*- coding: utf-8 -*-
import requests, json
import pandas as pd
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import numpy as np
import ast
# import regex as re
import re
PROD_URL =  "elastic server link"
PROD_AUTH = "Bearer "+"your token" # Fill in your appliaction token
url =  PROD_URL+ "/nosa-service-metadata/metadata/query"
headers = {'Content-type': 'application/json', 'Accept': 'application/json', 'Authorization': PROD_AUTH}
# ---- Choose your time range ----
start_date = datetime(2025, 10, 1, 10, 0, 0)   # start UTC time
days_to_collect = 5                             # number of days to collect

# ---- Data collector ----
all_data = []
daily_counts = []

for i in range(days_to_collect):
    gte = (start_date + timedelta(days=i)).isoformat() + "Z"
    lte = (start_date + timedelta(days=i+1)).isoformat() + "Z"

    data = {
        "query": {
            "bool": {
                "must": [
                    {
                        "query_string": {
                            "query": "ESID0002",
                            "time_zone": "Europe/Stockholm"
                        }
                    },
                    {
                        "range": {
                            "Created_Time": {
                                "format": "strict_date_optional_time",
                                "gte": gte,
                                "lte": lte
                            }
                        }
                    }
                ]
            }
        },
        "size": 9999
    }

    # ---- API request ----
    r = requests.post(url, data=json.dumps(data), headers=headers, verify=False)
    content = json.loads(r.text)

    # ---- Convert to DataFrame ----
    if 'results' in content:
        df_day = pd.json_normalize(content['results'])
        all_data.append(df_day)
        daily_counts.append({
            "date": gte[:10],
            "count": len(df_day)
        })
        print(f"✅ {gte[:10]} → {len(df_day)} rows")
    else:
        print(f"⚠️ No data for {gte[:10]}")

# ---- Combine all results ----
if all_data:
    df_all = pd.concat(all_data, ignore_index=True)
    print(f"\nTotal collected rows: {len(df_all)}")

# ---- Convert daily counts to DataFrame ----
df_counts = pd.DataFrame(daily_counts)

# ---- Save daily counts and raw data ----
df_counts.to_csv("daily_counts.csv", index=False)
#df_all.to_csv("all_data.csv", index=False)
#print("💾 Saved 'daily_counts.csv' and 'all_data.csv'")

# ---- Plot actual daily counts ----
plt.figure(figsize=(8, 4))
plt.plot(df_counts["date"], df_counts["count"], marker='o', label="Actual")
plt.title("Daily Data Volume")
plt.xlabel("Date")
plt.ylabel("Number of Rows")
plt.grid(True)
plt.legend()
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig("daily_data_volume.png", dpi=300)
plt.close()
print("📊 Saved 'daily_data_volume.png'")

# ---- INTERPOLATION + TREND-BASED EXTRAPOLATION ----
df_counts["date"] = pd.to_datetime(df_counts["date"])
df_counts.set_index("date", inplace=True)

# Daily frequency with missing days as NaN
df_daily = df_counts.resample('D').asfreq()

# Linear interpolation for historical missing days
df_daily["count"] = df_daily["count"].interpolate(method='linear')

# Fit trend line using historical data
y = df_daily["count"].dropna().values
x = np.arange(len(y))
coef = np.polyfit(x, y, 2)  # degree 1 = linear trend
trend = np.poly1d(coef)

# Extend to future days
future_days=3
total_days = len(df_daily) + future_days
x_full = np.arange(total_days)
full_counts = trend(x_full)

# Create full DataFrame with dates
full_index = pd.date_range(df_daily.index[0], periods=total_days)
full_df = pd.DataFrame({"count": full_counts}, index=full_index)

# ---- SAVE INTERPOLATED + TREND FORECAST ----
full_df.to_csv("trend_forecast.csv")
print("💾 Saved 'trend_forecast.csv'")

# ---- PLOT TREND FORECAST ----
plt.figure(figsize=(8, 4))
plt.plot(df_daily.index, df_daily["count"], "o-", label="Actual")
plt.plot(full_df.index, full_df["count"], "--", label="Trend Forecast")
plt.title("Trend-Based Prediction of Daily Data Volume")
plt.xlabel("Date")
plt.ylabel("Row Count")
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.savefig("trend_forecast.png", dpi=300)
plt.close()
print("📈 Saved 'trend_forecast.png'")

