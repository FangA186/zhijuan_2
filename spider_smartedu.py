#!/usr/bin/env python3
"""Compatibility entry point; the crawler now lives in tools/crawler/."""
from tools.crawler.spider_smartedu import filter_by_page_url, main, step1_fetch_tags, step2_fetch_all_materials
from tools.crawler.smartedu_details import step3_and_4_fetch_details_and_trees

if __name__ == "__main__":
    main()
