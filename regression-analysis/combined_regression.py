import pandas as pd
import numpy as np
import psycopg2
from sklearn.linear_model import LinearRegression
from scipy import stats
from urllib.parse import urlparse
from statsmodels.stats.outliers_influence import variance_inflation_factor

import sys
sys.path.append("..")
from globalFunctions import *


# ─── 1. CONNECT & FETCH ──────────────────────────────────────────────────────────

params = config(filename='../database-setup/database.ini', section='postgresql')

conn = psycopg2.connect(**params)
cur = conn.cursor()

def fetch_data(query, cur):
    cur.execute(query)
    cols = [d[0] for d in cur.description]
    return pd.DataFrame(cur.fetchall(), columns=cols)

urls_df       = fetch_data("SELECT * FROM urls", cur)
venues_df     = fetch_data("SELECT * FROM venues", cur)
papers_df     = fetch_data("SELECT * FROM papers", cur)
paper_urls_df = fetch_data("SELECT * FROM paper_urls", cur)

cur.close()
conn.close()

# Pre-compute is_active once for all models
urls_df['is_active'] = urls_df['active'].fillna(False).astype(int)


# ─── 2. SHARED INFERENCE UTILITY ─────────────────────────────────────────────────

def infer_stats(X, y, model):
    """
    Compute standard errors, t-statistics, p-values, 95% CIs,
    R² and adjusted R² for a fitted sklearn LinearRegression.
    """
    n = X.shape[0]
    p = X.shape[1] + 1          # intercept + slopes
    df = n - p

    X_design  = np.hstack([np.ones((n, 1)), X.values])
    residuals = y.values.flatten() - model.predict(X)
    RSS       = np.sum(residuals ** 2)
    sigma2    = RSS / df

    cov_mat  = sigma2 * np.linalg.inv(X_design.T @ X_design)
    se       = np.sqrt(np.diag(cov_mat))
    params_  = np.r_[model.intercept_, model.coef_.flatten()]
    t_stats  = params_ / se
    p_vals   = 2 * (1 - stats.t.cdf(np.abs(t_stats), df))

    t_crit   = stats.t.ppf(1 - 0.05 / 2, df)
    ci_lower = params_ - t_crit * se
    ci_upper = params_ + t_crit * se

    r2     = model.score(X, y)
    adj_r2 = 1 - (1 - r2) * (n - 1) / (n - p)

    report = pd.DataFrame({
        'parameter':   ['intercept'] + X.columns.tolist(),
        'coef':        params_,
        'std_err':     se,
        't_stat':      t_stats,
        'p_value':     p_vals,
        'ci_lower_95': ci_lower,
        'ci_upper_95': ci_upper,
    })
    return r2, adj_r2, report

# ─── Multicollinearity check (Model 1) — VIF ───────────────────────────────────
def compute_vif(X: pd.DataFrame) -> pd.DataFrame:
    # statsmodels expects a plain numeric matrix; we add intercept explicitly
    X_with_const = np.hstack([np.ones((X.shape[0], 1)), X.values])
    vifs = []
    for i in range(1, X_with_const.shape[1]):  # skip intercept
        vifs.append((X.columns[i - 1], variance_inflation_factor(X_with_const, i)))
    return pd.DataFrame(vifs, columns=["variable", "VIF"]).sort_values("VIF", ascending=False)


# ═══════════════════════════════════════════════════════════════════════════════
# MODEL 1 — URL + Paper Features  (multiple regression, paper_url row level)
#   Predictors: url_length, num_path_elements, paper_age, is_https,
#               venue_type (dummies),
#               section (3 groups: abstract / citations / other)
#   Response  : is_active  (binary, one row per citation)
# ═══════════════════════════════════════════════════════════════════════════════

REFERENCE_YEAR = 2024   # year data collection was performed


def count_path_elements(url):
    try:
        return len(urlparse(url).path.split('/')) - 1
    except Exception:
        return None


def get_is_https(url):
    try:
        return int(urlparse(url).scheme.lower() == 'https')
    except Exception:
        return None


# Build paper_url level dataset (one row = one citation)
m1_raw = (
    paper_urls_df
      .merge(
          urls_df[['id', 'url', 'is_active', 'section']],
          left_on='url_id', right_on='id', how='inner'
      ).drop(columns='id')
      .merge(
          papers_df[['id', 'venue_id', 'year']],
          left_on='paper_id', right_on='id', how='inner'
      ).drop(columns='id')
      .merge(
          venues_df[['id', 'type']],
          left_on='venue_id', right_on='id', how='inner'
      ).drop(columns='id')
)

# Derive features
m1_raw['url_length']        = m1_raw['url'].str.len()
m1_raw['num_path_elements'] = m1_raw['url'].apply(count_path_elements)
m1_raw['paper_age']         = REFERENCE_YEAR - m1_raw['year']
m1_raw['is_https']          = m1_raw['url'].apply(get_is_https)
m1_raw['venue_type']        = m1_raw['type'].str.strip().str.lower().fillna('other')

# Fixed 3-group section encoding: abstract | citations | other
# 'other' is set as the first (reference) category so that
# section_grp_abstract and section_grp_citations appear explicitly.
SECTION_GROUPS = {'abstract', 'citations'}
m1_raw['section_grp'] = pd.Categorical(
    m1_raw['section'].apply(lambda s: s if s in SECTION_GROUPS else 'other'),
    categories=['other', 'abstract', 'citations'],
)

