#__author:  bwzhang
#__date:    2018/7/18
import os
import re
from hashlib import md5
import json
from json.decoder import JSONDecodeError
from multiprocessing import Pool
import pymongo
from config import *
import requests
from urllib.parse import urlencode
from bs4 import BeautifulSoup
from requests.exceptions import RequestException
client = pymongo.MongoClient(MONGO_URL,connect=False)
db = client[MONGO_DB]
def get_page_index(offset,keyword):
    data = {
        'autoload':'ture',
        'count':'20',
        'cur_tab':3,
        'format': 'json',
        'keyword': keyword,
        'offset': offset,
    }
    url = 'https://www.toutiao.com/search_content/?' + urlencode(data)
    try:
        response = requests.get(url)
        if response.status_code==200:
            return response.text
        return None
    except RequestException:
        print('请求索引页出错')
        return None
def download_image(url):
    print('Downloading', url)
    try:
        response = requests.get(url)
        if response.status_code == 200:
            save_image(response.content)
        return None
    except ConnectionError:
        return None


def save_image(content):
    file_path = '{0}/{1}.{2}'.format(os.getcwd(), md5(content).hexdigest(), 'jpg')
    print(file_path)
    if not os.path.exists(file_path):
        with open(file_path, 'wb') as f:
            f.write(content)
            f.close()
def parse_page_index(html):
    try:
        data = json.loads(html)
        if data and 'data' in data.keys():
            for item in data.get('data'):
                yield item.get('article_url')
    except JSONDecodeError:
        pass
def get_page_detail(url):
    try:
        response = requests.get(url)
        if response.status_code==200:
            return response.text
        return None
    except RequestException:
        print('请求详情页面出错',url)
        return None
def parse_page_detail(html,url):
    soup = BeautifulSoup(html,'lxml')
    title = soup.select('title')[0].get_text()
    images_pattern = re.compile('gallery :JSON.parse\("(.*)"\)',re.S)
    result = re.search(images_pattern,html)
    if result:
        data = json.loads(result.group(1).replace('\\',''))
        if data and 'sub_images' in data.keys():
            sub_images=data.get('sub_images')
            images = [item.get('url') for item in sub_images]
            for image in images: download_image(image)
            return {
                'title':title,
                'url':url,
                'images':images
            }
def save_to_mongo(result):
    if db[MONGO_TABLE].insert(result):
        print('存储到MongoDB成功',result)
        return True
    return False
def main(offset):
    text = get_page_index(offset,KEYWORD)
    for url in parse_page_index(text):
        html = get_page_detail(url)
        result = parse_page_detail(html,url)
        if result:
            save_to_mongo(result)
if __name__ == '__main__0':
    pool = Pool()
    groups = ([x * 20 for x in range(GROUP_START,GROUP_END + 1)])
    pool.map(main,groups)
    pool.close()
    pool.join()