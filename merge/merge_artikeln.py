
from lxml import etree
import os
import datetime
import random
import psycopg2
import sqlite3




#Verbindung zum Postgress-Server, auf dem die Daten aus der dblp- und finele-Datenbank gespeichert werden
server_ = 'localhost'
database = 'anetz'
id_='postgres'
pw='Girasole123'

conn = psycopg2.connect(
                        host=server_,
                        dbname=database,
                        user=id_,
                        password=pw,
                        port=5433)


print("DB Connected..")
cursor = conn.cursor()

#Verbindung zum Sqlite-Server, auf dem die Daten von crossref gespeichert sind
conn2 = sqlite3.connect('crossref.db')
print("sqlite DB Connected..")
cursor2 = conn2.cursor()


#Speicherfunktion für den Vergleich von zwei Elementen, die nur aufgerufen wird, wenn die beiden Elemente nicht gleich sind
def confront(check,doi, d1, d2):
    date_ = str(datetime.date.today().isocalendar())
    logfilename= "/rasp_errors/confront" + date_ +".txt" 
    path = os.getcwd()+logfilename
    log="["+ str(datetime.datetime.now()) + "] "+ doi + "---------------"+ check + "\n" + str(d1) + "\n" + str(d2) + "\n" 
    with open(path, 'a',encoding="utf8") as f:
        f.write(log)
        f.close()

#Speicherfunktion für doi nicht in crossref vorhanden
def absent_doi(doi):
    date_ = str(datetime.date.today().isocalendar())
    logfilename= "/rasp_errors/absent" + date_ +".txt" 
    path = os.getcwd()+logfilename
    log="["+ str(datetime.datetime.now()) + "] "+ doi + "\n" 
    with open(path, 'a',encoding="utf8") as f:
        f.write(log)
        f.close()

#Alle Veröffentlichungen in der Postgresql-Datenbank
cursor.execute("""SELECT * FROM publication""") #
dois=cursor.fetchall()

n=0

for i in dois:
    n+=1
    #Prüfung, ob die doi in der crossref-Datenbank vorhanden ist
    current_doi=i[0]
    cursor2.execute("""SELECT * FROM documents WHERE doi = '%s'""" % current_doi)
    cfr = cursor2.fetchone()
    if cfr==None:
        absent_doi(current_doi)
    else:
        #Vergleicht crossref-Daten mit dblp-Daten und speichert die Unterschiede
        #Der Vorgang ist sehr langsam, aber für Datenbankanalysen sehr nützlich.
        cfr=list(cfr)
        title1=i[1]
        title2=cfr[1]
        if title1!=title2:
            confront("TITLE", current_doi, title1, title2)

        year1=i[2]
        year2=cfr[3][-4:]
        if year1!=year2:
            confront("VOLUME", current_doi, year1, year2)
            if year1==None and year2!="missing":
                cursor.execute ("""update publication SET year='%s' WHERE doi = '%s' """% (year2, current_doi))
                conn.commit()


        volume1=i[3]
        volume2=cfr[5]
        if volume1!=volume2:
            confront("VOLUME", current_doi, volume1, volume2)
            if volume1==None and volume2!="missing":
                cursor.execute ("""update publication SET volume='%s' WHERE doi = '%s' """% (volume2, current_doi))
                conn.commit()


        issue1=i[4]
        issue2=cfr[4]
        if issue1!=issue2:
            confront("ISSUE", current_doi, issue1, issue2)
            if issue1==None and issue2!="missing":
                cursor.execute ("""update publication SET issue='%s' WHERE doi = '%s' """% (issue2, current_doi))
                conn.commit()


        pages1=i[5]
        pages2=cfr[7]
        if pages1!=pages2:
            confront("PAGES", current_doi, pages1, pages2)
            if pages1==None and pages2!="missing":
                cursor.execute ("""update publication SET pages='%s' WHERE doi = '%s' """% (pages2, current_doi))
                conn.commit()


        url1=i[7]
        url2=cfr[10]
        if url1!=url2:
            confront("URL", current_doi, url1, url2)
            if url1==None and url2!="missing":
                cursor.execute ("""update publication SET url='%s' WHERE doi = '%s' """% (url2, current_doi))
                conn.commit()


        abstract=cfr[2]
        if abstract!='missing':
            abstract = abstract.replace("'", "''")
            cursor.execute ("""update publication SET abstract='%s' WHERE doi = '%s' """% (abstract, current_doi))
            conn.commit()
        print(n)
conn2.close()
conn.close()
print("END")