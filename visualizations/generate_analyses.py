# Imports
import psycopg2
import matplotlib.pyplot as plt
import matplotlib as mpl
import sys
import tldextract
import math
import datetime
import statistics
import csv
import pandas as pd
import seaborn as sns
from matplotlib.ticker import MultipleLocator

from error_mappings import curl_error_mapping, http_status_descriptions

sys.path.append('../')
from globalFunctions import *
params = config(filename='../database-setup/database.ini', section='postgresql')

sns.set_style("white")


# Turn on grid by default...
mpl.rcParams['axes.grid'] = True
# ...but only along the y-axis
mpl.rcParams['axes.grid.axis'] = 'y'
mpl.rcParams['grid.color']      = 'lightgray'
mpl.rcParams['grid.linestyle']  = '-'
mpl.rcParams['grid.linewidth']  = 0.5
# set axes below
mpl.rcParams['axes.axisbelow'] = True
# disable spines
mpl.rcParams['axes.spines.right'] = False
mpl.rcParams['axes.spines.top'] = False
mpl.rcParams['axes.spines.left'] = True
mpl.rcParams['axes.spines.bottom'] = True


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
    
    
    categories = ["Version Control", "Archival", "Other"]
    active_counts = []
    inactive_counts = []
    total_counts = []

    cursor.execute("SELECT * FROM urls WHERE active IS NOT NULL;")
    all_urls = cursor.fetchall()

    def calculate_percentages_and_counts(urls):
        active = sum(1 for url in urls if url[2])
        inactive = len(urls) - active
        active_percentage = (active / len(urls)) * 100
        inactive_percentage = (inactive / len(urls)) * 100
        return active_percentage, inactive_percentage, len(urls)


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

    # Other URLs
    other_urls = [url for url in all_urls if not is_version_control_url(url[1]) and not is_archival_url(url[1])]
    active_percentage, inactive_percentage, count = calculate_percentages_and_counts(other_urls)
    active_counts.append(active_percentage)
    inactive_counts.append(inactive_percentage)
    total_counts.append(count)


    # Plotting the stacked bar chart
    fig, ax = plt.subplots(figsize=(8,6))
    

    # add active count percentage (rounded to 2 decimals) (with label) in results.txt
    with open('results/results.txt', 'w') as f:
        f.write("Active percentages:\n")
        f.write("Version Control URLs: %s percent\n" % round(active_counts[0], 2))
        f.write("Archival URLs: %s percent\n" % round(active_counts[1], 2))
        f.write("Other URLs: %s percent\n" % round(active_counts[2], 2))

        f.write("\n")
        


    bars_active = ax.bar(categories, active_counts, label='Active', color="#7fcdbb",  hatch='..', edgecolor="black")
    bars_inactive = ax.bar(categories, inactive_counts, bottom=active_counts, label='Inactive', color="white", edgecolor="black")

    # Annotate with the number of URLs below the x-axis labels
    for i, rect in enumerate(bars_active):
        ax.text(rect.get_x() + rect.get_width()/2., -14 ,  # Adjusted y-coordinate to position below x-axis
                '(%s)' % (int(total_counts[i])),
                ha='center', va='bottom', fontsize=20)

    
    ax.set_xticklabels(categories, fontsize=20)
    ax.set_yticklabels([0, 20, 40, 60, 80, 100], fontsize=20)
    ax.set_ylabel('URL Percentage (%)', fontsize=20)
    # ax.set_title('Active and Inactive URLs', fontsize=15)
    # ax.legend(loc='center left', bbox_to_anchor=(1, 0.5), fontsize=15)
    ax.spines['right'].set_visible(False)
    ax.spines['top'].set_visible(False)

    plt.tight_layout()
    plt.show()
    fig.savefig('results/activeInactiveUrls_with_counts.pdf', dpi=300)


def generate_urls_section_stacked_bar_chart_with_counts(cursor):
    
    
    categories = ["Abstract", "Citation", "Body"]
    active_counts = []
    inactive_counts = []
    total_counts = []

    cursor.execute("SELECT * FROM urls WHERE active IS NOT NULL;")
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
    with open('results/results.txt', 'a') as f:
        f.write("Active percentages:\n")
        f.write("Abstract URLs: %s percent\n" % round(active_counts[0], 2))
        f.write("Citation URLs: %s percent\n" % round(active_counts[1], 2))
        f.write("Body URLs: %s percent\n" % round(active_counts[2], 2))
        f.write("\n")
        


    bars_active = ax.bar(categories, active_counts, label='Active', color="#7fcdbb",  hatch='..', edgecolor="black")
    bars_inactive = ax.bar(categories, inactive_counts, bottom=active_counts, label='Inactive', color="white", edgecolor="black")

    # Annotate with the number of URLs below the x-axis labels
    for i, rect in enumerate(bars_active):
        ax.text(rect.get_x() + rect.get_width()/2., -14 ,  # Adjusted y-coordinate to position below x-axis
                '(%s)' % (int(total_counts[i])),
                ha='center', va='bottom', fontsize=20)

    
    ax.set_xticklabels(categories, fontsize=20)
    ax.set_yticklabels([0, 20, 40, 60, 80, 100], fontsize=20)
    ax.set_ylabel('URL Percentage (%)', fontsize=20)
    # ax.set_title('Active and Inactive URLs', fontsize=15)
    # ax.legend(loc='center left', bbox_to_anchor=(1, 0.5), fontsize=15)
    ax.spines['right'].set_visible(False)
    ax.spines['top'].set_visible(False)

    plt.tight_layout()
    plt.show()
    fig.savefig('results/activeInactiveUrls_by_section.pdf', dpi=300)


