# Table: order_items

## Purpose
Order line items fact table containing one record per SKU within an order.

## Primary Key
- `order_item_id` (text)

## Foreign Keys
- `order_id` (text) → orders(order_id)
- `product_id` (text) → products(product_id)

## Columns

### Identifiers
- `order_item_id` (text, PRIMARY KEY) - Unique line item identifier
- `order_id` (text, FOREIGN KEY) - References orders table
- `product_id` (text, FOREIGN KEY) - References products table

### Metrics
- `quantity` (int) - Number of units ordered
- `unit_price_usd` (numeric(10,2)) - Price per unit in USD

## Indexes
- PRIMARY KEY on `order_item_id`
- INDEX on `order_id` - for order → items lookups
- INDEX on `product_id` - for product-level rollups
- **Recommended composite**: INDEX on `(product_id, order_id)` for product sales by order

## Relationships
- **Many-to-One with orders**: Each line item belongs to one order
  - Join: `order_items.order_id = orders.order_id`
- **Many-to-One with products**: Each line item references one product
  - Join: `order_items.product_id = products.product_id`

## Common Query Patterns
- Items in an order
- Revenue by product
- Average order value (requires join with orders)
- Sales by category and date
- Product quantity sold analysis
- Price point analysis

## Calculations
- **Line Total**: `quantity * unit_price_usd`
- **Order Total**: Sum of all line totals for an order
- **Revenue**: Sum of all line totals

## Performance Notes
- Use composite index `(product_id, order_id)` for product analysis
- Always join with orders table for timestamp-based filtering
- For revenue calculations, multiply quantity by unit_price_usd