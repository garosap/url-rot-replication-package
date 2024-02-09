import pandas as pd
import psycopg2
from sklearn.linear_model import LinearRegression

from visualization_function import visualize_data

import sys
sys.path.append("..")
from globalFunctions import *

params = config("../database-setup/database.ini", "postgresql")

# Connect to the database
conn = psycopg2.connect(**params)
cur = conn.cursor()

# Extracting data from the database using cursor and pandas
def fetch_data(query, cur):
    cur.execute(query)
    colnames = [desc[0] for desc in cur.description]
    data = cur.fetchall()
    return pd.DataFrame(data, columns=colnames)


venues_df = fetch_data("SELECT * FROM venues", cur)
papers_df = fetch_data("SELECT * FROM papers", cur)
urls_df = fetch_data("SELECT * FROM urls", cur)
paper_urls_df = fetch_data("SELECT * FROM paper_urls", cur)

# Close the cursor and connection
cur.close()
conn.close()

# Loading the journal_impact_factors.csv data
journal_impact_df = pd.read_csv("./datasets/journal_impact_factors.csv")

# Merging data
merged_df = venues_df.merge(journal_impact_df, on="acronym", how="inner")
merged_df = merged_df.merge(papers_df, left_on="id", right_on="venue_id", how="inner", suffixes=("_venue", "_paper"))
merged_df = merged_df.merge(paper_urls_df, left_on="id_paper", right_on="paper_id", how="inner", suffixes=("_paper", "_url"))
merged_df = merged_df.merge(urls_df, left_on="url_id", right_on="id", how="inner")

# Entries with null value in the active column are considered as inactive
merged_df['active'] = merged_df['active'].fillna(False)

# Calculate URL success rate
merged_df['is_active'] = merged_df['active'].astype(int)
success_rate_df = merged_df.groupby("acronym").agg({"is_active": "mean", "journal_impact_factor": "first"}).reset_index()

# Removing entries with null journal impact factors
success_rate_df = success_rate_df.dropna(subset=["journal_impact_factor"])

# Remove outliers


# Linear regression analysis
X = success_rate_df[['journal_impact_factor']]
y = success_rate_df['is_active']

model = LinearRegression()
model.fit(X, y)

y_pred = model.predict(X)

visualize_data(success_rate_df, X, y_pred, 'journal_impact_factor', 'is_active', 'Journal Impact Factor vs. URL Success Rate', 'journal_impact_factor_vs_url_success_rate')

# Results
print(f"Coefficient: {model.coef_[0]}")