def generate_active_inactive_urls_combined(cursor):
    """
    Creates a combined figure with two subplots:
      (a) Overall active/inactive % for All, VCS, Archival URLs
      (b) Active/inactive % by section: Abstract, Citation, Body
    Annotates each bar with the total URL counts below the x-axis.
    Saves the result as 'activeInactiveUrls_combined.pdf'.
    """

    

    # -- Helper to compute percentages & counts --
    def pct_and_count(urls):
        total = len(urls)
        active = sum(1 for url in urls if url[2])
        inactive = total - active
        return (active / total * 100,
                inactive / total * 100,
                total)

    # -- Fetch all URLs once --
    cursor.execute("SELECT * FROM urls WHERE active IS NOT NULL;")
    all_urls = cursor.fetchall()

    # -- Prepare data for subplot (a): Overall --
    cats_overall = ["All", "Version Control", "Archival"]
    lists_overall = [
        all_urls,
        [u for u in all_urls if is_version_control_url(u[1])],
        [u for u in all_urls if is_archival_url(u[1])]
    ]
    act_o, inact_o, tot_o = zip(*(pct_and_count(lst) for lst in lists_overall))

    # -- Prepare data for subplot (b): By section --
    cats_sec = ["Abstract", "Citation", "Body"]
    abstract = [u for u in all_urls if u[5] == "abstract"]
    citation = [u for u in all_urls if u[5] == "citations"]
    body     = [u for u in all_urls if u[5] not in ("abstract", "citations")]
    act_s, inact_s, tot_s = zip(*(pct_and_count(lst)
                                  for lst in (abstract, citation, body)))

    # -- Log both tables in one file write --
    with open('results/results.txt', 'w') as f:
        f.write("=== Overall Active % ===\n")
        for cat, a, t in zip(cats_overall, act_o, tot_o):
            f.write(f"{cat}: {round(a,2)}% ({t} URLs)\n")
        f.write("\n=== By Section Active % ===\n")
        for cat, a, t in zip(cats_sec, act_s, tot_s):
            f.write(f"{cat}: {round(a,2)}% ({t} URLs)\n")
        f.write("\n")

    # -- Build the figure with two subplots --
    fig, (ax0, ax1) = plt.subplots(1, 2, figsize=(16, 9), sharey=True)
    fig.subplots_adjust(wspace=5)

    # Subplot (a)
    ax0.bar(cats_overall, act_o,     label='Active',   color="#7fcdbb", hatch='..', edgecolor="black")
    ax0.bar(cats_overall, inact_o,    bottom=act_o,  label='Inactive', color="white",     edgecolor="black")
    ax0.set_title("(a) Overall URLs", loc='left', fontsize=25, pad=20)
    ax0.set_xticklabels(cats_overall, fontsize=25)
    ax0.set_ylabel('URL Percentage (%)', fontsize=25)
    ax0.tick_params(axis='y', labelsize=25)
    # ax0.legend(fontsize=25, loc='upper left')

    # Annotate totals below x-axis
    for i, (bar, tot) in enumerate(zip(ax0.patches[:3], tot_o)):
        x = bar.get_x() + bar.get_width() / 2
        ax0.text(x, -12, f"({tot})", ha='center', va='bottom', fontsize=25)

    # Subplot (b)
    ax1.bar(cats_sec, act_s,     label='Active',   color="#7fcdbb", hatch='..', edgecolor="black")
    ax1.bar(cats_sec, inact_s,    bottom=act_s,  label='Inactive', color="white",     edgecolor="black")
    ax1.set_title("(b) URLs by Section", loc='left', fontsize=25, pad=20)
    ax1.set_xticklabels(cats_sec, fontsize=25)
    ax1.tick_params(axis='y', labelsize=25)
    # ax1.legend(fontsize=10, loc='upper left')

    for i, (bar, tot) in enumerate(zip(ax1.patches[3:], tot_s)):
        x = bar.get_x() + bar.get_width() / 2
        ax1.text(x, -12, f"({tot})", ha='center', va='bottom', fontsize=25)

    # Common formatting
    for ax in (ax0, ax1):
        ax.spines['right'].set_visible(False)
        ax.spines['top'].set_visible(False)
        ax.set_ylim(0, 100)      # make room for annotations below
        ax.set_yticks([0,20,40,60,80,100])

    plt.tight_layout()
    fig.savefig('results/activeInactiveUrls_combined.pdf', dpi=300)
    plt.show()



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
    with open('results/results.txt', 'a') as f:
        f.write("\nActive percentages per venue:\n")
        for i in range(len(conf_names)):
            f.write("%s: %s percent\n" % (conf_names[i], round(activeUrlsPercentage[i], 2)))
        f.write("\n")

    # Plotting the stacked bar chart
    fig, ax = plt.subplots(figsize=(20, 10))
    
    # The bottom bar is for active URLs
    ax.bar(conf_names, activeUrlsPercentage, label='Active URLs', color="#7fcdbb", edgecolor="black")
    
    # The top bar (stacked on the bottom bar) is for inactive URLs
    ax.bar(conf_names, inactiveUrlsPercentage, bottom=activeUrlsPercentage, label='Inactive URLs', visible=False)
    
    ax.set_xticklabels(conf_names, rotation=45, fontsize=15)
    ax.set_ylabel('URL Percentage (%)', fontsize=15)
    ax.set_title('Active vs Inactive URLs percentage per conference', fontsize=15)
    ax.legend(loc='center left', bbox_to_anchor=(1, 0.5), fontsize=15)
    
    ax.spines['right'].set_visible(False)
    ax.spines['top'].set_visible(False)

    plt.tight_layout()
    fig.savefig('results/activeVsInactiveUrlsPerConf.pdf', dpi=300)
    plt.show()

