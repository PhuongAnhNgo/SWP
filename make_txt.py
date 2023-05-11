
import pyodbc
from PWS import SQL

def write(doi, url): 
    path= "C:/Users/chicc/Desktop/Neuer Ordner/data.txt" 
    data=doi + ";"+ url + "\n"
    with open(path, 'a') as f:
        f.write(data)
        f.close()


print("Connecting..")
conn = pyodbc.connect('Driver={ODBC Driver 13 for SQL Server};Server='+ SQL()[0]+',1433;Database='+ SQL()[1]+';Uid='+ SQL()[2]+';Pwd={'+ SQL()[3]+'};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;')
print("DB Connected..")
cursor = conn.cursor()

data = cursor.execute('SELECT "doi","url"  FROM "Publications"').fetchall()

for i in data:
    write(i[0], str(i[1] or ''))

