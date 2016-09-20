from flask import render_template, send_file, redirect, url_for
from flask import request
from flaskapp import app
import numpy as np
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy_utils import database_exists,create_database

import matplotlib.pyplot as plt
import psycopg2
import networkx as nx
from sklearn.linear_model import LogisticRegression

import StringIO
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.figure import Figure
import base64



dbuser = 'lainenoble' #add your username here (same as previous postgreSQL)            
host = 'localhost'
dbname = 'venmo_db'
db = create_engine('postgres://%s@%s/%s'%(dbuser,host,dbname))
con = None
con = psycopg2.connect(database = dbname, user = dbuser)
sqlalchemy_connection = db.connect()

# Extract training set
business_query = "SELECT * FROM users WHERE flagged_as_business=TRUE;"
businesses = pd.read_sql_query(business_query,con)

#sampling_query = "SELECT * FROM users WHERE RANDOM()<.0001 AND flagged_as_business IS NULL ORDER BY RANDOM() LIMIT 500;"
sampling_query = "SELECT * FROM users WHERE flagged_as_business IS NULL LIMIT 500;"
sample = pd.read_sql_query(sampling_query,con)

# Train model
featurecols = ['transaction_count','counterparty_count','null_counterparty_count']
Xtn=np.concatenate((sample.as_matrix(columns=featurecols),businesses.as_matrix(columns=featurecols)),axis=0)
ytn=np.concatenate((np.zeros((sample.shape[0],)),np.ones((businesses.shape[0],))),axis=0)

model=LogisticRegression()
model.fit(Xtn,ytn)

sql_query = "SELECT * FROM users WHERE transaction_count>20 AND flagged_as_business IS NOT TRUE;"
query_results = pd.read_sql_query(sql_query, con)

query_results['prediction']=model.predict(query_results[featurecols])

        
@app.route('/')
def mainpage():
    # for i in range(0,mainpage_query_results.shape[0]):
#         if mainpage_query_results.iloc[i]['flagged_as_business']:
#             continue
#         suspects.append(dict(mainpage_query_results.iloc[i]))
    # suspects=[{'id':'83295','username':'Laine','date_created':'2016_09_15'}]
    #query_results = query_results[query_results['flagged_as_business'==False]]
    suspects = query_results[query_results['prediction']==1].to_dict('records')
    return render_template("mainpage.html",suspects=suspects)

@app.route('/user/<user_id>', methods=['GET'])
def user(user_id):
    plt.clf()
    user_query="SELECT * FROM transactions WHERE actor = %(user_id)s OR target = %(user_id)s LIMIT 100;"
    # NOTE: using %(user_id)s [see psycopg2 documentation] prevents sql injection
    user_query_results = pd.read_sql_query(user_query, con,params={'user_id':user_id})
    import matplotlib
    
    # transaction timing visualization
    
    
    images=False
    hist_img_data=''
    if images:
    # passed axis not bound to passed figure ?? (or vice versa?)
        plt.clf()
        fig=Figure()
        ax=fig.add_subplot(111)
        pd.to_datetime(user_query_results.created_time).hist(bins=20,ax=ax)
        canvas=FigureCanvas(fig)
        png_output = StringIO.StringIO()
        canvas.print_png(png_output)
        hist_img_data = base64.standard_b64encode(png_output.getvalue())
    
    
    
    transactions=[]
    for i in range(0,user_query_results.shape[0]):
        print i
        transactions.append(dict(user_query_results.iloc[i]))
    
    
    nx_img_data=''
    DG=nx.DiGraph()
    if images:
        # user network visualization
        DG=nx.DiGraph()
        DG.add_node(str(user_id))
        for i in range(0,user_query_results.shape[0]):
            if user_query_results.loc[i]['type']=='payment':
                DG.add_edge(user_query_results.loc[i]['actor'],query_results.loc[i]['target'])
            else:
                DG.add_edge(user_query_results.loc[i]['target'],query_results.loc[i]['actor'])
        colorlist=['b' for node in DG.nodes()]
        colorlist[DG.nodes().index(str(user_id))]='r' #so that the user in question has red node
    
        plt.clf()
        fig=Figure()
        ax=fig.add_subplot(111)
        nx.draw(DG,with_labels=True,node_color=colorlist,arrows=True,font_weight='bold',ax=ax)
        canvas=FigureCanvas(fig)
        png_output = StringIO.StringIO()
        canvas.print_png(png_output)
        nx_img_data = base64.standard_b64encode(png_output.getvalue())
        
    # add user name to title
    name_query="SELECT username, flagged_as_business FROM users WHERE id='{0}';".format(str(user_id))
    name_query_results=pd.read_sql_query(name_query,con)
    username=name_query_results.loc[0]['username']
    flagged_as_business = name_query_results.loc[0]['flagged_as_business']
    
    return render_template("user.html",user_id=user_id, username=username, flagged_as_business=flagged_as_business,transactions=transactions,
        hist_img_data=hist_img_data,nx_img_data=nx_img_data,counterparties=len(DG.nodes())-1)
        
@app.route('/user/<user_id>',methods=['POST'])
def user_patch(user_id):
    print "INSIDE THE POST THINGY"
    print "user id: "+str(user_id)
    # Find the user with id user_id
    # Update the database record with whatever was passed in as the flagged_as_business parameter
    sql_stmt = "UPDATE users SET flagged_as_business = TRUE WHERE id = %(user_id)s;"
    sqlalchemy_connection.execute(sql_stmt, user_id=user_id)
    query_results.flagged_as_business[query_results.id==user_id]=True
    return redirect(url_for('user', user_id=user_id))
    
@app.route('/user_search')
def user_search():
    input = request.args.get('user_id')
    return redirect(url_for('user',user_id=input))