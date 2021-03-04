from flask import Flask, render_template, request,jsonify
from flask_cors import CORS,cross_origin
import requests
from bs4 import BeautifulSoup as bs
from urllib.request import urlopen as uReq
import pymongo
from application_logging.logger import App_Logger
from constants import constant
import pandas as pd
import seaborn as sns
#import matplotlib.pyplot as plt
import os

app = Flask(__name__)


@app.route('/',methods=['GET'])  # route to display the home page
@cross_origin()
def homePage():
    return render_template("index.html")

@app.route('/stats',methods=['POST','GET'])  # route to display Graph
@cross_origin()
def statsPage():
    if request.method == 'POST':
        try:
            connection_url = 'mongodb+srv://rav:12341234@cluster0.gjwto.mongodb.net/dbReviewScrapper?retryWrites=true&w=majority'
            client = pymongo.MongoClient(connection_url) #In Future We can keep the database connection file to seperate folder
            db = client.get_database('dbReviewScrapper')
            prodName = request.form['prdName']
            reviews = db.scrapper.find({"Product Name": prodName})
            df = pd.DataFrame(reviews)
            if os.path.isfile("static/plots/graph.png"):
                os.remove("static/plots/graph.png")
            sns.countplot(x='Rev Rating', data=df).get_figure().savefig("static/plots/graph.png")
            return render_template('graph.html', prodName=prodName)
        except Exception as e:
            print('The Exception message is: ', e)
            return 'something is wrong'

    return render_template("graph.html")

