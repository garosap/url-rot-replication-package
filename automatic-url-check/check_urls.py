import os
import shutil
import psycopg2
from curl_cffi import requests as curl_cffi_req
from tenacity import retry, stop_after_attempt, wait_fixed
import requests as python_req
import re
import sys
import subprocess
import time
from urllib.parse import urlparse

sys.path.append('../')
from globalFunctions import *

params = config(filename='../database-setup/database.ini', section='postgresql')
# check if url is valid
def is_valid_url(url):
    try:
        # Adding http just for the validity check
        if url.startswith("www."):
            url = "http://"+ url

        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except ValueError:
        return False



def get_network_error(url):
    command = f'curl --location --head --silent --max-time 5 --show-error "{url}" 2>&1 | grep -oP \'(?<=curl: \()\\d+(?=\))\''
    output = subprocess.getoutput(command)
    error_number = re.search(r'\d+', output)
    
    if error_number:
        return int(error_number.group())
    else:
        return None
    
    


@retry(reraise=True, stop=stop_after_attempt(3), wait=wait_fixed(45))
def fetch_with_retry(url, py_req):
    if py_req == False:
        response = curl_cffi_req.get(url, timeout=10,  impersonate="chrome110", allow_redirects=True) 
    else:
        response = python_req.get(url, timeout=10, allow_redirects=True) 

    return response



try:
    timeStart = time.time()

    connection = psycopg2.connect(**params)
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM urls WHERE active IS NULL AND status_code IS NULL AND network_error IS NULL")
    
    # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    
    # cursor.execute("""
        # SELECT DISTINCT u.*
        # FROM urls u
        # JOIN paper_urls pu ON u.id = pu.url_id
        # JOIN papers p     ON pu.paper_id = p.id
        # WHERE p.year = 2024
        # AND u.active IS NULL
        # AND u.status_code IS NULL
        # AND u.network_error IS NULL;
    # """)
    # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    
    urls = cursor.fetchall()
    
    cnt = 1

    # total urls
    totalUrls = len(urls)



    for url in urls:
        print(f"Checking url {cnt}/{totalUrls}")
        print("url", url)
        
        cnt += 1
        # print("url", url)
        # fetch the url to get error code
        url = url[1]

        # check if url is valid
        if not is_valid_url(url):
            print(f"Invalid URL: {url}")
            continue

        # check if url will download compressed file or zip rar
        if re.search(r'\.zip$', url) or re.search(r'\.tar$', url) or re.search(r'\.gz$', url) or re.search(r'\.bz2$', url) or re.search(r'\.xz$', url) or re.search(r'\.7z$', url) or re.search(r'\.rar$', url):
            print(f"URL is a compressed file: {url}")
            continue
        
        # Only check urls that have active | status_code | network_error = None
        cursor.execute("SELECT * FROM urls WHERE url = %s AND active IS NULL AND status_code IS NULL AND network_error IS NULL", (url,))
        urlDB = cursor.fetchone()
        if not urlDB:
            print(urlDB)
            continue
        
        
        time.sleep(30)
        
        try:
            # response = curl_cffi_req.get(url, timeout=10,)
            try:
                response = fetch_with_retry(url, py_req=False)
            except Exception as e:
                print("Error fetching url: ", e)
                raise python_req.exceptions.RequestException 
                
                # continue
            if response.status_code != 200:
                try:    
                    response = fetch_with_retry(url, py_req=True)
                except Exception as e:
                    print("Error fetching url: ", e)
                    raise python_req.exceptions.RequestException 

            print(url, response.status_code)
        
            active = response.status_code == 200
            # update the url table with the error code
            cursor.execute("UPDATE urls SET active = %s, status_code = %s, network_error = %s WHERE url = %s", (active, response.status_code, None, url))
            connection.commit()

        except python_req.exceptions.RequestException as e:
            errno = get_network_error(url)
            print("errno", errno)  
            
            if(errno):
                # update the url table with the error code
                cursor.execute("UPDATE urls SET active = False, network_error = %s, status_code = %s WHERE url = %s", (errno, None, url))
                connection.commit()
            else:
                cursor.execute("UPDATE urls SET active = False, network_error = %s, status_code = %s WHERE url = %s", (None, None, url))
                connection.commit()
            continue



        
        
except (Exception, psycopg2.DatabaseError) as error:
    print("ERROR:", error)
finally:
    print("Total time taken (s): ", time.time() - timeStart)
    if connection is not None:
        connection.close()


