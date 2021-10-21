from flask import Flask, request, abort

from linebot import (
    LineBotApi, WebhookHandler
)

from linebot.exceptions import (    
    InvalidSignatureError
)       

from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
    ImageSendMessage,
    LocationMessage,
    TemplateSendMessage, ButtonsTemplate, URITemplateAction,ImagemapSendMessage,
    StickerMessage, StickerSendMessage,
    CarouselTemplate, CarouselColumn, PostbackEvent,
    BaseSize, URIImagemapAction, ImagemapArea)

import pymssql
from gensim.models import Word2Vec
import jieba
import logging 
import random
import requests
import json
import urllib


app = Flask(__name__)

# Channel Access Token
line_bot_api = LineBotApi('YOUR API')
# Channel Secret
handler = WebhookHandler('YOUR WEBHOOK')

      




# 監聽所有來自 /callback 的 Post Request
@app.route("/callback", methods=['POST'])
def callback():  
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']
    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)
    # handle webhook body    
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

#處理位置
@handler.add(MessageEvent, message=LocationMessage)
def handle_location_message(event):
    logging.error(event)
    # 獲取使用者的經緯度
    lat = event.message.latitude
    long = event.message.longitude
    url='https://maps.googleapis.com/maps/api/geocode/json?latlng='+str(lat)+', '+str(long)+'&key=AIzaSyA6BMiHcg2Ayvy8FJ5pjxTOrXYRYGutXww'
    data = requests.get(url).json()
    find =''
    for results in data['results']:
        temp = results['formatted_address'].find('台北市')
        if(temp!=-1):
            find=results['formatted_address'][temp:temp+6]
    
    if(find[0:3] == "台北市" and  find[5]=="區" ):
        columns=[]
        House_Name = []
        Price_Num = []
        House_Site = []
        House_Web = []
        sqlsearch(find,House_Name,Price_Num,House_Site,House_Web)
        
        max_num = 0
        if (len(House_Name)>=10):
            max_num=10
        else:
            max_num=len(House_Name)
        r2 = []
        for i  in range(0,len(House_Name),1):
            r2.append(i)
        r1=random.sample(r2, k= max_num)
        count=0
        if(max_num>0):
            if (count == 0):
                 columns.append(CarouselColumn(
                       # thumbnail_image_url=str(House_Img[count]),
                        title='台北市的標準住宅單價(萬元/坪)趨勢',
                        text='提供近幾年該地區的每坪價格的趨勢給你參考',
                        actions=[
                                URITemplateAction(
                                        label='連結網址',
                                        uri='https://www.itushuo.com/embed/wqgsi'
                                        )
                            ]
                          ))
                 count+=1
            if(count==1):
                 columns.append(CarouselColumn(
                       # thumbnail_image_url=str(House_Img[count]),
                        title=find+'的商業活絡程度',
                        text='提供該地區的水、電力及商業資訊給你參考',
                        actions=[
                                URITemplateAction(
                                        label='連結網址',
                                        uri='https://jshare.com.cn/temp/'+str(areafin(find[3:6]))+'/share/pure'
                                        )
                            ]
                          ))
                 count+=1
            while(count<max_num-1):
                columns.append(CarouselColumn(
                       # thumbnail_image_url=str(House_Img[count]),
                        title=str(House_Name[r1[count]]),
                        text='價錢:'+str(Price_Num[r1[count]])+'萬元\n位置:'+str(House_Site[r1[count]]),
                        actions=[
                                URITemplateAction(
                                        label='連結網址',
                                        uri=str(House_Web[r1[count]])   
                                        )
                            ]
                          ))
                count+=1
            columns.append(CarouselColumn(
                   # thumbnail_image_url=str(House_Img[count]),
                    title=str(House_Name[r1[count]]),
                    text='價錢:'+str(Price_Num[r1[count]])+'萬元\n位置:'+str(House_Site[r1[count]]),
                    actions=[
                            URITemplateAction(
                                    label='連結網址',
                                    uri=str(House_Web[r1[count]])         
                                    )
                        ]
                         ))
            logging.error(columns)
            Carousel_template = TemplateSendMessage(
                    alt_text='Carousel template',
                    template=CarouselTemplate(
                            columns
                        )
                    )
            line_bot_api.reply_message(event.reply_token,Carousel_template)
            
            
        else:
            ar='抱歉沒有找到該地區房價，請搜尋其他地區!'
            line_bot_api.reply_message(event.reply_token,TextSendMessage(text=ar))
        
    else:
         ar='抱歉,我們目前只有做台北市的房價查詢以及商業程度喔~'
         line_bot_api.reply_message(event.reply_token,TextSendMessage(text=ar))


