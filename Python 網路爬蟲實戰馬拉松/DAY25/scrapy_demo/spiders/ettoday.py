import scrapy


class EttodaySpider(scrapy.Spider):
    name = 'ettoday'
    allowed_domains = ['www.ettoday.net']
    start_urls = ['https://www.ettoday.net/news/20201004/1824032.htm', 'https://www.ettoday.net/news/20210707/2024903.htm']

    def parse(self, response):
        title = response.xpath("//h1[@class='title']/text()").get()
        content = response.xpath("//div[@class='story']/p/text()").getall()
        
        print(title)
        print()
        print([i for i in content])
        print()
