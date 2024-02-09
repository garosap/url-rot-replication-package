# Imports
import psycopg2
import matplotlib.pyplot as plt
import tldextract
import math
import datetime
import statistics
import csv
import pandas as pd
import seaborn as sns

from error_mappings import curl_error_mapping, http_status_descriptions

import sys

sys.path.append('../')
from globalFunctions import *
params = config(filename='../database-setup/database.ini', section='postgresql')


# Checks if the url is version control url
def is_version_control_url(url):
    regex = r'^https?://(?:www\.)?(github\.com|bitbucket\.org|gitlab\.com)/.*$'
    return bool(re.match(regex, url))

# Checks if the url is archival url
def is_archival_url(url):
    regex = r'^https?://(?:www\.)?(zenodo\.org|arxiv\.org|archive\.org|softwareheritage\.org|figshare\.com|archive\.softwareheritage\.org)/.*$'
    return bool(re.match(regex, url))

# #  Generate active urls stacked bar chart
def generate_active_inactive_urls_stacked_bar_chart_with_counts(cursor):
    sns.set_style("whitegrid")
    
    categories = ["All", "Version Control", "Archival"]
    active_counts = []
    inactive_counts = []
    total_counts = [] 

    cursor.execute("SELECT * FROM urls;")
    all_urls = cursor.fetchall()

    def calculate_percentages_and_counts(urls):
        active = sum(1 for url in urls if url[2])
        inactive = len(urls) - active
        active_percentage = (active / len(urls)) * 100
        inactive_percentage = (inactive / len(urls)) * 100
        return active_percentage, inactive_percentage, len(urls)

    # All URLs
    active_percentage, inactive_percentage, count = calculate_percentages_and_counts(all_urls)
    active_counts.append(active_percentage)
    inactive_counts.append(inactive_percentage)
    total_counts.append(count)

    # Version Control URLs
    vc_urls = [url for url in all_urls if is_version_control_url(url[1])]
    active_percentage, inactive_percentage, count = calculate_percentages_and_counts(vc_urls)
    active_counts.append(active_percentage)
    inactive_counts.append(inactive_percentage)
    total_counts.append(count)

    # Archival URLs
    ar_urls = [url for url in all_urls if is_archival_url(url[1])]
    active_percentage, inactive_percentage, count = calculate_percentages_and_counts(ar_urls)
    active_counts.append(active_percentage)
    inactive_counts.append(inactive_percentage)
    total_counts.append(count)

    # Plotting the stacked bar chart
    fig, ax = plt.subplots(figsize=(8,6))
    

    # add active count percentage (rounded to 2 decimals) (with label) in results.txt
    with open('visualization-outputs/results.txt', 'w') as f:
        f.write("Active percentages:\n")
        f.write("All URLs: %s percent\n" % round(active_counts[0], 2))
        f.write("Version Control URLs: %s percent\n" % round(active_counts[1], 2))
        f.write("Archival URLs: %s percent\n" % round(active_counts[2], 2))
        f.write("\n")
        


    bars_active = ax.bar(categories, active_counts, label='Active', color="white",  hatch='..', edgecolor="black")
    bars_inactive = ax.bar(categories, inactive_counts, bottom=active_counts, label='Inactive', color="white", edgecolor="black")

    # Annotate with the number of URLs below the x-axis labels
    for i, rect in enumerate(bars_active):
        ax.text(rect.get_x() + rect.get_width()/2., -14 ,  # Adjusted y-coordinate to position below x-axis
                '(%s)' % (int(total_counts[i])),
                ha='center', va='bottom', fontsize=15)

    
    ax.set_xticklabels(categories, fontsize=15)
    ax.set_yticklabels([0, 20, 40, 60, 80, 100], fontsize=15)
    ax.set_ylabel('URL Percentage (%)', fontsize=15)
    ax.set_title('Active and Inactive URLs', fontsize=15)
    ax.legend(loc='center left', bbox_to_anchor=(1, 0.5), fontsize=15)
    ax.spines['right'].set_visible(False)
    ax.spines['top'].set_visible(False)

    plt.tight_layout()
    plt.show()
    fig.savefig('visualization-outputs/activeInactiveUrls_with_counts.pdf', dpi=300)


