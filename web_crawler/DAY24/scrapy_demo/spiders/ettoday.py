import scrapy


class EttodaySpider(scrapy.Spider):
    name = 'ettoday'
    allowed_domains = ['www.ettoday.net']
    start_urls = ['http://www.ettoday.net/']

    def parse(self, response):
        pass
