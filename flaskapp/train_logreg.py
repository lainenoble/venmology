def train_logreg():
    #load training set
    import pandas as pd
    import datetime
    
    transactions=pd.read_csv('~/Desktop/venmo/data/twoweeks/twoweeks_trans.csv')
    users=pd.read_csv('~/Desktop/venmo/data/twoweeks/twoweeks_users.csv')
    def payee(trans):
        if trans['type']=='payment':
            return trans['target']
        else: #transaction is a charge i.e. request for money
            return trans['actor']
    transactions['payee']=transactions.apply(payee,axis=1)

    users=users[users['date_created'].isnull()!=True]
    users=users.drop_duplicates()
    users=users.sample(2000)
    
    list0=users.loc[0]
    list0['id']=0
    list0['external_id']=0
    list0['name']='email'
    list0['firstname']='email'
    list0['lastname']='email'
    list0['username']='email'
    users.loc[0]=list0

    users=users.set_index('id')
    users['actor_count']=transactions.actor.value_counts()
    users['target_count']=transactions.target.value_counts()
    users['payee_count']=transactions.payee.value_counts()
    users['target_counterparties']=transactions.groupby('actor').target.nunique()
    users['actor_counterparties']=transactions.groupby('target').actor.nunique()

    users['target_counterparties']=users['target_counterparties'].fillna(0)
    users['actor_counterparties']=users['actor_counterparties'].fillna(0)
    users['target_count']=users['target_count'].fillna(0)
    users['actor_count']=users['actor_count'].fillna(0)
    users['payee_count']=users['payee_count'].fillna(0)
    transactions['message']=transactions['message'].fillna('')

    users['transaction_count']=users['actor_count']+users['target_count']
    users_without_transactions=users[users['transaction_count']==0]
    users=users[users['transaction_count']>0]
    users['payee_prop']=users['payee_count']/users['transaction_count']
    users['actor_prop']=users['actor_count']/users['transaction_count']
    users['counterparties_per_transaction']=(users['target_counterparties']+users['actor_counterparties'])/users['transaction_count']

    users['firstname']=users['firstname'].fillna('')
    users['lastname']=users['lastname'].fillna('')
    users['name']=users['name'].fillna('')

    businesses=pd.read_csv('~/Desktop/venmo/lowhangingfruit.csv')
    businesses=businesses[businesses['transaction_count']>0]

    featurecols=['transaction_count','payee_prop','actor_prop','counterparties_per_transaction']
    Xtn=users.as_matrix(columns=featurecols)
    ytn=np.concatenate((np.zeros((Xtn.shape[0],)),np.ones((businesses.shape[0],))),axis=0)
    Xtn=np.concatenate((Xtn,businesses.as_matrix(columns=featurecols)),axis=0)

    users.reset_index()

    from sklearn.linear_model import LogisticRegression
    mylogreg=LogisticRegression()

    mylogreg.fit(Xtn,ytn)

    return mylogreg