def generate_active_urls_per_year_stacked_bar_chart(cursor):
    # Retrieve unique years from the papers table
    cursor.execute("SELECT DISTINCT year FROM papers;")
    years = cursor.fetchall()

    activeUrlsPercentagePerYear = []
    inactiveUrlsPercentagePerYear = []
    medianUrlsPerPaperPerYear = []
    totalUrlsCountPerYear = []  # to store total URLs count per year
    totalPapersPerYear = []  # to store total papers count per year
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
        
        # Calculate the median number of URLs per paper
        cursor.execute("""
            SELECT p.id AS paper_id, COUNT(pu.url_id) AS url_count
            FROM papers p
            JOIN paper_urls pu ON p.id = pu.paper_id
            WHERE p.year = %s
            GROUP BY p.id;
        """, (year[0],))
        all_rows = cursor.fetchall()

        urls_per_paper = [row[1] for row in all_rows]

        # Calculate total papers per year
        total_papers = len(urls_per_paper)

        median_url_count = statistics.median(urls_per_paper)

        active_percentage = active_urls_count / total_urls_count * 100
        inactive_percentage = 100 - active_percentage

        valid_years.append(year[0])
        totalUrlsCountPerYear.append(total_urls_count)
        activeUrlsPercentagePerYear.append(active_percentage)
        inactiveUrlsPercentagePerYear.append(inactive_percentage)
        medianUrlsPerPaperPerYear.append(median_url_count)
        totalPapersPerYear.append(total_papers)
    



    # add active count percentage rounded to 2 decimals (with label) in results.txt
    with open('results/results.txt', 'a') as f:
        f.write("\nActive percentages per year:\n")
        for i in range(len(valid_years)):
            f.write("%s: %s percent, %s total Papers, %s total URLs, %s median URLs per paper\n" % (valid_years[i], round(activeUrlsPercentagePerYear[i], 2), totalPapersPerYear[i], totalUrlsCountPerYear[i], medianUrlsPerPaperPerYear[i]))
        f.write("\n")

    # Plotting the stacked bar chart
    fig, ax = plt.subplots(figsize=(20, 10))
    # ax.set_axisbelow(True)
    # ax.yaxis.grid(True, which='major', linestyle='-', linewidth=0.8, alpha=0.7)

    # The bottom bar is for active URLs
    ax.bar(valid_years, activeUrlsPercentagePerYear, label='Active URLs', color="#7fcdbb", edgecolor="black")
    
    # The top bar (stacked on the bottom bar) is for inactive URLs
    ax.bar(valid_years, inactiveUrlsPercentagePerYear, bottom=activeUrlsPercentagePerYear, label='Inactive URLs', visible=False)
    
    ax.set_xticks(valid_years)
    ax.set_xticklabels(valid_years, rotation=45, fontsize=25)
    ax.set_ylabel('Active URL Percentage (%)', fontsize=30)
    ax.set_ylim(0, 100)  # Set the y-axis limit to 100%
    # Show y lines
    ax.yaxis.set_major_locator(MultipleLocator(20))  # Set y-ticks at intervals of 20
    ax.tick_params(axis='y', labelsize=25)
    # ax.set_title('Active URLs Percentage per Year', fontsize=30)
    # ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.13), fontsize=30)

    # Adding second Y axis for total URL count
    ax2 = ax.twinx()
    ax2.grid(False)       
    # sort valid years and total URL count per year in ascending order
    valid_years_copy = valid_years.copy()
    valid_years_copy, totalUrlsCountPerYear, totalPapersPerYear, medianUrlsPerPaperPerYear = zip(*sorted(zip(valid_years_copy, totalUrlsCountPerYear, totalPapersPerYear, medianUrlsPerPaperPerYear)))


    ax2.plot(valid_years_copy, medianUrlsPerPaperPerYear, color='black', marker='o', label='Median URLs', linewidth=2)
    ax2.set_ylabel('Median URLs per Paper', fontsize=30,  labelpad=25)
    # Let matplotlib automatically determine the best y-ticks
    ax2.set_ylim(0, max(medianUrlsPerPaperPerYear)*1.1)  # Set upper limit to 110% of your max value for some margin


    ax2.tick_params(axis='y', labelsize=25)  # Adjust tick parameters and font size
    ax2.legend(loc='upper left', fontsize=25)
    
    ax.spines['right'].set_visible(False)
    ax.spines['top'].set_visible(False)

    plt.tight_layout()
    fig.savefig('results/activeVsInactiveUrlsPerYear.pdf', dpi=300)
    



    fig_new, ax_new = plt.subplots(figsize=(20, 10))
    # ax_new.set_axisbelow(True)
    # ax_new.yaxis.grid(True, which='major', linestyle='-', linewidth=0.8, alpha=0.7)
    
    ax_new.bar(valid_years_copy, totalPapersPerYear, label='Total Papers', color="#7fcdbb", edgecolor="black")

    ax_new.set_xticks(valid_years_copy)
    ax_new.set_xticklabels(valid_years_copy, rotation=45, fontsize=25)
    ax_new.set_ylabel('Total Papers', fontsize=30)
    # ax_new.set_ylim(0, 100)  # Set the y-axis limit to 100%
    ax_new.tick_params(axis='y', labelsize=25)
    # ax_new.set_title('Papers and URLs per Year', fontsize=30)

    # # Total papers + median URLs per paper
    # ax2_new = ax_new.twinx()
    # ax2_new.plot(valid_years_copy, medianUrlsPerPaperPerYear, color='black', marker='o', label='Total Papers', linewidth=2)
    # ax2_new.set_ylabel('Median URLs per Paper', fontsize=30,  labelpad=25)
    # ax2_new.set_ylim(0, max(medianUrlsPerPaperPerYear)*1.1)  # Set upper limit to 110% of your max value for some margin
    # ax2_new.tick_params(axis='y', labelsize=25)  # Adjust tick parameters and font size
    # ax2_new.legend(loc='upper left', fontsize=25)
    # ax_new.spines['right'].set_visible(False)
    # ax_new.spines['top'].set_visible(False)

    # plt.tight_layout()
    # fig_new.savefig('results/totalPapersMedianURLPerPaperPerYear.pdf', dpi=300)

    # Total papers + total URLs
    ax3_new = ax_new.twinx()
    ax3_new.grid(False)  # Disable grid for the second y-axis
    ax3_new.plot(valid_years_copy, totalUrlsCountPerYear, color='black', marker='o', label='Total URLs', linewidth=2)
    ax3_new.set_ylabel('Total URLs', fontsize=30,  labelpad=25)
    ax3_new.set_ylim(0, 21250)  # Set to custom upper limit to scale, for visibility
    ax3_new.tick_params(axis='y', labelsize=25)  # Adjust tick parameters and font size
    ax3_new.legend(loc='upper left', fontsize=25)
    ax_new.spines['right'].set_visible(False)
    ax_new.spines['top'].set_visible(False)

    plt.tight_layout()
    fig_new.savefig('results/totalPapersTotalURLPerYear.pdf', dpi=300)



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
    with open('results/results.txt', 'a') as f:
        f.write("HTTP Error Distribution:\n")
        for i in range(len(labels)):
            f.write("%s: %s percent\n" % (labels[i], round(sizes[i], 2)))
        f.write("\n")

    # Plotting the horizontal bar chart
    fig, ax = plt.subplots(figsize=(12, 8))
    
    
    ax.barh(labels, sizes, color="#7fcdbb", edgecolor="black")
    ax.set_xticklabels([0, 10, 20, 30, 40, 50, 60, 70], fontsize=15)
    ax.set_yticklabels(labels, fontsize=20)
    ax.set_xlabel('Distribution (%)', fontsize=22)
    # ax.set_title("HTTP Error Distribution", fontsize=22)
    ax.invert_yaxis()  # Display the bar with the highest percentage at the top
    
    ax.spines['right'].set_visible(False)
    ax.spines['top'].set_visible(False)

    plt.tight_layout()
    fig.savefig('results/httpErrorDistributionHorizontalBarPercentage.pdf', dpi=300)
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
    with open('results/results.txt', 'a') as f:
        f.write("Network error distribution: \n")
        for i in range(len(labels)):
            f.write("%s: %s percent\n" % (labels[i], round(sizes[i], 2)))
        f.write("\n")


