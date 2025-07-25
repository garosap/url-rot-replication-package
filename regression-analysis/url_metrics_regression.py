import pandas as pd
import numpy as np
import psycopg2
from sklearn.linear_model import LinearRegression
from scipy import stats
from urllib.parse import urlparse


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

urls_df = fetch_data("SELECT * FROM urls", cur)
cur.close()
conn.close()

# ─── 2. DERIVE FEATURES ──────────────────────────────────────────────────────────

def countPathElements(url):
    try:
        parts = urlparse(url).path.split('/')
        return len(parts) - 1
    except:
        return None

urls_df['url_length']        = urls_df['url'].str.len()
urls_df['num_path_elements'] = urls_df['url'].apply(countPathElements)
urls_df['active']            = urls_df['active'].fillna(False)
urls_df['is_active']         = urls_df['active'].astype(int)

# ─── 3. REGRESSION A: URL LENGTH vs. SUCCESS RATE ──────────────────────────────

# 3.1 Aggregate
length_df = (
    urls_df
      .groupby("url_length")
      .agg({"is_active": "mean"})
      .reset_index()
)

X_len = length_df[['url_length']]
y_len = length_df['is_active']

# 3.2 Fit model
model_len = LinearRegression().fit(X_len, y_len)
y_pred_len = model_len.predict(X_len)

# 3.4 Statistics
def infer_stats(X, y, model):
    n = X.shape[0]
    p = X.shape[1] + 1
    df = n - p

    X_design = np.hstack([np.ones((n,1)), X.values])
    residuals = y.values.flatten() - model.predict(X)
    RSS = np.sum(residuals**2)
    sigma2 = RSS / df

    cov_mat = sigma2 * np.linalg.inv(X_design.T @ X_design)
    se = np.sqrt(np.diag(cov_mat))

    params_ = np.r_[model.intercept_, model.coef_.flatten()]
    t_stats = params_ / se
    p_vals = 2 * (1 - stats.t.cdf(np.abs(t_stats), df))

    alpha = 0.05
    t_crit = stats.t.ppf(1 - alpha/2, df)
    ci_lower = params_ - t_crit * se
    ci_upper = params_ + t_crit * se

    r2     = model.score(X, y)
    adj_r2 = 1 - (1 - r2)*(n - 1)/(n - p)

    df_report = pd.DataFrame({
        'parameter':    ['intercept'] + X.columns.tolist(),
        'coef':         params_,
        'std_err':      se,
        't_stat':       t_stats,
        'p_value':      p_vals,
        'ci_lower_95':  ci_lower,
        'ci_upper_95':  ci_upper
    })
    return r2, adj_r2, df_report

r2_len, adj_r2_len, report_len = infer_stats(X_len, y_len, model_len)

print("Regression A: URL Length vs. Success Rate")
print(f"R² = {r2_len:.3f}, adjusted R² = {adj_r2_len:.3f}\n")
print(report_len.to_markdown(index=False))
print(f"\nSlope (β₁) = {model_len.coef_[0]:.6f}\n\n")

# ─── 4. REGRESSION B: PATH ELEMENTS vs. SUCCESS RATE ────────────────────────────

# 4.1 Drop nulls & aggregate
path_df = urls_df.dropna(subset=['num_path_elements']).copy()
path_df['num_path_elements'] = path_df['num_path_elements'].astype(int)
path_df = (
    path_df
      .groupby("num_path_elements")
      .agg({"is_active": "mean"})
      .reset_index()
)

X_path = path_df[['num_path_elements']]
y_path = path_df['is_active']

# 4.2 Fit model
model_path = LinearRegression().fit(X_path, y_path)
y_pred_path = model_path.predict(X_path)

# 4.4 Statistics
r2_path, adj_r2_path, report_path = infer_stats(X_path, y_path, model_path)

print("Regression B: Number of Path Elements vs. Success Rate")
print(f"R² = {r2_path:.3f}, adjusted R² = {adj_r2_path:.3f}\n")
print(report_path.to_markdown(index=False))
print(f"\nSlope (β₁) = {model_path.coef_[0]:.6f}")