def generate_urls_section_stacked_bar_chart_with_counts(cursor):
    sns.set_style("whitegrid")
    
    categories = ["Abstract", "Citation", "Body"]
    active_counts = []
    inactive_counts = []
    total_counts = []

    cursor.execute("SELECT * FROM urls;")
    all_urls = cursor.fetchall()

    def calculate_percentages_and_counts(urls):
        print(len(urls))
        active = sum(1 for url in urls if url[2])
        inactive = len(urls) - active
        active_percentage = (active / len(urls)) * 100
        inactive_percentage = (inactive / len(urls)) * 100
        return active_percentage, inactive_percentage, len(urls)


    abstract_urls = [url for url in all_urls if url[5] == "abstract"]
    active_percentage, inactive_percentage, count = calculate_percentages_and_counts(abstract_urls)
    active_counts.append(active_percentage)
    inactive_counts.append(inactive_percentage)
    total_counts.append(count)

    # section is citation
    citation_urls = [url for url in all_urls if url[5] == "citations"]
    active_percentage, inactive_percentage, count = calculate_percentages_and_counts(citation_urls)
    active_counts.append(active_percentage)
    inactive_counts.append(inactive_percentage)
    total_counts.append(count)

    # section other
    body_urls = [url for url in all_urls if url[5] not in ["abstract", "citations"]]
    active_percentage, inactive_percentage, count = calculate_percentages_and_counts(body_urls)
    active_counts.append(active_percentage)
    inactive_counts.append(inactive_percentage)
    total_counts.append(count)

    # Plotting the stacked bar chart
    fig, ax = plt.subplots(figsize=(8,6))
    

    # add active count percentage (rounded to 2 decimals) (with label) in results.txt
    with open('visualization-outputs/results.txt', 'a') as f:
        f.write("Active percentages:\n")
        f.write("Abstract URLs: %s percent\n" % round(active_counts[0], 2))
        f.write("Citation URLs: %s percent\n" % round(active_counts[1], 2))
        f.write("Body URLs: %s percent\n" % round(active_counts[2], 2))
        f.write("\n")
        


    bars_active = ax.bar(categories, active_counts, label='Active', color="white",  hatch='..', edgecolor="black")
    bars_inactive = ax.bar(categories, inactive_counts, bottom=active_counts, label='Inactive', color="white", edgecolor="black")

    # Annotate with the number of URLs below the x-axis labels
    for i, rect in enumerate(bars_active):
        ax.text(rect.get_x() + rect.get_width()/2., -14 ,  # Adjusted y-coordinate to position below x-axis
                '(%s)' % (int(total_counts[i])),
                ha='center', va='bottom', fontsize=15)

    
    ax.set_xticklabels(categories, fontsize=15)
    ax.set_yticklabels([0, 20, 40, 60, 80, 100], fontsize=15)
    ax.set_ylabel('URL Percentage (%)', fontsize=15)
    ax.set_title('Active and Inactive URLs', fontsize=15)
    ax.legend(loc='center left', bbox_to_anchor=(1, 0.5), fontsize=15)
    ax.spines['right'].set_visible(False)
    ax.spines['top'].set_visible(False)

    plt.tight_layout()
    plt.show()
    fig.savefig('visualization-outputs/activeInactiveUrls_by_section.pdf', dpi=300)




