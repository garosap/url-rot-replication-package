import pandas as pd
import sqlalchemy as sa
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error, r2_score
import psycopg2

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


# Loading the conference_core_ranking.csv data
core_ranking_df = pd.read_csv("./datasets/conference_core_ranking.csv")

# Merging data
venues_rankings = venues_df.merge(core_ranking_df, left_on="acronym", right_on="conference_acronym", how="inner")
venues_rankings_papers = venues_rankings.merge(papers_df, left_on="id", right_on="venue_id", how="inner", suffixes=("_venue'", "_paper'"))
venues_rankings_papers_urls = venues_rankings_papers.merge(paper_urls_df, left_on="id_paper'", right_on="paper_id", how="inner", suffixes=("_paper'", "_url'"))    
merged_df = venues_rankings_papers_urls.merge(urls_df, left_on="url_id", right_on="id", how="inner")

# Entries with null value in the active column are considered as inactive
merged_df['active'] = merged_df['active'].fillna(False)

# Calculate URL success rate
merged_df['is_active'] = merged_df['active'].astype(int)
success_rate_df = merged_df.groupby("acronym").agg({"is_active": "mean", "core_ranking": "first"}).reset_index()

# Convert CORE ranking into numerical values (e.g., A* -> 4, A -> 3, B -> 2)
ranking_conversion = {"A*": 4, "A": 3, "B": 2, "C": 1}


# Remove null values
success_rate_df = success_rate_df[success_rate_df['core_ranking'].notnull()]

success_rate_df['numerical_ranking'] = success_rate_df['core_ranking'].map(ranking_conversion)

# Linear regression analysis
X = success_rate_df[['numerical_ranking']]
y = success_rate_df['is_active']

model = LinearRegression()
model.fit(X, y)

y_pred = model.predict(X)

# Visualize the data
visualize_data(success_rate_df, X, y_pred, 'core_ranking', 'is_active', 'CORE Ranking vs. URL Success Rate', 'core_ranking_vs_url_success_rate')

# Results
print(f"Coefficient: {model.coef_[0]}")

