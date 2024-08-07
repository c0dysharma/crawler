import re
import scrapy
from scrapy.spiders import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
import json
from urllib.parse import urlparse


class MultiDomainCrawlSpider(CrawlSpider):
    name = "mdc"

    start_urls = [
        'https://en.wikipedia.org/wiki/Vim_(text_editor)',
        'https://in.ign.com/five-nights-at-freddys/187643/lists/how-to-play-the-five-nights-at-freddys-games-in-chronological-order',
    ]

    domain_regex = {
        'en.wikipedia.org': r'^https://en\.wikipedia\.org/wiki/.*$',
        'in.ign.com': r'^https://in\.ign\.com/.*$',
    }

    crawled_links = {}  # will store results
    max_depth = 1  # how much to crawl

    def __init__(self, *args, **kwargs):
        super(MultiDomainCrawlSpider, self).__init__(*args, **kwargs)
        self.rules = self.generate_rules()
        super(MultiDomainCrawlSpider, self)._compile_rules()

    def generate_rules(self):
        rules = []
        for domain, regex in self.domain_regex.items():
            rules.append(
                Rule(
                    LinkExtractor(allow=regex,
                                  allow_domains=domain),
                    callback='parse_page',
                    follow=True
                )
            )
        return tuple(rules)

    def parse_start_url(self, response):
        self.crawled_links[response.url] = []
        return self.parse_page(response)

    def parse_page(self, response):
        start_url = response.meta.get('start_url', response.url)
        current_depth = response.meta.get('depth', 0)

        self.crawled_links[start_url].append(response.url)

        if current_depth + 1 > self.max_depth:
            return

        for link in response.css('a::attr(href)').getall():
            absolute_link = response.urljoin(link)
            domain = urlparse(absolute_link).netloc
            if domain in self.domain_regex and re.match(self.domain_regex[domain], absolute_link):
                absolute_link = response.urljoin(link)
                yield scrapy.Request(
                    absolute_link,
                    meta={'start_url': start_url, 'depth': current_depth + 1},
                    callback=self.parse_page
                )

    def closed(self, reason):
        with open('crawled_links.json', 'w') as f:
            json.dump(self.crawled_links, f, indent=4)
