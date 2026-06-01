# Exploratory Data Analysis (EDA)

**Source:** https://github.com/nimrodfisher/data-analytics-skills  
**Attribution:** nimrodfisher — data analytics skills collection.  
**Adapted for Alfred:** applies when a new dataset lands and needs initial profiling before analysis or modelling.

---

## When This Skill Applies

Use when:
- A new CSV, Excel export, or database table needs to be understood before analysis
- Analysis results seem unexpected and the data itself needs sanity-checking
- A stakeholder questions the reliability of data
- Building a Power BI model and need to understand the grain and quality of source tables
- Before running any statistical model or forecast

---

## Seven-Step EDA Process

### Step 1 — Load and inspect structure
```python
import pandas as pd

df = pd.read_excel('data.xlsx')   # or read_csv, read_parquet

print(df.shape)          # rows × columns
print(df.dtypes)         # column types
print(df.head(10))       # sample rows
print(df.columns.tolist())  # column names
```

### Step 2 — Null profile
```python
null_report = pd.DataFrame({
    'nulls': df.isnull().sum(),
    'null_pct': (df.isnull().sum() / len(df) * 100).round(1)
}).sort_values('null_pct', ascending=False)

print(null_report[null_report['nulls'] > 0])
```

Flag columns where null % exceeds:
- **> 50%** 🔴 — likely unusable, investigate before proceeding
- **5–50%** 🟡 — document and handle explicitly
- **< 5%** 🟢 — acceptable, note in findings

### Step 3 — Distribution summary
```python
print(df.describe(include='all'))   # stats for numeric + categorical
```

For numeric columns, flag:
- Min/max outliers (values that seem implausible for the domain)
- Zero-inflated columns (lots of zeros — intentional or data gap?)
- Negative values where they shouldn't exist

### Step 4 — Outlier detection
```python
from scipy import stats

z_scores = stats.zscore(df.select_dtypes(include='number'))
outliers = (abs(z_scores) > 3).sum()
print(outliers[outliers > 0])
```

### Step 5 — Correlation check
```python
corr = df.select_dtypes(include='number').corr()
# Flag pairs with |r| > 0.85 — potential multicollinearity or duplicate columns
high_corr = corr.where(abs(corr) > 0.85).stack().reset_index()
print(high_corr[high_corr['level_0'] != high_corr['level_1']])
```

### Step 6 — Categorical cardinality
```python
for col in df.select_dtypes(include='object').columns:
    print(f"{col}: {df[col].nunique()} unique values")
    if df[col].nunique() < 20:
        print(df[col].value_counts())
```

Flags:
- Very high cardinality in an ID-like column → confirm it's actually an identifier
- Unexpected values (typos, mixed case, encoding issues)

### Step 7 — Document findings

EDA report covers:
- Dataset dimensions and grain (what does one row represent?)
- Data quality summary (nulls, types, suspicious values)
- Key distributions and outliers worth noting
- Recommended pre-processing steps before analysis
- Any blocker that needs resolving before proceeding

---

## Quick EDA Checklist

- [ ] Shape and column types confirmed
- [ ] Null profile reviewed — high-null columns flagged
- [ ] Numeric distributions checked for implausible values
- [ ] Outliers identified and cross-referenced against domain knowledge
- [ ] Categorical columns checked for unexpected values or encoding issues
- [ ] Date columns parsed correctly (not imported as strings)
- [ ] Grain confirmed (what does one row represent?)
- [ ] Findings documented before proceeding to analysis
