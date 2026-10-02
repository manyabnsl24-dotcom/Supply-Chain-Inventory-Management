import pandas as pd
from pathlib import Path
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans

BASE = Path(__file__).resolve().parent.parent
CLEAN = BASE / "02_Clean_Data"

suppliers = pd.read_csv(CLEAN / "suppliers_clean.csv")

# Normalize order-frequency text
suppliers["Order_Frequency"] = (
    suppliers["Order_Frequency"].astype(str).str.strip().str.lower()
)

frequency_map = {
    "weekly": 52,
    "biweekly": 26,
    "bi-weekly": 26,
    "fortnightly": 26,
    "monthly": 12,
    "daily": 365,
    "quarterly": 4
}

suppliers["Orders_Per_Year"] = (
    suppliers["Order_Frequency"].map(frequency_map)
)

features = suppliers[
    ["Lead_Time (days)", "Orders_Per_Year"]
].copy()

valid = features.notna().all(axis=1)
valid_features = features.loc[valid]

if len(valid_features) < 3:
    raise ValueError(
        "At least 3 supplier records with recognized frequency values are required."
    )

scaled = StandardScaler().fit_transform(valid_features)

model = KMeans(n_clusters=3, random_state=42, n_init=10)
suppliers["Supplier_Cluster"] = pd.Series(
    pd.NA, index=suppliers.index, dtype="Int64"
)
suppliers.loc[valid, "Supplier_Cluster"] = model.fit_predict(scaled)

summary = (
    suppliers.loc[valid]
    .groupby("Supplier_Cluster")
    .agg(
        Supplier_Count=("Supplier_ID", "nunique"),
        Average_Lead_Time=("Lead_Time (days)", "mean"),
        Average_Orders_Per_Year=("Orders_Per_Year", "mean")
    )
    .reset_index()
)

suppliers.to_csv(CLEAN / "supplier_clusters.csv", index=False)
summary.to_csv(CLEAN / "supplier_cluster_summary.csv", index=False)

print("Supplier cluster summary:")
print(summary.to_string(index=False))
print("Saved supplier clusters to:", CLEAN / "supplier_clusters.csv")
