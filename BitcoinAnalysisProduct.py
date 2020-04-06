import tkinter as tk 
from tkinter import ttk
import tkinter.messagebox

import matplotlib
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg , NavigationToolbar2Tk
from matplotlib.figure import Figure
from matplotlib import style
import matplotlib.animation as animation

import sqlite3
import numpy, math
import quandl
from sklearn import preprocessing, model_selection, svm
from sklearn.linear_model import LinearRegression
from datetime import datetime
import time

quandl.ApiConfig.api_key = "Ks1E_iRxeu81M4sNCG4i"
LARGE_FONT = ("Verdana", 12)
matplotlib.use("TkAgg")
style.use("ggplot")
ticker = 'BITFINEX/BTCUSD'

fig = Figure(figsize=(10,7), dpi=80)
sub = fig.add_subplot(211)
barFig = Figure()
barSub = fig.add_subplot(212)
dates = []
lastPrices = []
volume = []

class BitcoinAnalyzer(tk.Tk):
    
      
    def __init__(self, *args, **kwargs):
        tk.Tk.__init__(self, *args, **kwargs)
        tk.Tk.wm_title(self, "Bitcoin Price Analyzer")
        
        container = tk.Frame(self)
        
        container.pack(side="top", fill="both", expand=True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)
        
        self.frames = {}
        
        for f in (AuthenticationPage, HomePage):
            frame = f(container, self)
            self.frames[f] = frame
            frame.grid(row=0, column=0, sticky="nsew")
        
        self.showFrame(AuthenticationPage)
        
    def showFrame(self, container):
        
        frame = self.frames[container]
        frame.tkraise()
        
