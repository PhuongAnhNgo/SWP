import csv
from tkinter.messagebox import NO
import pyodbc
#import xml.etree.ElementTree as etree
from lxml import etree
from lxml.etree import XMLSyntaxError
import sys
import os
from PWS import SQL
from sqlalchemy import null
import re

server_ = 'localhost\MSSQLSERVER01'
database = 'AuthorNetz'
id_='Fra'
pw='Fra'
conn = pyodbc.connect(Driver='{ODBC Driver 17 for SQL Server}', 
                        SERVER=server_,
                        DATABASE=database,
                        UID=id_,
                        PWD=pw)


print("DB Connected..")
cursor = conn.cursor()

def write(doi, txtName): 
    path= txtName+".txt" 
    data=doi + "\n"
    with open(path, 'a') as f:
        f.write(data)
        f.close()

#orchid Validierer
orchidList = [orchid[0] for orchid in cursor.execute('SELECT "orchid" FROM "Author"').fetchall()] 
for orchid in orchidList:  
    orchid = orchid.replace(" ","")
    if len(orchid) != 16:
        continue
    if not(orchid.isdigit()):
        continue
    print(orchid)        
       #write(orchid, 'si')
        
#ISSN Validierer
issnList = [issn[0] for issn in cursor.execute('SELECT "issn" FROM "Journal"').fetchall()] 
for issn in issnList:
    issn=issn.replace(" ","")
    issn_numbers= re.findall('[0-9]',issn)
    if len(issn_numbers)!=8 or (len(issn_numbers)!=7 and issn[-1] !="X"):
        continue
    print(issn)
    #write(issn,'si')
 
#DOI Validierer
doiList = cursor.execute('SELECT "doi" FROM "Publications"').fetchall() 
for i in doiList:
    removedSpace = i[0].strip()
    prefixes=['https://www.tandfonline.com/doi/full/', 'https://doi.org/','http://doi.acm.org/','http://dl.acm.org/citation.cfm?doid=','http://journals.sagepub.com/doi/full/','https://dl.acm.org/doi/','http://www.emeraldinsight.com/doi/full/','http://eudl.eu/doi/','http://www.emeraldinsight.com/doi/full/','http://journals.sagepub.com/doi/pdf/','https://www.tandfonline.com/doi/abs/','http://doi.ieeecomputersociety.org/']
    for prefix in prefixes:   
        if removedSpace.startswith(prefix):
            removedPrefix=removedSpace[len(prefix):]
            if removedPrefix.startswith('10.'):
                doi=removedPrefix
            elif prefix=="http://dl.acm.org/citation.cfm?doid=": 
                doi="10.1145/"+ removedPrefix
            else:
                print("ERROR")
            #write(doi, 'si')
    
