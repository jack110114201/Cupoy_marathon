from selenium import webdriver
from selenium.webdriver.support.ui import Select
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup

chrome_options = Options()
chrome_options.add_argument('--headless')
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-dev-shm-usage')


browser = webdriver.Chrome(executable_path='./chromedriver',chrome_options=chrome_options)
browser.get("https://www.cupoy.com/clubnews/ai_tw/0000016E62FB84E4000000026375706F795F72656C656173654B5741535354434C5542/0000016F69B5DB8C000000266375706F795F72656C656173654B5741535354434C55424E455753")