# Plotting the horizontal bar chart
    fig, ax = plt.subplots(figsize=(12, 8))
        
    ax.barh(labels, sizes, color="#7fcdbb", edgecolor="black",)  # Set the bar color to black
    ax.set_xticklabels([0, 10, 20, 30, 40, 50, 60, 70], fontsize=15)
    ax.set_yticklabels(labels, fontsize=20)
    ax.set_xlabel('Distribution (%)', fontsize=22)
    # ax.set_title("Network Error Distribution", fontsize=22)
    ax.invert_yaxis()  # Display the bar with the highest percentage at the top
    
    ax.spines['right'].set_visible(False)
    ax.spines['top'].set_visible(False)

    plt.tight_layout()
    fig.savefig('results/networkErrorDistributionHorizontalBar.pdf', dpi=300)
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
    with open('results/results.txt', 'a') as f:
        f.write("\nSuccess rate per protocol:\n")
        for i in range(len(sorted_protocols)):
            f.write("%s: %s percent\n" % (sorted_protocols[i][0], round(sorted_protocols[i][3], 2)))
        f.write("\n")



def generate_success_percentage_per_tld(cursor):
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
    # only keep tlds no second level domain
    sorted_tlds = [(tld, percent) for tld, percent in sorted_tlds if len(tld.split('.')) == 1]
    
    top_10_tlds = dict(sorted_tlds[:10])

    labels = [f"{tld}\n({tld_stats[tld]['total']})" for tld in top_10_tlds.keys()]
    sizes = list(top_10_tlds.values())

    with open('results/results.txt', 'a') as f:
        f.write("\nTop 10 success percentages per TLD:\n")
        for i in range(len(labels)):
            f.write("%s: %s percent\n" % (labels[i], round(sizes[i], 2)))
        f.write("\n")
        
    # include the 10 worse TLDs 
    bottom_10_tlds = dict(sorted_tlds[-10:])
    labels_bottom = [f"{tld}\n({tld_stats[tld]['total']})" for tld in bottom_10_tlds.keys()]
    sizes_bottom = list(bottom_10_tlds.values())
    with open('results/results.txt', 'a') as f:
        f.write("\nBottom 10 success percentages per TLD:\n")
        for i in range(len(labels_bottom)):
            f.write("%s: %s percent\n" % (labels_bottom[i], round(sizes_bottom[i], 2)))
        f.write("\n")

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

    # calclulate the median number of URLs per paper
    median_url_count = statistics.median(url_counts)
    # caluclate the mean number of URLs per paper
    mean_url_count = statistics.mean(url_counts)

    print("Median URL count per paper:", median_url_count)
    print("Mean URL count per paper:", mean_url_count)


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
    fig.savefig('results/url_counts_vs_broken_urls_scatter.pdf', dpi=300)
    plt.show()






