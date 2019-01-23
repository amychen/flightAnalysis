from flask import Flask, render_template, request
from sqlalchemy import create_engine
import matplotlib
import matplotlib.pyplot as plt
matplotlib.use('Agg')
import pandas as pd
import time  
from sklearn.cluster import KMeans,DBSCAN
from sklearn.preprocessing import StandardScaler, Normalizer
import seaborn as sns
from pandas.tools.plotting import table

app = Flask(__name__)
conn_string = 'mysql://{user}:{password}@{host}/{db}?charset=utf8'.format(
    user='root', 
    password='x3rGjkz93e6CIkd7', 
    host = '35.237.252.223',  
    db='kayak'
)
engine = create_engine(conn_string)
con = engine.connect()

@app.route("/summary")
def home():
    default_data = con.execute("SELECT * FROM kayak.flight A INNER JOIN \
                                ( \
                                    SELECT MIN(Price) as Price, Destination FROM kayak.flight \
                                    WHERE Date(Timestamp) = '2018-12-11' GROUP BY Destination \
                                ) B on A.Destination = B.Destination \
                                AND A.Price = B.Price AND Date(Timestamp) = '2018-12-11' ")
    
    avg_bos, date_bos = graph('BOS')[0], graph('BOS')[1]
    avg_sfo, avg_las = graph('SFO')[0], graph('LAS')[0]
    avg_lax, avg_chi = graph('LAX')[0], graph('CHI')[0]
    avg_sea, avg_den = graph('SEA')[0], graph('DEN')[0]
    avg_dca, avg_orl = graph('DCA')[0], graph('ORL')[0]
    
    return render_template('home.html', default_data=default_data, avg_bos=avg_bos, date_bos=date_bos, avg_sfo = avg_sfo, avg_las=avg_las, avg_lax=avg_lax, avg_chi=avg_chi, avg_sea=avg_sea, avg_den=avg_den, avg_dca=avg_dca, avg_orl=avg_orl)

@app.route("/")
def search():
    return render_template('search.html')

@app.route("/price_over_time")
def price_over_time():
    airport = request.args.get("airport")
    date = request.args.get("date")
    
    # generate table of cheapest flights
    sql_for_table = "SELECT * FROM kayak.flight WHERE Destination=%s AND Date =%s AND Timestamp >='2018-12-01 07:00:00' ORDER BY Price, Time LIMIT 25"
    parameters = (airport,date)
    flights_for_table = con.execute(sql_for_table, parameters)
    
    # sql query for graphs
    sql = "SELECT * FROM kayak.flight WHERE Destination=%s AND Date =%s AND Timestamp >='2018-12-01 07:00:00'"
    
    flights = con.execute(sql, parameters)

    # generate table
    flights_table = pd.read_sql(sql, params=parameters, con=con)
    
    # cluster image
    kmean_table, image_filename = cluster_price_hour(add_hour(flights_table),airport,date)
    
    tab = kmean_table.to_html()
    
    # average data for top graph
    avg_data = flights_table[['Price','Timestamp']].groupby('Timestamp').mean()
    avg_data = avg_data.reset_index()
    
    # minimum data for top graph
    min_data = flights_table[['Price','Timestamp']].groupby('Timestamp').min()
    min_data = min_data.reset_index()
    
    # data for airline analytics graph
    avg_airline = flights_table[['Price','Airline']].groupby('Airline').mean().sort_values('Price')
    avg_airline = avg_airline.reset_index()
    
    avg_airline_price = avg_airline.Price.tolist()
    airline = avg_airline.Airline.tolist()
    
    # add timestamp to top graph axis
    timestamp = avg_data.Timestamp.astype('str').tolist()
    
    avg = avg_data.Price.tolist()
    Min = min_data.Price.tolist()

    # print out Kayak prediction
    kayak_pred = flights_table.Prediction.iloc[-1]
    if "rise" in kayak_pred:
        kayak_pred = "Prices predicted to rise within 7 days"
    
    accuracy_score = Kayak_Accuracy(flights_table)
    
    return render_template('flight_data.html', flights=flights_for_table, cluster=image_filename, time= timestamp, average=avg, Min = Min, airport = airport, date = date, kayak_pred=kayak_pred, avg_airline_price=avg_airline_price, airline=airline, accuracy_score = accuracy_score, kmean_table = tab)

def graph(destination):
    boston_flight = "SELECT Price, Date FROM kayak.flight WHERE Destination=\"" + destination + "\""
    boston_flight = pd.read_sql(boston_flight, con=con)
    boston_flight = boston_flight[['Price', 'Date']].groupby('Date').mean()
    boston_flight = boston_flight.reset_index()
    avg = boston_flight.Price.tolist()
    date = boston_flight.Date.tolist()
    return [avg, date]

def convert24(s):
    x = s[-2:]
    y = s[-8:-6]
    if (x == 'am') and (y == '12'):
        ss = ("00" + s[-6:-3]).strip()
    elif x == 'am' and y != '10' and y != '11':
        ss = ('0' + s[:-2]).strip()
    elif x == 'am':
        ss = s[:-2].strip()        
    elif (x == 'pm') and (y == '12'):
        ss = (s[:-2]).strip()
    else:
        ss = (str(int(y) +12) + s[-6:-3]).strip()
    return ss

