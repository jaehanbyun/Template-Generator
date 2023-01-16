import pymysql

db = pymysql.connect(host='localhost',
                     port=3306,
                     user='root',
                     passwd='hana0304',
                     db='template',
                     charset='utf8')