# One-hot encode categoricals (drop_first avoids perfect multicollinearity)
m1_enc = pd.get_dummies(
    m1_raw[['url_length', 'num_path_elements', 'paper_age', 'is_https',
            'venue_type', 'section_grp', 'is_active']],
    columns=['venue_type', 'section_grp'],
    drop_first=True,
).dropna()
# get_dummies returns bool columns in newer pandas — cast to int
for col in m1_enc.select_dtypes(include='bool').columns:
    m1_enc[col] = m1_enc[col].astype(int)

feature_cols = [c for c in m1_enc.columns if c != 'is_active']
X1 = m1_enc[feature_cols]
y1 = m1_enc['is_active']

vif_df = compute_vif(X1)
print("-" * 65)
print("MODEL 1 — VIF (multicollinearity diagnostic)")
print(vif_df.to_markdown(index=False))
print()

model1             = LinearRegression().fit(X1, y1)
r2_1, adj_r2_1, report_1 = infer_stats(X1, y1, model1)

print("=" * 65)
print("MODEL 1 — URL + Paper Features  (paper_url row level)")
print(f"  Reference year for paper_age : {REFERENCE_YEAR}")
print(f"  Section groups : abstract | citations | other")
print(f"  n = {len(X1):,}  |  R² = {r2_1:.4f}  |  Adjusted R² = {adj_r2_1:.4f}")
print(f"  Predictors ({len(feature_cols)}): {feature_cols}")
print()
print(report_1.to_markdown(index=False))
print()


# ═══════════════════════════════════════════════════════════════════════════════
# MODEL 2 — Conference CORE Ranking → success_rate
#   (conference venues only; CORE rank mapped to ordinal numeric scale)
# ═══════════════════════════════════════════════════════════════════════════════

core_ranking_df = pd.read_csv("../datasets/conference_core_ranking.csv")

core_merged = (
    venues_df
      .merge(core_ranking_df,  left_on="acronym",  right_on="conference_acronym", how="inner")
      .merge(papers_df,        left_on="id",        right_on="venue_id",           how="inner",
             suffixes=("_venue", "_paper"))
      .merge(paper_urls_df,    left_on="id_paper",  right_on="paper_id",           how="inner")
      .merge(urls_df[['id', 'is_active']], left_on="url_id", right_on="id",        how="inner")
)

core_agg = (
    core_merged
      .groupby("acronym")
      .agg(is_active=('is_active', 'mean'), core_ranking=('core_ranking', 'first'))
      .reset_index()
      .dropna(subset=['core_ranking'])
)

ranking_map = {"A*": 3.82, "A": 15.09, "B": 36.62, "C": 75.35}
core_agg['numerical_ranking'] = core_agg['core_ranking'].map(ranking_map)
core_agg = core_agg.dropna(subset=['numerical_ranking'])

X2      = core_agg[['numerical_ranking']]
y2      = core_agg['is_active']
model2  = LinearRegression().fit(X2, y2)
y_pred2 = model2.predict(X2)
r2_2, adj_r2_2, report_2 = infer_stats(X2, y2, model2)

print("=" * 65)
print("MODEL 2 — CORE Ranking → URL Success Rate")
print("  Predictor : CORE ranking (A* / A / B / C → numeric ordinal)")
print("  Response  : mean success_rate per conference venue")
print(f"  n = {len(X2):,}  |  R² = {r2_2:.4f}  |  Adjusted R² = {adj_r2_2:.4f}")
print()
print(report_2.to_markdown(index=False))
print(f"\n  β(numerical_ranking) = {model2.coef_[0]:.6f}")
print()



# ═══════════════════════════════════════════════════════════════════════════════
# MODEL 3 — Journal Impact Factor → success_rate
#   (journal venues only; mutually exclusive with MODEL 2)
# ═══════════════════════════════════════════════════════════════════════════════

journal_impact_df = pd.read_csv("../datasets/journal_impact_factors.csv")

journal_merged = (
    venues_df
      .merge(journal_impact_df, on="acronym",        how="inner")
      .merge(papers_df,         left_on="id",        right_on="venue_id",  how="inner",
             suffixes=("_venue", "_paper"))
      .merge(paper_urls_df,     left_on="id_paper",  right_on="paper_id",  how="inner")
      .merge(urls_df[['id', 'is_active']], left_on="url_id", right_on="id", how="inner")
)

journal_agg = (
    journal_merged
      .groupby("acronym")
      .agg(is_active=('is_active', 'mean'), journal_impact_factor=('journal_impact_factor', 'first'))
      .reset_index()
      .dropna(subset=['journal_impact_factor'])
)

X3      = journal_agg[['journal_impact_factor']]
y3      = journal_agg['is_active']
model3  = LinearRegression().fit(X3, y3)
y_pred3 = model3.predict(X3)
r2_3, adj_r2_3, report_3 = infer_stats(X3, y3, model3)

print("=" * 65)
print("MODEL 3 — Journal Impact Factor → URL Success Rate")
print("  Predictor : journal impact factor")
print("  Response  : mean success_rate per journal venue")
print(f"  n = {len(X3):,}  |  R² = {r2_3:.4f}  |  Adjusted R² = {adj_r2_3:.4f}")
print()
print(report_3.to_markdown(index=False))
print(f"\n  β(journal_impact_factor) = {model3.coef_[0]:.6f}")
print()
