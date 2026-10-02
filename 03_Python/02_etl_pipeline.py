import pandas as pd
import numpy as np
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
RAW = BASE_DIR / "01_Raw_Data"
CLEAN = BASE_DIR / "02_Clean_Data"
SQL_DIR = BASE_DIR / "04_SQL"

CLEAN.mkdir(exist_ok=True)
SQL_DIR.mkdir(exist_ok=True)

# 1. Extract data
sales = pd.read_excel(RAW / "sales_data_2.xlsx")
inventory = pd.read_excel(RAW / "inventory_data.xlsx")
suppliers = pd.read_excel(RAW / "suppliers_data.xlsx")
orders = pd.read_excel(RAW / "purchase_orders_data.xlsx")

# 2. Validate expected columns
required = {
    "sales": [
        "Sale_ID", "Product_ID", "Store_ID",
        "Sale_Date", "Quantity_Sold", "Revenue"
    ],
    "inventory": [
        "Product_ID", "Store_ID", "Warehouse_ID",
        "Stock_Level", "Reorder_Level", "Last_Updated"
    ],
    "suppliers": [
        "Supplier_ID", "Supplier_Name", "Product_ID",
        "Lead_Time (days)", "Order_Frequency"
    ],
    "orders": [
        "Order_ID", "Product_ID", "Supplier_ID",
        "Order_Date", "Quantity", "Arrival_Date"
    ]
}

for name, df in [
    ("sales", sales),
    ("inventory", inventory),
    ("suppliers", suppliers),
    ("orders", orders)
]:
    missing = set(required[name]) - set(df.columns)
    if missing:
        raise ValueError(f"{name} is missing columns: {sorted(missing)}")

# 3. Remove duplicate records
sales = sales.drop_duplicates(subset=["Sale_ID"])
inventory = inventory.drop_duplicates()
suppliers = suppliers.drop_duplicates()
orders = orders.drop_duplicates(subset=["Order_ID"])

# 4. Convert dates
sales["Sale_Date"] = pd.to_datetime(sales["Sale_Date"], errors="coerce")
inventory["Last_Updated"] = pd.to_datetime(inventory["Last_Updated"], errors="coerce")
orders["Order_Date"] = pd.to_datetime(orders["Order_Date"], errors="coerce")
orders["Arrival_Date"] = pd.to_datetime(orders["Arrival_Date"], errors="coerce")

# 5. Convert numeric columns
for col in ["Quantity_Sold", "Revenue"]:
    sales[col] = pd.to_numeric(sales[col], errors="coerce")

for col in ["Stock_Level", "Reorder_Level"]:
    inventory[col] = pd.to_numeric(inventory[col], errors="coerce")

suppliers["Lead_Time (days)"] = pd.to_numeric(suppliers["Lead_Time (days)"], errors="coerce")
orders["Quantity"] = pd.to_numeric(orders["Quantity"], errors="coerce")

# 6. Remove rows missing essential values
sales = sales.dropna(subset=[
    "Sale_ID", "Product_ID", "Store_ID",
    "Sale_Date", "Quantity_Sold", "Revenue"
]).copy()

inventory = inventory.dropna(subset=[
    "Product_ID", "Store_ID", "Stock_Level", "Reorder_Level"
]).copy()

suppliers = suppliers.dropna(subset=[
    "Supplier_ID", "Product_ID",
    "Lead_Time (days)", "Order_Frequency"
]).copy()

orders = orders.dropna(subset=[
    "Order_ID", "Product_ID", "Supplier_ID",
    "Order_Date", "Quantity", "Arrival_Date"
]).copy()

# 7. Remove invalid negative values
sales = sales[(sales["Quantity_Sold"] >= 0) & (sales["Revenue"] >= 0)].copy()
inventory = inventory[(inventory["Stock_Level"] >= 0) & (inventory["Reorder_Level"] >= 0)].copy()
suppliers = suppliers[suppliers["Lead_Time (days)"] >= 0].copy()
orders = orders[orders["Quantity"] >= 0].copy()

# 8. Flag dates later than today for review
today = pd.Timestamp.today().normalize()
sales["Date_Review_Flag"] = (sales["Sale_Date"] > today).astype(int)
orders["Order_Date_Review_Flag"] = (orders["Order_Date"] > today).astype(int)
orders["Arrival_Date_Review_Flag"] = (orders["Arrival_Date"] > today).astype(int)

# 9. Calculate average daily demand by product
daily_sales = (
    sales.groupby(["Product_ID", "Sale_Date"], as_index=False)
    ["Quantity_Sold"].sum()
)

