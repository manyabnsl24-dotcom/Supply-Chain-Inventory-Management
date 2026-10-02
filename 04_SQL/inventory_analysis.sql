-- 1. Sales by product in the latest three-month data window
WITH latest AS (
    SELECT MAX(date(Sale_Date)) AS max_date
    FROM sales
)
SELECT
    s.Product_ID,
    SUM(s.Quantity_Sold) AS Units_Sold,
    SUM(s.Revenue) AS Total_Revenue
FROM sales AS s
CROSS JOIN latest AS l
WHERE date(s.Sale_Date) >= date(l.max_date, '-3 months')
  AND date(s.Sale_Date) <= l.max_date
GROUP BY s.Product_ID
ORDER BY Units_Sold DESC;


-- 2. Fast-moving products
SELECT
    Product_ID,
    SUM(Quantity_Sold) AS Units_Sold
FROM sales
GROUP BY Product_ID
ORDER BY Units_Sold DESC;


-- 3. Slow-moving products
SELECT
    Product_ID,
    SUM(Quantity_Sold) AS Units_Sold
FROM sales
GROUP BY Product_ID
ORDER BY Units_Sold ASC;


-- 4. Products below the existing reorder level
SELECT
    Product_ID,
    Store_ID,
    Warehouse_ID,
    Stock_Level,
    Reorder_Level,
    Reorder_Level - Stock_Level AS Stock_Shortfall
FROM inventory
WHERE Stock_Level < Reorder_Level
ORDER BY Stock_Shortfall DESC;


-- 5. Supplier lead-time analysis
SELECT
    Supplier_ID,
    Supplier_Name,
    Product_ID,
    "Lead_Time (days)" AS Lead_Time_Days,
    Order_Frequency
FROM suppliers
ORDER BY "Lead_Time (days)" DESC;


-- 6. Actual purchase-order delivery time
SELECT
    Order_ID,
    Supplier_ID,
    Product_ID,
    Order_Date,
    Arrival_Date,
    CAST(
        julianday(Arrival_Date) - julianday(Order_Date)
        AS INTEGER
    ) AS Actual_Lead_Time_Days,
    Quantity
FROM purchase_orders
ORDER BY Actual_Lead_Time_Days DESC;


-- 7. Monthly sales aggregation
SELECT
    strftime('%Y-%m', Sale_Date) AS Sales_Month,
    Product_ID,
    SUM(Quantity_Sold) AS Units_Sold,
    SUM(Revenue) AS Revenue
FROM sales
GROUP BY Sales_Month, Product_ID
ORDER BY Sales_Month, Product_ID;


-- 8. Inventory summary
SELECT
    Product_ID,
    SUM(Stock_Level) AS Total_Stock,
    SUM(Reorder_Level) AS Total_Reorder_Level
FROM inventory
GROUP BY Product_ID
ORDER BY Total_Stock DESC;


-- 9. Purchase quantity by supplier
SELECT
    Supplier_ID,
    COUNT(*) AS Number_Of_Orders,
    SUM(Quantity) AS Total_Units_Ordered
FROM purchase_orders
GROUP BY Supplier_ID
ORDER BY Total_Units_Ordered DESC;


-- 10. Restock report using the calculated reorder point
SELECT *
FROM restock_report
WHERE Stock_Level < Calculated_Reorder_Point
ORDER BY Calculated_Restock_Quantity DESC;


-- 11. Product revenue summary
SELECT
    Product_ID,
    COUNT(*) AS Sales_Records,
    SUM(Quantity_Sold) AS Units_Sold,
    SUM(Revenue) AS Total_Revenue
FROM sales
GROUP BY Product_ID
ORDER BY Total_Revenue DESC;