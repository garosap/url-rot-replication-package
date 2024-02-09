import os.path
from os import path
from sqlalchemy import create_engine
from sqlalchemy.sql import text
import argparse
from doi2pdf_custom import doi2pdf
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
dbPaths=args.dir
venue=args.venue
year=args.year
Maxyear=args.Maxyear
Minyear=args.Minyear

if not venue is None:
    ConditionVenue=" where acronym='"+str(venue)+"'"
else:
    ConditionVenue=''
if not year is None:
    ConditionYear=" and year='"+str(year)+"'"
else:
    ConditionYear=''
if not Maxyear is None:
    ConditionYear+=" and year<='"+str(Maxyear)+"'"
if not Minyear is None:
    ConditionYear+=" and year>='"+str(Minyear)+"'" 


engine = create_engine('postgresql://'+params['user']+':'+params['password']+'@'+params['host']+':5432/'+params['database'])

conn = engine.connect()
count=0
tcount=0
ncount=0
conferences=conn.execute(text("SELECT * FROM venues"+ConditionVenue+";"))
print("Number of conferences", conferences.rowcount)

number_of_conferences=conferences.rowcount
conference_count=0
for conf in conferences:  
    print(conf)
    conference_count=conference_count+1
    print("Starting conference", conference_count, "out of", number_of_conferences)
    pdfpath = dbPaths+'/pdf/'+conf[1]
    if not path.exists(pdfpath):
        os.makedirs(pdfpath)
    result_set=conn.execute(text("SELECT id,doi,ee FROM papers WHERE venue_id="+str(conf[0])+ConditionYear+";"))
    

    filenameBuffer=""
    tcount = 0
    for paper in result_set: 
        tcount=tcount+1
        print("Paper",tcount,"out of", result_set.rowcount)
        try:
            doi = paper[1]

            # if doi starts with http, only keep the doi part
            if doi and doi.startswith("http"):
                doi=doi.split(".org/")[1]

            filename=doi
            if not path.exists(os.path.join(pdfpath, doi.replace("/", "\\")+'.pdf')):
                print("Downloading paper", os.path.join(pdfpath, doi.replace("/", "\\")+'.pdf'))


                output_file_name = os.path.join(pdfpath, doi.replace("/", "\\")+'.pdf')

                try:
                    doi2pdf(doi, output=output_file_name)
                    # print("Downloaded paper", output_file_name)
                except Exception as e:
                    print("Error:",e)
                    pass


            else:
                print("Paper", doi, "already exists")
        except Exception as e:
            count=count+1
            ncount=ncount+1
            print("Error:",e)
            pass


    

print('Number of papers that are not downloaded:',count,'out of', tcount,'// ',ncount,' papers with no doi')
conn.close()

