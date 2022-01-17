# -*- coding: utf-8 -*-
import scrapy
from scrapy_demo.items import ScrapyDemoItem


class EttodaySpider(scrapy.Spider):
    name = 'ettoday'
    allowed_domains = ['www.ettoday.net']
    start_urls = ['https://www.ettoday.net/news/20201004/1824032.htm',
                  'https://www.ettoday.net/news/20201009/1826868.htm']

    def parse(self, response):
        item = ScrapyDemoItem()
        item['title'] = response.xpath('//title/text()').get()
        item['content'] = response.xpath('//div[@itemprop="articleBody"]//p/text()').getall()
        yield item