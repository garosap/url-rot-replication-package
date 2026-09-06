#!/usr/bin/env python3
"""
Citation-level regression — robustness of inference
=====================================================
Reproduces Model 1 (citation-level linear probability model) from
combined_regression.py on the identical design matrix, then
re-estimates inference under a sequence of increasingly permissive
standard-error specifications, to address Referee 1's objection that
significance claims rest on unassessed OLS assumptions
(independence, homoscedasticity, normality):

  1. Classical (nonrobust) OLS SEs   — sanity check against Table 5
  2. HC3 heteroskedasticity-robust SEs
  3. Standard errors clustered by paper_id
  4. Standard errors clustered by domain (registered domain, tldextract)
  5. Two-way clustering (paper_id, domain)

A logistic-regression robustness check (same outcome, observations,
predictors, and reference categories) is fit with paper-clustered SEs,
reporting average marginal effects (AMEs) on the probability scale so
they are directly comparable to the linear-probability coefficients.
A flexible logistic specification with B-spline terms for the two
continuous predictors (url_length, paper_age) is fit as an additional
check on functional-form sensitivity.
"""

import numpy as np
import pandas as pd
import psycopg2
import statsmodels.api as sm
import statsmodels.formula.api as smf
import tldextract
from urllib.parse import urlparse

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

urls_df['is_active'] = urls_df['active'].fillna(False).infer_objects(copy=False).astype(int)


# ─── 2. REBUILD MODEL-1 DESIGN MATRIX (identical to combined_regression.py) ─────

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


def get_domain(url):
    try:
        return tldextract.extract(url).registered_domain or None
    except Exception:
        return None


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

m1_raw['url_length']        = m1_raw['url'].str.len()
m1_raw['num_path_elements'] = m1_raw['url'].apply(count_path_elements)
m1_raw['paper_age']         = REFERENCE_YEAR - m1_raw['year']
m1_raw['is_https']          = m1_raw['url'].apply(get_is_https)
m1_raw['venue_type']        = m1_raw['type'].str.strip().str.lower().fillna('other')
m1_raw['domain']            = m1_raw['url'].apply(get_domain)

# Fixed 3-group section encoding: abstract | citations | other
SECTION_GROUPS = {'abstract', 'citations'}
m1_raw['section_grp'] = pd.Categorical(
    m1_raw['section'].apply(lambda s: s if s in SECTION_GROUPS else 'other'),
    categories=['other', 'abstract', 'citations'],
)

# Keep paper_id and domain alongside the modeled columns so cluster
# groups stay row-aligned. dropna() is restricted to the actual model
# features (matching combined_regression.py's row set exactly, n=204,383):
# domain is only a clustering label, so a small number of URLs tldextract
# can't map to a registered domain (bare IPs, unusual TLDs) must NOT be
# dropped from the regression itself — they get a sentinel cluster instead.
m1_enc = pd.get_dummies(
    m1_raw[['paper_id', 'domain', 'url_length', 'num_path_elements', 'paper_age',
            'is_https', 'venue_type', 'section_grp', 'is_active']],
    columns=['venue_type', 'section_grp'],
    drop_first=True,
)
feature_cols = [c for c in m1_enc.columns if c not in ('is_active', 'paper_id', 'domain')]
m1_enc = m1_enc.dropna(subset=feature_cols + ['paper_id'])
m1_enc['domain'] = m1_enc['domain'].fillna('__unresolved_domain__')
for col in m1_enc.select_dtypes(include='bool').columns:
    m1_enc[col] = m1_enc[col].astype(int)
X = sm.add_constant(m1_enc[feature_cols].astype(float))
y = m1_enc['is_active'].astype(float)
groups_paper  = m1_enc['paper_id'].values
groups_domain = m1_enc['domain'].astype(str).values

