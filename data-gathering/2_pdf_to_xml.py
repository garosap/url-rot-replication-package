import subprocess  
import os
from os import path
from sqlalchemy.sql import text
from sqlalchemy import create_engine
import shutil
import os
import sys
import argparse

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

engine =  create_engine('postgresql://'+params['user']+':'+params['password']+'@'+params['host']+':5432/'+params['database'])
conn = engine.connect()

count=0
conferences=conn.execute(text("SELECT * FROM venues"+ConditionVenue+";"))
# iterate over all conferences as dictionaries

conference_count=conferences.rowcount

copy_count=0
print('Copying pdf files to grobidXML folder')

for conf in conferences:  

    copy_count=copy_count+1
    print('Copying pdf files to grobidXML folder', copy_count, 'of', conference_count)

    # row to dictionary
    conf = conf._asdict()

    Cpath = dbPaths+'/grobidXML/'+conf['acronym']
    pdfpath=dbPaths+'/pdf/'+conf['acronym']
    if not path.exists(Cpath):
        os.makedirs(Cpath)
    result_set=conn.execute(text("SELECT id, ee, year, doi FROM papers WHERE venue_id="+str(conf['id'])+ConditionYear+";"))
    for paper in result_set: 
        paper = paper._asdict()
        try:
            if paper['doi']!=None:
                doi=paper['doi'].replace("/", "\\", 1)
                filename=doi
                if (not path.exists(os.path.join(Cpath,filename+".tei.xml"))) & (not path.exists(os.path.join(Cpath,filename+".pdf"))):  
                    try:
                        filename=filename+'.pdf'
                        shutil.copy(os.path.join(pdfpath,str(filename)), Cpath)
                    except Exception as e:   
                        count=count+1
                        pass
            else:
                count=count+1
        except Exception as e:
            count=count+1 
            print(e)


                
print('number of pdfs not found:',count)


print('Running Grobid')
command_dir="./grobid/"
conferences=conn.execute(text("SELECT * FROM venues"+ConditionVenue+";"))

parsing_count=0

for conf in conferences:  
    parsing_count=parsing_count+1
    print('Running Grobid', parsing_count, 'of', conference_count)
    
    conf = conf._asdict()
    print("Running Grobid for", conf['acronym'])
    Gpath = dbPaths+'/grobidXML/'+conf['acronym']
    if not path.exists(Gpath):
        os.makedirs(Gpath)
    Gpath = '../'+dbPaths+'/grobidXML/'+conf['acronym']
    drun="-Xmx4G -jar grobid-core/build/libs/grobid-core-0.7.2-onejar.jar -gH grobid-home -dIn "+ Gpath+ " -dOut "+ Gpath+" -exe processFullText" 
    subprocess.call(['java'] + drun.split(), cwd = command_dir)
    
    
    

