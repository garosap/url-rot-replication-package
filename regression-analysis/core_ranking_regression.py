import pandas as pd
import numpy as np
import psycopg2
from sklearn.linear_model import LinearRegression
from scipy import stats

import sys
sys.path.append("..")
from globalFunctions import *

# ─── 1. CONNECT & FETCH ─────────────────────────────────────────────────────────


params = config(filename='../database-setup/database.ini', section='postgresql')

conn = psycopg2.connect(**params)
cur = conn.cursor()

def fetch_data(query, cur):
    cur.execute(query)
    cols = [d[0] for d in cur.description]
    data = cur.fetchall()
    return pd.DataFrame(data, columns=cols)

venues_df      = fetch_data("SELECT * FROM venues", cur)
papers_df      = fetch_data("SELECT * FROM papers", cur)
urls_df        = fetch_data("SELECT * FROM urls", cur)
paper_urls_df  = fetch_data("SELECT * FROM paper_urls", cur)

cur.close()
conn.close()

# ─── 2. LOAD RANKINGS & MERGE ────────────────────────────────────────────────────

core_ranking_df = pd.read_csv("../datasets/conference_core_ranking.csv")

merged_df = (
    venues_df
      .merge(core_ranking_df, 
             left_on="acronym", right_on="conference_acronym", how="inner")
      .merge(papers_df,     left_on="id", right_on="venue_id", how="inner",
             suffixes=("_venue","_paper"))
      .merge(paper_urls_df, left_on="id_paper", right_on="paper_id", how="inner")
      .merge(urls_df,       left_on="url_id", right_on="id", how="inner")
)

merged_df['active']    = merged_df['active'].fillna(False)
merged_df['is_active'] = merged_df['active'].astype(int)

success_rate_df = (
    merged_df
      .groupby("acronym")
      .agg({"is_active": "mean", "core_ranking": "first"})
      .reset_index()
      .query("core_ranking.notnull()")
)

ranking_conversion = {"A*": 3.82, "A": 15.09, "B": 36.62, "C": 75.35}
success_rate_df['numerical_ranking'] = success_rate_df['core_ranking'].map(ranking_conversion)

# ─── 3. FIT LINEAR MODEL ─────────────────────────────────────────────────────────

X = success_rate_df[['numerical_ranking']]
y = success_rate_df['is_active']

model = LinearRegression()
model.fit(X, y)
y_pred = model.predict(X)

# ─── 4. COMPUTE STATISTICAL INFERENCE ────────────────────────────────────────────

n = X.shape[0]             # observations
p = X.shape[1] + 1         # parameters: intercept + slope
df = n - p                 # degrees of freedom

# 4.1 Design matrix with intercept
X_design = np.hstack([np.ones((n,1)), X.values])

# 4.2 Residuals & variance estimate
residuals = y.values.flatten() - y_pred
RSS       = np.sum(residuals**2)
sigma2    = RSS / df

# 4.3 Variance–covariance matrix & standard errors
cov_mat = sigma2 * np.linalg.inv(X_design.T @ X_design)
se      = np.sqrt(np.diag(cov_mat))

# 4.4 Parameter estimates (intercept, slope)
params_  = np.r_[model.intercept_, model.coef_.flatten()]

# 4.5 t-statistics & two-sided p-values
t_stats  = params_ / se
p_values = 2 * (1 - stats.t.cdf(np.abs(t_stats), df))

# 4.6 95% confidence intervals
alpha   = 0.05
t_crit  = stats.t.ppf(1 - alpha/2, df)
ci_lower = params_ - t_crit * se
ci_upper = params_ + t_crit * se

# 4.7 R² and adjusted R²
r2     = model.score(X, y)
adj_r2 = 1 - (1 - r2)*(n - 1)/(n - p)

# Assemble report
report_df = pd.DataFrame({
    'parameter':    ['intercept'] + X.columns.tolist(),
    'coef':         params_,
    'std_err':      se,
    't_stat':       t_stats,
    'p_value':      p_values,
    'ci_lower_95':  ci_lower,
    'ci_upper_95':  ci_upper
})

# ─── 5. OUTPUT RESULTS ──────────────────────────────────────────────────────────

print(f"R² = {r2:.3f}, adjusted R² = {adj_r2:.3f}\n")
print(report_df.to_markdown(index=False))


# ─── 7. COEFFICIENT SUMMARY ────────────────────────────────────────────────────

print(f"\nSlope (β₁) = {model.coef_[0]:.6f}")
