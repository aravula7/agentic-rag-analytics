# Table: churn_predictions

## Purpose
Batch churn inference outputs from ML models predicting customer churn risk.

## Composite Key
- UNIQUE (`customer_id`, `snapshot_month`, `model_name`)

## Foreign Keys
- `customer_id` (text) → customers(customer_id)

## Columns

### Identifiers
- `customer_id` (text, FOREIGN KEY) - References customers table
- `snapshot_month` (date) - Month of prediction (typically first day of month)
- `model_name` (text) - Name of the model used (e.g., 'lightgbm', 'deepfm')

### Predictions
- `churn_probability` (numeric(6,4)) - Probability of churn (0.0000 to 1.0000)
- `churn_flag` (boolean) - Binary churn prediction (TRUE if high risk)

## Indexes
- UNIQUE constraint on `(customer_id, snapshot_month, model_name)`
- INDEX on `snapshot_month` - for monthly trend analysis
- INDEX on `churn_flag` - for filtering high-risk customers
- **Recommended composite**: INDEX on `(snapshot_month, churn_flag)` for high-risk counts per month

## Relationships
- **Many-to-One with customers**: Each prediction belongs to one customer
  - Join: `churn_predictions.customer_id = customers.customer_id`

## Common Query Patterns
- High churn risk customers for current month
- Churn rate trend over time
- Model comparison (accuracy, predictions)
- High-risk customers by plan (requires subscription join)
- Regional churn analysis
- Churn probability distribution

## Interpretation Notes
- `churn_probability`: Higher values indicate higher risk (typical threshold at 0.5 or 0.6)
- `churn_flag`: Binary indicator, TRUE = high risk
- `snapshot_month`: Typically the first day of the prediction month
- Multiple models can produce predictions for the same customer/month
- Use most recent snapshot_month for current predictions