def calculate_half_life(cursor):
    # Get distinct years from the papers table
    cursor.execute("SELECT DISTINCT year FROM papers;")
    years = cursor.fetchall()
    current_year = datetime.datetime.now().year
    half_lives = []
    persistence_with_age = []


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

        
        # print(year[0], active_urls_count, total_urls_count)
        # Calculate the half-life based on the active and total URLs count
        if total_urls_count > 0:
            # If there are no active URLs, set the active URLs count to 1 to avoid ln(0)
            if active_urls_count == 0:
                active_urls_count = 0.00000001

            # t(h) = [t * ln(0.5)] / [ln(W(t)) - ln(W(0))]
            # half_life = ((current_year - year[0]) * math.log(0.5)) / (math.log(active_urls_count / total_urls_count) - math.log(1))
            half_life = ((current_year - year[0]) * math.log(0.5)) / (math.log(active_urls_count) - math.log(total_urls_count))
            half_lives.append((year[0], half_life))
            persistence_with_age.append((year[0], (active_urls_count / total_urls_count) / (current_year - year[0])))
    
    # print(half_lives)

    half_lives = sorted(half_lives, key=lambda x: x[0])

    half_lives_years = [val[0] for val in half_lives]
    half_lives_values = [val[1] for val in half_lives]

    print(len(half_lives_years))
    print(len(half_lives_values))
    
    fig, ax = plt.subplots(figsize=(12, 10))
    
    ax.bar(half_lives_years, half_lives_values, color="#7fcdbb", edgecolor="black")
    ax.set_xlabel('Year', fontsize=15)
    ax.set_title("Half-life", fontsize=15)
    # ax.invert_yaxis()
    ax.spines['right'].set_visible(False)
    ax.spines['top'].set_visible(False)

    plt.tight_layout()
    fig.savefig('results/half_lives.pdf', dpi=300)
    plt.show()

    

    # calculate mean
    mean_half_life = statistics.mean(half_lives_values)

    persistence_with_age = sorted(persistence_with_age, key=lambda x: x[0])
    persistence_years = [val[0] for val in persistence_with_age]
    persistence_values = [val[1] for val in persistence_with_age]
    # Add another ax for (URL Active % / URL age) line plot

    fig, ax = plt.subplots(figsize=(12, 10))
    # ax2 = ax.twinx()
    # ax.plot(persistence_years, persistence_values, color='black', marker='o', label='Persistence', linewidth=2)
    # ax.set_ylabel('Persistence', fontsize=15)
    # # ax.set_ylim(0, 1)  # Set the y-axis limit to 100%
    # ax.tick_params(axis='y', labelsize=15)
    # ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.13), fontsize=15)
    # ax.spines['right'].set_visible(False)
    # ax.spines['top'].set_visible(False)

    ax.bar(half_lives_years, half_lives_values, color="#7fcdbb", edgecolor="black")
    ax.set_xlabel('Year', fontsize=15)
    ax.set_ylabel('Half-life', fontsize=15)
    ax.set_title("Half-life", fontsize=15)
    # ax.invert_yaxis()
    ax.spines['right'].set_visible(False)
    ax.spines['top'].set_visible(False)


    ax2 = ax.twinx()
    ax2.grid(False)  # Disable grid for the second y-axis
    ax2.plot(persistence_years, persistence_values, color='black', marker='o', label='Persistence', linewidth=2)
    # ax2.set_ylabel('Persistence', fontsize=15)
    # # ax2.set_ylim(0, 1)  # Set the y-axis limit to 100%
    # ax2.tick_params(axis='y', labelsize=15)
    # ax2.legend(loc='upper center', bbox_to_anchor=(0.5, -0.13), fontsize=15)
    # ax2.spines['right'].set_visible(False)
    # ax2.spines['top'].set_visible(False)



    plt.tight_layout()
    fig.savefig('results/half_lives_with_line.pdf', dpi=300)
    plt.show()

    # add half life (with label) in results.txt
    with open('results/results.txt', 'a') as f:
        f.write("\nHalf life:\n")
        f.write("%s\n" % round(mean_half_life, 2))
        f.write("\n")

    return mean_half_life


