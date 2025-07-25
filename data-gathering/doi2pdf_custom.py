import argparse
from typing import Optional
import os
import bs4
import requests
import time
import random
import re
import xml.etree.ElementTree as ET
from get_ieee_pdf import get_ieee_pdf

class NotFoundError(Exception):
    pass


SCI_HUB_URL = os.getenv("SCI_HUB_URL", "https://sci-hub.ee/")


def doi2pdf(
    doi: Optional[str] = None,
    *,
    output: Optional[str] = None,
    name: Optional[str] = None,
    url: Optional[str] = None,
    open_pdf: bool = False,
):
    """Retrieves the pdf file from DOI, name or URL of a research paper.
    Args:
        doi (Optional[str]): _description_. Defaults to None.
        output (str, optional): _description_. Defaults to None.
        name (Optional[str], optional): _description_. Defaults to None.
        url (Optional[str], optional): _description_. Defaults to None.
        open_pdf (bool, optional): _description_. Defaults to False.
    """

    if len([arg for arg in (doi, name, url) if arg is not None]) > 1:
        raise ValueError("Only one of doi, name, url must be specified.")

    pdf_content = None


    # try different Sci hub urls to retrieve 
    sci_hub_urls = [
        "https://sci-hub.ee/",
        "https://sci-hub.se/",
        "https://sci-hub.do/",
        "https://sci-hub.st/", 
        "https://sci-hub.wf/"       
    ]

    try:
        for sci_hub_url in sci_hub_urls:
            try:
                doi, title, official_pdf_url = get_paper_metadata(doi, name, url)
                sci_hub_pdf_url = retrieve_scihub(doi, sci_hub_url)
                pdf_content = get_pdf_from_url(sci_hub_pdf_url)
            except Exception as e:
                print(f"Sci-hub {sci_hub_url} mirror not working, trying other sources...")
                print(e)
                continue

            if pdf_content is None: 
                print("Sci-hub not working, trying other sources...")
                continue
            else:
                # PDF was found, break the loop
                break

    except Exception as e:
        print(e)
        print("Sci-hub not working, trying arxiv...")
        pass

    # try arxiv
    if pdf_content is None:
        try:
            doi, title, official_pdf_url = get_paper_metadata(doi, name, url)
            print(title)
            pdf_content = download_arxiv_pdf(title)
        except Exception as e:
            print(e)
            print("Arxiv not working, trying official URL...")
            pass


    # try official URL
    if pdf_content is None:
        try:
            doi, title, official_pdf_url = get_paper_metadata(doi, name, url)
            print(official_pdf_url)

            # check if the official pdf url redirects 
            redirect_url = check_redirect(official_pdf_url)
            print("REDIRECT URL: ", redirect_url)

            # check if it redirects to ieee
            if redirect_url is not None :
                if "ieeexplore.ieee.org" in redirect_url:
                    # if ieee urls ends with /, remove it
                    if redirect_url[-1] == "/":
                        redirect_url = redirect_url[:-1]

                    ieee_doc_id = redirect_url.split("/")[-1]
                    pdf_content = get_ieee_pdf(ieee_doc_id)
                elif "springer.com" in redirect_url:
                    pdf_content = get_springer_pdf(doi)
                elif "dl.acm.org" in redirect_url:
                    pdf_content = get_acm_pdf(doi)
                elif "authorea.com" in redirect_url:
                    pdf_content = get_authorea_pdf(doi)
            else:
                pdf_content = get_pdf_from_url(official_pdf_url)
            

            # add a 60-120 second delay to avoid being blocked by the website
            time.sleep(random.randint(60, 120))

        except NotFoundError:
            print("Official URL not working PDF can't be retrieved.")
            pass


    

    # if pdf was found and does not start with <!DOCTYPE html>, save it
    if pdf_content != None and not pdf_content.startswith(b"<!DOCTYPE html>"):
        filename = title.replace(" ", "_") + ".pdf"
        if output is None:
            output = f"{filename}"

        print(f"SUCCESS: PDF saved to {output}")
        with open(output, "wb") as f:
            f.write(pdf_content)




def get_paper_metadata(doi, name, url):
    """Returns metadata of a paper with http://openalex.org/"""
    if name:
        api_res = requests.get(
            f"https://api.openalex.org/works?search={name}&per-page=1&page=1&sort=relevance_score:desc"
        )
    if doi:
        api_res = requests.get(f"https://api.openalex.org/works/https://doi.org/{doi}")
    if url:
        api_res = requests.get(f"https://api.openalex.org/works/{url}")

    if api_res.status_code != 200:
        raise NotFoundError("Paper not found.")

    metadata = api_res.json()
    if metadata.get("results") is not None:
        metadata = metadata["results"][0]

    if metadata.get("doi") is not None:
        doi = metadata["doi"][len("https://doi.org/") :]
    title = metadata["display_name"]
    pdf_url = metadata["open_access"]["oa_url"]
    if pdf_url is None:
        if metadata.get("host_venue") is not None:
            pdf_url = metadata["host_venue"]["url"]
        elif metadata.get("primary_location") is not None:
            pdf_url = metadata["primary_location"]["landing_page_url"]
        else:
            raise NotFoundError("PDF URL not found.")

    print("Found paper: ", title)
    return doi, title, pdf_url


