一、專題摘要 
=============
1. 期末專題主題 : PTT政黑板
2. 期末專題基本目標 : 
   * 自PTT政黑板爬取所需資料 (例如 : 文章標題、作者、日期與內容等)。
   * 將爬取的資料存入本地端的MongoDB server。
	* 針對所有爬取的文章內容透過jieba套件進行分詞，並使用自定義與過濾辭典，讓分詞出來的結果較好。
	* 依據發文者名稱與IP，期望可以發現文章的發文者的IP相同，但為不同帳號的情況，並針對文章內容進行分詞。
	* 將分詞結果以長條圖與文字雲的方式呈現。

二、流程圖
=============
![image](http://clubfile.cupoy.com/0000017E472852B5000000026375706F795F72656C656173654B5741535354434C55424E455753/1641962487691/large)

三、實作方法介紹
=============
(一) 爬蟲
-------------

1. 匯入爬取資料時所使用的套件

```python
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import re
import time
import random
import datetime
import pandas as pd
```
2. 透過list的方式，來裝爬取下來的內容 
   * 預計爬取7個項目。
	* article_message_* 的資料是透過計算所得出的值。
	* _id 是用來當作資料存入MongoDB時所要用的資訊。

```python
article_title = [] # 文章標題
article_URL = [] # 文章內文連結
article_author = [] # 文章作者
article_date = [] # 發文日期
article_author_ip = [] # 發文者IP
article_content = [] # 文章內容
article_messages = [] #文章中的每筆留言資訊 (含留言者ID、時間、推噓中立狀態、內容)
article_message_count_all = [] # 整體留言數量
article_message_count_status = [] # 推文-噓文數量，顯示何者狀態較多
article_message_count_push = [] # 推文數量
article_message_count_boo = []  # 噓文數量
article_message_count_neutral = [] # 中立數量
_id = [] # 發文日期+文章標題+文章作者+發文者IP
```
3. 爬取PTT政黑板前500篇文章資訊

```python
url = 'https://www.ptt.cc/bbs/HatePolitics/index.html'
resp = requests.get(url, cookies={'over18': '1'})
soup = BeautifulSoup(resp.text, 'html.parser')
main_list = soup.find('div', class_='bbs-screen')
N = 500
count = 0
while count < N:
    # 依序檢查文章列表中的 tag, 遇到分隔線就結束，忽略這之後的文章
    
    for div in main_list.findChildren('div', recursive=False):    
        if count < N:
            class_name = div.attrs['class']
            # 遇到目標文章
            if class_name and 'r-ent' in class_name:
                div_title = div.find('div', class_='title')
                a_title = div_title.find('a', href=True)
                # 如果文章已經被刪除則跳過
                if not a_title or not a_title.has_attr('href'):
                    continue
    
                article_URL_text = urljoin('https://www.ptt.cc', a_title['href'])
                article_URL.append(article_URL_text)
                article_title_text = a_title.text
                print(article_title_text)
                
                
                article_content_response =  requests.get(article_URL_text, cookies={'over18': '1'})
                #print(article_content_response.text)
                soup = BeautifulSoup(article_content_response.text)
                # 取得文章內容主體
                main_content = soup.find(id='main-content')
                # 假如文章有屬性資料 (meta), 我們在從屬性的區塊中爬出作者 (author), 文章標題 (title), 發文日期 (date)
                metas = main_content.select('div.article-metaline')
                author = ''
                title = ''
                date = ''
                if metas:
                    if metas[0].select('span.article-meta-value')[0]:
                        author = metas[0].select('span.article-meta-value')[0].string.split('(')[0]
                        article_author.append(author)
                        
                    if metas[1].select('span.article-meta-value')[0]:
                        title = metas[1].select('span.article-meta-value')[0].string
                        article_title.append(title)
                    if metas[2].select('span.article-meta-value')[0]:
                        date = metas[2].select('span.article-meta-value')[0].string
                        date = datetime.datetime.strptime(date, '%a %b %d %H:%M:%S %Y').strftime('%Y/%m/%d %H:%M:%S')
                        article_date.append(date)
                    
                    # 從 main_content 中移除 meta 資訊（author, title, date 與其他看板資訊）
                    for m in metas:
                        m.extract()
                    for m in main_content.select('div.article-metaline-right'):
                        m.extract()
                # 取得留言區主體
                pushes = main_content.find_all('div', class_='push')
                for p in pushes:
                    p.extract()
                # 假如文章中有包含「※ 發信站: 批踢踢實業坊(ptt.cc), 來自: xxx.xxx.xxx.xxx」的樣式
                # 透過 regular expression 取得 IP
                try:
                    ip = main_content.find(text=re.compile(u'※ 發信站:'))
                    ip = re.search('[0-9]*\.[0-9]*\.[0-9]*\.[0-9]*', ip).group()
                    article_author_ip.append(ip)
                except Exception as e:
                    ip = ''
                    article_author_ip.append(ip)
                _id.append(date+title+author+ip) 
                
                
                # 移除文章主體中 '※ 發信站:', '◆ From:', 空行及多餘空白 (※ = u'\u203b', ◆ = u'\u25c6')
                # 保留英數字, 中文及中文標點, 部分特殊符號
                filtered = []
                for v in main_content.stripped_strings:
                    # 假如字串開頭不是特殊符號或是以 '--' 開頭的, 我們都保留其文字
                    if v[0] not in [u'※', u'◆'] and v[:2] not in [u'--']:
                        filtered.append(v)
                # 定義一些特殊符號與全形符號的過濾器
                expr = re.compile(u'[^一-龥。；，：“”（）、？《》\s\w:/-_.?~%()]')
                for i in range(len(filtered)):
                    filtered[i] = re.sub(expr, '', filtered[i])
                # 移除空白字串, 組合過濾後的文字即為文章本文 (content)
                filtered = [i for i in filtered if i]
                content = ' '.join(filtered)
                content = re.sub(r'^(https).*(png)', '', content)
                content = re.sub(r'https://[a-zA-Z0-9\./_]+','',content)
                content = content.replace('\n','-')
                article_content.append(content)
                
                
                # 處理留言區
                # p 計算推文數量
                # b 計算噓文數量
                # n 計算箭頭數量
                p, b, n = 0, 0, 0
                messages = []
                for push in pushes:
                    # 假如留言段落沒有 push-tag 就跳過
                    if not push.find('span', 'push-tag'):
                        continue
                    # 過濾額外空白與換行符號
                    # push_tag 判斷是推文, 箭頭還是噓文
                    # push_userid 判斷留言的人是誰
                    # push_content 判斷留言內容
                    # push_ipdatetime 判斷留言日期時間
                    push_tag = push.find('span', 'push-tag').string.strip(' \t\n\r')
                    push_userid = push.find('span', 'push-userid').string.strip(' \t\n\r')
                    push_content = push.find('span', 'push-content').strings
                    push_content = ' '.join(push_content)[1:].strip(' \t\n\r')
                    push_ipdatetime = push.find('span', 'push-ipdatetime').string.strip(' \t\n\r')
                    
                    # 整理打包留言的資訊, 並統計推噓文數量
                    
                    messages.append({
                        'push_tag': push_tag,
                        'push_userid': push_userid,
                        'push_content': push_content,
                        'push_ipdatetime': push_ipdatetime})    
                    if push_tag == u'推':
                        p += 1
                    elif push_tag == u'噓':
                        b += 1
                    else:
                        n += 1
                        
                # 統計推噓文                    
                article_message_count_all.append(p+b+n)
                article_message_count_status.append(p-b)
                article_message_count_push.append(p)
                article_message_count_boo.append(b)
                article_message_count_neutral.append(n)
                
                # 檢視文章中是否有留言，沒有的話，以'no comments' 作為值
                if len(messages) == 0 :
                    messages.append('no comments')
                    article_messages.append(messages)
                else:
                    article_messages.append(messages)
                count += 1
                print('--------------------------------------------------------------------')
        else:
            break
    
            
        if class_name and 'r-list-sep' in class_name:
            print('Reach the last article in the first page')
            break
           
    print('******************************************************************************')
    print('Go to the next page')
    print('******************************************************************************')
    soup = BeautifulSoup(resp.text, 'html.parser')   
    next_url = 'https://www.ptt.cc' + soup.select_one('#action-bar-container > div > div.btn-group.btn-group-paging > a:nth-child(2)')['href']
    resp = requests.get(next_url, cookies={'over18': '1'})
    soup = BeautifulSoup(resp.text, 'html.parser')
    main_list = soup.find('div', class_='bbs-screen')
    time.sleep(random.uniform(1, 6))
    
else:
    print(len(article_title))
```
4. 使用Pandas，將裝有爬取資訊的list，整合成一個DataFrame。


```python
df = pd.DataFrame({"_id":_id,"article_date":article_date,"article_title":article_title,"article_author":article_author,"article_author_ip":article_author_ip,"article_content":article_content,\
                  "article_URL":article_URL,"article_message_count_all":article_message_count_all,"article_message_count_status":article_message_count_status,\
                  "article_message_count_push":article_message_count_push,"article_message_count_boo":article_message_count_boo,"article_message_count_neutral":article_message_count_neutral,\
                  "article_messages":article_messages})
```
![image](http://clubfile.cupoy.com/0000017E472852B5000000026375706F795F72656C656173654B5741535354434C55424E455753/1641791818249/large)


5. 將DataFrame格式轉換成Json格式
   * 使用json套件。
	   * DataFrame轉換成json格式時，可以透過參數調整json格式。
		* 最終採用'records'的格式。
		* 參考網址 : https://www.delftstack.com/zh-tw/howto/python-pandas/pandas-dataframe-to-json/
	* 當成功將DataFrame轉換成json格式後，由於資料來源主要為中文，因此出現編碼的問題，所以轉換出來的結果為亂碼，後來加入force_ascii = False後，排除編碼的問題。
	   * 參考網址 : https://stackoverflow.com/questions/39612240/writing-pandas-dataframe-to-json-in-unicode
	* 由於DataFrame轉換成Json格式的樣態為str，為了讓str轉換成json，則使用json.loads()
       * 參考網址 : https://cutejaneii.wordpress.com/2017/11/07/python-5-%E5%9E%8B%E6%85%8B%E8%BD%89%E6%8F%9B%E7%B3%BB%E5%88%97%EF%BD%9Ejson-string-to-object/


```python
import json
# 透過force_ascii=False 解決中文的編碼問題
js = df.to_json(orient = 'records', force_ascii=False) # date type = str

# str 轉換成 json

obj = json.loads(js)
obj
```
![image](http://clubfile.cupoy.com/0000017E472852B5000000026375706F795F72656C656173654B5741535354434C55424E455753/1641962487665/large)



(二) 資料儲存
-------------
1. 資料匯入MongoDB server
	* 透過pymongo套件，將資料匯入MongoDB
 	  * 參考網址 : https://stackoverflow.com/questions/49510049/how-to-import-json-file-to-mongodb-using-python/49510257
	* 在最一開始有準備_id 的list，是因為資料匯入MongoDB時，如果資料中沒有_id的key值，會自行建立_id並給予value。
	* 由於可能會有多次執行爬蟲程式的情況，這時候可能會產生爬取到同一位文章作者所撰寫的同一篇文章，但留言訊息會有變動的情況。
		* 如果使用MongoDB自行產生的_id，將多次爬取的資料匯入MongoDB時，就會發生僅有留言資料有變動，但其餘資訊皆為重複的情況，但卻會產生一筆新的資料。
		* 為了避免這種情況發生，才會製作獨特的 _id用來識別。
	* 當匯入的資料已經存在於MongoDB(例如: _id相同)，則會出現BulkWriteError的錯誤資訊。
		* 參考網址 : https://www.cnblogs.com/zhangjpn/p/7775242.html
		* 即使了解發生BulkWriteError的錯誤資訊，並嘗試使用try/except的方式解決，但如果沒有先import BulkWriteError的話，會出現 name error的情況。
		  * 參考網址 : https://stackoverflow.com/questions/30355790/mongodb-bulk-write-error
		* 由於出現BulkWriteError的錯誤資訊，因此需要更新MongoDB裡的資訊。這邊使用update_one()的方法並以_id作為query且只更新留言訊息的資料。
		  * 參考網址 : https://www.runoob.com/python3/python-mongodb-update-document.html

```python
from pymongo import MongoClient
from pymongo.errors import BulkWriteError # 如果不import，在except使用BulkWriteError時會出現name error

client = MongoClient('localhost', 27017)
db = client['ptt_project'] # 尋找或建立db
collection_currency = db['HatePolitics'] #尋找或建立collection

try:
    collection_currency.insert_many(obj) #將json資料導入
except BulkWriteError:
    myquery = { "_id": obj[0]['_id']}
    newvalues = { "$set": { "article_message_count_all": obj[0]['article_message_count_all'],
                        "article_message_count_status" : obj[0]['article_message_count_status'],
                       "article_message_count_push" : obj[0]['article_message_count_push'],
                       "article_message_count_boo" : obj[0]['article_message_count_boo'],
                       "article_message_count_neutral" : obj[0]['article_message_count_neutral'],
                       "article_messages" : obj[0]['article_messages']
                      }       
            }
collection_currency.update_one(myquery, newvalues)


client.close()

```

(三) Jieba與文字雲
-------------
#### A. 針對所有的文章內容進行Jieba斷詞
1. 自MongoDB導出所需資料
	* 使用pymongo與MongoDB進行互動。
	* 利用find()的方法，只撈取文章內容，並將資料放入article_content中。


```python
# 自Mongodb撈取文章內容

from pymongo import MongoClient
client = MongoClient('localhost', 27017)
db = client['ptt_project'] # 尋找或建立db
collection_currency = db['HatePolitics'] #尋找或建立collection

article_content = [] # 用來儲存所需要的資料

content = collection_currency.find({},{"article_content":1})
for i in content:
    article_content.append(i['article_content'])

client.close()
```
2. 使用Jieba套件進行斷詞
	* 使用Jieba的指定辭典檔以及經過嘗試後所產生的自定義辭典檔與過濾辭典檔。

```python
import jieba
import jieba.analyse
from wordcloud import WordCloud
from collections import Counter

jieba.set_dictionary('./jieba/dict.txt.big') #指定辭典檔
jieba.load_userdict('./jieba/mydict.txt') #使用自訂義辭典
breakword = []
for i in article_content:
	#print(i)
    breakword += str(list(jieba.cut(i))).replace('[','').replace(']','')
    all_article_text = ''.join(breakword)
		#print(all_article_text)
```


```python
#stop word
with open(file='./jieba/stop_words.txt', mode='r', encoding='utf-8') as file:
    stop_words = file.read().split('\n')

# 準備一個利用stop word過濾後的分詞結果
seg_stop_words_list = []
seg_words_list = jieba.lcut(all_article_text)
for term in seg_words_list:
    if term not in stop_words:
        seg_stop_words_list.append(term)
seg_stop_words_list

```
3. 使用Counter()統計字詞數量

```python
# 計算詞彙數量
from collections import Counter
seg_stop_counter = Counter(seg_stop_words_list)
seg_stop_counter
```
4. 字詞數量以長條圖呈現
	
	* 由於字詞的個數很多，所以先取數量前10的字詞及數量
	  * 利用Counter()的most_common方法來取出數量前10的字詞。
	  * 參考網址 : https://stackoverflow.com/questions/27303619/how-to-count-top-10-most-common-values-in-a-dict-in-python
	* 製作長條圖
		* 透過迴圈的方式製作長條圖所需的x軸與y軸資料
		* 使用matplotlib套件繪製長條圖
			* 在繪製長條圖的時候，這邊也遇到中文字以亂碼呈現的狀況，後來透過指定使用文字樣態的方法解決問題。
			* 尋找matplotlib文件位置 : https://pyecontech.com/2020/03/27/python_matplotlib_chinese/
			* 畫圖方法 : https://stackoverflow.com/questions/37920935/matplotlib-cant-find-font-installed-in-my-linux-machine


```python
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt

seg_stop_counter_10 = seg_stop_counter.most_common(10)

words = []
count = []

for i in range(0,10):
    words.append(seg_stop_counter_10[i][0])
    count.append(seg_stop_counter_10[i][1])


font_path = '/home/weiche/.local/lib/python3.8/site-packages/matplotlib/mpl-data/fonts/ttf/kaiu.ttf'  # the location of the font file
my_font = fm.FontProperties(fname=font_path)  # get the font based on the font_path

fig, ax = plt.subplots()

ax.bar(words, count, color='green')
ax.set_xlabel(u'words', fontproperties=my_font)
ax.set_ylabel(u'count', fontproperties=my_font)
ax.set_title(u'字詞分布', fontproperties=my_font)
for label in ax.get_xticklabels():
    label.set_fontproperties(my_font)
```

![image](http://clubfile.cupoy.com/0000017E472852B5000000026375706F795F72656C656173654B5741535354434C55424E455753/1641962487689/large)


5. 字詞數量以文字雲呈現
	* 使用WordCloud()繪製文字雲
	* 這邊同樣遇到無法顯示中文的情況，透過設定指定使用文字樣態的方法解決問題。
		* 參考網址 : https://www.twblogs.net/a/5b8c961c2b7177188333e13f

```python
import matplotlib.pyplot as plt

wordcloud = WordCloud(width=900,height=800,background_color = 'white',font_path='/mnt/c/Windows/Fonts/kaiu.ttf').generate_from_frequencies(seg_stop_counter)

plt.imshow(wordcloud, interpolation='bilinear')
plt.axis("off")
plt.show()
```
![image](http://clubfile.cupoy.com/0000017E472852B5000000026375706F795F72656C656173654B5741535354434C55424E455753/1641962487690/large)


#### B. 找出發文數較多的作者，並針對所撰寫的文章內容進行Jieba斷詞
1. 自MongoDB導出所需資料
	* 利用find()的方法，撈取發文日期、文章作者、發文者IP及文章內容。

```python
from pymongo import MongoClient

client = MongoClient('localhost', 27017)
db = client['ptt_project'] # 尋找或建立db
collection_currency = db['HatePolitics'] #尋找或建立collection

article_date = [] # 發文日期
article_author = [] # 文章作者
article_author_ip = [] # 發文者IP
article_content = [] # 用來儲存所需要的資料

content = collection_currency.find({},{"article_date":1,"article_author":1,"article_author_ip":1,"article_content":1})
for i in content:
    article_date.append(i['article_date'])
    article_author.append(i['article_author'])
    article_author_ip.append(i['article_author_ip'])
    article_content.append(i['article_content'])
    
client.close()
```
2. 使用Pandas整理資料
	* 利用文章作者欄位(article_author)進行分組並計算筆數。
	* 尋找筆數大於6筆的資料並保留文章作者欄位。
	* 利用merge的方法，取得資料筆數大於6的相關資訊
	* 最後，將筆數大於6的相關資訊輸出成csv檔。

```python
# 依照文章作者欄位進行分組，計算出現次數
df = pd.DataFrame({"article_date":article_date,"article_author":article_author,"article_author_ip":article_author_ip,"article_content":article_content})
df_count = df.groupby(['article_author']).count().sort_values(['article_date'],ascending=False).reset_index()

# 尋找次數大於等於6的資料
df_count_over_6 = df_count.query('article_content >= 6')

# 找出次數大於6的資料後，保留文章作者的名單
# 用來跟原始資料集(df)做整合
df_count_over_6 = df_count_over_6.iloc[:,[0]]

# 原始資料集(df) 跟 資料次數大於6的資料集(df_count_over_6) 整合後，得出資料次數大於6的相關資訊
df_merge = pd.merge(df,df_count_over_6, how = "inner",on=['article_author'])
df_merge.to_csv('./df_merge.csv',index=False)
df_merge
```
![image](http://clubfile.cupoy.com/0000017E472852B5000000026375706F795F72656C656173654B5741535354434C55424E455753/1641962487667/large)

3. 依據發文數量，尋找目標對象
	* 經過資料排序後，選定article_author為akway及CavendishJr的文章作為文字雲的對象。
	* 利用query的方式顯示目標對象的相關資訊。

```python
# 針對發表文章數進行排序
df_merge.groupby(['article_author']).size().reset_index(name='counts')\
                                    .sort_values(['counts'],ascending=False)\
                                    .reset_index(drop=True).head()
```
![image](http://clubfile.cupoy.com/0000017E472852B5000000026375706F795F72656C656173654B5741535354434C55424E455753/1641962487668/large)

```python
# 依據上表尋找article_author 為 akway 的資料
author_akway =  df_merge.query('article_author == "akway "')
author_akway
```
![image](http://clubfile.cupoy.com/0000017E472852B5000000026375706F795F72656C656173654B5741535354434C55424E455753/1641962487670/large)

```python
# 依據上表尋找article_author 為 CavendishJr 的資料
author_CavendishJr =  df_merge.query('article_author == "CavendishJr "')
author_CavendishJr
```
![image](http://clubfile.cupoy.com/0000017E472852B5000000026375706F795F72656C656173654B5741535354434C55424E455753/1641962487671/large)

4. 依據目標對象的文章內容分別以文字雲的方式作呈現
	* 文字雲的製作流程同前所述。

akway
![image](http://clubfile.cupoy.com/0000017E472852B5000000026375706F795F72656C656173654B5741535354434C55424E455753/1641962487685/large)

CavendishJr
![image](http://clubfile.cupoy.com/0000017E472852B5000000026375706F795F72656C656173654B5741535354434C55424E455753/1641962487686/large)


#### C. 找出文章作者是否有使用相同IP但卻為不同帳號，並針對所撰寫的文章內容進行Jieba斷詞

1. 使用Pandas整理資料
	* 利用文章作者IP欄位(article_author_ip)及文章作者欄位(article_author)進行分組，並將結果輸出成csv檔。 
	* 利用pandas的duplicated()，發現有不同帳號，但卻有相同IP的情況。
	* 將他們視為目標對象並列出他們的相關資訊。

```python
ip_check = df_merge.groupby(['article_author_ip','article_author']).size().reset_index(name='counts')

ip_check.to_csv('./ip_check.csv',index=False)
ip_check
```
![image](http://clubfile.cupoy.com/0000017E472852B5000000026375706F795F72656C656173654B5741535354434C55424E455753/1641962487673/large)

```python
# 發現不同帳號，但是相同IP的情況
ip_check[ip_check['article_author_ip'].duplicated()]['article_author_ip']
```
![image](http://clubfile.cupoy.com/0000017E472852B5000000026375706F795F72656C656173654B5741535354434C55424E455753/1641962487674/large)

```python
# 發現擁有相同IP，但發文作者有2人
ip_check.query('article_author_ip == "111.243.138.118"')
```
![image](http://clubfile.cupoy.com/0000017E472852B5000000026375706F795F72656C656173654B5741535354434C55424E455753/1641962487675/large)

```python
# 檢視他們的發文數量
ip_check.query('article_author == ["abc1204 ","RichWomen "]')
```
![image](http://clubfile.cupoy.com/0000017E472852B5000000026375706F795F72656C656173654B5741535354434C55424E455753/1641962487676/large)

```python
# 列出 article_author 為 RichWomen 及 abc1204的資料
author_RichWomen =  df_merge.query('article_author == "RichWomen "')
author_abc1204 =  df_merge.query('article_author == "abc1204 "')
author_RichWomen
author_abc1204
```
![image](http://clubfile.cupoy.com/0000017E472852B5000000026375706F795F72656C656173654B5741535354434C55424E455753/1641962487677/large)
![image](http://clubfile.cupoy.com/0000017E472852B5000000026375706F795F72656C656173654B5741535354434C55424E455753/1641962487678/large)


2. 依據目標對象的文章內容分別以文字雲的方式作呈現
	* 文字雲的製作流程同前所述。

RichWomen
![image](http://clubfile.cupoy.com/0000017E472852B5000000026375706F795F72656C656173654B5741535354434C55424E455753/1641962487687/large)

abc1204
![image](http://clubfile.cupoy.com/0000017E472852B5000000026375706F795F72656C656173654B5741535354434C55424E455753/1641962487688/large)

四、成果
============
本次爬取資料的時間介於111年1月7日至1月10日，恰好遇到1月9日臺中立委補選及立委林昶佐罷免案，總共爬取1343筆資料。首先，所有的文章內經過斷詞處理後，主要討論的內容以補選及罷免案的議題為主。接下來針對2位發文數較多的作者(akway及CavendishJr)所撰寫的文章進行斷詞處理後，作者akway所撰寫的文章內容範圍涉及較廣，但仍以補選與罷免案的議題為主，但作者CavendishJr不論是在1月9日前後所撰寫的文章，內容皆與疫情相關議題有關。最後，針對2位文章作者(RichWomen、abc1204)但卻有相同IP紀錄的文章內容進行斷詞處理後，雖然結果不盡相同，但如果檢視2位作者的發文日期，作者RichWomen的發文日期在1月7日與1月8日，而作者abc1204的發文日期在1月9日與1月10日，且有關撰寫的文章內容所使用的語氣，有多處相似的地方，因此推測2位文章作者實際上很有可能為同一人。

五、結論
=============
1. 本次專題的問題
本次專題是採用單線程爬蟲的方式去爬取資料，雖然所花費的時間尚可接受，但將嘗試使用scrapy框架進行爬蟲並使流程自動化。另外本專題所使用的分析方法比較簡單且沒有針對留言區的資訊進行分析，接下來將參加NLP 經典機器學習馬拉松，期望完賽後會有新的想法，可以做出有趣的分析結果。

2. 心得
這是我初次參加馬拉松，每天會有要解決每日課題的動力。由於嘗試在Linux環境下撰寫程式，所以在做Selenium的課程時，花了許多時間在解決環境的問題，解決後還滿有成就感的。感謝CUPOY平臺上有許多馬拉松可以參加，除了可以不斷學習外，也可以累積做專題的經驗~

另外，發現文章預覽後，底部多了好一大塊空白，不知道怎麼排除，請見諒~

六、期末專題作者資訊
================================================================
1. 個人Gihub連結 : https://github.com/jack110114201
2. 個人在百日馬拉松顯示名稱 : 許維哲