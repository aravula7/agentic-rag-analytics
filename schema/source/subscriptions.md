# Table: subscriptions

## Purpose
Clean subscription events/snapshots used for churn features and subscription analytics.

## Primary Key
- `subscription_id` (text)

## Foreign Keys
- `customer_id` (text) → customers(customer_id)

## Columns

### Identifiers
- `subscription_id` (text, PRIMARY KEY) - Unique subscription identifier
- `customer_id` (text, FOREIGN KEY) - References customers table

### Timestamps
- `event_timestamp` (timestamptz) - When the subscription event occurred (UTC)
- `last_billed_timestamp` (timestamptz) - Last successful billing timestamp

### Plan Information
- `plan_name` (text) - Subscription plan name
- `billing_cycle` (text) - Billing frequency (e.g., monthly, annual)
- `plan_price_usd` (numeric(10,2)) - Subscription price in USD
- `status` (text) - Current status (e.g., active, past_due, canceled)

### Location
- `state` (char(2)) - Two-letter state code

### Behavioral Metrics
- `failed_payments_30d` (int) - Number of failed payment attempts in last 30 days
- `autopay_enabled` (boolean) - Whether autopay is enabled
- `support_tickets_30d` (int) - Number of support tickets in last 30 days

## Indexes
- PRIMARY KEY on `subscription_id`
- INDEX on `customer_id` - for customer subscription history
- INDEX on `event_timestamp` - for time-based queries
- **Recommended composite**: INDEX on `(customer_id, event_timestamp DESC)` for latest subscription state
- **Optional partial index**: INDEX on `status WHERE status IN ('past_due', 'canceled')` for at-risk analysis

## Relationships
- **Many-to-One with customers**: Each subscription belongs to one customer
  - Join: `subscriptions.customer_id = customers.customer_id`

## Common Query Patterns
- Active subscriptions by plan
- Latest subscription state per customer
- At-risk subscriptions (failed payments)
- Monthly recurring revenue (MRR) calculations
- Subscription status transitions
- Churn analysis by plan

## Data Quality Notes
- Use latest `event_timestamp` for current state
- Status values: active, past_due, canceled, paused
- Billing cycle values: monthly, annual, quarterly
- Multiple events per customer represent subscription history