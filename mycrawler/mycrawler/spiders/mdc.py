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
    rules_dict = {}

    def __init__(self, *args, **kwargs):
        super(MultiDomainCrawlSpider, self).__init__(*args, **kwargs)
        self.rules = self.generate_rules()
        super(MultiDomainCrawlSpider, self)._compile_rules()

    def generate_rules(self):
        rules_dict = {}
        for domain, regex in self.domain_regex.items():
            rules_dict[domain] = (
                Rule(
                    LinkExtractor(allow=regex),
                    callback='parse_page',
                    follow=True
                ),
            )
        self.rules_dict = rules_dict
        # Flatten the rules into a single tuple for the CrawlSpider
        return tuple(rule for rules in rules_dict.values() for rule in rules)

    def _requests_to_follow(self, response):
        if not isinstance(response, scrapy.http.HtmlResponse):
            return
        seen = set()
        domain = urlparse(response.url).netloc
        rules = self.rules_dict.get(domain, self.rules)

        for rule in rules:
            links = [l for l in rule.link_extractor.extract_links(
                response) if l not in seen]
            if links and rule.process_links:
                links = rule.process_links(links)
            for link in links:
                seen.add(link)
                r = self._build_request(link, rule)
                yield rule.process_request(r, response)

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
            yield scrapy.Request(
                absolute_link,
                meta={'start_url': start_url, 'depth': current_depth + 1},
                callback=self.parse_page,
            )

    def closed(self, reason):
        with open('crawled_links.json', 'w') as f:
            json.dump(self.crawled_links, f, indent=4)
