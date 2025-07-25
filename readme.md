# Replication Package for: URL Rot in Software Engineering Scholarly Works

## Overview

This repository contains the replication package for the research paper titled "URL Rot in Software Engineering Scholarly Works". The package includes the data gathering process, tools, and scripts used to collect and analyze the data. 

If you wish to completely reproduce the study (Data Gathering and Data analysis), you will need to follow the instructions in all of the sections below.

If your goal is to replicate the findings, without re-collecting the data, you can skip the Data Gathering section and, after completing the Installation steps, proceed to the Analyses section.

## Installation

### PostgreSQL Database Setup

#### Database Schema Creation

After ensuring PostgreSQL is installed on your system, you can set up the database schema required for the replication package. Follow these steps to create the schema:

1. Open a terminal or command prompt.
2. Switch to the PostgreSQL user (if required) using: `sudo -i -u postgres`
3. Start the PostgreSQL command line interface: `psql`
4. Create a new database for the project, e.g., `link_rot_db`: `CREATE DATABASE link_rot_db;`
5. Exit the PostgreSQL interface: `\q`
6. Exit the PostgreSQL user session if you switched to it: `exit`
7. Navigate to the directory `database-setup`, which contains the `link_rot_db_schema.sql` file.
8. Import the schema into your newly created database using:
   `
   psql -d link_rot_db -f link_rot_db_schema.sql
   `
   
   This command will create the necessary tables and relationships as defined in the SQL file.

#### Using a Database Dump

If you prefer to start with a pre-populated database, you can use the `link_rot_db_data.sql` file, which contains a database dump, including the data. To import this dump, follow these instructions (after creating the database and schema as described above):

2. Navigate to the directory `database-setup`, which contains the `link_rot_db_data.sql` file.
3. Import the database dump using:
   ```
   psql -d link_rot_db -f link_rot_db_data.sql
   ```
   This will populate your database with the data contained in the SQL dump file.

#### Database Configuration

After setting up the database, you need to configure the connection details in the `database-setup/database.ini` file. Open the file and update the following fields with your database connection details:
- `host`
- `database`
- `user`
- `password`


### Tools and Libraries

#### python3 and pip3
Make sure you have python3 and pip3 installed on your system. You can install python3 and pip3 using the following commands:

```
sudo apt update
sudo apt install python3
sudo apt install python3-pip
```

#### Python Libraries

The replication package uses several Python libraries. You can install these libraries using the following command:

```
pip3 install -r requirements.txt
```

#### Grobid Installation
If you wish to replicate the data gathering process, you will need to install Grobid, a machine learning library for extracting and parsing scholarly documents.

For this, JAVA is required. You can install Java using the following command:

```
sudo apt install openjdk-17-jdk
```


