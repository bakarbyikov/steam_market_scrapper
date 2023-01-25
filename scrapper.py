import csv
import json
import os
from datetime import datetime
from itertools import count
from time import sleep, time
from typing import List

import requests
from dotenv import load_dotenv
from tqdm import tqdm

load_dotenv()

request_delay_s = 6

pricehistory_link = "https://steamcommunity.com/market/pricehistory/"
search_link = "https://steamcommunity.com/market/search/render/"

header = {
    "Host": "steamcommunity.com",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/109.0",
    "Accept": "*/*",
    "Accept-Language": "ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://steamcommunity.com/profiles/76561198257383222/inventory",
    "Connection": "keep-alive",
    "Sec-Fetch-Dest": "empty",
    "Cookie": f"steamLoginSecure={steamLoginSecure}",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "Pragma": "no-cache",
    "Cache-Control": "no-cache",
}


def parse_date(date: str) -> datetime:
    time_parse_pattern = "%b %d %Y %H: +0"
    return datetime.strptime(date, time_parse_pattern)

def not_so_fast(func):
    delay = request_delay_s
    func.last_run = 0

    def inner(*args, **kwargs):
        delta = time() - func.last_run
        if delta < delay:
            sleep(delay-delta)
        func.last_run = time()
        return func(*args, **kwargs)

    return inner

@not_so_fast
def make_request(link, params=None, attempt=0) -> requests.Response:
    req = requests.get(link, headers=header, params=params)
    if req.status_code == 200:
        return req
    if attempt < 3:
        return make_request(link, params, attempt+1)
    raise ConnectionError(f"Cant reach link. {req.status_code = }, {link = }")

def get_item_prices(item_name: str, appid: int) -> List[List[str]]:
    params = {
        "appid": str(appid),
        "market_hash_name": item_name
    }
    req = make_request(pricehistory_link, params)
    parsed = json.loads(req.text)
    if not parsed['success']:
        print(f"Failed to get '{item_name}', {parsed=}")
        return None
    prices = parsed['prices']
    return prices

def save_items(items, appid=730):
    try:
        os.mkdir('resultfile')
    except FileExistsError:
        pass

    for item in tqdm(items, desc='Processing items'):
        filename = item.replace(':', '_')
        with open(f'resultfile/{filename}.csv', 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(["Date", "Price", "Sold"])
            prices = get_item_prices(item, appid)
            for row in prices:
                day, price, count = row
                day = parse_date(day)
                writer.writerow([day, price, count])

def search_items(appid: int, query: str):
    page_size = 100
    names = []
    for i in count(0, page_size):
        params = {
            "appid": str(appid),
            "query": query,
            "count": str(page_size),
            "norender": "1",
            "start": str(i),
        }
        req = make_request(search_link, params)
        res = json.loads(req.text)
        if not res['success']: 
            to_print = {k: v for k, v in res.items()}
            del to_print['results']
            raise AssertionError(f'request unseccessfull: res = {to_print}')
            
        names.extend([i['hash_name'] for i in res['results']])
        if res["total_count"] <= i + page_size:
            break
        
    return names

if __name__ == "__main__":
    appid = 730
    search_query = 'кейс'
    items = search_items(appid, search_query)
    items.sort(key=str.lower)
    print(f"Finded {len(items)} items:")
    print(*items, sep='\n')
    save_items(items, appid)
    