# 處理訊息
@handler.add(MessageEvent, message=TextMessage) 
def handle_message(event): 
    logging.error(event)
    model = 'w2v.mod'
    model_loaded = Word2Vec.load(model)
    candidates = []
    with open('target.txt' , 'r' ,encoding='utf-8') as f:
        for line in f:
            candidates.append(line.strip().split())
    Ans = []
    with open('A.txt' , 'r' ,encoding='utf-8') as fs:
        for line in fs:
            a = line.replace("\\n"," ")
            Ans.append(a.strip())

    

    if (event.message.text == "時價登錄") :
        answer = " 請輸入欲查詢地區(只限台北市)，仿照下列格式 — 例: [台北市信義區] "
        line_bot_api.reply_message(event.reply_token,TextSendMessage(text=answer))
    
    elif(event.message.text =="GPS定位功能" ):
        answer = " 只要上傳你的定位資訊，我們便會提供給你:\n該地區(限台北市)商業活絡程度及房屋資訊喔!!"
        line_bot_api.reply_message(event.reply_token,TextSendMessage(text=answer))
    
    
    elif(event.message.text == "商業活絡程度"):
        answer = " 請輸入欲查詢地區(只限台北市)，仿照下列格式 — 例: [台北市信義區資訊] "
        line_bot_api.reply_message(event.reply_token,TextSendMessage(text=answer))
    
    elif( (len(event.message.text)==10) and event.message.text[1:4] == "台北市" and event.message.text[6]=="區" and event.message.text[0]=="[" and event.message.text[9]=="]"  and event.message.text[7:9] =='資訊' ):
        find = event.message.text[1:7]
        uri = 'https://jshare.com.cn/temp/'+str(areafin(find[3:6]))+'/share/pure'
        answer = find+'的商業活絡程度請連結至以下網址:  \n' + uri
        line_bot_api.reply_message(event.reply_token,TextSendMessage(text=answer))
    
        
    elif((len(event.message.text)==8) and  event.message.text[1:4] == "台北市" and  event.message.text[6]=="區" and event.message.text[0]=="[" and event.message.text[7]=="]" ):
        columns=[]
        House_Name = []
        Price_Num = []
        House_Site = []
        House_Web = []
        sqlsearch(event.message.text[1:7],House_Name,Price_Num,House_Site,House_Web)
        
        max_num = 0
        if (len(House_Name)>=10):
            max_num=10
        else:
            max_num=len(House_Name)
        r2 = []
        for i  in range(0,len(House_Name),1):
            r2.append(i)
        r1=random.sample(r2, k= max_num)
        count=0
        if(max_num>0):
            if (count == 0):
                 columns.append(CarouselColumn(
                       # thumbnail_image_url=str(House_Img[count]),
                        title='台北市的標準住宅單價(萬元/坪)趨勢',
                        text='提供近幾年該地區的每坪價格的趨勢給你參考',
                        actions=[
                                URITemplateAction(
                                        label='連結網址',
                                        uri='https://www.itushuo.com/embed/wqgsi'
                                        )
                            ]
                          ))
                 count+=1
            while(count<max_num-1):
                columns.append(CarouselColumn(
                       # thumbnail_image_url=str(House_Img[count]),
                        title=str(House_Name[r1[count]]),
                        text='價錢:'+str(Price_Num[r1[count]])+'萬元\n位置:'+str(House_Site[r1[count]]),
                        actions=[
                                URITemplateAction(
                                        label='連結網址',
                                        uri=str(House_Web[r1[count]])   
                                        )
                            ]
                          ))
                count+=1
            columns.append(CarouselColumn(
                   # thumbnail_image_url=str(House_Img[count]),
                    title=str(House_Name[r1[count]]),
                    text='價錢:'+str(Price_Num[r1[count]])+'萬元\n位置:'+str(House_Site[r1[count]]),
                    actions=[
                            URITemplateAction(
                                    label='連結網址',
                                    uri=str(House_Web[r1[count]])         
                                    )
                        ]
                         ))
            logging.error(columns)
            Carousel_template = TemplateSendMessage(
                    alt_text='Carousel template',
                    template=CarouselTemplate(
                            columns
                        )
                    )
            line_bot_api.reply_message(event.reply_token,Carousel_template)
        else:
            ar='抱歉沒有找到該地區房價，請搜尋其他地區!'
            line_bot_api.reply_message(event.reply_token,TextSendMessage(text=ar))
            
    elif((len(event.message.text)==5) and event.message.text[0:5] == "生活小幫手" ):
        imagemap_message = ImagemapSendMessage(
            base_url='https://i.imgur.com/MNlaWgX.jpg',
            alt_text='this is an imagemap',
            base_size=BaseSize(height=1040, width=1040),
            actions=[
                    URIImagemapAction(
                            link_uri='https://drive.google.com/open?id=1jyyA5J5OudRCsykJI4yWcqdXKoYgN3rY&usp=sharing',
                            area=ImagemapArea(
                                    x=0, y=0, width=519, height=440
                                )
                            ),
                    URIImagemapAction(
                            link_uri='https://drive.google.com/open?id=1j9MZriaPTJVcQGzhGxNql2-uWOfII-vB&usp=sharing',
                            area=ImagemapArea(
                                    x=520, y=0, width=519, height=440
                                )
                            ),
                    URIImagemapAction(
                            link_uri='https://drive.google.com/open?id=1hvKl65mWcmfDQRywnLsmcqJSgo3pJPTI&usp=sharing',
                            area=ImagemapArea(
                                    x=0, y=441, width=519, height=440
                                )
                            ),
                    URIImagemapAction(
                            link_uri='https://drive.google.com/open?id=1CKWg04o8Sq-tEgbcVmWQZEf68CZJdJsI&usp=sharing',
                            area=ImagemapArea(
                                    x=520, y=441, width=519, height=440
                                )
                            ),
                        ]
                    )
        line_bot_api.reply_message(event.reply_token,imagemap_message)
        
    else :
        while True:
            text = event.message.text
            words = list(jieba.cut(text.strip(), cut_all=False))
            res = []
            index = 0
            for candidate in candidates:
                # print candidate
                score = model_loaded.n_similarity(words, candidate)
                res.append(ResultInfo(index, score, " ".join(candidate)))
                index += 1
            res.sort(key=lambda x:x.score, reverse=True)
            k = 0
            count = 0
            dans=""
            dans+="我們將從資料庫中找出幾筆最相關的Q&A給您\n"
            for i in res:
                k += 1
                if i.score > 0.6 :
                    dans+="Q"+str(count+1)+" : " +(i.text)+"\n"
                    dans+="A"+str(count+1)+" : " +Ans[i.id]+"\n"
                    count += 1
                    if k > 9 or count==3:
                        break
            if count==0 :
                ans = "請換個方式問問看"
                line_bot_api.reply_message(event.reply_token,TextSendMessage(text=ans))
            else:
                line_bot_api.reply_message(event.reply_token,TextSendMessage(text=dans))


def sqlsearch(target,HN,PN,HS,HW):
    coon = pymssql.connect(host='163.14.68.48', user='sa', password='875421', database='HousePrice')
    cursor = coon.cursor()
    cursor.execute('SELECT House_Name,Price_Num,House_Site,House_Web FROM HouseInfo WHERE House_Site LIKE' + "'%"+target+"%'")
   
    for row in cursor.fetchall():
        HN.append(row[0])
        PN.append(row[1])
        HS.append(row[2])
        HW.append(row[3])     
    coon . close ()



def areafin(area):
    darea = {
        '北投區':'BCF1Wj',
        '士林區':'UU41Ws',
        '內湖區':'EMF1Wl',
        '南港區':'MFE1W3',
        '文山區':'rpJ1Wn',
        '萬華區':'UOJ1Wz',
        '大同區':'JtP1Wm',
        '中正區':'dPe1W8',
        '中山區':'ZtF1Wf',
        '大安區':'NRY1Wy',
        '信義區':'HZN1WT',
        '松山區':'ECN1WG'
            }
    return darea.get(area,None)
        
class ResultInfo(object):
    def __init__(self, index, score, text):
        self.id = index
        self.score = score
        self.text = text

import os
if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
    
    
    

