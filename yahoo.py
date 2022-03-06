import requests
from bs4 import BeautifulSoup
import json
import calc


def update_now_value(df):
    count = 0
    for index, row in df.iterrows():
        # なぜかcodeの先頭に余分な2が付いているので削除する
        code = row['code'][1:]
        update_date, price, change_price, change_price_rate = get_quote(code)

        # 現在値
        df.loc[count, '現在値'] = price

        # 数量
        number = int(row['数量'])

        # 取得単価
        unit_price = int(row['取得単価'])

        # 評価額（小数点以下2位で丸め）
        valuation = calc.calc_valuation(number, price)
        df.loc[count, '評価額'] = round(valuation, 2)

        # 損益
        profit = calc.calc_profit(number, unit_price, valuation)
        df.loc[count, '損益'] = round(profit, 2)

        # 損益（％）
        profit_rate = calc.calc_profit_rate(unit_price, price)
        df.loc[count, '損益（％）'] = round(profit_rate, 2)

        # 前日比
        df.loc[count, '前日比'] = round(change_price, 2)

        # 前日比（％）.
        df.loc[count, '前日比（％）'] = round(change_price_rate, 2)

        # 前日比（金額）
        df.loc[count, '前日比（金額）'] = round(calc.calc_change_price(price, number, change_price_rate), 2)

        count += 1

    print(df)

    return df


def get_quote(code):
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
        print(f'[{name}（{market_name}）] 更新日: {update_date}, 基準価額: {price}円, 前日比: {change_price}円（{change_price_rate}％）')

        return update_date, int(price.replace(',', '')), float(change_price.replace(',', '')), float(change_price_rate.
                                                                                                     replace(',', ''))
