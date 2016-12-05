import MySQLdb

conn= MySQLdb.connect(
        host='localhost',
        port = 3306,
        user='root',
        passwd='root',
        db ='mode',
        )

cur = conn.cursor()
aa=cur.execute("select * from md_user_authority")
print aa

cur.close()
conn.commit()
conn.close()
cur = conn.cursor()