def generate_active_urls_per_conference_stacked_bar_chart(cursor):
    # Retrieve venue records from the venues table
    cursor.execute("SELECT * FROM venues;")
    confs = cursor.fetchall()

    data = []

    for conf in confs:
        cursor.execute("""
            SELECT COUNT(DISTINCT urls.id)
            FROM papers
            JOIN paper_urls ON paper_urls.paper_id = papers.id
            JOIN urls ON urls.id = paper_urls.url_id
            WHERE papers.venue_id = %s;
        """, (conf[0],))
        total_urls_count = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(DISTINCT urls.id)
            FROM papers
            JOIN paper_urls ON paper_urls.paper_id = papers.id
            JOIN urls ON urls.id = paper_urls.url_id
            WHERE papers.venue_id = %s
            AND urls.active = TRUE;
        """, (conf[0],))
        active_urls_count = cursor.fetchone()[0]

        if conf[1] == "MSR":
            print("MSR:", active_urls_count, total_urls_count)

        if total_urls_count == 0:
            active_percentage = 0
            inactive_percentage = 0
        else:
            active_percentage = active_urls_count / total_urls_count * 100
            inactive_percentage = 100 - active_percentage

        data.append((conf[1], active_percentage, inactive_percentage))

    # Sort the data based on active URL percentages
    data.sort(key=lambda x: x[1])

    # Separate out the sorted data
    conf_names = [item[0] for item in data]
    activeUrlsPercentage = [item[1] for item in data]
    inactiveUrlsPercentage = [item[2] for item in data]

    # add active count percentage rounded to 2 decimals (with label) in results.txt
    with open('visualization-outputs/results.txt', 'a') as f:
        f.write("\nActive percentages per venue:\n")
        for i in range(len(conf_names)):
            f.write("%s: %s percent\n" % (conf_names[i], round(activeUrlsPercentage[i], 2)))
        f.write("\n")

    # Plotting the stacked bar chart
    fig, ax = plt.subplots(figsize=(20, 10))
    
    # The bottom bar is for active URLs
    ax.bar(conf_names, activeUrlsPercentage, label='Active URLs', color="white", edgecolor="black")
    
    # The top bar (stacked on the bottom bar) is for inactive URLs
    ax.bar(conf_names, inactiveUrlsPercentage, bottom=activeUrlsPercentage, label='Inactive URLs', visible=False)
    
    ax.set_xticklabels(conf_names, rotation=45, fontsize=15)
    ax.set_ylabel('URL Percentage (%)', fontsize=15)
    ax.set_title('Active vs Inactive URLs percentage per conference', fontsize=15)
    ax.legend(loc='center left', bbox_to_anchor=(1, 0.5), fontsize=15)
    
    ax.spines['right'].set_visible(False)
    ax.spines['top'].set_visible(False)

    plt.tight_layout()
    fig.savefig('visualization-outputs/activeVsInactiveUrlsPerConf.pdf', dpi=300)
    plt.show()

def generate_active_urls_per_year_stacked_bar_chart(cursor):
    # Retrieve unique years from the papers table
    cursor.execute("SELECT DISTINCT year FROM papers;")
    years = cursor.fetchall()

    activeUrlsPercentagePerYear = []
    inactiveUrlsPercentagePerYear = []
    totalUrlsCountPerYear = []  # to store total URLs count per year
    valid_years = []

    for year in years:
        cursor.execute("""
            SELECT COUNT(DISTINCT urls.id)
            FROM papers
            JOIN paper_urls ON paper_urls.paper_id = papers.id
            JOIN urls ON urls.id = paper_urls.url_id
            WHERE papers.year = %s;
        """, (year[0],))
        total_urls_count = cursor.fetchone()[0]

        if total_urls_count == 0:
            continue  # Skip years without URLs

        cursor.execute("""
            SELECT COUNT(DISTINCT urls.id)
            FROM papers
            JOIN paper_urls ON paper_urls.paper_id = papers.id
            JOIN urls ON urls.id = paper_urls.url_id
            WHERE papers.year = %s
            AND urls.active = TRUE;
        """, (year[0],))
        active_urls_count = cursor.fetchone()[0]

        if total_urls_count < 50:
            continue
            # print(year[0], active_urls_count, total_urls_count)

        active_percentage = active_urls_count / total_urls_count * 100
        inactive_percentage = 100 - active_percentage

        valid_years.append(year[0])
        totalUrlsCountPerYear.append(total_urls_count)
        activeUrlsPercentagePerYear.append(active_percentage)
        inactiveUrlsPercentagePerYear.append(inactive_percentage)
    



    # add active count percentage rounded to 2 decimals (with label) in results.txt
    with open('visualization-outputs/results.txt', 'a') as f:
        f.write("\nActive percentages per year:\n")
        for i in range(len(valid_years)):
            f.write("%s: %s percent\n" % (valid_years[i], round(activeUrlsPercentagePerYear[i], 2)))
        f.write("\n")

    # Plotting the stacked bar chart
    fig, ax = plt.subplots(figsize=(20, 10))
    
    # The bottom bar is for active URLs
    ax.bar(valid_years, activeUrlsPercentagePerYear, label='Active URLs', color="white", edgecolor="black")
    
    # The top bar (stacked on the bottom bar) is for inactive URLs
    ax.bar(valid_years, inactiveUrlsPercentagePerYear, bottom=activeUrlsPercentagePerYear, label='Inactive URLs', visible=False)
    
    ax.set_xticks(valid_years)
    ax.set_xticklabels(valid_years, rotation=45, fontsize=25)
    ax.set_ylabel('Active URL Percentage (%)', fontsize=30)
    ax.set_ylim(0, 100)  # Set the y-axis limit to 100%
    ax.tick_params(axis='y', labelsize=25)
    ax.set_title('Active URLs Percentage per Year', fontsize=30)
    # ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.13), fontsize=30)

    # Adding second Y axis for total URL count
    ax2 = ax.twinx()

    # sort valid years and total URL count per year in ascending order
    valid_years, totalUrlsCountPerYear = zip(*sorted(zip(valid_years, totalUrlsCountPerYear)))


    ax2.plot(valid_years, totalUrlsCountPerYear, color='black', marker='o', label='Total URLs', linewidth=2)
    ax2.set_ylabel('Total URL Count', fontsize=30,  labelpad=25)
    # Let matplotlib automatically determine the best y-ticks
    ax2.set_ylim(0, max(totalUrlsCountPerYear)*1.1)  # Set upper limit to 110% of your max value for some margin


    ax2.tick_params(axis='y', labelsize=25)  # Adjust tick parameters and font size
    ax2.legend(loc='upper left', fontsize=25)
    
    ax.spines['right'].set_visible(False)
    ax.spines['top'].set_visible(False)

    plt.tight_layout()
    fig.savefig('visualization-outputs/activeVsInactiveUrlsPerYear.pdf', dpi=300)
    plt.show()
# Note: The function now only considers and displays years that have URLs associated with them.



def generate_http_error_distribution_horizontal_bar_chart(cursor):
    # Mapping of HTTP status codes to their descriptions

    # Retrieve HTTP Error records from the urls table
    cursor.execute("SELECT status_code, COUNT(*) FROM urls WHERE active = false GROUP BY status_code HAVING status_code IS NOT NULL;")
    http_errors = cursor.fetchall()

    # Sort the errors by count
    sorted_errors = sorted(http_errors, key=lambda x: x[1], reverse=True)

    # Take top 5 errors
    top_5_errors = sorted_errors[:5]

    # Calculate total errors count
    total_errors = sum([error[1] for error in sorted_errors])

    # Calculate percentages for top 5 errors
    top_5_percentages = [(error[0], (error[1] / total_errors) * 100) for error in top_5_errors]

    # Combine counts of all other errors into the "Other" category
    other_errors_count = total_errors - sum([error[1] for error in top_5_errors])
    other_percentage = (other_errors_count / total_errors) * 100

    # Add the "Other" category to the list
    percentages = top_5_percentages + [('Other', other_percentage)]

    # Extract labels and sizes for plotting. If the status code is recognized, use its description.
    labels = [f"{http_status_descriptions.get(int(error[0]), str(error[0]))} \n ({error[0]})" if error[0] != 'Other' else 'Other' for error in percentages]
    sizes = [error[1] for error in percentages]

    # add active count percentage rounded to 2 decimals (with labels) in results.txt
    with open('visualization-outputs/results.txt', 'a') as f:
        f.write("HTTP Error Distribution:\n")
        for i in range(len(labels)):
            f.write("%s: %s percent\n" % (labels[i], round(sizes[i], 2)))
        f.write("\n")

    # Plotting the horizontal bar chart
    fig, ax = plt.subplots(figsize=(12, 8))
    
    
    ax.barh(labels, sizes, color="white", edgecolor="black")
    ax.set_xticklabels([0, 10, 20, 30, 40, 50, 60, 70], fontsize=15)
    ax.set_yticklabels(labels, fontsize=20)
    ax.set_xlabel('Distribution (%)', fontsize=22)
    ax.set_title("HTTP Error Distribution", fontsize=22)
    ax.invert_yaxis()  # Display the bar with the highest percentage at the top
    
    ax.spines['right'].set_visible(False)
    ax.spines['top'].set_visible(False)

    plt.tight_layout()
    fig.savefig('visualization-outputs/httpErrorDistributionHorizontalBarPercentage.pdf', dpi=300)
    plt.show()



# 
def generate_network_error_distribution_horizontal_bar_chart(cursor):
    # Retrieve Network Error records from the urls table
    cursor.execute("SELECT network_error, COUNT(*) FROM urls WHERE active = false GROUP BY network_error HAVING network_error IS NOT NULL;")
    network_errors = cursor.fetchall()

    # Sort the errors by count
    sorted_errors = sorted(network_errors, key=lambda x: x[1], reverse=True)

    # Take top 5 errors
    top_5_errors = sorted_errors[:5]

    # Calculate total errors count
    total_errors = sum([error[1] for error in sorted_errors])

    # Combine counts of all other errors into the "Other" category
    other_errors_count = total_errors - sum([error[1] for error in top_5_errors])

    # Add the "Other" category to the list
    counts = top_5_errors + [('Other', other_errors_count)]

    # Extract labels and sizes for plotting
    labels = [f"{curl_error_mapping.get(int(error[0]), str(error[0]))} \n ({error[0]})" if error[0] != 'Other' else 'Other' for error in counts]
    sizes = [(error[1] / total_errors) * 100 for error in counts]  # percentages

    # add active count percentage rounded to 2 decimals (with labels) in results.txt
    with open('visualization-outputs/results.txt', 'a') as f:
        f.write("Network error distribution: \n")
        for i in range(len(labels)):
            f.write("%s: %s percent\n" % (labels[i], round(sizes[i], 2)))
        f.write("\n")


# Plotting the horizontal bar chart
    fig, ax = plt.subplots(figsize=(12, 8))
        
    ax.barh(labels, sizes, color="white", edgecolor="black",)  # Set the bar color to black
    ax.set_xticklabels([0, 10, 20, 30, 40, 50, 60, 70], fontsize=15)
    ax.set_yticklabels(labels, fontsize=20)
    ax.set_xlabel('Distribution (%)', fontsize=22)
    ax.set_title("Network Error Distribution", fontsize=22)
    ax.invert_yaxis()  # Display the bar with the highest percentage at the top
    
    ax.spines['right'].set_visible(False)
    ax.spines['top'].set_visible(False)

    plt.tight_layout()
    fig.savefig('visualization-outputs/networkErrorDistributionHorizontalBar.pdf', dpi=300)
    plt.show()

def generate_success_rate_per_protocol(cursor):
    # Retrieve Failing URL records per Protocol from the urls table
    cursor.execute("""
        SELECT SUBSTRING(u.url FROM '^(.*?):') AS protocol,
            COUNT(u.id) AS total_urls,
            SUM(CASE WHEN u.active = true THEN 1 ELSE 0 END) AS active_urls,
            (SUM(CASE WHEN u.active = true THEN 1 ELSE 0 END)::decimal / COUNT(u.id)) * 100 AS success_rate
        FROM urls u
        GROUP BY protocol
        HAVING SUBSTRING(u.url FROM '^(.*?):') IS NOT NULL;
    """)

    protocol_stats = cursor.fetchall()

    # Sorting protocols by success rate
    sorted_protocols = sorted(protocol_stats, key=lambda x: x[3], reverse=True)
    # only keep http and https
    sorted_protocols = [protocol for protocol in sorted_protocols if protocol[0] in ['http', 'https']]

    # print the success rate per protocol (with label) in results.txt
    with open('visualization-outputs/results.txt', 'a') as f:
        f.write("\nSuccess rate per protocol:\n")
        for i in range(len(sorted_protocols)):
            f.write("%s: %s percent\n" % (sorted_protocols[i][0], round(sorted_protocols[i][3], 2)))
        f.write("\n")



def generate_success_percentage_per_tld_horizontal_bar_chart(cursor):
    cursor.execute("""
        SELECT u.url, u.active
        FROM urls u;
    """)
    all_urls = cursor.fetchall()

    tld_stats = {}
    
    for url, is_active in all_urls:
        domain = tldextract.extract(url)
        tld = domain.suffix
        if tld:
            if tld not in tld_stats:
                tld_stats[tld] = {'total': 0, 'successful': 0}
            tld_stats[tld]['total'] += 1
            if is_active:
                tld_stats[tld]['successful'] += 1

    success_percentages = {}
    for tld, stats in tld_stats.items():
        if stats['total'] > 50:
            success_percent = (stats['successful'] / stats['total']) * 100
            success_percentages[tld] = success_percent

    sorted_tlds = sorted(success_percentages.items(), key=lambda x: x[1], reverse=True)
    top_10_tlds = dict(sorted_tlds[:10])

    labels = [f"{tld}\n({tld_stats[tld]['total']})" for tld in top_10_tlds.keys()]
    sizes = list(top_10_tlds.values())

    with open('visualization-outputs/results.txt', 'a') as f:
        f.write("\Success percentages per TLD:\n")
        for i in range(len(labels)):
            f.write("%s: %s percent\n" % (labels[i], round(sizes[i], 2)))
        f.write("\n")

    fig, ax = plt.subplots(figsize=(12, 10))
    ax.barh(labels, sizes, color="white", edgecolor="black")
    ax.set_xlabel('Success Percentage (%)', fontsize=15)
    ax.set_title("Success Percentage per Top-Level Domain (TLD)", fontsize=15)
    ax.invert_yaxis()
    ax.spines['right'].set_visible(False)
    ax.spines['top'].set_visible(False)

    plt.tight_layout()
    fig.savefig('visualization-outputs/successPercentagePerTLDHorizontalBar_withLabelCounts.pdf', dpi=300)
    plt.show()

# Mock test (without executing due to environment limitations)
# generate_fail_percentage_per_tld_horizontal_bar_chart_with_label_counts(cursor_mock())





def plot_url_counts_vs_broken_urls(cursor):
    # Retrieve paper and URL information from the tables
    cursor.execute("""
        SELECT papers.id, COUNT(urls.id) AS url_count, COUNT(CASE WHEN urls.active = FALSE THEN 1 END) AS broken_url_count
        FROM papers
        LEFT JOIN paper_urls ON paper_urls.paper_id = papers.id
        LEFT JOIN urls ON urls.id = paper_urls.url_id
        GROUP BY papers.id;
    """)
    paper_url_data = cursor.fetchall()

    # Extract URL counts and broken URL counts from the retrieved data
    url_counts = [data[1] for data in paper_url_data]
    broken_url_counts = [data[2] for data in paper_url_data]


    # Plotting the scatter plot
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.scatter(url_counts, broken_url_counts, alpha=0.2, color="black")  # Set the scatter plot points to black
    ax.set_xticklabels([0, 10, 20, 30, 40, 50, 60, 70, 80], fontsize=15)
    ax.set_yticklabels([0, 5, 10, 15, 20, 25, 30, 35], fontsize=15)
    ax.set_xlabel('URL Count', fontsize=15)
    ax.set_ylabel('Inactive URL Count', fontsize=15)
    ax.set_title('URL Counts vs Inactive URLs per Paper', fontsize=15)
    
    ax.spines['right'].set_visible(False)
    ax.spines['top'].set_visible(False)

    plt.tight_layout()
    fig.savefig('visualization-outputs/url_counts_vs_broken_urls_scatter.pdf', dpi=300)
    plt.show()






def calculate_half_life(cursor):
    # Get distinct years from the papers table
    cursor.execute("SELECT DISTINCT year FROM papers;")
    years = cursor.fetchall()
    current_year = datetime.datetime.now().year
    half_lives = []
    

    for year in years:
        # Get the count of active and total URLs for the current year
        cursor.execute("""
            SELECT COUNT(DISTINCT urls.id)
            FROM papers
            JOIN paper_urls ON paper_urls.paper_id = papers.id
            JOIN urls ON urls.id = paper_urls.url_id
            WHERE papers.year = %s;
        """, (year[0],))
        total_urls_count = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(DISTINCT urls.id)
            FROM papers
            JOIN paper_urls ON paper_urls.paper_id = papers.id
            JOIN urls ON urls.id = paper_urls.url_id
            WHERE papers.year = %s
            AND urls.active = TRUE;
        """, (year[0],))
        active_urls_count = cursor.fetchone()[0]

        

        # Calculate the half-life based on the active and total URLs count
        if total_urls_count > 0:
            # If there are no active URLs, set the active URLs count to 1 to avoid ln(0)
            if active_urls_count == 0:
                active_urls_count = 0.00000001

            # t(h) = [t * ln(0.5)] / [ln(W(t)) - ln(W(0))]
            half_life = ((current_year - year[0]) * math.log(0.5)) / (math.log(active_urls_count / total_urls_count) - math.log(1))
            half_lives.append(half_life)
        
    mean_half_life = statistics.mean(half_lives)

    # add half life (with label) in results.txt
    with open('visualization-outputs/results.txt', 'a') as f:
        f.write("\nHalf life:\n")
        f.write("%s\n" % round(mean_half_life, 2))
        f.write("\n")

    return mean_half_life


