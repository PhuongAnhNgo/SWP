
import pyodbc
from PWS import SQL

print("Connecting..")
conn = pyodbc.connect('Driver={ODBC Driver 13 for SQL Server};Server='+ SQL()[0]+',1433;Database='+ SQL()[1]+';Uid='+ SQL()[2]+';Pwd={'+ SQL()[3]+'};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;')
print("DB Connected..")
cursor = conn.cursor()



