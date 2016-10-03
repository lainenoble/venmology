from flask import render_template, send_file, redirect, url_for
from flask import request
from flaskapp import app
import numpy as np
import pandas as pd
from sqlalchemy import create_engine

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import psycopg2
import networkx as nx
from sklearn.linear_model import LogisticRegression


import threading # this is for periodically retraining
import datetime

import StringIO
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.figure import Figure
import base64

# Establish database connection

# For working locally
# dbuser = 'lainenoble' #add your username here (same as previous postgreSQL)   
# host = 'localhost'
# dbname = 'venmo_db'
# db = create_engine('postgres://%s@%s/%s'%(dbuser,host,dbname))
# password = ''

# For working on EC2/RDS
dbuser = 'lainenoble' #add your username here (same as previous postgreSQL)            
host = 'venmo.cnjwpcz1pk7b.us-west-2.rds.amazonaws.com'
password = '7rB-pEE-3tg-sby'
dbname = 'venmo'
db = create_engine('postgres://%s:%s@%s/%s'%(dbuser,password,host,dbname))

def establish_connection():
    con = None
    con = psycopg2.connect(database = dbname, user = dbuser, password = password, host = host)
    return con
    

def train_model():
    global query_results
    print(datetime.datetime.now())
    print('training...')
    con = establish_connection()
    # Extract training set
    business_query = "SELECT * FROM users WHERE flagged_as_business=TRUE;"
    businesses = pd.read_sql_query(business_query,con)
    
    nonbusiness_query = "SELECT * FROM users WHERE flagged_as_business=FALSE"
    nonbusinesses = pd.read_sql_query(business_query,con)

    #sampling_query = "SELECT * FROM users WHERE flagged_as_business IS NULL LIMIT 500;"
    sampling_query = "SELECT * FROM users WHERE RANDOM()<.0001 AND flagged_as_business IS NULL ORDER BY RANDOM() LIMIT 500;"
    sample = pd.read_sql_query(sampling_query,con)

    # Train model
    featurecols = ['transaction_count','counterparty_count','null_counterparty_count','most_common_word_count','time_var']
    Xtn=np.concatenate((sample.as_matrix(columns=featurecols),businesses.as_matrix(columns=featurecols)),axis=0)
    ytn=np.concatenate((np.zeros((sample.shape[0],)),np.ones((businesses.shape[0],))),axis=0)
    #Xtn=np.concatenate((sample.as_matrix(columns=featurecols),nonbusinesses.as_matrix(columns=featurecols),businesses.as_matrix(columns=featurecols)),axis=0)
    #ytn=np.concatenate((np.zeros((sample.shape[0]+nonbusinesses.shape[0],)),np.ones((businesses.shape[0],))),axis=0)

    model=LogisticRegression()
    model.fit(Xtn,ytn)

    # Get users to be classified
    sql_query = "SELECT * FROM users WHERE transaction_count>10 AND flagged_as_business IS NULL;"
    query_results = pd.read_sql_query(sql_query, con)
    
    con.close()

    query_results['prediction']=model.predict(query_results[featurecols])
    query_results['prob']=model.predict_proba(query_results[featurecols])[:,1]
    
    query_results.sort_values(by='prob',ascending=False,inplace=True)
    query_results = query_results.head(n=500)
    query_results = query_results.round(3)
    query_results = query_results.set_index('id',drop=False) #so that rows can be easily dropped as users are flagged
    print('done!')
    training_timer = threading.Timer(7200,train_model)
    training_timer.daemon = True
    training_timer.start()

#     query= "SELECT * FROM users WHERE transaction_count>20 LIMIT 100;"
#     query_results = pd.read_sql_query(query,con)
#     return query_results

#query_results=train_model()
train_model()


        
@app.route('/')
def mainpage():
    suspects = query_results.to_dict('records')
    #query = "SELECT * FROM users WHERE transaction_count>10 AND flagged_as_business IS NULL ORDER BY prob LIMIT 500;"
    return render_template("mainpage.html",suspects=suspects)

