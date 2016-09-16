from flask import render_template, send_file
from flaskapp import app
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy_utils import database_exists,create_database
import train_logreg
import matplotlib.pyplot as plt
import psycopg2
#mylogreg=train_logreg.train_logreg()

dbuser = 'lainenoble' #add your username here (same as previous postgreSQL)            
host = 'localhost'
dbname = 'test_db'
db = create_engine('postgres://%s%s/%s'%(dbuser,host,dbname))
con = None
con = psycopg2.connect(database = dbname, user = dbuser)

@app.route('/')
def mainpage():
    suspects = [ 
        {'id':'820531',   'username':'ibotta',            'date_created':'2013-12-22'}, 
        {'id':'3371876',  'username':'paulinaparsons',    'date_created':'2015-01-14'}, 
        {'id':'3062903',  'username':'USCDKA',            'date_created':'2014-12-11'}, 
        {'id':'10532979', 'username':'Marissa-Nicole-7',  'date_created':'2016-05-03'}, 
        {'id':'2403136',  'username':'Madeline-Adolf',    'date_created':'2014-09-22'}, 
        {'id':'9141025',  'username':'SHOPDUSE',          'date_created':'2016-02-25'}, 
        {'id':'5329637',  'username':'Burair110',         'date_created':'2015-07-05'}, 
        {'id':'1787593',  'username':'Mason-Porter-1',    'date_created':'2014-07-03'}, 
        {'id':'12209948', 'username':'Marwan-Fattouhi',   'date_created':'2016-07-17'}, 
        {'id':'2526756',  'username':'Michelle-Koen',     'date_created':'2014-10-07'}, 
        {'id':'4188588',  'username':'SeatGeek',          'date_created':'2015-04-01'}, 
        {'id':'2456091',  'username':'csardini',          'date_created':'2014-09-29'}, 
        {'id':'1850842',  'username':'edmsc',             'date_created':'2014-07-15'}, 
        {'id':'4681320',  'username':'Mateo-Arenas',      'date_created':'2015-05-12'}, 
        {'id':'8448040',  'username':'dart56',            'date_created':'2016-01-19'}, 
        {'id':'7082706',  'username':'ryanelgar',         'date_created':'2015-10-26'}, 
        {'id':'13417526', 'username':'madeleineroberts',  'date_created':'2016-08-31'}, 
        {'id':'11251229', 'username':'jameswilson27',     'date_created':'2016-06-05'}, 
        {'id':'11231835', 'username':'Zae-Brown',         'date_created':'2016-06-04'}, 
        {'id':'8108954',  'username':'Jennifer-Roeske-1', 'date_created':'2015-12-31'} 
    ]

#     sql_query = """SELECT users.id, users.username, users.date_created 
#     FROM users JOIN transactions ON transactions.actor=users.id OR transactions.target=users.id
#     GROUP BY users.id
#     HAVING COUNT(*)>5;"""
#     query_results = pd.read_sql_query(sql_query, con)
#     suspects=[]
#     for i in range(0,query_results.shape[0]):
#         suspects.append(dict(query_results.iloc[i]))
    # suspects=[{'id':'83295','username':'Laine','date_created':'2016_09_15'}]
    return render_template("mainpage.html",suspects=suspects)

@app.route('/user/<user_id>')
def user(user_id):
    plt.clf()
    sql_query="SELECT * FROM transactions WHERE actor = '{0}' OR target = '{0}';".format(str(user_id))
    query_results = pd.read_sql_query(sql_query, con)
    import matplotlib
    pd.to_datetime(query_results.created_time).hist(bins=20)
    matplotlib.pyplot.savefig("flaskapp/" + user_id+ "_histogram.png")
    
    bad_sql = "SELECT COUNT(*) FROM transactions WHERE actor = '{0}' OR target = '{0}';".format(str(user_id))
    transactions=[]
    for i in range(0,query_results.shape[0]):
        print i
        transactions.append(dict(query_results.iloc[i]))
    name_query="SELECT username FROM users WHERE id='{0}';".format(str(user_id))
    query_results=pd.read_sql_query(name_query,con)
    username=query_results.loc[0][0]
    return render_template("user.html",user_id=user_id, username=username,transactions=transactions)
    
@app.route('/images/<user_id>_histogram.png')
def images_histogram(user_id):
    return send_file(user_id+"_histogram.png", mimetype='image/png')
    
# @app.route('/userpage')
# def userpage():
#     return render_template("userpage.html")
