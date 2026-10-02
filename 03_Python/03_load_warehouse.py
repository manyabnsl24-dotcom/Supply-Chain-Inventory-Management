import sqlite3
import pandas as pd
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
CLEAN = BASE / "02_Clean_Data"
DB = BASE / "04_SQL" / "supply_chain.db"

sales = pd.read_csv(CLEAN / "sales_clean.csv", parse_dates=["Sale_Date"])
inventory = pd.read_csv(
    CLEAN / "inventory_clean.csv", parse_dates=["Last_Updated"]
)
suppliers = pd.read_csv(CLEAN / "suppliers_clean.csv")
orders = pd.read_csv(
    CLEAN / "purchase_orders_clean.csv",
    parse_dates=["Order_Date", "Arrival_Date"]
)

# Build dimensions
products = pd.DataFrame({
    "Product_ID": pd.concat([
        sales["Product_ID"],
        inventory["Product_ID"],
        suppliers["Product_ID"],
        orders["Product_ID"]
    ]).dropna().astype(str).unique()
})
products.insert(0, "ProductKey", range(1, len(products) + 1))

stores = pd.DataFrame({
    "Store_ID": pd.concat([
        sales["Store_ID"], inventory["Store_ID"]
    ]).dropna().astype(str).unique()
})
stores.insert(0, "StoreKey", range(1, len(stores) + 1))

supplier_dim = suppliers[
    ["Supplier_ID", "Supplier_Name", "Product_ID",
     "Lead_Time (days)", "Order_Frequency"]
].drop_duplicates().reset_index(drop=True)
supplier_dim.insert(0, "SupplierKey", range(1, len(supplier_dim) + 1))

date_values = pd.concat([
    sales["Sale_Date"],
    inventory["Last_Updated"],
    orders["Order_Date"],
    orders["Arrival_Date"]
]).dropna().dt.normalize().drop_duplicates().sort_values()

date_dim = pd.DataFrame({"FullDate": date_values.dt.strftime("%Y-%m-%d")})
date_dim.insert(
    0,
    "DateKey",
    pd.to_datetime(date_dim["FullDate"]).dt.strftime("%Y%m%d").astype(int)
)
date_dim["Year"] = pd.to_datetime(date_dim["FullDate"]).dt.year
date_dim["Month"] = pd.to_datetime(date_dim["FullDate"]).dt.month
date_dim["MonthName"] = pd.to_datetime(date_dim["FullDate"]).dt.month_name()
date_dim["Quarter"] = pd.to_datetime(date_dim["FullDate"]).dt.quarter

# Map business IDs to surrogate keys
product_map = products.set_index("Product_ID")["ProductKey"]
store_map = stores.set_index("Store_ID")["StoreKey"]
supplier_map = supplier_dim.set_index("Supplier_ID")["SupplierKey"]
date_map = date_dim.set_index("FullDate")["DateKey"]

sales["ProductKey"] = sales["Product_ID"].astype(str).map(product_map)
sales["StoreKey"] = sales["Store_ID"].astype(str).map(store_map)
sales["DateKey"] = sales["Sale_Date"].dt.strftime("%Y-%m-%d").map(date_map)

fact_sales = sales[
    ["Sale_ID", "ProductKey", "StoreKey", "DateKey",
     "Quantity_Sold", "Revenue"]
].copy()

inventory["ProductKey"] = inventory["Product_ID"].astype(str).map(product_map)
inventory["StoreKey"] = inventory["Store_ID"].astype(str).map(store_map)

fact_inventory = inventory[
    ["ProductKey", "StoreKey", "Warehouse_ID",
     "Stock_Level", "Reorder_Level", "Last_Updated"]
].copy()
fact_inventory.insert(0, "InventoryKey", range(1, len(fact_inventory) + 1))

orders["ProductKey"] = orders["Product_ID"].astype(str).map(product_map)
orders["SupplierKey"] = orders["Supplier_ID"].map(supplier_map)

fact_orders = orders[
    ["Order_ID", "ProductKey", "SupplierKey",
     "Order_Date", "Arrival_Date", "Quantity"]
].copy()

# Aggregate monthly sales
sales["Sales_Month"] = sales["Sale_Date"].dt.to_period("M").astype(str)
monthly = (
    sales.groupby(["Sales_Month", "Product_ID"], as_index=False)
    .agg(
        Units_Sold=("Quantity_Sold", "sum"),
        Revenue=("Revenue", "sum")
    )
)

# Load all warehouse tables
with sqlite3.connect(DB) as conn:
    products.to_sql("DimProduct", conn, if_exists="replace", index=False)
    stores.to_sql("DimStore", conn, if_exists="replace", index=False)
    supplier_dim.to_sql("DimSupplier", conn, if_exists="replace", index=False)
    date_dim.to_sql("DimDate", conn, if_exists="replace", index=False)
    fact_sales.to_sql("FactSales", conn, if_exists="replace", index=False)
    fact_inventory.to_sql("FactInventory", conn, if_exists="replace", index=False)
    fact_orders.to_sql("FactPurchaseOrders", conn, if_exists="replace", index=False)
    monthly.to_sql(
        "AggregateMonthlySales", conn, if_exists="replace", index=False
    )

    # Check row counts
    for table in [
        "DimProduct", "DimStore", "DimSupplier", "DimDate",
        "FactSales", "FactInventory", "FactPurchaseOrders",
        "AggregateMonthlySales"
    ]:
        count = pd.read_sql_query(
            f'SELECT COUNT(*) AS n FROM "{table}"', conn
        ).iloc[0]["n"]
        print(table, ":", count, "rows")

print("Warehouse loading completed.")