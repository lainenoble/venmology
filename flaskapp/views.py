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

import matplotlib

import StringIO
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.figure import Figure
import base64

# For working locally
dbuser = 'lainenoble' #add your username here (same as previous postgreSQL)   
host = 'localhost'
dbname = 'venmo_db'
db = create_engine('postgres://%s@%s/%s'%(dbuser,host,dbname))
con = None
con = psycopg2.connect(database = dbname, user = dbuser)
sqlalchemy_connection = db.connect()

# For working on EC2/RDS
# dbuser = 'lainenoble' #add your username here (same as previous postgreSQL)            
# host = 'venmo.cnjwpcz1pk7b.us-west-2.rds.amazonaws.com:5432'
# password = '7rB-pEE-3tg-sby'
# dbname = 'venmo'
# db = create_engine('postgres://%s:%s@%s/%s'%(dbuser,password,host,dbname))
# con = None
# con = psycopg2.connect(database = dbname, user = dbuser, password = password, host = host)
# sqlalchemy_connection = db.connect()

# Extract training set
business_query = "SELECT * FROM users WHERE flagged_as_business=TRUE;"
businesses = pd.read_sql_query(business_query,con)

#sampling_query = "SELECT * FROM users WHERE flagged_as_business IS NULL LIMIT 500;"
sampling_query = "SELECT * FROM users WHERE RANDOM()<.0001 AND flagged_as_business IS NULL ORDER BY RANDOM() LIMIT 500;"
sample = pd.read_sql_query(sampling_query,con)

# Train model
featurecols = ['transaction_count','counterparty_count','null_counterparty_count']
Xtn=np.concatenate((sample.as_matrix(columns=featurecols),businesses.as_matrix(columns=featurecols)),axis=0)
ytn=np.concatenate((np.zeros((sample.shape[0],)),np.ones((businesses.shape[0],))),axis=0)

model=LogisticRegression()
model.fit(Xtn,ytn)

sql_query = "SELECT * FROM users WHERE transaction_count>20 AND flagged_as_business IS NULL;"
query_results = pd.read_sql_query(sql_query, con)

query_results['prediction']=model.predict(query_results[featurecols])
query_results=query_results[query_results['prediction']==1]
query_results=query_results.set_index('id',drop=False) #so that rows can be easily dropped as users are flagged


        
@app.route('/')
def mainpage():
    suspects = query_results.to_dict('records')
    return render_template("mainpage.html",suspects=suspects)

@app.route('/user/<user_id>', methods=['GET'])
def user(user_id):
    plt.clf()
    user_query="SELECT * FROM transactions WHERE actor = %(user_id)s OR target = %(user_id)s;"
    # NOTE: using %(user_id)s [see psycopg2 documentation] prevents sql injection
    user_query_results = pd.read_sql_query(user_query, con,params={'user_id':user_id})
    tn_count=len(user_query_results.index)
    
    # transaction timing visualization
    hist_img_data=''
    if True:
        plt.clf()
        user_hist = pd.to_datetime(user_query_results.created_time).hist(bins=15,xrot=30)
        # TODO: set x limits to be whole date range of database
        # TODO: specify xticklabels via ax.set_xticklabels(xtl)
        # TODO: adjust label sizes
        # TODO: maybe change color?
        plt.tight_layout()
        user_hist.get_figure().patch.set_alpha(0) #removes ugly gray background box
        canvas = FigureCanvas(user_hist.get_figure())
        png_output = StringIO.StringIO()
        canvas.print_png(png_output)
        hist_img_data = base64.standard_b64encode(png_output.getvalue())
    
    
    
    transactions=user_query_results.to_dict('records')
    
    
    nx_img_data=''
    DG=nx.DiGraph()
    if True:
        # user network visualization
        DG=nx.DiGraph()
        DG.add_node(str(user_id))
        for i in range(0,min(user_query_results.shape[0],30)):
            if user_query_results.loc[i]['type']=='payment':
                DG.add_edge(user_query_results.loc[i]['actor'],user_query_results.loc[i]['target'])
            else:
                DG.add_edge(user_query_results.loc[i]['target'],user_query_results.loc[i]['actor'])
        colorlist=['b' for node in DG.nodes()]
        colorlist[DG.nodes().index(str(user_id))]='r' #so that the user in question has red node
    
        plt.clf()
        fig = Figure()
        ax = fig.add_subplot(111)
        # TODO: try messing with this, see if it can be sped up
        nx.draw(DG,with_labels=False,node_color=colorlist,arrows=True,font_weight='bold',ax=ax)
        canvas = FigureCanvas(fig)
        png_output = StringIO.StringIO()
        canvas.print_png(png_output)
        nx_img_data = base64.standard_b64encode(png_output.getvalue())
        
    # add user name to title
    name_query="SELECT username, flagged_as_business,transaction_count,counterparty_count FROM users WHERE id='{0}';".format(str(user_id))
    name_query_results=pd.read_sql_query(name_query,con)
    username=name_query_results.loc[0]['username']
    cp_count = name_query_results.loc[0]['counterparty_count']
    flagged_as_business = name_query_results.loc[0]['flagged_as_business']
    
    return render_template("user.html",user_id=user_id, username=username, flagged_as_business=flagged_as_business,transactions=transactions,
        hist_img_data=hist_img_data,nx_img_data=nx_img_data,transaction_count=tn_count,counterparties=cp_count)
        
@app.route('/user/<user_id>',methods=['POST'])
def user_patch(user_id):
    print "INSIDE THE POST THINGY"
    print "user id: "+str(user_id)
    print "flagged as business: "+str(request.form['flagged_as_business'])
    # Find the user with id user_id
    # Update the database record with whatever was passed in as the flagged_as_business parameter
    sql_stmt = "UPDATE users SET flagged_as_business = %(flagged_as_business)s WHERE id = %(user_id)s;"
    sqlalchemy_connection.execute(sql_stmt, user_id=user_id,flagged_as_business=request.form['flagged_as_business'])
    # remove the user from the "suspects" data frame so that they no longer show up on mainpage
    query_results.drop(str(user_id),axis=0,inplace=True) # this line causing "query results referenced before assignment"??
    

    return redirect(url_for('user', user_id=user_id))
    
@app.route('/user_search')
def user_search():
    input = request.args.get('user_id')
    return redirect(url_for('user',user_id=input))