print("=" * 70)
print("DESIGN MATRIX")
print(f"  n = {len(X):,}")
print(f"  papers  (clusters) = {m1_enc['paper_id'].nunique():,}")
print(f"  domains (clusters) = {pd.Series(groups_domain).nunique():,}")
print(f"  predictors: {feature_cols}")
print()


# ─── 3. HELPER — FORMAT A FITTED OLS RESULT AS A REPORT TABLE ───────────────────

def ols_report(res, label):
    ci = res.conf_int()
    report = pd.DataFrame({
        'parameter':   res.params.index,
        'coef':        res.params.values,
        'std_err':     res.bse.values,
        'p_value':     res.pvalues.values,
        'ci_lower_95': ci[0].values,
        'ci_upper_95': ci[1].values,
    })
    print("-" * 70)
    print(f"MODEL 1 — {label}")
    print(f"  n = {int(res.nobs):,}  |  R² = {res.rsquared:.4f}  |  Adj. R² = {res.rsquared_adj:.4f}")
    print(report.to_markdown(index=False))
    print()
    return report


# ═══════════════════════════════════════════════════════════════════════════════
# MODEL 1 — SEQUENCE OF STANDARD-ERROR SPECIFICATIONS
# ═══════════════════════════════════════════════════════════════════════════════

# 1. Classical (nonrobust) — sanity check against Table 5 (main.tex)
ols_base   = sm.OLS(y, X).fit()
rep_classical = ols_report(ols_base, "Classical (nonrobust) SEs [sanity check vs. Table 5]")

# 2. HC3 heteroskedasticity-robust
ols_hc3    = sm.OLS(y, X).fit(cov_type='HC3')
rep_hc3    = ols_report(ols_hc3, "HC3 heteroskedasticity-robust SEs")

# 3. Clustered by paper_id
ols_paper  = sm.OLS(y, X).fit(cov_type='cluster', cov_kwds={'groups': groups_paper})
rep_paper  = ols_report(ols_paper, "Clustered by paper_id")

# 4. Clustered by domain
ols_domain = sm.OLS(y, X).fit(cov_type='cluster', cov_kwds={'groups': groups_domain})
rep_domain = ols_report(ols_domain, "Clustered by domain")

# 5. Two-way clustering (paper_id, domain)
# statsmodels builds a structured array internally for two-way clustering,
# which requires both group columns to share a single numeric dtype.
groups_2way = np.column_stack([
    pd.factorize(groups_paper)[0],
    pd.factorize(groups_domain)[0],
]).astype(np.int64)
ols_2way    = sm.OLS(y, X).fit(cov_type='cluster', cov_kwds={'groups': groups_2way})
rep_2way    = ols_report(ols_2way, "Two-way clustered (paper_id, domain)")


# ═══════════════════════════════════════════════════════════════════════════════
# COMBINED ROBUSTNESS COMPARISON TABLE (coef stable across specs; SE/CI/p vary)
# ═══════════════════════════════════════════════════════════════════════════════

specs = [
    ("classical", rep_classical),
    ("HC3", rep_hc3),
    ("cluster: paper", rep_paper),
    ("cluster: domain", rep_domain),
    ("cluster: paper+domain", rep_2way),
]

comparison_rows = []
for param in rep_classical['parameter']:
    row = {"parameter": param, "coef": float(rep_classical.loc[rep_classical['parameter'] == param, 'coef'].iloc[0])}
    for spec_name, rep in specs:
        p = rep.loc[rep['parameter'] == param].iloc[0]
        row[f"p ({spec_name})"] = round(p['p_value'], 4)
    comparison_rows.append(row)

comparison_df = pd.DataFrame(comparison_rows)
print("=" * 70)
print("ROBUSTNESS COMPARISON — p-values across specifications")
print(comparison_df.to_markdown(index=False))
print()


# ═══════════════════════════════════════════════════════════════════════════════
# MODEL 1-L — LOGISTIC-REGRESSION ROBUSTNESS CHECK (same spec, paper-clustered SEs)
# ═══════════════════════════════════════════════════════════════════════════════

