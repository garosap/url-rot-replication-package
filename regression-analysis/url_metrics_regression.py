import pandas as pd
import psycopg2
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error, r2_score
from urllib.parse import urlparse

from visualization_function import visualize_data

import sys
sys.path.append("..")
from globalFunctions import *

params = config("../database-setup/database.ini", "postgresql")

# Connect to the database
conn = psycopg2.connect(**params)
cur = conn.cursor()

def countPathElements(url):
    try:
        # Parse the URL and split the path into elements
        path_elements = urlparse(url).path.split('/')
        
        # Subtract 1 to account for the initial empty string before the first '/'
        count = len(path_elements) - 1
        
        return count
    except Exception as e:
        # Return None (which is equivalent to NULL in databases) on error
        return None



# Extracting data from the database using cursor and pandas
def fetch_data(query, cur):
    cur.execute(query)
    colnames = [desc[0] for desc in cur.description]
    data = cur.fetchall()
    return pd.DataFrame(data, columns=colnames)

# Fetching URLs and their active statuses
urls_df = fetch_data("SELECT * FROM urls", cur)

# Close the cursor and connection
cur.close()
conn.close()

# Calculate URL length
urls_df['url_length'] = urls_df['url'].str.len()

# Calculate the number of path elements in the URL
urls_df['num_path_elements'] = urls_df['url'].apply(lambda x: countPathElements(x))

# Entries with null value in the active column are considered as inactive
urls_df['active'] = urls_df['active'].fillna(False)
urls_df['is_active'] = urls_df['active'].astype(int)

# Merge the same length URLs and calculate the success rate
urls_length_df = urls_df.groupby("url_length").agg({"is_active": "mean"}).reset_index()


# Linear Regression for URL Length vs. Success Rate
X_length = urls_length_df[['url_length']]
y = urls_length_df['is_active']

model_length = LinearRegression()
model_length.fit(X_length, y)

y_pred_length = model_length.predict(X_length)

# Visualize the data
visualize_data(urls_length_df, X_length, y_pred_length, 'url_length', 'is_active', 'URL Length vs. Success Rate', 'url_length_vs_success_rate')

# Results for URL Length vs. Success Rate
print("Regression: URL Length vs. Success Rate")
print(f"Coefficient: {model_length.coef_[0]}")
print("\n")

urls_df = urls_df.dropna(subset=["num_path_elements"])

# Merge the same length URLs and calculate the success rate
urls_df['num_path_elements'] = urls_df['num_path_elements'].astype(int)
urls_df = urls_df.groupby("num_path_elements").agg({"is_active": "mean"}).reset_index()


# Linear Regression for Number of Path Elements vs. Success Rate
X_path = urls_df[['num_path_elements']]
y = urls_df['is_active']

model_path = LinearRegression()
model_path.fit(X_path, y)

y_pred_path = model_path.predict(X_path)

# Visualize the data
visualize_data(urls_df, X_path, y_pred_path, 'num_path_elements', 'is_active', 'Number of Path Elements vs. Success Rate', 'num_path_elements_vs_success_rate')

# Results for Number of Path Elements vs. Success Rate
print("Regression: Number of Path Elements vs. Success Rate")
print(f"Coefficient: {model_path.coef_[0]}")
