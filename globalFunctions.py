from configparser import ConfigParser
import re

# Function to read the database.ini file and return the connection parameters
def config(filename='database-setup/database.ini', section='postgresql'):
    # create a parser
    parser = ConfigParser()
    # read config file
    parser.read(filename)

    # get section, default to postgresql
    db = {}
    if parser.has_section(section):
        params = parser.items(section)
        for param in params:
            db[param[0]] = param[1]
    else:
        raise Exception('Section {0} not found in the {1} file'.format(section, filename))

    return db


# Function to extract URLs from a string of text
def extract_urls_xml(text):
    url_regex = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')

    urls = []
    matches = url_regex.findall(text)
    urls.extend(matches)            

    return urls


# remove any trailing ")", "}", "]", ".", ",", "?", "!", etc. characters from the URL
def formatURL(url):
    if(url[-1] in ")}].,?!"):
        # remove any trailing ")", "}", "]", ".", ",", "?", "!", etc.
        url = url.rstrip(")}].,?!") 
        return formatURL(url)

    return url