def export_all_failed_domains_to_file(cursor, file_path="./visualization-outputs/all_failed_domains_stats.csv"):
    # Retrieve all URLs and their active status
    cursor.execute("""
        SELECT url, active
        FROM urls;
    """)
    all_urls = cursor.fetchall()

    domain_stats = {}

    # Extract domain from each URL, count occurrences, and track active status
    for url, is_active in all_urls:
        domain = tldextract.extract(url).registered_domain
        if domain:
            if domain not in domain_stats:
                domain_stats[domain] = {'total': 0, 'active': 0, 'failed': 0}
            domain_stats[domain]['total'] += 1
            if is_active:
                domain_stats[domain]['active'] += 1
            else:
                domain_stats[domain]['failed'] += 1

    # Calculate active percentage for each domain
    for domain, stats in domain_stats.items():
        stats['active_percentage'] = (stats['active'] / stats['total']) * 100

    # Sorting domains by failed count
    sorted_domains = sorted(domain_stats.items(), key=lambda x: x[1]['failed'], reverse=True)

    # Writing to CSV file
    with open(file_path, 'w', newline='') as csvfile:
        fieldnames = ['Domain', 'Total URLs', 'Failed URLs', 'Active Percentage']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        for domain, stats in sorted_domains:
            writer.writerow({
                'Domain': domain,
                'Total URLs': stats['total'],
                'Failed URLs': stats['failed'],
                'Active Percentage': f"{stats['active_percentage']:.2f}%"
            })

    return file_path