def add_hour(df):
    df['24time'] = df['Time'].astype(str)
    df['converted'] = df['24time'].apply(convert24)
    df['Hour'] = pd.to_numeric(df['converted'].str.slice(0,2))
    return df
    
def cluster_price_hour(df_dest,airport,date):
    subset = df_dest[['Hour','Price']]
    subset_features = subset.columns
    
    scaler = StandardScaler()
    price_data_scaled = scaler.fit_transform(subset[subset_features])
    price_data_scaled = pd.DataFrame(price_data_scaled,columns=subset_features)
    
    kmeans = KMeans(n_clusters=2,random_state=1234)
    kmeans.fit(price_data_scaled)
    
    # K-means on scaled data
    subset['Kmeans Clusters'] = [ "cluster_" + str(label+1) for label in kmeans.labels_ ]
    kmean_center = subset.groupby('Kmeans Clusters').mean()
    kmean_center.reset_index(inplace=True)
    #kmean_center.set_index('Kmeans Clusters',inplace=True)
    
    #ax = plt.subplot(111, frame_on=False) # no visible frame

    #table(ax, kmean_center)
    #ax.xaxis.set_visible(False)  # hide the x axis
    #ax.yaxis.set_visible(False)  # hide the y axis
    #ax.axis('off')

    #table_name = 'static/table-' + airport + '_' + date + '.png'
    #plt.savefig(table_name, bbox_inches='tight', pad_inches = 0.0)
    
    
    
    # Cluster image
    subset["Price Clusters by Hour"] = ["cluster_"+str(label+1) for label in kmeans.labels_]
    sns.pairplot(subset,hue="Price Clusters by Hour")
    
    plot = sns.pairplot(subset,hue="Price Clusters by Hour")
    plot.fig.suptitle('Prices Clustered by Hour of Flight Departure')
    # Store the file under the static folder, and give a name plot-<stationid>.png
    filename = 'static/plot-'+ airport + '_' + date +'.png'
    #fig = plot.get_figure()
    plot.savefig(filename)
    #plot.clear()
    # Return back the name of the image file

    return kmean_center, filename

def Kayak_Accuracy(df):
    # find mean of prices
    price_mean = df.groupby(['Destination','Date','Timestamp']).mean()

    # create prediction dataframe
    pred_mean = price_mean.merge(df[['Destination','Date','Timestamp','Prediction']],on=['Destination','Date','Timestamp'])
    pred_mean.drop_duplicates(inplace=True)
    pred_mean['Price_Shift'] = pred_mean.Price.shift(-1)
    pred_mean['Price_Diff'] = pred_mean.Price_Shift - pred_mean.Price
    pred_mean['Rise_Fall'] = pred_mean.Price_Diff / abs(pred_mean.Price_Diff)
    pred_mean.Rise_Fall.fillna(0,inplace=True)
    
    # code prediction as single letter
    pred_code = []
    for i in pred_mean.Prediction:
        if "rise" in i:
            pred_code.append('R')
        elif 'unlikely' in i:
            pred_code.append('U')
        elif 'fall' in i:
            pred_code.append('F')
        else:
            pred_code.append('NA')

    pred_mean['Pred_Code'] = pred_code

    # Test accuracy of prediction; 1 for True, 0 for False
    accuracy = []
    for i in range(len(pred_mean.Rise_Fall)):
        if pred_mean.Pred_Code.iloc[i] == 'R' and pred_mean.Rise_Fall.iloc[i] == 1:
            accuracy.append(1)
        elif pred_mean.Pred_Code.iloc[i] == 'U' and (pred_mean.Rise_Fall.iloc[i] == 1 or pred_mean.Rise_Fall.iloc[i] == 0):
            accuracy.append(1)
        elif pred_mean.Pred_Code.iloc[i] == 'F' and pred_mean.Rise_Fall.iloc[i] == -1:
            accuracy.append(1)
        else:
            accuracy.append(0)
    
    pred_mean['Accuracy'] = accuracy
    
    # return accuracy rate
    Rise = pred_mean[pred_mean.Pred_Code == 'R']
    Fall = pred_mean[pred_mean.Pred_Code == 'F']
    No_fall = pred_mean[pred_mean.Pred_Code == 'U']

    kayak_pred = pred_mean.Pred_Code.iloc[-1]

    if kayak_pred == 'R':
        acc_rate = Rise.Accuracy.sum() / len(Rise) * 100 
    elif kayak_pred == 'F':
        acc_rate = Fall.Accuracy.sum() / len(Fall) * 100 
    elif kayak_pred == 'U':
        acc_rate = No_fall.Accuracy.sum() / len(No_fall) * 100 
    else:
        acc_rate = 0

    return round(acc_rate,2)

    
app.run(host='0.0.0.0', port=5000, debug=True)