logit_res = sm.Logit(y, X).fit(cov_type='cluster', cov_kwds={'groups': groups_paper}, disp=0)
print("=" * 70)
print("MODEL 1-L — Logistic regression (paper-clustered SEs)")
print(f"  n = {int(logit_res.nobs):,}  |  Pseudo R² = {logit_res.prsquared:.4f}")
print(logit_res.summary2().tables[1].to_markdown())
print()

ame = logit_res.get_margeff(at='overall')
ame_df = pd.DataFrame({
    'parameter':   ame.summary_frame().index,
    'dy/dx':       ame.summary_frame()['dy/dx'].values,
    'std_err':     ame.summary_frame()['Std. Err.'].values,
    'p_value':     ame.summary_frame()['Pr(>|z|)'].values,
    'ci_lower_95': ame.summary_frame()['Conf. Int. Low'].values,
    'ci_upper_95': ame.summary_frame()['Cont. Int. Hi.'].values,  # statsmodels' own column name (typo upstream)
})
print("MODEL 1-L — Average marginal effects (probability scale)")
print(ame_df.to_markdown(index=False))
print()

fitted = logit_res.predict(X)
print(f"  Fitted-probability range: [{fitted.min():.4f}, {fitted.max():.4f}]  (LPM fitted values may fall outside [0,1])")
print()

# ─── LPM vs. logistic-AME side-by-side comparison ───────────────────────────────

lpm_vs_logit = rep_paper[['parameter', 'coef', 'p_value']].rename(
    columns={'coef': 'LPM coef (paper-clustered)', 'p_value': 'LPM p'}
).merge(
    ame_df[['parameter', 'dy/dx', 'p_value']].rename(
        columns={'dy/dx': 'Logit AME (paper-clustered)', 'p_value': 'Logit p'}
    ),
    on='parameter', how='left'
)
print("=" * 70)
print("LPM (paper-clustered) vs. LOGISTIC AME (paper-clustered)")
print(lpm_vs_logit.to_markdown(index=False))
print()


# ═══════════════════════════════════════════════════════════════════════════════
# MODEL 1-L-SPLINE — LOGISTIC WITH B-SPLINE TERMS FOR CONTINUOUS PREDICTORS
# ═══════════════════════════════════════════════════════════════════════════════

spline_df = m1_enc.copy()
non_continuous_cols = [c for c in feature_cols if c not in ('url_length', 'num_path_elements', 'paper_age')]
formula = (
    "is_active ~ bs(url_length, df=4) + num_path_elements + bs(paper_age, df=4) + "
    + " + ".join(non_continuous_cols)
)

logit_spline_res = smf.logit(formula, data=spline_df).fit(
    cov_type='cluster', cov_kwds={'groups': spline_df['paper_id']}, disp=0
)
print("=" * 70)
print("MODEL 1-L-SPLINE — Logistic with B-splines (url_length, paper_age), paper-clustered SEs")
print(f"  n = {int(logit_spline_res.nobs):,}  |  Pseudo R² = {logit_spline_res.prsquared:.4f}")
print(logit_spline_res.summary2().tables[1].to_markdown())
print()

spline_ame = logit_spline_res.get_margeff(at='overall')
spline_ame_df = pd.DataFrame({
    'parameter':   spline_ame.summary_frame().index,
    'dy/dx':       spline_ame.summary_frame()['dy/dx'].values,
    'p_value':     spline_ame.summary_frame()['Pr(>|z|)'].values,
})
print("MODEL 1-L-SPLINE — Average marginal effects for non-spline terms")
print(spline_ame_df[~spline_ame_df['parameter'].str.contains('bs\\(')].to_markdown(index=False))
print()
print("  Note: spline AMEs for url_length/paper_age are basis-term specific and not")
print("  individually interpretable; compare overall significance pattern of the")
print("  remaining predictors against MODEL 1-L to assess functional-form sensitivity.")
