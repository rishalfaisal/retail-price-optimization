import psycopg2
import pandas as pd
from statsmodels.formula.api import ols
import numpy as np
import streamlit as st
import os

DATABASE_URL = os.environ['DATABASE_URL']

#Page Config
st.set_page_config(page_title='Retail Price Optimisation',layout="wide")

#For whole data
#df3  = pd.read_csv("https://raw.githubusercontent.com/Charlie005/price-optimization/master/Products.csv")
#For small data
df3 = pd.read_csv("https://raw.githubusercontent.com/Charlie005/price-optimization/master/smallProducts.csv")

names = ['< PRODUCT >']
categories = ['< CATEGORY >'] + sorted(df3['MC'].unique().tolist())
brands = ['< BRAND >']
# cName = df['NAME'].value_counts()
zones = ['< ZONE >']

# Title

st.title("Retail Price Optimisation")

cont = st.container()

col1, col2, col3, col4 = cont.columns(4)

category = col1.selectbox('Select Category',categories,index=categories.index('< CATEGORY >'))
if (category != '< CATEGORY >' ):
    val = df3.loc[(df3['MC'] == category)]
    brands = ['< BRAND >'] + sorted(val['Brand'].unique().tolist())
brand = col2.selectbox('Select Brand',brands,index = brands.index('< BRAND >'))
if(brand != '< BRAND >'):
    val = df3.loc[(df3['MC'] == category) & (df3['Brand'] == brand)]
    names = ['< PRODUCT >'] + sorted(val['NAME'].unique().tolist())
product = col3.selectbox('Select Product',names,index = names.index('< PRODUCT >'))
if(product != '< PRODUCT >'):
    val = df3.loc[(df3['NAME'] == product)]
    zones = ['< ZONE >'] + val['ZONE'].unique().tolist()

zone = col4.selectbox('Select Zone',zones,index = zones.index('< ZONE >'))
if(zone != '< ZONE >'):
    val = df3.loc[(df3['NAME'] == product) & (df3['ZONE'] == zone)]
    pricerange = val['Price_Range'].iloc[0]
    mrpr = 'Previous MRP Range : ' + pricerange
    st.write(mrpr)
mrp = st.number_input("Enter MRP")


gp = st.button('Get Price')


def getprice():
    
    #establishing the connection
    conn = psycopg2.connect(DATABASE_URL)
    
    #Creating a cursor object using the cursor() method
    cursor = conn.cursor()
    
    #Retrieving data
    cursor.execute("SELECT * from priceoptimise WHERE NAME = %s AND ZONE = %s",[product,zone])
    result = cursor.fetchall();
    df = pd.DataFrame(result,columns = ['UID', 'NAME', 'ZONE', 'Brand', 'MC', 'Fdate', 'NSU', 'NSV', 'GST', 'NSV-GST', 'Sales_at_Cost', 'MARGIN', 'MARGIN%' ,'Gross_Sales' ,'Gross_Margin' ,'Gross_Margin%' ,'MRP' ,'SP' ,'DIS' ,'DIS%'])
    #Creating columns for Unit Cost and Unit GST
    df['UC'] = df['Sales_at_Cost']/df['NSU']
    df['UGST'] = df['GST']/df['NSU']
    
    df["UID"] = pd.to_numeric(df["UID"], downcast="float")
    df["SP"] = pd.to_numeric(df["SP"], downcast="float")
    df["UC"] = pd.to_numeric(df["UC"], downcast="float")
    df["NSU"] = pd.to_numeric(df["NSU"], downcast="float")
    df.dropna(inplace=True)

    df = df.loc[df['Sales_at_Cost'] >= 0]
    df = df.loc[df['NSU'] >= 0]
    df = df.loc[df['MRP'] >= 0]
    df = df.loc[df['SP'] >= 0]

    model = ols("NSU ~ SP + UC", data = df).fit()
    p = model.params
    cost = df.UC.mean()
    gst = df.UGST.mean()


    S = []
    for i in np.arange(mrp/2,mrp,0.01):
         S = S + [i]

    intercept = p[0]
    spcoef = p[1]
    uccoef = p[2]
    Revenue = []
    N = []
    Discount = []
    DisPer = []
    for p in S:
        nsu = intercept + (spcoef * p) + (uccoef * cost)
        N.append(nsu)
        # profit function
        Revenue.append(nsu * (p - cost - gst))
        dis = mrp - p
        disper = (dis/mrp) * 100
        Discount.append(dis)
        DisPer.append(disper)
    # create data frame of price and revenue
    profit = pd.DataFrame({"NSU":N,"Price": S, "Revenue": Revenue,"Discount":Discount,"Discount%":DisPer})

    # taking only positive NSU's 
    profit2 = profit.loc[(profit['NSU']>0) & (profit['Revenue']>0)]
    if len(profit2) == 0:
        st.write('Error: Given MRP cannot create positive Revenue!')
    else:
        # to find the Price at which maximum units are sold AND max revenue is generated
        profit2['Revenue x NSU'] = profit2['Revenue'] * profit2['NSU']


      # FOR PLOTTING #  
        # plt.plot(profit2['Price'], profit2['Revenue x NSU'])
        # plt.xlabel('Price')
        # plt.ylabel('Max revenue with Max NSU')

     # Optimal price is where Revenue and NSU is maximum
        optimal_price = profit2.loc[profit2['Revenue x NSU'] == max(profit2['Revenue x NSU'])]
        rop = round((optimal_price['Price'].values[0]),2)
        rnsu = round((optimal_price['NSU'].values[0]),2)
        rrev = round((optimal_price['Revenue'].values[0]),2)
        rdis = round((optimal_price['Discount%'].values[0]),2)
        outputtable = pd.DataFrame({'Product':product,'Price':[rop],'NSU':[rnsu],'Revenue':[rrev],'Discount%':[rdis]})
        outputtable.set_index('Product',inplace=True)
        st.table(outputtable)

if(gp):
    if((category != '< CATEGORY >' ) and (brand != '< BRAND >') and (product != '< PRODUCT >') and (zone != '< ZONE >')):
        getprice()

