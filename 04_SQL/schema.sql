CREATE TABLE IF NOT EXISTS DimProduct (
    ProductKey INTEGER PRIMARY KEY,
    Product_ID TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS DimStore (
    StoreKey INTEGER PRIMARY KEY,
    Store_ID TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS DimSupplier (
    SupplierKey INTEGER PRIMARY KEY,
    Supplier_ID TEXT NOT NULL,
    Supplier_Name TEXT,
    Product_ID TEXT,
    Lead_Time_Days REAL,
    Order_Frequency TEXT
);

CREATE TABLE IF NOT EXISTS DimDate (
    DateKey INTEGER PRIMARY KEY,
    FullDate TEXT UNIQUE NOT NULL,
    Year INTEGER,
    Month INTEGER,
    MonthName TEXT,
    Quarter INTEGER
);

CREATE TABLE IF NOT EXISTS FactSales (
    Sale_ID TEXT PRIMARY KEY,
    ProductKey INTEGER,
    StoreKey INTEGER,
    DateKey INTEGER,
    Quantity_Sold REAL,
    Revenue REAL,
    FOREIGN KEY (ProductKey) REFERENCES DimProduct(ProductKey),
    FOREIGN KEY (StoreKey) REFERENCES DimStore(StoreKey),
    FOREIGN KEY (DateKey) REFERENCES DimDate(DateKey)
);

CREATE TABLE IF NOT EXISTS FactInventory (
    InventoryKey INTEGER PRIMARY KEY,
    ProductKey INTEGER,
    StoreKey INTEGER,
    Warehouse_ID TEXT,
    Stock_Level REAL,
    Reorder_Level REAL,
    Last_Updated TEXT,
    FOREIGN KEY (ProductKey) REFERENCES DimProduct(ProductKey),
    FOREIGN KEY (StoreKey) REFERENCES DimStore(StoreKey)
);

CREATE TABLE IF NOT EXISTS FactPurchaseOrders (
    Order_ID TEXT PRIMARY KEY,
    ProductKey INTEGER,
    SupplierKey INTEGER,
    Order_Date TEXT,
    Arrival_Date TEXT,
    Quantity REAL,
    FOREIGN KEY (ProductKey) REFERENCES DimProduct(ProductKey),
    FOREIGN KEY (SupplierKey) REFERENCES DimSupplier(SupplierKey)
);

CREATE TABLE IF NOT EXISTS AggregateMonthlySales (
    Sales_Month TEXT,
    Product_ID TEXT,
    Units_Sold REAL,
    Revenue REAL,
    PRIMARY KEY (Sales_Month, Product_ID)
);