import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from sklearn.linear_model import LinearRegression

BASE = Path(__file__).resolve().parent.parent
CLEAN = BASE / "02_Clean_Data"
SCREENSHOTS = BASE / "06_Screenshots"

CLEAN.mkdir(exist_ok=True)
SCREENSHOTS.mkdir(exist_ok=True)

# Load cleaned sales data
sales = pd.read_csv(
    CLEAN / "sales_clean.csv",
    parse_dates=["Sale_Date"]
)

# Clean required columns
sales["Sale_Date"] = pd.to_datetime(
    sales["Sale_Date"], errors="coerce"
)
sales["Quantity_Sold"] = pd.to_numeric(
    sales["Quantity_Sold"], errors="coerce"
)

sales = sales.dropna(
    subset=["Product_ID", "Sale_Date", "Quantity_Sold"]
)

# Aggregate daily sales into monthly product demand
sales["Sales_Month"] = (
    sales["Sale_Date"].dt.to_period("M").dt.to_timestamp()
)

monthly = (
    sales.groupby(
        ["Product_ID", "Sales_Month"], as_index=False
    )["Quantity_Sold"]
    .sum()
    .rename(columns={"Quantity_Sold": "Monthly_Demand"})
)

results = []

for product, group in monthly.groupby("Product_ID"):
    group = group.sort_values("Sales_Month").copy()

    # Keep only the date index and demand column
    group = group[["Sales_Month", "Monthly_Demand"]]
    group = group.set_index("Sales_Month")

    # Ensure monthly dates are continuous
    full_months = pd.date_range(
        start=group.index.min(),
        end=group.index.max(),
        freq="MS"
    )

    group = group.reindex(full_months)
    group.index.name = "Sales_Month"

    # Fill missing demand values only
    group["Monthly_Demand"] = (
        group["Monthly_Demand"].fillna(0)
    )

    if len(group) < 3:
        print(
            f"Skipping {product}: "
            "fewer than 3 monthly observations."
        )
        continue

    group["Month_Index"] = np.arange(len(group))

    X = group[["Month_Index"]]
    y = group["Monthly_Demand"]

    # Train linear regression model
    model = LinearRegression()
    model.fit(X, y)

    # Predict demand for the next month
    next_index = len(group)

    predicted_value = model.predict(
        pd.DataFrame({"Month_Index": [next_index]})
    )[0]

    predicted = max(0, int(round(predicted_value)))

    next_month = (
        group.index.max() + pd.offsets.MonthBegin(1)
    )

    results.append({
        "Product_ID": product,
        "Last_Observed_Month": group.index.max(),
        "Forecast_Month": next_month,
        "Last_Month_Demand": int(y.iloc[-1]),
        "Forecast_Demand": predicted,
        "Months_Of_History": len(group)
    })

    # Create forecast chart
    plt.figure(figsize=(9, 4))

    plt.plot(
        group.index,
        y,
        marker="o",
        label="Historical demand"
    )

    plt.scatter(
        [next_month],
        [predicted],
        marker="x",
        s=100,
        label="Forecast"
    )

    plt.title(f"Demand Forecast - {product}")
    plt.xlabel("Month")
    plt.ylabel("Units sold")
    plt.legend()
    plt.xticks(rotation=45)
    plt.tight_layout()

    safe_product = "".join(
        c if c.isalnum() or c in "-_" else "_"
        for c in str(product)
    )

    plt.savefig(
        SCREENSHOTS / f"forecast_{safe_product}.png"
    )
    plt.close()

# Save forecast results
forecast_df = pd.DataFrame(results)

forecast_path = CLEAN / "demand_forecast.csv"
forecast_df.to_csv(forecast_path, index=False)

if forecast_df.empty:
    print("No forecasts generated. Check the sales data and dates.")
else:
    print("\nDemand Forecast Results:")
    print(forecast_df.to_string(index=False))

print("\nForecast saved to:", forecast_path)
print("Forecast charts saved to:", SCREENSHOTS)