def export_all_failed_domains_to_file(cursor, file_path="./results/all_failed_domains_stats.csv"):

    
    # Retrieve all URLs and their active status
    cursor.execute("""
        SELECT url, active
        FROM urls
        WHERE active IS NOT NULL;
    """)
    all_urls = cursor.fetchall()

    domain_stats = {}


    # failing_domains = [ "acm.org","sciencedirect.com","ieee.org","nasa.gov","wiley.com","psu.edu","java.net","jstor.org","aclweb.org","uci.edu","uwaterloo.ca","scopus.com","berkeley.edu","hp.com","usc.edu","nytimes.com","nec.com","gmu.edu","etherscan.io","bham.ac.uk","twitter.com","umd.edu","uiuc.edu","utexas.edu","aaai.org","codeplex.com","tigris.org","springerlink.com","ic.ac.uk","gatech.edu","ncsu.edu","wm.edu","googlecode.com","toronto.edu","tue.nl","ethz.ch","virginia.edu","ucalgary.ca","mvnrepository.com","iastate.edu","uva.nl","researchgate.net","tiny.cc","msdn.com","af.mil","columbia.edu","queensu.ca","polymtl.ca","menzies.us","fbk.eu","epfl.ch","cwi.nl","tudelft.nl","princeton.edu","utah.edu","borland.com","tu-darmstadt.de","carleton.ca","upm.es","upv.es","soton.ac.uk","uvic.ca","irisa.fr",    ]

    # Extract domain from each URL, count occurrences, and track active status
    for url, is_active in all_urls:
        
        domain = tldextract.extract(url).registered_domain
        if(domain=="nasa.com"):
            print(domain)
        # if(domain in failing_domains and not is_active):
        #     # add it to failing urls.txt
        #     with open('results/failing_urls.txt', 'a') as f:
        #         f.write("%s\n" % url)
                
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
    top_domains['Failed URLs'].plot(kind='barh', color="#7fcdbb", edgecolor="black", ax=ax1)  # Using black color for bars
    ax1.invert_yaxis()  # This will display the domain with the highest count at the top
    ax1.set_xlabel('Number of Inactive URLs', fontsize=15)
    ax1.set_title(f'Top {top_n} Domains with the Most Inactive URLs', fontsize=15)
    plt.tight_layout()
    fig1.savefig('results/top_failed_domains_chart.pdf', dpi=300)
    plt.show()

    # Calculating the failure percentage for each domain
    top_domains['Failure Percentage'] = (top_domains['Failed URLs'] / top_domains['Total URLs']) * 100



    # add number of failed urls and failure percentage (with label) in results.txt
    with open('results/results.txt', 'a') as f:
        f.write("Domain: (Number of inactive URLs, Inactivity Percentage)\n")
        for i in range(len(top_domains)):
            f.write("%s: (%s, %s percent)\n" % (top_domains.index[i], top_domains['Failed URLs'].iloc[i], round(top_domains['Failure Percentage'].iloc[i], 2)))
        f.write("\n")

    # Plotting the failure percentage for each domain
    fig2, ax2 = plt.subplots(figsize=(15, 12))
    bars = top_domains['Failure Percentage'].plot(kind='barh', color="#7fcdbb", edgecolor="black", ax=ax2)  # Using black color for bars
    ax2.invert_yaxis()  # This will display the domain with the highest failure percentage at the top
    ax2.set_xticklabels([0, 20, 40, 60, 80, 100], fontsize=18)
    ax2.set_xlabel('Failure Percentage (%)', fontsize=25)
    ax2.set_title(f'Failure Percentages for Top {top_n} Domains', fontsize=25)
    

    plt.tight_layout()
    new_labels = [f"{label}\n ({top_domains['Total URLs'].iloc[i]})" for i, label in enumerate(top_domains.index)]
    ax2.set_yticklabels(new_labels, fontsize=18)

    fig2.savefig('results/top_failed_domains_failure_percentages_chart.pdf', dpi=300)
    plt.show()

