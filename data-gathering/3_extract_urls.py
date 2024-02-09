from os import path
import ast
import random
from sqlalchemy.sql import text
import psycopg2
import argparse
import time
from xml_to_dict import xml_to_dict
import sys
import os

sys.path.append('../')
from globalFunctions import *
params = config(filename='../database-setup/database.ini', section='postgresql')


pparser = argparse.ArgumentParser()
pparser.add_argument('--dir', required=True, help='directory')
pparser.add_argument('--venue', required=False, help='venue name')
pparser.add_argument('--year', required=False, help='specify year')
pparser.add_argument('--Maxyear', required=False, help='specify upper limit year')
pparser.add_argument('--Minyear', required=False, help='specify lower limit year')
args = pparser.parse_args()
dbPaths = args.dir
venue = args.venue
year = args.year
Maxyear = args.Maxyear
Minyear = args.Minyear


if venue is not None:
    ConditionVenue = " where acronym='" + str(venue) + "'"
else:
    ConditionVenue = ''

if year is not None:
    ConditionYear = " and year='" + str(year) + "'"
else:
    ConditionYear = ''

if Maxyear is not None:
    ConditionYear += " and year<='" + str(Maxyear) + "'"

if Minyear is not None:
    ConditionYear += " and year>='" + str(Minyear) + "'"



def checkAndInsertURL(url, section, cursor, connection):
    # format the url
    url = formatURL(url)

    # check if the url is already in the urls table
    cursor.execute("SELECT id FROM urls WHERE url=%s;", (url,))
    url_id = cursor.fetchone()

    if url_id is None:
        try:
            # Insert url into the urls table
            cursor.execute("INSERT INTO urls (url, status_code, section) VALUES (%s, %s, %s) RETURNING id;",
                        (url, None, section))
            url_id = cursor.fetchone()[0]
            connection.commit()
        except Exception as e:
            print('error saving URL:', e)
            if e == 'current transaction is aborted, commands ignored until end of transaction block':
                connection.rollback()
            pass

    return url_id



def checkAndInsertPaperURL(paper_id, url_id, cursor, connection):
    # check if the url is already in the paper_urls table
    cursor.execute("SELECT url_id FROM paper_urls WHERE paper_id=%s AND url_id=%s;",
                   (paper_id, url_id))
    url_id_check = cursor.fetchone()

    if url_id_check is None:
        # Create an entry in the paper_urls table
        try:
            cursor.execute("INSERT INTO paper_urls (paper_id, url_id) VALUES (%s, %s);",
                       (paper_id, url_id))
            connection.commit()
        except Exception as e:
            print('error saving PAPER URLs:', e)
            if e == 'current transaction is aborted, commands ignored until end of transaction block':
                connection.rollback()
            pass

try:
    connection = psycopg2.connect(**params)
    cursor = connection.cursor()

    # Retrieve venue records from the venues table
    cursor.execute("SELECT * FROM venues" + ConditionVenue + ";")
    confs = cursor.fetchall()
    total = 0
    urls = {}

    initTime = time.time()

    total_urls_found = 0

    for conf in confs:

        count = 0
        ngramList = []
        confName = conf[1]
        CTpathXML = dbPaths + '/grobidXML/' + confName

        # Construct the SQL query to retrieve paper records
        query = "SELECT id, doi FROM papers l WHERE venue_id=" + str(conf[0]) + ConditionYear + ";"
        cursor.execute(query)
        paper_records = cursor.fetchall()
        rem = len(paper_records)
        total = total + rem
        cnt = 0
        
        for paper in paper_records:
            paper_url_count = 0
            cnt = cnt + 1
            print(cnt, 'out of', rem, 'in', confName)
            try:
                filename = paper[1].replace("/", "\\", 2)
                fname = os.path.join(CTpathXML, filename + ".tei.xml")

                if path.exists(fname):
                    paper_dict = xml_to_dict(fname)
                    if paper_dict is not None:
                        # extract from 1. abstract, 2. citations, 3. sections

                        # 1. abstract
                        if "abstract" in paper_dict:
                            abstract = paper_dict["abstract"]
                            if abstract is not None:                                
                                # extract urls from abstract
                                url_list = extract_urls_xml(abstract)
                                
                                for url in url_list:
                                    paper_url_count += 1
                                    url_id = checkAndInsertURL(url, "abstract", cursor, connection)
                                    checkAndInsertPaperURL(paper[0], url_id, cursor, connection)

                        # 2. citations
                        if "citations" in paper_dict:
                            citations = paper_dict["citations"]
                            if citations is not None:
                                for citation in citations:                                
                                    # check if the citation url exists
                                    if "url" in citation and citation["url"] is not None:
                                        paper_url_count += 1
                                        url_id = checkAndInsertURL(citation["url"], "citations", cursor, connection)
                                        checkAndInsertPaperURL(paper[0], url_id, cursor, connection)

                        # 3. sections
                        if "sections" in paper_dict:
                            sections = paper_dict["sections"]
                            if sections is not None:
                                for section in sections:
                                    # print(section, sections[section])
                                    section_text = sections[section]
                                    if section_text is not None:
                                        url_list = extract_urls_xml(section_text)
                                        
                                        for url in url_list:
                                            paper_url_count += 1
                                            url_id = checkAndInsertURL(url, section, cursor, connection)
                                            checkAndInsertPaperURL(paper[0], url_id, cursor, connection)

            except Exception as e:
                print('error:', e)
                if e == 'current transaction is aborted, commands ignored until end of transaction block':
                    connection.close()
                    connection = psycopg2.connect(**params)
                    cursor = connection.cursor()
                pass
        
            print('paper_url_count:', paper_url_count)
            total_urls_found += paper_url_count
            print('total_urls_found:', total_urls_found)

    # connection.commit()

except (Exception, psycopg2.Error) as error:
    print("Error while fetching data from PostgreSQL", error)
finally:

    print("Total time taken: ", time.time() - initTime)
    # Commit the changes and close the database connection
    connection.commit()
    if connection:
        cursor.close()
        connection.close()