# This function will export all domain data to a CSV file and return the path to the file.

def visualize_top_failed_domains_from_csv(file_path, top_n=10):
    # Load the CSV file into a pandas DataFrame
    df = pd.read_csv(file_path)

    # Filter the top domains with the most failed URLs
    top_domains = df.head(top_n).copy()  # Explicitly create a copy to avoid warning
    top_domains.set_index('Domain', inplace=True)

    # Plotting the top domains with the most failed URLs
    fig1, ax1 = plt.subplots(figsize=(15, 10))
    top_domains['Failed URLs'].plot(kind='barh', color="white", edgecolor="black", ax=ax1)  # Using black color for bars
    ax1.invert_yaxis()  # This will display the domain with the highest count at the top
    ax1.set_xlabel('Number of Inactive URLs', fontsize=15)
    ax1.set_title(f'Top {top_n} Domains with the Most Inactive URLs', fontsize=15)
    plt.tight_layout()
    fig1.savefig('visualization-outputs/top_failed_domains_chart.pdf', dpi=300)
    plt.show()

    # Calculating the failure percentage for each domain
    top_domains['Failure Percentage'] = (top_domains['Failed URLs'] / top_domains['Total URLs']) * 100



    # add number of failed urls and failure percentage (with label) in results.txt
    with open('visualization-outputs/results.txt', 'a') as f:
        f.write("Domain: (Number of inactive URLs, Inactivity Percentage)\n")
        for i in range(len(top_domains)):
            f.write("%s: (%s, %s percent)\n" % (top_domains.index[i], top_domains['Failed URLs'].iloc[i], round(top_domains['Failure Percentage'].iloc[i], 2)))
        f.write("\n")

    # Plotting the failure percentage for each domain
    fig2, ax2 = plt.subplots(figsize=(15, 12))
    bars = top_domains['Failure Percentage'].plot(kind='barh', color="white", edgecolor="black", ax=ax2)  # Using black color for bars
    ax2.invert_yaxis()  # This will display the domain with the highest failure percentage at the top
    ax2.set_xticklabels([0, 20, 40, 60, 80, 100], fontsize=18)
    ax2.set_xlabel('Failure Percentage (%)', fontsize=25)
    ax2.set_title(f'Failure Percentages for Top {top_n} Domains', fontsize=25)
    

    plt.tight_layout()
    new_labels = [f"{label}\n ({top_domains['Total URLs'].iloc[i]})" for i, label in enumerate(top_domains.index)]
    ax2.set_yticklabels(new_labels, fontsize=18)

    fig2.savefig('visualization-outputs/top_failed_domains_failure_percentages_chart.pdf', dpi=300)
    plt.show()

# The function has been fixed to avoid the pandas warning and will visualize both the top failed domains 
# and their corresponding failure percentages.



# MAIN FUNCTION
try:
    connection = psycopg2.connect(**params)
    cursor = connection.cursor()
    
    generate_active_inactive_urls_stacked_bar_chart_with_counts(cursor)
    generate_urls_section_stacked_bar_chart_with_counts(cursor)
    generate_active_urls_per_conference_stacked_bar_chart(cursor)
    generate_active_urls_per_year_stacked_bar_chart(cursor)
    generate_http_error_distribution_horizontal_bar_chart(cursor)
    generate_network_error_distribution_horizontal_bar_chart(cursor)
    generate_success_rate_per_protocol(cursor)
    generate_success_percentage_per_tld_horizontal_bar_chart(cursor)
    plot_url_counts_vs_broken_urls(cursor)
    print("Half-life:", calculate_half_life(cursor))
    export_all_failed_domains_to_file(cursor)
    visualize_top_failed_domains_from_csv('visualization-outputs/all_failed_domains_stats.csv', top_n=20)

except (Exception, psycopg2.DatabaseError) as error:
    print("ERROR:", error)
finally:
    if connection is not None:
        connection.close()
