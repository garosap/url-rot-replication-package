import pandas as pd
import psycopg2
import random
import sys

sys.path.append('../')
from globalFunctions import *

params = config(filename='../database-setup/database.ini', section='postgresql')

# Connect to the database
conn = psycopg2.connect(**params)
cur = conn.cursor()

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

# Filter for active URLs
active_urls = urls_df[urls_df['active'] == True]['url'].tolist()

# Set a seed for deterministic randomness
random.seed(42)

# Randomly sample 200 URLs
url_sample = 200
sampled_urls = random.sample(active_urls, url_sample)

# Store the URLs in a txt file
with open("sampled_active_urls.txt", "w") as file:
    for url in sampled_urls:
        file.write(url + "\n")

print("url_sample active URLs have been written to sampled_active_urls.txt.")
