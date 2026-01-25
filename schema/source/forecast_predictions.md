# Table: forecast_predictions

## Purpose
Next-month daily demand forecasts from ML models predicting product sales by region.

## Composite Key
- UNIQUE (`product_id`, `region`, `forecast_date`, `model_name`)

## Foreign Keys
- `product_id` (text) → products(product_id)

## Columns

### Identifiers
- `product_id` (text, FOREIGN KEY) - References products table
- `region` (text) - Geographic region (West, Midwest, South, East)
- `forecast_date` (date) - Date of the forecast
- `model_name` (text) - Name of the forecasting model (e.g., 'prophet', 'xgboost_lstm')

### Predictions
- `predicted_units` (numeric(10,2)) - Point forecast for units sold
- `predicted_units_lower` (numeric(10,2), nullable) - Lower bound of prediction interval
- `predicted_units_upper` (numeric(10,2), nullable) - Upper bound of prediction interval

## Indexes
- UNIQUE constraint on `(product_id, region, forecast_date, model_name)`
- INDEX on `forecast_date` - for date-based queries
- INDEX on `region` - for regional analysis
- **Recommended composite**: INDEX on `(forecast_date, region, product_id)` for dashboard queries

## Relationships
- **Many-to-One with products**: Each forecast belongs to one product
  - Join: `forecast_predictions.product_id = products.product_id`

## Common Query Patterns
- Forecast for next month by category and region
- Top forecasted products for a specific date
- Model comparison for a product/region
- Forecast with uncertainty intervals
- Aggregate demand by category
- Forecast accuracy analysis (requires joining with actual sales)

## Interpretation Notes
- `predicted_units`: Point estimate of demand
- `predicted_units_lower/upper`: Confidence interval (may be NULL for some models)
- Regions: West, Midwest, South, East
- Forecast horizon: Typically next calendar month (daily granularity)
- Multiple models can produce forecasts for the same product/region/date