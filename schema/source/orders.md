# Table: orders

## Purpose
Order header fact table containing one record per order.

## Primary Key
- `order_id` (text)

## Foreign Keys
- `customer_id` (text) → customers(customer_id)

## Columns

### Identifiers
- `order_id` (text, PRIMARY KEY) - Unique order identifier
- `customer_id` (text, FOREIGN KEY) - References customers table

### Timestamps
- `order_timestamp` (timestamptz) - When the order was placed (UTC timezone-aware)

### Promotions
- `promo_code` (text, nullable) - Promotional code used, can be null

## Indexes
- PRIMARY KEY on `order_id`
- INDEX on `customer_id` - for customer order history
- INDEX on `order_timestamp` - for time-based queries
- **Recommended composite**: INDEX on `(customer_id, order_timestamp DESC)` for latest orders per customer

## Relationships
- **Many-to-One with customers**: Each order belongs to one customer
  - Join: `orders.customer_id = customers.customer_id`
- **One-to-Many with order_items**: An order can have multiple line items
  - Join: `orders.order_id = order_items.order_id`

## Common Query Patterns
- Orders in a date range
- Customer order history
- Orders with promo codes
- Daily/monthly order counts
- Order frequency analysis

## Performance Notes
- Use composite index `(customer_id, order_timestamp DESC)` for customer timelines
- Consider partitioning by month on `order_timestamp` for large datasets
- Always filter on `order_timestamp` for time-based queries