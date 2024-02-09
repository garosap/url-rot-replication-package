from sqlalchemy import create_engine
from sqlalchemy_utils import database_exists
from sqlalchemy.orm import sessionmaker
import json
# from initDB import Paper

from init_db import Paper, Venue
from init_db import initDB

import argparse
from sqlalchemy import and_, or_, not_
import sys
sys.path.append('../../')
from globalFunctions import *

params = config(filename='../../database-setup/database.ini', section='postgresql')


def getConfName(conf):
    if conf=='fse':
        return [x.lower() for x in ['ESEC / SIGSOFT FSE','ESEC/SIGSOFT FSE','SIGSOFT FSE']]
    if conf=='saner':
        return [x.lower() for x in ['SANER','CSMR-WCRE']]
    return [conf.lower()]

def getJournalName(abvr):
    j= {     
'SPE':'Softw. Pract. Exp.',
'REJ': 'Requir. Eng.',
'ESE' :'Empir. Softw. Eng.'  ,
'SOSYM'  :  'Softw. Syst. Model.',
'SQJ' :'Softw. Qual. J.',
'ISSE' :'Innov. Syst. Softw. Eng.',
'IJSEKE' :'Int. J. Softw. Eng. Knowl. Eng.',
'NOTES': 'ACM SIGSOFT Softw. Eng. Notes',
'JSS' :'J. Syst. Softw.',
'SPE' :'Softw. Pract. Exp.',
'STVR':'Softw. Test. Verification Reliab.',
'ASEJ':'Autom. Softw. Eng.',
'TSE':'IEEE Trans. Software Eng.',
'TOSEM' :'ACM Trans. Softw. Eng. Methodol.' ,
 'SW':'IEEE Softw.'   ,
 'IST' :'Inf. Softw. Technol.',
'SMR':  'J. Softw. Evol. Process.'
       }
    
    return j[abvr]





conferences = ['ASE', 'ESEM', 'FASE', 'FSE', 'GPCE', 'ICPC', 'ICSE', 'ICSM', 'ICSME', 'ICST',
'ISSTA', 'MODELS', 'MSR', 'RE', 'SANER', 'SCAM', 'SSBSE', 'WCRE']


#conferences = ['issta','icst','ssbse','esem','re','mdls']
#journals=['tosem','jss','esem','tse','j-ase']
journals=['ASEJ', 'ESE', 'IJSEKE', 'ISSE', 'IST', 'JSS', 'REJ', 'NOTES',
 'SMR', 'SOSYM', 'SPE', 'SQJ', 'STVR', 'SW', 'TOSEM', 'TSE']

# Conference impact computed for the entire period 2000-2013
# http://shine.icomp.ufam.edu.br/index.php


Cname = {
    'ICSE':'International Conference on Software Engineering', 
    'ICSM':'IEEE International Conference on Software Maintenance', 
    'WCRE':'Working Conference on Reverse Engineering',
    'MSR':'Working Conference on Mining Software Repositories',
    'ICSME':'International Conference on Software Maintenance and Evolution',
    'ASE':'IEEE/ACM International Conference on Automated Software Engineering',
    'SCAM':'International Working Conference on Source Code Analysis & Manipulation',
    'ICPC':'IEEE International Conference on Program Comprehension',
    'FSE':'ACM SIGSOFT Symposium on the Foundations of Software Engineering',
    'SANER':'IEEE International Conference on Software Analysis, Evolution and Reengineering',
    'FASE':  'Fundamental Approaches to Software Engineering',
    'GPCE': 'Generative Programming and Component Engineering',
    'ISSTA': 'International Symposium on Software Testing and Analysis',
    'ICST': 'IEEE International Conference on Software Testing, Verification and Validation',
    'SSBSE': 'International Symposium on Search Based Software Engineering' ,
    'ESEM': 'International Symposium on Empirical Software Engineering and Measurement',
    'RE': 'IEEE International Requirements Engineering Conference',
    'MODELS': 'International Conference On Model Driven Engineering Languages And Systems'

}
Jname={
    
'SOSYM' :'Software and System Modeling',
'REJ' :'Requirements Engineering Journal' ,
'ESE' :'Empirical Software Engineering',
'SQJ' :'Software Quality Journal' ,
'IST': 'Information and Software Technology' ,
'ISSE': 'Innovations in Systems and Software Engineering' ,
'IJSEKE': 'International Journal of Software Engineering and Knowledge Engineering', 
'NOTES': 'ACM SIGSOFT Software Engineering Notes' ,
'SPE' :'Software: Practice and Experience' ,
'STVR': 'Software Testing, Verification and Reliability',
'TSE': 'IEEE - Transactions on Software Engineering',
'TOSEM': 'ACM - Transactions on Software Engineering Methodology',
'ESE':'Springer - Empirical Software Engineering' ,
'JSS':'Elsevier - Journal of Systems and Software',
'ASEJ':'Automated Software Engineering',
'SW': 'IEEE Software'   , 
'SMR': 'Journal of Software: Evolution and Process'

   
}    