Follow the instructions on the [Grobid website](https://grobid.readthedocs.io/en/latest/Install-Grobid/) to install Grobid.
Make sure Grobid is stored in a folder named `grobid` in the `data-gathering` directory of the replication package.

## Data Gathering

This section details the processes used to gather and prepare the data for analysis. It covers metadata extraction from DBLP, PDF retrieval, conversion of PDFs to XML, and the extraction of URLs from the converted XML files.

### Metadata Extraction from DBLP

This step involves downloading the DBLP dataset and extracting metadata relevant to your study. The process uses the `dblp/get_dblp_db.py` script to parse `dblp.xml` and convert it into a more manageable JSON format.

#### Instructions

1. **Download DBLP Dataset**:
   Navigate into the `data-gathering/dblp` directory.
   Use `curl` commands in your terminal to download the `dblp.xml.gz` and `dblp.dtd.gz` files. These files contain the complete DBLP dataset and the document type definition necessary for parsing. Run the following commands:

<!-- TODO: VERIFY VERSION -->
   - Download `dblp.xml.gz`:
     ```
     curl -o dblp.xml.gz https://dblp.org/xml/release/dblp-2025-02-01.xml.gzI.  
     ```
   - Download `dblp.dtd.gz`:
     ```
     curl -O https://dblp.org/xml/dblp.dtd.gz
     ```

2. **Extract the Downloaded Files**:
   - Use a tool like `gunzip` to extract the `.gz` files. In a terminal, run:
     ```
     gunzip dblp.xml.gz
     gunzip dblp.dtd.gz
     ```
   - This will result in `dblp.xml` and `dblp.dtd` files in your current directory.

3. **Run the Parsing Script**:
   - Execute the script to parse the DBLP XML and generate the `output.json` file. Run:
     ```
     python get_dblp_db.py --dblp dblp.xml --output output.json
     ```
   - Ensure the `dblp.xml` and `dblp.dtd` files are accessible to the script, preferably in the same directory or specify the path within the script.

4. **Populate the Database**:
   - After generating the `output.json` file, you can populate the database with the extracted metadata. Execute  `python populate_db.py `  to insert the data into the PostgreSQL database.


#### Notes
- Make sure you have enough storage space available for the `dblp.xml` file and the generated `output.json` file, as the DBLP dataset is large.

### PDF Retrieval

This section outlines the process of retrieving PDFs for the papers identified in the database. The process uses a Python script `1_download_pdfs.py` for downloading and a shell script for parallel execution across multiple venues.

#### Python Script: `1_download_pdfs.py`

The Python script downloads PDFs based on DOIs extracted from the database. It supports filtering by venue, year, and a range of years.

#### Usage

1. Ensure all dependencies are installed and the PostgreSQL database is accessible.
2. Ensure the 'parallel_download.sh' script is executable. If not, run `chmod +x parallel_download.sh`.
3. Run the shell script:
    ```
    ./parallel_download.sh
    ```
4. The script will create a logs/pdf_downloads directory for logs and execute downloads in parallel for the venues listed in the script.



### PDF to XML Conversion

This section describes the process of converting PDF documents to XML format using Grobid, a machine learning library for extracting, parsing, and re-structuring raw documents such as PDFs into structured XML format.

#### Python Script: `2_pdf_to_xml.py`

The Python script prepares PDF files for conversion by copying them into a specific directory structure expected by Grobid, then invokes Grobid to perform the conversion.

#### Usage

1. Ensure Grobid is installed.
2. Ensure the `parallel_pdf_parsing.sh` script is executable. If not, run `chmod +x parallel_pdf_parsing.sh`.
3. Run the shell script:
    ```
    ./parallel_pdf_parsing.sh
    ```
4. The script will create a logs/xml_parsing directory for logs and execute the conversion in parallel for the venues listed in the script.

### URL Extraction

This section details the process of extracting URLs from XML-converted documents using the `3_extract_urls.py` Python script.

#### Python Script: `3_extract_urls.py`

The script scans through XML files generated by Grobid, extracting URLs from various sections of the document, such as abstracts, citations, and body text.


#### Usage

1. Ensure all dependencies are installed and the PostgreSQL database is accessible.
2. Place the Python script in a directory that has access to `globalFunctions.py` for configuration management and `xml_to_dict.py` for XML processing.
3. Run the script with necessary arguments. For example, to extract URLs from documents in a specific directory and for a given venue and year range:
   ```bash
   python3 3_extract_urls.py --dir ../data  --Minyear 1971 --Maxyear 2023
   ```


### Automatic URL Crawling

Automated checks on URLs are performed using the `automatic-url-check/check_urls.py` script, which verifies URL availability and updates their status in a PostgreSQL database.


#### Instructions
1. Navigate to the `automatic-url-check` directory.
2. Run `python3 check_urls.py` to start the URL checking process.

This process ensures URLs in scholarly documents are accurately tracked for their availability status.

### Manual URL Checks

In order to replicate the Manual URL check that we did on a sample of active URLs, you can use the `manual-url-check` directory. This directory contains a `generate_random_sample.py` that generates a (seeded) random sample of URLs from the database and stores it in a TXT file. 



## Analyses

Make sure you PostgreSQL database is set up and the connection details are configured in the `database.ini` file (detailed steps in the `Installations` section).

### Visualizations

#### Instructions
1. Navigate to the `visualizations` directory.
2. Run `python3 visualizations.py` to generate visualizations and results based on the data in the database.

#### Outputs
The script generates visualizations that are saved in the `visualizations/visualization-outputs/` directory in pdf format. In the same folder, you will also find a `results.txt` file that contains the results of the analyses in numerical format.

### Regression Analysis

#### Instructions

1. Navigate to the `regression-analysis` directory.
2. Run the following commands to execute the regression analysis scripts:
```
python3 core_ranking_regression.py
python3 journal_impact_factor_regression.py
python3 url_metrics_regression.py
```
3. The results of the regression analyses will be printed to the console.



