import pandas as pd
import sqlite3
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
CLEAN = BASE / "02_Clean_Data"
DB = BASE / "04_SQL" / "supply_chain.db"

sales = pd.read_csv(CLEAN / "sales_clean.csv", parse_dates=["Sale_Date"])
sales["Sales_Month"] = sales["Sale_Date"].dt.to_period("M").astype(str)

monthly = (
    sales.groupby(["Sales_Month", "Product_ID"], as_index=False)
    .agg(
        Units_Sold=("Quantity_Sold", "sum"),
        Revenue=("Revenue", "sum"),
        Sales_Records=("Sale_ID", "count")
    )
)

monthly.to_csv(CLEAN / "aggregate_monthly_sales.csv", index=False)

with sqlite3.connect(DB) as conn:
    monthly.to_sql(
        "aggregate_monthly_sales",
        conn,
        if_exists="replace",
        index=False
    )

print("Monthly aggregation completed.")
print(monthly.head(10).to_string(index=False))
