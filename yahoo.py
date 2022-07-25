import requests
from bs4 import BeautifulSoup
import json
import calc
import util
import datetime as dt
import cloudscraper


def update_now_value(df):
    count = 0
    unit_number = 10000
    update_date_list = []
    for index, row in df.iterrows():
        # なぜかcodeの先頭に余分な2が付いているので削除する
        code = row['code'][1:]
        update_date, price, change_price, change_price_rate = get_ja_quote(code)

        # 現在値
        df.loc[count, '現在値'] = price

        # 数量
        number = int(row['数量'])

        # 取得単価
        unit_price = int(row['取得単価'])

        # 評価額（小数点以下2位で丸め）
        valuation = calc.calc_valuation(number, unit_number, price)
        df.loc[count, '評価額'] = round(valuation, 2)

        # 損益
        profit = calc.calc_profit(number, unit_number, unit_price, valuation)
        df.loc[count, '損益'] = round(profit, 2)

        # 損益（％）
        profit_rate = calc.calc_profit_rate(unit_price, price)
        df.loc[count, '損益（％）'] = round(profit_rate, 2)

        # 前日比
        df.loc[count, '前日比'] = round(change_price, 2)

        # 前日比（％）.
        df.loc[count, '前日比（％）'] = round(change_price_rate, 2)

        # 前日比（金額）
        df.loc[count, '前日比（金額）'] = round(calc.calc_change_price(price, number, unit_number, change_price_rate), 2)

        # 更新日時（03/10という形式から変換）
        now_year = dt.date.today().strftime('%Y')
        update_date_year_added = f'{now_year}/{update_date}'
        # もし2020/12/31のデータを2021/1/1に取得すると，2021/12/31となってしまうため，1年引く処理を入れる
        if dt.datetime.strptime(update_date_year_added, '%Y/%m/%d').date() > dt.date.today():
            now_year -= 1
            update_date_year_added = f'{now_year}/{update_date}'
        update_date_ja = dt.datetime.strptime(update_date_year_added, '%Y/%m/%d')
        update_date_list.append(update_date_ja.strftime('%Y/%m/%d %H:%M:%S'))

        count += 1

    df['update'] = update_date_list
    print(df)

    return df


def get_ja_quote(code):
    url = 'https://finance.yahoo.co.jp/quote/' + code
    res = requests.get(url)
    res.encoding = res.apparent_encoding
    soup = BeautifulSoup(res.text, 'html.parser')
    script_tags = soup.select('script')

    json_data = None

    for script_tag in script_tags:
        if 'PRELOADED_STATE' in script_tag.text:
            json_text = script_tag.text.split(' = ')[1]
            # print(json_text)
            json_data = json.loads(json_text)
            break

    if json_data is not None:
        name = json_data['mainFundPriceBoard']['fundPrices']['name']
        market_name = json_data['mainFundPriceBoard']['fundPrices']['marketName']
        update_date = json_data['mainFundPriceBoard']['fundPrices']['updateDate']
        price = json_data['mainFundPriceBoard']['fundPrices']['price']
        change_price = json_data['mainFundPriceBoard']['fundPrices']['changePrice']
        change_price_rate = json_data['mainFundPriceBoard']['fundPrices']['changePriceRate']
        print(f'[{name}（{market_name}）] 更新日: {update_date}, 基準価額: {price}円, '
              f'前日比: {change_price}円（{change_price_rate}％）')

        return update_date, util.str2float(price), util.str2float(change_price), util.str2float(change_price_rate)


def update_foreign_now_value(df):
    count = 0
    unit_number = 1
    update_date_list = []
    _, usd_jyp, _, _ = get_foreign_quote('JPY=X')
    for index, row in df.iterrows():
        code = row['code']
        update_date, price, change_price, change_price_rate = get_foreign_quote(code)
        price = usd_jyp * price
        change_price = usd_jyp * change_price

        # 現在値
        df.loc[count, '現在値'] = round(price, 2)

        # 数量
        number = int(row['数量'])

        # 取得単価
        unit_price = int(row['取得単価'])

        # 評価額（小数点以下2位で丸め）
        valuation = calc.calc_valuation(number, unit_number, price)
        df.loc[count, '評価額'] = round(valuation, 2)

        # 損益
        profit = calc.calc_profit(number, unit_number, unit_price, valuation)
        df.loc[count, '損益'] = round(profit, 2)

        # 損益（％）
        profit_rate = calc.calc_profit_rate(unit_price, price)
        df.loc[count, '損益（％）'] = round(profit_rate, 2)

        # 前日比
        df.loc[count, '前日比'] = round(change_price, 2)

        # 前日比（％）.
        df.loc[count, '前日比（％）'] = round(change_price_rate, 2)

        # 前日比（金額）
        df.loc[count, '前日比（金額）'] = round(calc.calc_change_price(price, number, unit_number, change_price_rate), 2)

        # 更新日時
        update_date_ja = dt.datetime.fromtimestamp(update_date, dt.timezone(dt.timedelta(hours=9)))
        update_date_list.append(update_date_ja.strftime('%Y/%m/%d %H:%M:%S'))

        count += 1

    df['update'] = update_date_list
    print(df)

    return df


def get_foreign_quote(code):
    url = 'https://finance.yahoo.com/quote/' + code
    # print(url)
    scraper = cloudscraper.create_scraper()
    res = scraper.get(url)
    # res = requests.get(url)
    res.encoding = res.apparent_encoding
    soup = BeautifulSoup(res.text, 'html.parser')
    # print(soup)
    script_tags = soup.select('script')

    json_data = None

    for script_tag in script_tags:
        if 'root.App.main' in script_tag.text:
            json_text = script_tag.text.split('root.App.main = ')[1].split(';\n')[0]
            # print(json_text)
            # with open(f'./log/{code}.json', mode='w') as f:
            #     f.write(json_text.encode('cp932', "ignore").decode('cp932'))
            json_data = json.loads(json_text)
            break

    if json_data is not None:
        quote_summary_store = json_data['context']['dispatcher']['stores']['QuoteSummaryStore']
        # print(json.dumps(quote_summary_store['price']))
        name = quote_summary_store['price']['longName']
        market_name = quote_summary_store['price']['exchangeName']
        update_date = quote_summary_store['price']['regularMarketTime']
        price = quote_summary_store['price']['regularMarketPrice']['fmt']
        change_price = quote_summary_store['price']['regularMarketChange']['fmt']
        change_price_rate = quote_summary_store['price']['regularMarketChangePercent']['fmt'].replace('%', '')
        currency = quote_summary_store['price']['currency']
        symbol = quote_summary_store['price']['symbol']

        update_date_ja = dt.datetime.fromtimestamp(update_date, dt.timezone(dt.timedelta(hours=9)))
        update_date_ja = update_date_ja.strftime('%Y/%m/%d %H:%M:%S')
        print(f'[{name}({symbol})（{market_name}）] 更新日: {update_date_ja}, 基準価額: {price}{currency}, '
              f'前日比: {change_price}{currency}（{change_price_rate}％）')

        return update_date, util.str2float(price), util.str2float(change_price), util.str2float(change_price_rate)
