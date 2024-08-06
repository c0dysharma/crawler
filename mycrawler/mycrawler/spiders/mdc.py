import scrapy
import re
import json
from urllib.parse import urlparse


class MultiDomainSpider(scrapy.Spider):
    name = "mdc"

    start_urls = [
        'https://en.wikipedia.org/wiki/Vim_(text_editor)',
        'https://in.ign.com/five-nights-at-freddys/187643/lists/how-to-play-the-five-nights-at-freddys-games-in-chronological-order'
    ]

    domain_regex = {
        'en.wikipedia.org': r'^https://en\.wikipedia\.org/wiki/.*$',
        'in.ign.com': r'^https://in\.ign\.com/.*$',
    }

    crawled_links = {}  # will store results
    max_depth = 1  # how much to crawl

    def start_requests(self):
        for url in self.start_urls:
            domain = urlparse(url).netloc
            self.crawled_links[url] = []  # Initialize with an empty list

            # setting first depth as 0
            yield scrapy.Request(url, meta={'origin_domain': domain, 'start_url': url, 'depth': 0}, callback=self.parse)

    def parse(self, response):
        origin_domain = response.meta['origin_domain']
        start_url = response.meta['start_url']
        current_depth = response.meta['depth']

        # check if the current depth exceeds the maximum depth
        if current_depth > self.max_depth:
            return  # stop processing further links

        regex_pattern = self.domain_regex.get(origin_domain, None)
        if not regex_pattern:
            self.logger.warning(
                f"No regex pattern found for domain: {origin_domain}")
            return

        links_found = response.css('a::attr(href)').getall()
        self.logger.info(f"Found {len(links_found)} links in {response.url}")

        for link in links_found:
            absolute_link = response.urljoin(link)

            if re.match(regex_pattern, absolute_link):
                self.crawled_links[start_url].append(absolute_link)
                if current_depth + 1 <= self.max_depth:
                    yield scrapy.Request(absolute_link, meta={'origin_domain': origin_domain, 'start_url': start_url, 'depth': current_depth + 1}, callback=self.parse)

    def closed(self):
        with open('crawled_links.json', 'w') as f:
            json.dump(self.crawled_links, f, indent=4)
        self.logger.info(f"Crawled links: {self.crawled_links}")