class AuthenticationPage(tk.Frame):
    
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        label = tk.Label(self, text="Login", font=LARGE_FONT)
        label.grid(row = 0, column=0, columnspan=2, pady=10)
        
        usernameLabel = tk.Label(self, text = "Username:")
        username = tk.Entry(self)
        usernameLabel.grid(row = 1, column=0, pady = 2, sticky = tk.E)
        username.grid(row = 1, column=1, pady = 2, stick = tk.W)
        passwordLabel = tk.Label(self, text = "Password:")
        passwordLabel.grid(row = 2, column=0, pady = 2, sticky = tk.E)
        password = tk.Entry(self)
        password.grid(row = 2, column=1, pady = 2, stick = tk.W)
        
        submitButton = ttk.Button(self, text="Submit",
                            command=lambda: authenticateUser(username.get(), password.get(), controller))
        submitButton.grid(row = 3, column=0, columnspan=2, pady=10)
        
        errorMessage = ""
        errorLabel = tk.Label(self, text=errorMessage)
        errorLabel.grid(row=4, column=0, pady = 2)
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        
class HomePage(tk.Frame):
    
    def __init__(self, parent, controller):
        
        dataAccuracy = ""
        databasePerformance = "Inserting new data took "
        
        tk.Frame.__init__(self, parent)
        label = tk.Label(self, text="Home Page", font=LARGE_FONT)
        label.grid(row = 0, column=0, columnspan=2, pady=5)
        
        newData = pullAndCleanData(ticker)
        
        conn = sqlite3.connect('BitcoinPricing.db')
        c = conn.cursor()
        c.execute("SELECT date, volume from prices")
        if int(c.fetchone()[1]) == int(round(newData.iloc[0][5])):
            dataAccuracy += "Accuracy: Pulled data matches previous pulled data. Passed"
        else:
            dataAccuracy += "Accuracy: Pulled data doesn't match previous pulled data. Failed"
        
        c.close()
        conn.close()
        
        start = time.process_time()
        insertData(newData)
        databasePerformance += str(time.process_time() - start) + " seconds"
        
        futureDataTuple = forecastPrices(newData[[ 'Last', 'HL_PCT', 'Volume' ]])
        futureData = futureDataTuple[0]
        confidenceScore = str(futureDataTuple[1])
        
        conn = sqlite3.connect('BitcoinPricing.db')
        c = conn.cursor()
        c.execute("SELECT date, last, volume from prices")
        for row in c.fetchall():
            dates.append(time.mktime(datetime.strptime(row[0], '%Y-%m-%d %H:%M:%S').timetuple()))
            lastPrices.append(row[1])
            volume.append(row[2])
    
        c.close()
        conn.close()
        
        canvas = FigureCanvasTkAgg(fig, self)
        canvas.draw()
        canvas.get_tk_widget().grid(row = 1, column=0, columnspan=2, padx=5)
        
        #toolbar = NavigationToolbar2Tk(canvas, self)
        #toolbar.update()
        #canvas._tkcanvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        
        plotData(self)
        
        filterDatesLabel = tk.Label(self, text="Filter Dates", font=LARGE_FONT)
        filterDatesLabel.grid(row = 2, column=0, columnspan=2)
        fromDateLabel = tk.Label(self, text="From Date:")
        fromDateLabel.grid(row = 3, column=0, pady=2, sticky=tk.E)
        fromDate = tk.Entry(self)
        fromDate.insert(0, '2018-01-01')
        fromDate.grid(row = 3, column=1, pady=2, sticky=tk.W)
        
        toDateLabel = tk.Label(self, text = "To Date:")
        toDateLabel.grid(row = 4, column=0, pady=2, sticky=tk.E)
        toDate = tk.Entry(self)
        toDate.insert(0, '2020-01-01')
        toDate.grid(row = 4, column=1, pady=2, sticky=tk.W)
        filterButton = ttk.Button(self, text="Filter Dates",
                            command=lambda: filterData("SELECT date, last, volume from prices WHERE date BETWEEN '" + fromDate.get() + "' AND '" + toDate.get() + "'", self))
        filterButton.grid(row = 5, column=0, pady=2, padx=2, sticky=tk.E)
        
        resetGraphButton = ttk.Button(self, text="Reset",
                            command=lambda: filterData("SELECT date, last, volume from prices", self))
        resetGraphButton.grid(row = 5, column=1, pady=2, sticky=tk.W)
        
        futurePriceLabel = tk.Label(self, text="Future Price Forecast Chart", font=LARGE_FONT)
        futurePriceStr = ""
        for i, v in futureData.iteritems():
            futurePriceStr += "Date: " + i.strftime("%B %d, %Y") + " - Price: " + "$%.2f" % round(v, 2) + "\n"
        
        futureDataText = tk.Text(self, width=35, font=('Arial', 12, 'bold'))
        futureDataText.insert(tk.END, futurePriceStr)
        confidenceScoreLabel = tk.Label(self, text="Confidence Score = " + confidenceScore)
        
        
        futurePriceLabel.grid(row = 0, column=3, padx=20,pady=5,sticky=tk.S)
        futureDataText.grid(row = 1, column=3, padx=20, sticky=tk.N)
        confidenceScoreLabel.grid(row = 3, column=3, padx=20, sticky=tk.N)
        
        monitorHealth(dataAccuracy, databasePerformance)
        
        monitorHealthButton = ttk.Button(self, text="Application Health Log", command=lambda:healthMessage())
        monitorHealthButton.grid(row = 4, column=3, padx=20, sticky=tk.N)
        
def filterData(sql, self):
    dates.clear()
    lastPrices.clear()
    volume.clear()
    conn = sqlite3.connect('BitcoinPricing.db')
    c = conn.cursor()
    c.execute(sql)
    for row in c.fetchall():
        dates.append(time.mktime(datetime.strptime(row[0], '%Y-%m-%d %H:%M:%S').timetuple()))
        lastPrices.append(row[1])
        volume.append(row[2])
    c.close()
    conn.close()

def plotData(self):
    sub.clear()
    sub.plot(numpy.array(dates).astype("datetime64[s]"), lastPrices)
    sub.set_title("Bitcoin Price Data")
    
    barSub.clear()
    barSub.plot(numpy.array(dates).astype("datetime64[s]"), volume)
    barSub.set_title("Volume")
    
