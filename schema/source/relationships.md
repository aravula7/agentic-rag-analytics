# Database Relationships and Join Patterns

## Entity Relationship Overview

### Customer-Centric Relationships
```
customers (1) ──→ (M) orders
customers (1) ──→ (M) subscriptions
customers (1) ──→ (M) churn_predictions
```

### Product-Centric Relationships
```
products (1) ──→ (M) order_items
products (1) ──→ (M) forecast_predictions
```

### Order Relationships
```
orders (1) ──→ (M) order_items
```

### Complete Join Path
```
customers ──→ orders ──→ order_items ──→ products
    │           │
    │           └─→ (includes order_timestamp)
    │
    ├──→ subscriptions
    └──→ churn_predictions
```

## Foreign Key Constraints

### Customer Foreign Keys
- `orders.customer_id` → `customers.customer_id`
- `subscriptions.customer_id` → `customers.customer_id`
- `churn_predictions.customer_id` → `customers.customer_id`

### Product Foreign Keys
- `order_items.product_id` → `products.product_id`
- `forecast_predictions.product_id` → `products.product_id`

### Order Foreign Keys
- `order_items.order_id` → `orders.order_id`

## Common Join Patterns

### Customer with Orders and Items
- Path: customers → orders → order_items → products
- Use for: Customer purchase history, revenue analysis

### Customer Purchase Metrics
- Join: customers LEFT JOIN orders LEFT JOIN order_items
- Aggregations: COUNT(orders), SUM(revenue), AVG(order_value)

### Product Sales Analysis
- Path: products → order_items → orders
- Use for: Product performance, category analysis

### Products with Forecast and Actual Sales
- Join: products → forecast_predictions
- Optional join with order_items for accuracy comparison

### Churn Risk with Subscription Details
- Path: customers → churn_predictions
- Additional join with subscriptions for context

## Recommended Composite Indexes for Joins

### Customer-based queries
- `orders(customer_id, order_timestamp DESC)` - for customer order history
- `subscriptions(customer_id, event_timestamp DESC)` - for subscription timeline

### Product-based queries
- `order_items(product_id, order_id)` - for product sales analysis
- `forecast_predictions(product_id, region, forecast_date)` - for forecasts

### Time-based queries
- `orders(order_timestamp)` - for date range filters
- `forecast_predictions(forecast_date, region)` - for forecast lookups

## Join Guidelines

### Use INNER JOIN when:
- Relationship is required (e.g., order_items must have an order)
- Filtering out NULL relationships is desired

### Use LEFT JOIN when:
- Relationship may not exist (e.g., customers without orders)
- Want to include all records from left table

### Performance Tips
- Filter on indexed columns first (timestamps, IDs)
- Use composite indexes for multi-column joins
- Consider join order: filter smallest table first
- Use EXPLAIN ANALYZE to verify index usage

## Data Integrity Notes
- All foreign key relationships should be enforced with constraints
- Orphaned records should not exist (e.g., order without customer)
- Use appropriate join types based on data completeness requirements