pparser = argparse.ArgumentParser()
pparser.add_argument('--input', required=True, help='input file')
pparser.add_argument('--db', required=True, help='database name')
args = pparser.parse_args()
dbname=args.db
inputfile=args.input

engine = create_engine('postgresql://'+params['user']+':'+params['password']+'@'+params['host']+':5432/'+params['database'])


if database_exists(engine.url):
    print('database exists')
    initDB(engine)
    conn = engine.connect()
    
else:
    engine = create_engine('postgresql://'+params['user']+':'+params['password']+'@'+params['host']+':5432/')
    conn = engine.connect()
    conn.execute("commit")
    conn.execute("create database "+dbname+";")
    initDB(engine)
    




# Create a session for this conference
Session = sessionmaker(engine)
session = Session()


print('Loading papers:')
file = open(inputfile, 'r')
reader = file.readlines()
count=0

print("Conferences:")

venue_counter=0
for conferenceAcro in conferences:
    venue_counter=venue_counter+1
    print(venue_counter,  'out of ', len(conferences))

    Pcount=0
    # Create a new conference object
    qvenue = session.query(Venue).filter(Venue.acronym == conferenceAcro.upper()).first()
    cAcro=conferenceAcro.lower()
    if not qvenue:
        venue = Venue(conferenceAcro.upper(),Cname[conferenceAcro.upper()],'conference')
        session.add(venue)
    else:
        venue=qvenue

    for row in reader:
        # Deconstruct each row of papers table
        publication=json.loads(row)
        if ("author" in publication.keys()) & ("booktitle" in publication.keys()):
            

            if publication['booktitle'].lower() in getConfName(cAcro):   
                try:
                    if cAcro in ['icsm','icst']:
                        if not str('/'+cAcro+'/') in publication['crossref'][0]:
                            continue
                    year = int(publication['year'])
                    author_names = publication['author']
                    title = publication['title']
                    try:
                        pages = publication['pages']
                    except:
                        pages = None     
                    try:
                        ee = publication['ee']
                    except:
                        ee = None
                    try:
                        url = publication['url']
                    except:
                        url = None
                    crossref=publication['crossref']
                    genre=publication['genre']
                    try:
                        doi=ee[0].replace("https://doi.org/", "", 1)
                        doi=doi.replace("http://doi.ieeecomputersociety.org/", "", 1)
                        #doi=doi.replace("/", "\\", 2)
                    except:
                        doi = None

                    paperExists=session.query(Paper).filter(and_(Paper.venue_id == venue.id, Paper.year == year, Paper.doi == doi)).first()

                    if not paperExists:
                        paper = Paper(venue, year, ee, doi)            
                        session.add(paper)

                    Pcount=Pcount+1
                except Exception as e:
                    print('1',e)
                
    print(conferenceAcro.upper(), Pcount) 
    
    
    
  #================================================  
    
    
print('Journals:')

venue_counter=0
for journalAcro in journals:
    Pcount=0
    count=count+1
    venue_counter=venue_counter+1
    print(venue_counter,  'out of ', len(journals))
    # Create a new journal object
    qvenue = session.query(Venue).filter(Venue.acronym == journalAcro.upper()).first()

    if not qvenue:
        venue = Venue(journalAcro.upper(), Jname[journalAcro.upper()],'journal')
        session.add(venue)
    else:
        venue=qvenue
        
    for row in reader:
        # Deconstruct each row of articl table
        publication=json.loads(row)
        if ("journal" in publication.keys()) :
            if publication['journal']== getJournalName(journalAcro.upper()):
                try:
                    year = int(publication['year'])
                    try:
                        author_names = publication['author']
                    except:
                        author_names = None

                    title = publication['title']
                    try:
                        pages = publication['pages']
                    except:
                        pages = None     
                    try:
                        ee = publication['ee']
                    except:
                        ee = None
                    try:
                        url = publication['url']
                    except:
                        url = None
                    volume=publication['volume']
                    genre=publication['genre']
                    try:
                        doi=ee[0].replace("https://doi.org/", "", 1)
                        doi=doi.replace("http://doi.ieeecomputersociety.org/", "", 1)
                        #doi=doi.replace("/", "\\", 2)
                    except:
                        doi = None

                    paperExists=session.query(Paper).filter(and_(Paper.venue_id == venue.id, Paper.year == year, Paper.doi == doi)).first()
                        
                    if not paperExists:
                        paper = Paper(venue, year, ee, doi)            
                        session.add(paper)
                        #Pcount=Pcount+1
                        #break
                    Pcount=Pcount+1
                except Exception as e:
                    print('2',e)
    print(journalAcro.upper(), Pcount) 



try:
    session.commit()
except Exception as e:
    print('except2',e)
    session.rollback()
    
conn.close()

print( 'Finished loading data')