@app.route('/review',methods=['POST','GET']) # route to show the review comments in a web UI
@cross_origin()
def index():

    if request.method == 'POST':
        try:
            connection_url = 'mongodb+srv://rav:12341234@cluster0.gjwto.mongodb.net/dbReviewScrapper?retryWrites=true&w=majority'
            client = pymongo.MongoClient(connection_url)
            db = client.get_database('dbReviewScrapper')
            searchString = request.form['content'].replace(" ", "")  #Will Replace the Extra Spaces
            reviews = db.scrapper.find({"Search Key": searchString})

            if reviews.count() > 0: # if there is a collection with searched keyword and it has records in it
                message = "Reviews Found In Database :: %s" % reviews.count() + "\n"
                App_Logger(message)
                return render_template('results.html', reviews=reviews) # show the results to user
            #
            else:
                flipkart_url = "https://www.flipkart.com/search?q=" + searchString
                message = "Reviews Not Found In Database, Now Searching Data in Internet: %s" % searchString + "\n"
                App_Logger(message)
                uClient = uReq(flipkart_url) # Requesting the master product linkd
                flipkartPage = uClient.read()
                uClient.close()
                flipkart_html = bs(flipkartPage, "html.parser")
                bigboxes = flipkart_html.findAll("div", {"class": "_1AtVbE col-12-12"})
                del bigboxes[0:3]       #Deleting as top 3 boxes not required
                reviews = []

                for box in bigboxes:    #Fetching all products one by one
                    #box = bigboxes[3]
                    productLink = "https://www.flipkart.com" + box.div.div.div.a['href']
                    App_Logger("_"*constant.line)
                    App_Logger("Link: " + str(productLink))
                    prodRes = requests.get(productLink)
                    prodRes.encoding= constant.encodingtype
                    prod_html = bs(prodRes.text, "html.parser")

                    #### Fetching Product Features
                    try:
                        model_name = prod_html.find('span', {'class': "B_NuCI"}).text
                    except:
                        model_name = 'Not Available'
                    try:
                        rating = prod_html.find('div', {'class': "_3LWZlK"}).text
                    except:
                        rating = 'No Rating'
                    try:
                        model_price = prod_html.find('div', {'class': "_30jeq3"}).text
                    except:
                        model_price = 'Not Available'
                    try:
                        offers =[]
                        for offer in (prod_html.findAll('span', {'class': "_3j4Zjq"})[:2]):
                            #offers = offers + "* " + offer.li.text + "\n"
                            offers.append(offer.li.text)
                    except:
                        offers = 'No Offers'
                    try:
                        hightlights = ""
                        for highlight in (prod_html.findAll('li', {'class': "_21Ahn-"})):
                            hightlights = hightlights + "* " + highlight.text + "\n"
                            #hightlights.append(highlight.text)
                    except:
                        hightlights = 'No Highlights'
                    App_Logger("Model Name: " + str(model_name))

                    ####  Fetching Product Reviews
                    allreviews = prod_html.find('div', {'class': "col JOpGWq"})
                    reviewLink = allreviews.findAll('a')[-1]  # Review Page Link
                    prdReviewLink = "https://www.flipkart.com" + reviewLink['href']  # Review Page link Main
                    prodRev = requests.get(prdReviewLink)
                    prodRev.encoding= constant.encodingtype
                    prod_rev_html = bs(prodRev.text, "html.parser")
                    reviewPage = prod_rev_html.findAll('a', {'class': "ge-49M"})[0]  #Fetching Generic/first link for the review pages
                    for i in range(1, constant.revPageCount):
                        if i == 1:
                            prdReviewPage = "https://www.flipkart.com" + reviewPage['href']
                        else:                                   #appending number to fetch 2,3,4... review page
                            prdReviewPage = "https://www.flipkart.com" + reviewPage['href'] + "&page=" + str(i)
                        App_Logger("Reading Next Review Page: " + prdReviewPage + "\n")

                        prodRevPag = requests.get(prdReviewPage)
                        if prodRevPag == constant.errorCode1:                   #Error Handling If Next Review Page is not found
                            break
                        prodRevPag.encoding = constant.encodingtype
                        prod_rev_page_html = bs(prodRevPag.text, "html.parser")
                        commentboxes = prod_rev_page_html.findAll('div', {'class': "_27M-vq"})
                        if len(commentboxes) == 0:  #Breaks if page does not contains any comments
                            break
                        filename = searchString + ".csv"
                        fw = open("Products/" + filename, "w")
                        headers = "Product, Customer Name, Rating, Heading, Comment \n"
                        fw.write(headers)
                        for commentbox in commentboxes:
                            try:
                                #name.encode(encoding='utf-8')
                                name = commentbox.div.div.find_all('p', {'class': '_2sc7ZR'})[0].text
                            except:
                                name = 'No Name'

                            try:
                                #rating.encode(encoding='utf-8')
                                rev_rating = commentbox.div.div.div.div.text
                            except:
                                rev_rating = 'No Rating'

                            try:
                                #commentHead.encode(encoding='utf-8')
                                commentHead = commentbox.div.div.div.p.text
                                App_Logger("Reading Comment: " + str(commentHead))
                            except:
                                commentHead = 'No Comment Heading'

                            try:
                                comtag = commentbox.div.div.find_all('div', {'class': ''})
                                #custComment.encode(encoding='utf-8')
                                custComment = comtag[0].div.text
                            except Exception as e:
                                App_Logger("Going in Exception for Reading Comment: " + str(commentHead))
                                print("Exception while creating dictionary: ",e)

                            mydict = {"Search Key": searchString, "Product Name": model_name,"Rating": rating,"Price": model_price, "Offers": offers, "Features": hightlights, "Rev Name": name, "Rev Rating": rev_rating, "CommentHead": commentHead,
                                      "Comment": custComment}
                            reviews.append(mydict)
                            if len(reviews) > constant.maxRevCount:  #In Future Can Keep this whole logic Inside Def and then use return instead
                                break
                        if len(reviews) > constant.maxRevCount:
                            break
                    if len(reviews) > constant.maxRevCount:
                        break
                App_Logger("Total Review Count: " + str(len(reviews)))
                db.scrapper.insert_many(reviews)
                return render_template('results.html', reviews=reviews[0:(len(reviews)-1)])
        except Exception as e:
            print('The Exception message is: ',e)
            return 'something is wrong'
    # return render_template('results.html')

    else:
        return render_template('index.html')

if __name__ == "__main__":
    #app.run(host='127.0.0.1', port=8001, debug=True)
	app.run(debug=True)
