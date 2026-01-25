# Table: customers

## Purpose
Customer dimension table containing unique customer profiles with geographic information.

## Primary Key
- `customer_id` (text) - Unique identifier for each customer

## Unique Constraints
- `email` (text) - Must be unique across all customers

## Columns

### Identifiers
- `customer_id` (text, PRIMARY KEY) - Unique customer identifier
- `email` (text, UNIQUE) - Customer email address, must be unique

### Personal Information
- `full_name` (text) - Customer's full name
- `address` (text) - Street address
- `city` (text) - City name
- `state` (char(2)) - Two-letter state code (e.g., CA, NY, TX)
- `zip_code` (text) - Postal ZIP code
- `region` (text) - Geographic region, one of: West, Midwest, South, East

## Indexes
- PRIMARY KEY on `customer_id`
- UNIQUE INDEX on `email`
- INDEX on `region` - for regional analysis
- INDEX on `state` - for state-level queries

## Relationships
- **One-to-Many with orders**: A customer can have multiple orders
  - Join: `customers.customer_id = orders.customer_id`
- **One-to-Many with subscriptions**: A customer can have multiple subscription events
  - Join: `customers.customer_id = subscriptions.customer_id`
- **One-to-Many with churn_predictions**: A customer can have churn predictions for multiple months
  - Join: `customers.customer_id = churn_predictions.customer_id`

## Common Query Patterns
- Find customer by email
- Count customers by region
- Customer details with order counts
- Customer purchase history and lifetime value

## Data Quality Notes
- Email must be unique and not null
- State should be 2-character code
- Region should be one of: West, Midwest, South, East