# Table: products

## Purpose
Product/SKU dimension table with pricing and categorization information.

## Primary Key
- `product_id` (text) - Surrogate key generated during ETL

## Unique Constraints
- `sku` (text) - Business key, unique stock keeping unit identifier

## Columns

### Identifiers
- `product_id` (text, PRIMARY KEY) - Surrogate key for internal use
- `sku` (text, UNIQUE) - Stock keeping unit, business identifier

### Product Information
- `product_name` (text) - Display name of the product
- `category` (text) - Product category for grouping
- `base_price_usd` (numeric(10,2)) - Base price in USD

## Indexes
- PRIMARY KEY on `product_id`
- UNIQUE INDEX on `sku`
- INDEX on `category` - for category-level analysis

## Relationships
- **One-to-Many with order_items**: A product can appear in multiple order line items
  - Join: `products.product_id = order_items.product_id`
- **One-to-Many with forecast_predictions**: A product can have forecasts for multiple dates/regions
  - Join: `products.product_id = forecast_predictions.product_id`

## Common Query Patterns
- Products by category
- Find product by SKU
- Top selling products (requires join with order_items)
- Product performance metrics
- Average price by category

## Data Quality Notes
- SKU must be unique
- Base price should be positive
- Category should be normalized (consistent casing)