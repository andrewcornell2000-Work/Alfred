# Data Time Series Analysis & Forecasting

**Source:** https://github.com/nimrodfisher/data-analytics-skills  
**Attribution:** nimrodfisher — data analytics skills collection.  
**Adapted for Alfred:** applies to labour planning, headcount forecasting, and finance trend analysis.

---

## When This Skill Applies

Use when:
- Detecting trends or seasonality in a metric over time (headcount, cost, volume)
- Forecasting future values for planning or budgeting
- Distinguishing genuine trends from seasonal fluctuation
- Detecting anomalies in time series data
- Establishing a baseline before/after a change to measure impact

---

## Six-Step Process

### Step 1 — Validate data quality
- Confirm consistent time intervals (daily, weekly, monthly)
- Address missing values — interpolate or flag gaps
- Ensure the series has at least **two complete seasonal cycles** for reliable decomposition

### Step 2 — Stationarity check
Apply Augmented Dickey-Fuller (ADF) test:
- **Non-stationary** → trend or seasonal component present — proceed to decomposition
- **Stationary** → no structural trend, simpler models apply

### Step 3 — Decompose into components

```python
from statsmodels.tsa.seasonal import seasonal_decompose

result = seasonal_decompose(df['metric'], model='additive', period=12)
# Components: trend, seasonal, residual
```

Measure component strength on a 0–1 scale:
- **Trend strength > 0.6** → meaningful directional change
- **Seasonality strength > 0.6** → seasonal adjustment needed for forecasting

### Step 4 — Anomaly detection
Flag outliers exceeding **3 standard deviations** from the rolling median. Cross-reference against event logs (org changes, system changes, data issues).

### Step 5 — Forecast

```python
from statsmodels.tsa.arima.model import ARIMA

model = ARIMA(train_data, order=(1, 1, 1))
fit = model.fit()
forecast = fit.forecast(steps=forecast_period)
```

- Validate against a holdout test set (hold back last 20% of data)
- Generate confidence intervals — always show upper/lower bounds, not just point estimates
- For simple series: 3-month or 6-month moving average is often good enough

### Step 6 — Document findings
Report must include:
- Pattern characterisation (trending up/down/flat, seasonal period, volatility)
- Decomposition summary (trend strength, seasonal amplitude)
- Anomaly list with dates and likely causes
- Forecast table with confidence intervals

---

## Required Inputs

- Date column + metric column
- At least 2 complete seasonal cycles of history
- Data granularity (daily / weekly / monthly)
- Desired forecast horizon
- Business context about what drives the metric

---

## Labour Planning Note
For Alfred's Maersk labour planning context: headcount and labour cost data typically has strong monthly seasonality. Use multiplicative decomposition when variance scales with level (i.e. seasonal swings are bigger in bigger months). Use additive when swings are roughly constant.