def visualize_top_active_domains_from_csv(file_path, top_n=10, min_urls=50):
    """
    Reads a CSV of domains and URL statuses, filters to domains with at least `min_urls`,
    selects the top `top_n` domains by Active Percentage, and then:
      1. Plots a horizontal bar chart of active percentages (annotated with total URL counts).
      2. Saves the chart as a PDF.
      3. Appends a text summary of active counts and percentages to a results file.
    """
    # Load the CSV file into a pandas DataFrame
    df = pd.read_csv(file_path)

    # Filter domains by minimum total URLs
    df_filtered = df[df['Total URLs'] >= min_urls].copy()

    # Convert 'Active Percentage' from string (e.g., '88.87%') to float
    df_filtered['Active Percentage'] = (
        df_filtered['Active Percentage']
        .str.rstrip('%')
        .astype(float)
    )

    # Sort by active percentage descending and take top N
    top_active = (
        df_filtered
        .sort_values('Active Percentage', ascending=False)
        .head(top_n)
    )
    top_active.set_index('Domain', inplace=True)

    # Plotting the active percentage for each domain
    fig, ax = plt.subplots(figsize=(15, 12))
    ax.barh(
        top_active.index,
        top_active['Active Percentage'],
        color='#7fcdbb',
        edgecolor='black',
        linewidth=1
    )
    ax.invert_yaxis()  # Display the domain with the highest active % at the top

    # Configure x-axis ticks and labels
    ax.set_xticks([0, 20, 40, 60, 80, 100])
    ax.set_xticklabels([0, 20, 40, 60, 80, 100], fontsize=18)
    ax.set_xlabel('Active Percentage (%)', fontsize=25)
    ax.set_title(
        f'Top {top_n} Domains by Active Percentage (min {min_urls} URLs)',
        fontsize=25
    )

    # Annotate y-axis labels with total URL counts
    new_labels = [
        f"{domain}\n ({int(top_active.at[domain, 'Total URLs'])})"
        for domain in top_active.index
    ]
    ax.set_yticklabels(new_labels, fontsize=18)

    plt.tight_layout()
    fig.savefig('results/top_active_domains_chart.pdf', dpi=300)
    plt.show()

    # Append a summary to a text file
    with open('results/results.txt', 'a') as f:
        f.write(
            f"Top {top_n} domains by active percentage (min {min_urls} URLs):\n"
        )
        f.write("Domain: (Active URLs, Active Percentage%)\n")
        for domain in top_active.index:
            total = top_active.at[domain, 'Total URLs']
            failed = top_active.at[domain, 'Failed URLs']
            active_count = total - failed
            active_pct = top_active.at[domain, 'Active Percentage']
            f.write(
                f"{domain}: ({active_count}, {round(active_pct, 2)} percent)\n"
            )
            
        f.write("\n")

def visualize_bottom_active_domains_from_csv(file_path, bottom_n=10, min_urls=80):
    """
    Reads a CSV of domains and URL statuses, filters to domains with at least `min_urls`,
    selects the bottom `bottom_n` domains by Active Percentage, and then:
      1. Plots a horizontal bar chart of active percentages (annotated with total URL counts).
      2. Saves the chart as a PDF.
      3. Appends a text summary of active counts and percentages to a results file.
    """
    # Load the CSV file into a pandas DataFrame
    df = pd.read_csv(file_path)

    # Filter domains by minimum total URLs
    df_filtered = df[df['Total URLs'] >= min_urls].copy()

    # Convert 'Active Percentage' from string (e.g., '88.87%') to float
    df_filtered['Active Percentage'] = (
        df_filtered['Active Percentage']
        .str.rstrip('%')
        .astype(float)
    )

    # Sort by active percentage ascending and take bottom N
    bottom_active = (
        df_filtered
        .sort_values('Active Percentage', ascending=True)
        .head(bottom_n)
    )
    bottom_active.set_index('Domain', inplace=True)

    # Plotting the active percentage for each domain
    fig, ax = plt.subplots(figsize=(15, 12))
    ax.barh(
        bottom_active.index,
        bottom_active['Active Percentage'],
        color='#f03b20',  # Use a reddish color to signify poor performance
        edgecolor='black',
        linewidth=1
    )
    ax.invert_yaxis()  # Display the domain with the lowest active % at the top

    # Configure x-axis ticks and labels
    ax.set_xticks([0, 20, 40, 60, 80, 100])
    ax.set_xticklabels([0, 20, 40, 60, 80, 100], fontsize=18)
    ax.set_xlabel('Active Percentage (%)', fontsize=25)
    ax.set_title(
        f'Bottom {bottom_n} Domains by Active Percentage',
        fontsize=25
    )

    # Annotate y-axis labels with total URL counts
    new_labels = [
        f"{domain}\n ({int(bottom_active.at[domain, 'Total URLs'])})"
        for domain in bottom_active.index
    ]
    ax.set_yticklabels(new_labels, fontsize=18)

    plt.tight_layout()
    fig.savefig('results/bottom_active_domains_chart.pdf', dpi=300)
    plt.show()

    # Append a summary to a text file
    with open('results/results.txt', 'a') as f:
        f.write(
            f"Bottom {bottom_n} domains by active percentage:\n"
        )
        f.write("Domain: (Active URLs, Active Percentage%)\n")
        for domain in bottom_active.index:
            total = bottom_active.at[domain, 'Total URLs']
            failed = bottom_active.at[domain, 'Failed URLs']
            active_count = total - failed
            active_pct = bottom_active.at[domain, 'Active Percentage']
            f.write(
                f"{domain}: ({active_count}, {round(active_pct, 2)} percent)\n"
            )
        f.write("\n")