@app.route('/user/<user_id>', methods=['GET'])
def user(user_id):
    plt.clf()
    con = establish_connection()
    
    user_query="SELECT * FROM transactions WHERE actor = %(user_id)s OR target = %(user_id)s;"
    # NOTE: using %(user_id)s [see psycopg2 documentation] prevents sql injection
    user_query_results = pd.read_sql_query(user_query, con,params={'user_id':user_id})
    tn_count=len(user_query_results.index)
    
        # add user name to title
    name_query="SELECT * FROM users WHERE id='{0}';".format(str(user_id))
    name_query_results_dict=pd.read_sql_query(name_query,con).to_dict('records')[0]
    
    cp_query="""WITH both_ends AS (SELECT actor, target
            FROM transactions 
            WHERE transactions.actor='{0}' OR transactions.target='{0}'),
            parties AS (SELECT actor AS id from both_ends UNION SELECT target AS id from both_ends)
            SELECT actor, target,type
            FROM parties AS a JOIN transactions ON a.id=transactions.actor
            JOIN parties AS b ON transactions.target=b.id;""".format(str(user_id))
    cp_query_results = pd.read_sql_query(cp_query,con)
        
    con.close()
    
    # transaction timing visualization
    hist_img_data=''
    if True:
        plt.clf()
        plt.figure(figsize=(12, 9))
        ax = plt.subplot(111)
        dstart=datetime.datetime(2016,8,22)
        dend=datetime.datetime(2016,9,6)
        days=[dstart+datetime.timedelta(days=i,hours=12) for i in range(0,15)]
        user_hist = user_query_results.created_time.hist(xrot=90,grid=False, bins=len(days),range=(dstart,dend),edgecolor='w',lw=5)
        plt.xlim(dstart,dend)
        plt.xticks(days,[day.strftime('%a %b %d') for day in days],fontsize=18)
        plt.yticks(fontsize=18)
        # TODO: maybe change color?
        
        ax.spines["top"].set_visible(False)    
        ax.spines["bottom"].set_visible(False)    
        ax.spines["right"].set_visible(False)    
        ax.spines["left"].set_visible(False)
        ax.get_xaxis().tick_bottom()    
        ax.get_yaxis().tick_left() 
        
        plt.tight_layout()
        user_hist.get_figure().patch.set_alpha(0) #removes ugly gray background box
        canvas = FigureCanvas(user_hist.get_figure())
        png_output = StringIO.StringIO()
        canvas.print_png(png_output)
        hist_img_data = base64.standard_b64encode(png_output.getvalue())
    
    
    user_query_results.sort_values(by='created_time',ascending=False,inplace=True)
    transactions=user_query_results.to_dict('records')
    
    
    nx_img_data=''
    DG=nx.DiGraph()
    if True:
        # user network visualization
        DG=nx.DiGraph()
        DG.add_node(str(user_id))
        for i in range(0,user_query_results.shape[0]):
            if user_query_results.loc[i]['type']=='payment':
                DG.add_edge(user_query_results.loc[i]['actor'],user_query_results.loc[i]['target'])
            else:
                DG.add_edge(user_query_results.loc[i]['target'],user_query_results.loc[i]['actor'])
        remitter_count = DG.out_degree(str(user_id))
        payee_count = DG.in_degree(str(user_id))
        for i in range(0,min(cp_query_results.shape[0],30)):
            if cp_query_results.loc[i]['type']=='payment':
                DG.add_edge(cp_query_results.loc[i]['actor'],cp_query_results.loc[i]['target'])
            else:
                DG.add_edge(cp_query_results.loc[i]['target'],cp_query_results.loc[i]['actor'])
        colorlist=['b' for node in DG.nodes()]
        colorlist[DG.nodes().index(str(user_id))]='r' #so that the user in question has red node
    
        plt.clf()
        fig = Figure()
        ax = fig.add_subplot(111)
        nx.draw(DG,with_labels=False,node_color=colorlist,arrows=True,font_weight='bold',ax=ax,linewidths=0,edgecolor='w')
        canvas = FigureCanvas(fig)
        png_output = StringIO.StringIO()
        canvas.print_png(png_output)
        nx_img_data = base64.standard_b64encode(png_output.getvalue())
        
    
    
    return render_template("user.html",
        user_id=user_id, 
        user_info=name_query_results_dict, 
        transactions=transactions, 
        remitter_count = remitter_count,
        payee_count = payee_count,
        hist_img_data=hist_img_data,
        nx_img_data=nx_img_data)
        
@app.route('/user/<user_id>',methods=['POST'])
def user_patch(user_id):
    print "flagged as business: "+str(request.form['flagged_as_business'])
    # Find the user with id user_id
    # Update the database record with whatever was passed in as the flagged_as_business parameter
    sqlalchemy_connection = db.connect()
    sql_stmt = "UPDATE users SET flagged_as_business = %(flagged_as_business)s WHERE id = %(user_id)s;"
    sqlalchemy_connection.execute(sql_stmt, user_id=user_id,flagged_as_business=request.form['flagged_as_business'])
    sqlalchemy_connection.close()
    # remove the user from the "suspects" data frame so that they no longer show up on mainpage
    query_results.drop(str(user_id),axis=0,inplace=True, errors='ignore')
    
    return redirect(url_for('mainpage'))
    
@app.route('/search')
def search():
    input = request.args.get('search_terms')
    con = establish_connection()
    search_query = """SELECT * FROM users WHERE
                    username LIKE '%{0}%' OR
                    name LIKE '%{0}%' OR
                    id = '{0}';""".format(input)
    search_results = pd.read_sql_query(search_query,con)
    con.close()
    search_results = search_results.to_dict('records')
                    
    return render_template("results.html",results = search_results)
    
@app.route('/presentation')
def presentation():
    #return send_file('/Users/lainenoble/Desktop/venmo/venmo_app_files/flaskapp/static/index.html',mimetype='text/html')
    return render_template("embed_presentation.html")