def authenticateUser(user, password, controller):
    conn = sqlite3.connect('BitcoinPricing.db')
    c = conn.cursor()
    c.execute("SELECT password from users WHERE username = '" + user + "'")
    dbPassword = None
    
    try:
        dbPassword = c.fetchall()[0][0]
    except IndexError:
        print("That user isn't in the database")
    if password == dbPassword:
        controller.showFrame(HomePage)
    else:
        print("Error: Not the password for that user")
        tk.messagebox.showerror("Error", "Username or password is wrong")
    
    c.close()
    conn.close()
    
def pullAndCleanData(ticker):
    dataFrame = quandl.get(ticker)
    dataFrame['HL_PCT'] = (dataFrame['High'] - dataFrame['Last']) / dataFrame['Last'] * 100
    dataFrame['Date'] = dataFrame.index
    dataFrame = dataFrame[['Date', 'High', 'Low', 'HL_PCT', 'Last', 'Volume']]
    dataFrame.fillna(-99999, inplace=True) 
    return dataFrame
        
def insertData(dataFrame):
    conn = sqlite3.connect('BitcoinPricing.db')
    c = conn.cursor()
    for row in dataFrame.itertuples(index=True, name='Pandas'):
        date = str(getattr(row, "Date"))
        high = str(round(getattr(row, "High")))
        low = str(round(getattr(row, "Low")))
        HL_PCT = str(round(getattr(row, "HL_PCT"),2))
        last = str(round(getattr(row, "Last")))
        volume = str(round(getattr(row, "Volume")))
        c.execute("INSERT INTO prices (date, high, low, HL_PCT, last, volume) SELECT '"
            + date + "', " + high + ", " + low + ", " + HL_PCT + ", " + last + ", " + volume
            + " WHERE NOT EXISTS (SELECT * FROM prices WHERE date = '" + date + "');")
    conn.commit()
    c.close()
    conn.close()
    
def monitorHealth(dataAccuracy, databasePerformance):
    
    f = open("healthLog.txt", "a+")
    dateString = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    f.write(dateString + "\n" + dataAccuracy + "\n" + databasePerformance + "\n\n")
    f.close()
    
def healthMessage():
    logData = ""
    f = open("healthLog.txt", "r")
    lines = f.readlines()
    for line in lines:
        logData += line
    tkinter.messagebox.showinfo("Health Info", logData)
    f.close()
    
def forecastPrices(dataFrame):
   
    forecastOut = int(math.ceil(0.01*len(dataFrame)))
    dataFrame['label'] = dataFrame['Last'].shift(-forecastOut)
    
    X = numpy.array(dataFrame.drop(['label'],1))
    X = preprocessing.scale(X)
    recentX = X[-forecastOut:]
    X = X[:-forecastOut]
    
    y = numpy.array(dataFrame['label'])
    y = y[:-forecastOut]

    X_train, X_test, y_train, y_test = model_selection.train_test_split(X, y, test_size=0.2)
    
    classifier = LinearRegression(n_jobs=-1)
    classifier.fit(X_train, y_train)
    score = round(classifier.score(X_test, y_test),2)
    print(score)
    futurePrices = classifier.predict(recentX)
    
    dataFrame['Forecast'] = numpy.nan
    lastDay = dataFrame.iloc[-1].name
    lastUnix = lastDay.timestamp()
    oneDay = 86400
    nextUnix = lastUnix + oneDay + oneDay
    
    for i in futurePrices:
        nextDay = datetime.fromtimestamp(nextUnix)
        nextUnix += oneDay
        dataFrame.loc[nextDay] = [numpy.nan for _ in range(len(dataFrame.columns)-1)] + [i]
        
    return (dataFrame['Forecast'][-forecastOut:], score)
    
    
app = BitcoinAnalyzer()

app.geometry("1280x720")
ani = animation.FuncAnimation(fig, plotData, interval=1000)
app.mainloop()