def generate_url_types_evolution_per_year(cursor):
    """
    Plots a 3-segment stacked bar chart per year (years with ≥50 URLs):
      • VCS URLs
      • Archival URLs
      • Other URLs  = Total − (VCS + Archival)
    Saves the plot as 'urlTypesEvolutionPerYear_3segment.pdf'.
    """

    

    # 1) Fetch & filter years
    cursor.execute("SELECT DISTINCT year FROM papers;")
    all_years = sorted(r[0] for r in cursor.fetchall())

    valid_years = []
    vc_counts, arch_counts, total_counts = [], [], []

    for year in all_years:
        cursor.execute("""
            SELECT DISTINCT u.id, u.url
            FROM papers p
            JOIN paper_urls pu ON pu.paper_id = p.id
            JOIN urls u ON u.id = pu.url_id
            WHERE p.year = %s;
        """, (year,))
        rows = cursor.fetchall()
        total = len(rows)
        if total < 50:
            continue

        vc   = sum(1 for _, url in rows if is_version_control_url(url))
        arch = sum(1 for _, url in rows if is_archival_url(url))

        valid_years.append(year)
        vc_counts.append(vc)
        arch_counts.append(arch)
        total_counts.append(total)

    # 2) Compute the “Other” slice
    other_counts = [t - v - a for t, v, a in zip(total_counts, vc_counts, arch_counts)]

    # 3) (Optional) Log values
    with open('results/results.txt', 'a') as f:
        f.write("\n3-Segment URL Types per Year:\n")
        for y, v, a, o, t in zip(valid_years, vc_counts, arch_counts, other_counts, total_counts):
            f.write(f"{y}: VCS={v}, Archival={a}, Other={o}, Total={t}\n")
        f.write("\n")

    # 4) Plot
    fig, ax = plt.subplots(figsize=(20, 10))
    ax.bar(valid_years,
           vc_counts,
           label='VCS URLs',
           color='#7fcdbb',
           edgecolor='black')
    
    ax.bar(valid_years,
           arch_counts,
           bottom=vc_counts,
           label='Archival URLs',
           color='#3690c0',
           edgecolor='black')
    
    ax.bar(valid_years,
           other_counts,
           bottom=[v + a for v, a in zip(vc_counts, arch_counts)],
           label='Other URLs',
           color='#f7fcb9',
           edgecolor='black')

    # 5) Annotate total on top of each bar
    # for x, t in zip(valid_years, total_counts):
    #     ax.text(x,
    #             t + max(total_counts)*0.01,
    #             str(t),
    #             ha='center',
    #             va='bottom',
    #             fontsize=16,
    #             fontweight='bold')

    # 6) Formatting
    ax.set_xticks(valid_years)
    ax.set_xticklabels(valid_years, rotation=45, fontsize=25)
    ax.set_ylabel('URL Count', fontsize=30, labelpad=25)
    ax.tick_params(axis='y', labelsize=25)
    ax.legend(loc='upper left', fontsize=25)
    ax.spines['right'].set_visible(False)
    ax.spines['top'].set_visible(False)
    

    plt.tight_layout()
    fig.savefig('results/urlTypesEvolutionPerYear.pdf', dpi=300)
    plt.show()

    





# MAIN FUNCTION
try:
    connection = psycopg2.connect(**params)
    cursor = connection.cursor()
    
    generate_active_inactive_urls_combined(cursor)
    generate_active_inactive_urls_stacked_bar_chart_with_counts(cursor)
    generate_urls_section_stacked_bar_chart_with_counts(cursor)
    generate_active_urls_per_year_stacked_bar_chart(cursor)
    generate_http_error_distribution_horizontal_bar_chart(cursor)
    generate_network_error_distribution_horizontal_bar_chart(cursor)
    export_all_failed_domains_to_file(cursor)
    generate_url_types_evolution_per_year(cursor)
    
    
    # BACKUP
    # generate_active_urls_per_conference_stacked_bar_chart(cursor)
    # generate_success_rate_per_protocol(cursor)
    # generate_success_percentage_per_tld(cursor)
    # plot_url_counts_vs_broken_urls(cursor)
    # print("Half-life:", calculate_half_life(cursor))
    # visualize_top_failed_domains_from_csv('results/all_failed_domains_stats.csv', top_n=20)
    visualize_top_active_domains_from_csv('results/all_failed_domains_stats.csv', top_n=10)
    visualize_bottom_active_domains_from_csv('results/all_failed_domains_stats.csv', bottom_n=10)

except (Exception, psycopg2.DatabaseError) as error:
    print("ERROR:", error)
finally:
    if connection is not None:
        connection.close()

