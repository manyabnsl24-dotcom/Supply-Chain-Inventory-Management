import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "01_Raw_Data"

files = {
    "Sales": "sales_data_2.xlsx",
    "Inventory": "inventory_data.xlsx",
    "Suppliers": "suppliers_data.xlsx",
    "Purchase Orders": "purchase_orders_data.xlsx"
}

for name, filename in files.items():
    path = DATA_DIR / filename
    df = pd.read_excel(path)

    print("\n", "=" * 50)
    print(name.upper())
    print("=" * 50)
    print("Rows and columns:", df.shape)
    print("Column names:", df.columns.tolist())
    print("\nData types:")
    print(df.dtypes)
    print("\nMissing values:")
    print(df.isnull().sum())
    print("\nDuplicate rows:", df.duplicated().sum())
    print("\nFirst five rows:")
    print(df.head())

    for col in df.columns:
        if "date" in col.lower() or col == "Last_Updated":
            dates = pd.to_datetime(df[col], errors="coerce")
            print(
                col,
                "range:",
                dates.min(),
                "to",
                dates.max()
            )