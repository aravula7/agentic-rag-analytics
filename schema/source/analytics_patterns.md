# Common Analytics Patterns and Query Concepts

## Revenue Analytics Patterns

### Daily/Monthly Revenue Trends
- Aggregate by date: Use DATE() or DATE_TRUNC() functions
- Join path: orders → order_items
- Metrics: COUNT(orders), SUM(quantity * unit_price), AVG(order_value)

### Revenue by Region and Category
- Join path: customers → orders → order_items → products
- Group by: region, category
- Metrics: Total revenue, average order value, unit counts

## Customer Analytics Patterns

### Customer Lifetime Value (CLV)
- Join path: customers → orders → order_items
- Aggregations: Total orders, total revenue, date range
- Metrics: COUNT(DISTINCT order_id), SUM(revenue), MIN/MAX(order_timestamp)

### Customer Cohort Analysis
- Group by: DATE_TRUNC('month', first_order_date)
- Metrics: Cohort size, cohort revenue, retention rate

### Active vs Inactive Customers
- Classification based on: MAX(order_timestamp) compared to CURRENT_DATE
- Categories: Active (< 90 days), At Risk (90-180 days), Inactive (> 180 days)

## Product Analytics Patterns

### Best Selling Products
- Join path: products → order_items → orders
- Aggregations: SUM(quantity), SUM(revenue)
- Filters: Date range on order_timestamp
- Sort by: Revenue or units sold descending

### Product Performance by Region
- Join path: products → order_items → orders → customers
- Group by: category, region
- Metrics: Units sold, revenue

## Churn Analytics Patterns

### Churn Rate by Plan
- Join path: subscriptions → churn_predictions
- Filters: Latest snapshot_month, active status
- Calculation: (churned_count / total_customers) * 100

### High-Risk Customer Profile
- Join path: churn_predictions → customers
- Filters: churn_flag = TRUE, latest snapshot_month
- Group by: region, state, plan_name
- Metrics: AVG(churn_probability), COUNT(customers)

## Forecast Analytics Patterns

### Forecast Accuracy
- Join path: forecast_predictions → products
- Optional join: order_items for actual sales
- Comparison: predicted_units vs actual units sold
- Metric: ABS(forecast - actual) as forecast_error

### Demand Forecast by Category
- Join path: forecast_predictions → products
- Group by: category, region
- Aggregation: SUM(predicted_units)
- Filters: forecast_date range, specific model_name

## Time-Series Aggregations

### Monthly Sales Trend
- Use: DATE_TRUNC('month', order_timestamp)
- Metrics: COUNT(orders), SUM(revenue)
- Sort: By month descending

### Rolling Averages
- Use: Window functions with ROWS BETWEEN n PRECEDING AND CURRENT ROW
- Common windows: 7-day, 30-day rolling averages
- Apply to: Daily revenue, order counts

## Filtering Best Practices

### Date Range Filters
- Use >= and < for timestamp ranges (not BETWEEN for inclusive ranges)
- Extract dates: DATE(timestamp_column) for daily aggregations
- Month aggregations: DATE_TRUNC('month', timestamp_column)

### Region Filters
- Valid regions: 'West', 'Midwest', 'South', 'East'
- Case-sensitive matching required

### Status Filters
- Subscription status: 'active', 'past_due', 'canceled', 'paused'
- Use WHERE status IN (...) for multiple values

### Performance Tips
- Filter on indexed columns first (timestamps, customer_id, product_id)
- Use composite indexes for multi-column filters
- Limit result sets with LIMIT for exploratory queries
- Use aggregate functions appropriately (COUNT, SUM, AVG)
- Consider materialized views for complex repeated queries

## Common Aggregation Functions

### COUNT Functions
- COUNT(*) - Total rows
- COUNT(DISTINCT column) - Unique values
- COUNT(column) - Non-null values

### Numeric Aggregations
- SUM(column) - Total sum
- AVG(column) - Average value
- MIN/MAX(column) - Minimum/maximum values

### Window Functions
- ROW_NUMBER() - Sequential numbering
- RANK() - Ranking with gaps
- LAG/LEAD - Previous/next row values
- SUM/AVG OVER - Running totals and averages

## Join Performance Considerations

### Index Usage
- Ensure foreign key columns have indexes
- Use composite indexes for frequently joined columns
- Check EXPLAIN ANALYZE for index scans vs sequential scans

### Query Optimization
- Filter before joining when possible
- Use appropriate join types (INNER vs LEFT)
- Avoid SELECT * - specify only needed columns
- Use CTEs or subqueries for complex multi-step logic