def get_html(url):
    """Returns bs4 object that you can iterate through based on html elements and attributes."""
    s = requests.Session()
    print("Retrieving HTML from", url)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2228.0 Safari/537.36",
    }
    html = s.get(url, timeout=10, headers=headers, allow_redirects=False)
    html.encoding = "utf-8"
    html.raise_for_status()
    html = bs4.BeautifulSoup(html.text, "html.parser")
    return html


def retrieve_scihub(doi, sci_hub_url=SCI_HUB_URL):
    """Returns the URL of the pdf file from the DOI of a research paper thanks to sci-hub."""
    html_sci_hub = get_html(f"{sci_hub_url}{doi}")
    # print(html_sci_hub)
    iframe = html_sci_hub.find("iframe", {"id": "pdf"})
    if iframe is None:
        raise NotFoundError("DOI not found.")

    return iframe["src"]


def get_pdf_from_url(url):
    """Returns the content of a pdf file from a URL."""
    res = requests.get(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2228.0 Safari/537.36",
        },
        # allow_redirects=False,
    )

    if res.status_code != 200:
        raise NotFoundError("Bad PDF URL.")
    
    # print(res.content)
    return res.content


def check_redirect(url):
    """Returns the content of a pdf file from a URL."""
    res = requests.get(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko)",
        },
        allow_redirects=False,
    )

    
    redirect_location = res.headers.get("Location")
    if redirect_location is not None:
        return redirect_location
    else:
        return None
    
    


def main():
    parser = argparse.ArgumentParser(
        description="Retrieves the pdf file from DOI of a research paper.", epilog=""
    )

    parser.add_argument(
        "-o",
        "--output",
        type=str,
        help="Relative path of the target pdf file.",
        metavar="path",
    )

    parser.add_argument(
        "--doi", type=str, help="DOI of the research paper.", metavar="DOI"
    )

    parser.add_argument(
        "-n", "--name", type=str, help="Name of the research paper.", metavar="name"
    )

    parser.add_argument(
        "--url", type=str, help="URL of the research paper.", metavar="url"
    )

    parser.add_argument(
        "--open", action="store_true", help="Open the pdf file after downloading.",
    )

    args = parser.parse_args()

    if args.doi is None and args.name is None and args.url is None:
        parser.error("At least one of --doi, --name, --url must be specified.")
    if len([arg for arg in (args.doi, args.name, args.url) if arg is not None]) > 1:
        parser.error("Only one of --doi, --name, --url must be specified.")

    doi2pdf(
        args.doi, output=args.output, name=args.name, url=args.url, open_pdf=args.open
    )


def doi_to_arxiv_id(doi):
    """
    Extracts the arXiv ID from a DOI. 
    This function assumes the DOI is for an arXiv document.
    """
    # Example pattern: '10.48550/arXiv.2105.04881'
    match = re.search(r'arXiv\.(\d+\.\d+)', doi)
    if match:
        return match.group(1)
    else:
        raise ValueError("DOI does not contain a valid arXiv ID")

def title_to_arxiv_url(title):
    """
    Searches arXiv for a given title and attempts to find the corresponding arXiv ID.
    """
    query = '+AND+'.join(title.split())
    url = f'http://export.arxiv.org/api/query?search_query=ti:{query}&start=0&max_results=1'
    response = requests.get(url)


    if response.status_code != 200:
        raise ValueError("Failed to query arXiv API.")

    root = ET.fromstring(response.content)
    namespace = {'arxiv': 'http://www.w3.org/2005/Atom'}
    entry = root.find('{http://www.w3.org/2005/Atom}entry')

    if entry is not None:
        for link in entry.findall('{http://www.w3.org/2005/Atom}link'):
            if 'title' in link.attrib and link.attrib['title'] == 'pdf':
                return link.attrib['href']

    else:
        raise ValueError("No matching arXiv record found for the given title.")



def download_arxiv_pdf(title):
    """
    Downloads a PDF from arXiv given a DOI.
    """

    print(f"Searching arXiv for {title}...")
    try:
        # arxiv_id = doi_to_arxiv_id(doi)
        pdf_url = title_to_arxiv_url(title)
    except ValueError as e:
        print(f"Error: {e}")
        return

    response = requests.get(pdf_url)

    if response.status_code == 200:
        # print(f"FOUND ARXIV PDF {pdf_url}")
        return response.content
        # print(response.content)
        # with open(save_path, 'wb') as f:
        #     f.write(response.content)
    else:
        print(f"Failed to download PDF. Status code: {response.status_code}")
    
def get_springer_pdf(doi):
    url = f"https://link.springer.com/content/pdf/{doi}.pdf"
    """Returns the content of a pdf file from a URL."""
    res = requests.get(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko)",
        },

    )

    if res.status_code != 200:
        raise NotFoundError("Bad PDF URL.")
    
    return res.content


def get_acm_pdf(doi):
    url = f"https://dl.acm.org/doi/pdf/{doi}"
    """Returns the content of a pdf file from a URL."""
    res = requests.get(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko)",
        },

    )

    if res.status_code != 200:
        raise NotFoundError("Bad PDF URL.")
    
    return res.content

def get_authorea_pdf(doi):
    url = f"https://www.authorea.com/doi/pdf/{doi}"
    """Returns the content of a pdf file from a URL."""
    res = requests.get(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko)",
        },

    )

    if res.status_code != 200:
        raise NotFoundError("Bad PDF URL.")
    
    return res.content




if __name__ == "__main__":
    main()
