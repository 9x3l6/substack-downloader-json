#!/usr/bin/env python3

# python3 -m venv .venv
# . .venv/bin/activate
# pip3 install requests markdownify pillow gazpacho
# ./ssjl.py https://karenkingston.substack.com ~/Downloads/karenkingston

import os
import sys
import argparse
import requests
from requests.exceptions import HTTPError
import markdownify
from PIL import Image
from gazpacho import Soup
from time import sleep, perf_counter
from random import randrange
import asyncio
import json
from pathlib import Path

def create_dir(directory):
    if not os.path.isdir(directory):
        if os.path.exists(directory):
            raise ValueError('Path exists: %s' % directory)
        else:
            os.makedirs(directory)

def fetch_json(url, params):
    if '/api/v1' in url:
        endpoint = url
    else:
        endpoint = "%s/api/v1/archive" % url
    try:
        response = requests.get(endpoint, params=params)
        response.raise_for_status()
        return response.json()
    except HTTPError as err:
        print(f'HTTP error occurred: {err}')
        raise ValueError(err)
    except Exception as err:
        print(f'Other error occurred: {err}')

def fetch_html(url):
    try:
        response = requests.get(url)
        return response.text
    except HTTPError as err:
        print(f'HTTP error occurred: {err}')
        raise ValueError(err)
    except Exception as err:
        print(f'Other error occurred: {err}')

def fetch_and_parse(url, archive=None):
    try:
        limit = 12
        offset = 0
        results_len = 1
        items = []
        if archive:
            if not os.path.exists(archive):
                Path(archive).touch()
            files = open(archive, 'r').readlines()
        else:
            files = []
        while results_len != 0:
            params = {'limit': limit, 'offset': offset}
            try:
                entries = fetch_json(url, params=params)
            except ValueError as err:
                print('Waiting 5 minutes')
                sleep(300)
                entries = fetch_json(url, params=params)
            for item in entries:
                Link = item['canonical_url']
                if '%s\n' % os.path.basename(Link) not in files:
                    Title = item['title']
                    Type = item['type']
                    Slug = item['slug']
                    Subtitle = item['subtitle']
                    Thumb = item['cover_image']
                    Date = item['post_date']
                    try:
                        Html = fetch_html(Link)
                    except ValueError as err:
                        print('Waiting 3 minutes')
                        sleep(180)
                        Html = fetch_html(Link)
                    soup = Soup(Html)
                    content = soup.find('div', {'class': 'markup'})
                    if content:
                        md = html2md(content.html)
                        images = content.find('img')
                        if Type == 'video':
                            videos = content.find('div', {'id': 'media-'}, partial=True)
                        else:
                            videos = []
                        # print(videos)
                        yield {
                            'title': Title,
                            'subtitle': Subtitle,
                            'type': Type,
                            'link': Link,
                            'thumb': Thumb,
                            'md': md,
                            'images': images,
                            'videos': videos,
                            'date': Date,
                        }
                timeout = randrange(5, 60)
                print('Waiting: %s' % timeout)
                sleep(timeout)
            offset = limit + offset
            results_len = len(entries)
    except KeyboardInterrupt:
        sys.exit()

def html2md(html):
    return markdownify.markdownify(html)

def save_files(directory, items, archive=None):
    try:
        create_dir(directory)
        start = perf_counter()
        for item in items:
            print(item['title'])
            file_path = os.path.basename(item['link'])
            # with open('%s%s%s.md' % (directory, os.path.sep, file_path), 'w') as file:
            #     file.write(item['md'])
            #     print('File saved: %s%s%s.md' % (directory, os.path.sep, file_path))
            with open('%s%s%s.json' % (directory, os.path.sep, file_path), 'w') as file:
                file.write(json.dumps({
                    'title': item['title'],
                    'subtitle': item['subtitle'],
                    'type': item['type'],
                    'link': item['link'],
                    'date': item['date'],
                    'md': item['md'],
                }))
                if archive:
                    with open('%s' % archive, 'a') as saved:
                        saved.write('%s\n' % file_path)
                print('File saved: %s.json' % file_path)
            save_article_thumb(directory, item)
            asyncio.run(save_article_images(directory, item))
        end = perf_counter()
        print(f'It took {round(end-start, 0)} second(s) to complete.')
    except KeyboardInterrupt:
        sys.exit()

def save_image(url, file_path):
    if url:
        data = requests.get(url).content
        ext = os.path.splitext(url)[1]
        if ext:
            with open('%s%s' % (file_path, ext), 'wb') as file:
                file.write(data)
                print('Image saved: %s%s' % (file_path, ext))

def save_article_thumb(directory, item):
    url = item['thumb']
    if url:
        file_path = '%s%s%s' % (directory, os.path.sep, os.path.basename(item['link']))
        save_image(url, file_path)

async def save_article_images(directory, item):
    async def download_image(url):
        if url:
            ext = os.path.splitext(url)[1]
            file_path = '%s%s%s%s%s' % (directory, os.path.sep, os.path.basename(item['link']), os.path.sep, os.path.basename(url).replace(ext, ''))
            d = os.path.dirname(file_path)
            if not os.path.isdir(d):
                os.makedirs(d)
            save_image(url, file_path)
    if item['images']:
        if type(item['images']) == list:
            urls = [img.attrs['src'] for img in item['images']]
        else:
            urls = [item['images'].attrs['src']]
        imgs = []
        for img in urls:
            imgs.append(asyncio.create_task(download_image(img)))
        await asyncio.gather(*imgs)

def arguments():
    parser = argparse.ArgumentParser(description='Substack Downloader')
    parser.add_argument('url', help='Substack URL to download')
    parser.add_argument('dir', help='Directory where to download')
    parser.add_argument("--archive", required=False, help="Archive that saves list of downloaded files")

    args = parser.parse_args()
    return args

if __name__ == '__main__':
    args = arguments()
    save_files(args.dir, fetch_and_parse(args.url, args.archive), args.archive)