demand = (
    daily_sales.groupby("Product_ID")
    .agg(
        Total_Units_Sold=("Quantity_Sold", "sum"),
        First_Sale_Date=("Sale_Date", "min"),
        Last_Sale_Date=("Sale_Date", "max")
    )
    .reset_index()
)

demand["Observed_Days"] = (
    demand["Last_Sale_Date"] - demand["First_Sale_Date"]
).dt.days + 1

demand["Average_Daily_Demand"] = (
    demand["Total_Units_Sold"] / demand["Observed_Days"].clip(lower=1)
)

demand_std = (
    daily_sales.groupby("Product_ID")["Quantity_Sold"]
    .std()
    .rename("Daily_Demand_Std")
    .reset_index()
)

demand = demand.merge(demand_std, on="Product_ID", how="left")
demand["Daily_Demand_Std"] = demand["Daily_Demand_Std"].fillna(0)

# 10. Calculate average supplier lead time by product
lead = (
    suppliers.groupby("Product_ID", as_index=False)
    .agg(Average_Lead_Time=("Lead_Time (days)", "mean"))
)

reorder = demand.merge(lead, on="Product_ID", how="left")
reorder["Average_Lead_Time"] = reorder["Average_Lead_Time"].fillna(0)

# Safety stock uses a 95% service-level approximation
reorder["Safety_Stock"] = (
    1.65 * reorder["Daily_Demand_Std"] * np.sqrt(reorder["Average_Lead_Time"])
)

reorder["Calculated_Reorder_Point"] = np.ceil(
    reorder["Average_Daily_Demand"] * reorder["Average_Lead_Time"] + reorder["Safety_Stock"]
).fillna(0).astype(int)

# 11. Create restock report
restock = inventory.merge(
    reorder[["Product_ID", "Calculated_Reorder_Point"]],
    on="Product_ID",
    how="left"
)

restock["Calculated_Reorder_Point"] = (
    restock["Calculated_Reorder_Point"].fillna(0).astype(int)
)

restock["Stock_Status"] = np.where(
    restock["Stock_Level"] < restock["Reorder_Level"],
    "Below Existing Reorder Level",
    "At or Above Existing Reorder Level"
)

restock["Calculated_Restock_Quantity"] = (
    restock["Calculated_Reorder_Point"] - restock["Stock_Level"]
).clip(lower=0).astype(int)

# 12. Save clean CSV files
datasets = {
    "sales_clean.csv": sales,
    "inventory_clean.csv": inventory,
    "suppliers_clean.csv": suppliers,
    "purchase_orders_clean.csv": orders,
    "reorder_analysis.csv": reorder,
    "restock_report.csv": restock
}

for filename, df in datasets.items():
    df.to_csv(CLEAN / filename, index=False)

# 13. Load tables into SQLite safely

db_path = SQL_DIR / "supply_chain.db"

tables = [
    ("sales", sales),
    ("inventory", inventory),
    ("suppliers", suppliers),
    ("purchase_orders", orders),
    ("reorder_analysis", reorder),
    ("restock_report", restock)
]

SQLITE_INT_MIN = -(2**63)
SQLITE_INT_MAX = 2**63 - 1

def is_out_of_range_integer(value):
    if isinstance(value, (int, np.integer)) and not isinstance(
        value, (bool, np.bool_)
    ):
        number = int(value)
        return (
            number < SQLITE_INT_MIN or
            number > SQLITE_INT_MAX
        )
    return False

with sqlite3.connect(db_path) as conn:
    for table, df in tables:
        sqlite_df = df.copy()

        for col in sqlite_df.columns:
            values = sqlite_df[col]

            # Check both numeric and object columns
            has_large_integer = values.map(
                is_out_of_range_integer
            ).any()

            if has_large_integer:
                print(
                    f"Large integer found in {table}.{col}; "
                    "saving that column as text."
                )

                sqlite_df[col] = values.astype(object).map(
                    lambda x: (
                        str(int(x))
                        if is_out_of_range_integer(x)
                        else x
                    )
                )

        print(f"Saving {table}: {len(sqlite_df)} rows")

        sqlite_df.to_sql(
            table,
            conn,
            if_exists="replace",
            index=False
        )

        print(f"Successfully saved {table}")

print("\nETL completed successfully.")
print("Database:", db_path)

for filename, df in [
    ("sales_clean.csv", sales),
    ("inventory_clean.csv", inventory),
    ("suppliers_clean.csv", suppliers),
    ("purchase_orders_clean.csv", orders),
    ("reorder_analysis.csv", reorder),
    ("restock_report.csv", restock)
]:
    print(f"{filename}: {len(df)} rows")