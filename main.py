import os
import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome import service as cs
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import yahoo
import calc
import util


# 参考: https://hato.yokohama/scraping_sbi_investment/
def connect_sbi(user_id, user_password, driver_path):
    options = Options()
    service = cs.Service(executable_path=driver_path)
    # ヘッドレスモード(chromeを表示させないモード)
    options.add_argument('--headless')
    driver = webdriver.Chrome(options=options, service=service)
    # 一度設定すると find_element 等の処理時に、
    # 要素が見つかるまで指定時間繰り返し探索するようになります。
    driver.implicitly_wait(10)

    # SBI証券のトップ画面を開く
    driver.get('https://www.sbisec.co.jp/ETGate')

    # ユーザーIDとパスワード
    input_user_id = driver.find_element(by=By.NAME, value='user_id')
    input_user_id.send_keys(user_id)
    input_user_password = driver.find_element(by=By.NAME, value='user_password')
    input_user_password.send_keys(user_password)

    # ログインボタンをクリック
    driver.find_element(by=By.NAME, value='ACT_login').click()

    return driver


def write_html(path, source):
    # Windows向けの変換
    html = source.encode('cp932', "ignore").decode('cp932')
    with open(path, mode='w') as f:
        f.write(html)


def read_html(path):
    with open(path) as f:
        s = f.read()

    return s


def init_df(data_list):
    return pd.DataFrame(columns=data_list)


def format_data(df_data, category, data_list):
    # 必要な列のみ抽出
    df_data = df_data.loc[:, data_list]

    df_data['カテゴリー'] = category

    return df_data


def get_ja_table_data(table_tag, name, data_list):
    # 文字が入っている部分の親の次の兄弟
    soup = BeautifulSoup(str(table_tag.parent.next_sibling.next_sibling), 'html.parser')
    table_tag = soup.select_one('table[bgcolor="#9fbf99"]')
    df = pd.read_html(str(table_tag), header=0)[0]
    df = format_data(df, name, data_list)
    # print(df)

    # コードを取得してdfに追加する処理
    tr_tags = soup.select('tr[align=center]')
    code_list = []
    for tr_tag in tr_tags:
        # タイトル行は飛ばす
        bgcolor = tr_tag.select('td')[0]['bgcolor']
        if bgcolor == '#b9e8ae':
            continue

        code = tr_tag.select('td')[1].select_one('a')['href'].split('=')[1].split('&')[0]
        code_list.append(code)
    df['code'] = code_list

    return df


# 同じcodeの株式や投資信託を1つのデータにまとめる
def merge_same_code(df):
    # first：最初の値以外は重複(True)として扱う
    duplicated_bool = df.duplicated(subset=['code'], keep='first')
    # print(duplicated_bool)

    delete_row_list = []
    change_price_list = []
    count = 0
    unit_number = 10000
    old_number = 0
    old_unit_price = 0
    for index, row in df.iterrows():
        if duplicated_bool[count]:
            # 現在値
            now_price = row['現在値']

            # 数量
            number = int(row['数量'])
            added_number = number + old_number
            df.loc[count, '数量'] = added_number
            # print(f'old_number: {old_number}, number: {number}, added_number: {added_number}')

            # 取得単価
            unit_price = int(row['取得単価'])
            added_unit_price = calc.calc_unit_price(old_number, number, old_unit_price, unit_price, added_number)
            df.loc[count, '取得単価'] = int(added_unit_price)

            # 評価額（小数点以下2位で丸め）
            added_valuation = calc.calc_valuation(added_number, unit_number, now_price)
            df.loc[count, '評価額'] = round(added_valuation, 2)

            # 損益
            added_profit = calc.calc_profit(added_number, unit_number, added_unit_price, added_valuation)
            df.loc[count, '損益'] = round(added_profit, 2)

            # 損益（％）
            added_profit_rate = calc.calc_profit_rate(added_unit_price, now_price)
            df.loc[count, '損益（％）'] = round(added_profit_rate, 2)

            delete_row_list.append(count - 1)

        # print(row[2])
        old_number = int(row['数量'])
        old_unit_price = int(row['取得単価'])
        count += 1

    df = df.drop(delete_row_list)
    for index, row in df.iterrows():
        # 現在値
        now_price = row['現在値']
        # 前日比（％）
        change_price_ratio = row['前日比（％）']

        # 前日比（金額）
        change_price = calc.calc_change_price(now_price, row['数量'], unit_number, change_price_ratio)
        change_price_list.append(round(change_price, 2))

    df['前日比（金額）'] = change_price_list
    df = df.reset_index().drop(columns=['level_0', 'index', 'カテゴリー'])
    print(df)

    return df


# ポートフォリオページから保有中の株・投資信託情報を取得
def get_ja_data(driver, data_list):
    portfolio_path = './portfolio.html'

    if driver is not None:
        # 遷移するまで待つ
        # time.sleep(4)

        # ポートフォリオの画面に遷移
        driver.find_element(by=By.XPATH, value='//*[@id="link02M"]/ul/li[1]/a/img').click()
        # ID指定したページ上の要素が読み込まれるまで待機（10秒でタイムアウト判定）
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, 'FOOTER02')))

        # 文字コードをUTF-8に変換
        html = driver.page_source.encode('utf-8')
        write_html(portfolio_path, driver.page_source)

        # BeautifulSoupでパース
        soup = BeautifulSoup(html, 'html.parser')
    else:
        html = read_html(portfolio_path)
        soup = BeautifulSoup(html, 'html.parser')

    # 株式
    table_tags = soup.select('td[class="mtext"][align="left"]')

    # 初期化
    df_stock_specific = init_df(data_list)
    df_stock_fund_nisa = init_df(data_list)
    df_fund_specific = init_df(data_list)
    df_fund_nisa = init_df(data_list)
    df_fund_nisa_accumulation = init_df(data_list)

    for table_tag in table_tags:
        if '株式（現物/特定預り）' in table_tag.text:
            df_stock_specific = get_ja_table_data(table_tag, '株式（現物/特定預り）', data_list)
        elif '株式（現物/NISA預り）' in table_tag.text:
            df_stock_fund_nisa = get_ja_table_data(table_tag, '株式（現物/NISA預り）', data_list)
        elif '投資信託（金額/特定預り）' in table_tag.text:
            df_fund_specific = get_ja_table_data(table_tag, '投資信託（金額/特定預り）', data_list)
        elif '投資信託（金額/NISA預り）' in table_tag.text:
            df_fund_nisa = get_ja_table_data(table_tag, '投資信託（金額/NISA預り）', data_list)
        elif '投資信託（金額/つみたてNISA預り）' in table_tag.text:
            df_fund_nisa_accumulation = get_ja_table_data(table_tag, '投資信託（金額/つみたてNISA預り）', data_list)

    # 結合
    df_ja_result = pd.concat(
        [df_stock_specific, df_stock_fund_nisa, df_fund_specific, df_fund_nisa, df_fund_nisa_accumulation])
    # code順に並び替え，インデックスを0から順に振り直す
    df_ja_result = df_ja_result.sort_values('code').reset_index()
    # print(df_ja_result)

    # 同じcodeの株式や投資信託を1つのデータにまとめる
    df_ja_result = merge_same_code(df_ja_result)

    # 総合計を算出する
    calc.calc_total(df_ja_result)

    # 最新の基準価額に更新する
    df_ja_result = yahoo.update_now_value(df_ja_result)

    # 総合計を算出する
    calc.calc_total(df_ja_result)

    return df_ja_result


def format_foreign_data(df, data_list):
    def get_price(value):
        return value.split(' ')[1].replace('円', '')

    name_list = []
    number_list = []
    unit_price_list = []
    price_list = []
    profit_list = []
    profit_rate_list = []
    valuation_list = []
    code_list = []
    count = 0
    for index, row in df.iterrows():
        # dfの最後の1行は合計なので飛ばす
        if count < len(df) - 1:
            # ファンド名
            name_pre = row['銘柄コード･市場']
            name = name_pre.replace(' ' + name_pre.split(' ')[-1], '')
            name_list.append(name)

            # code
            code = name.split(' ')[-1]
            code_list.append(code)

            # 数量
            number_pre = row['保有数量(売却注文中)']
            number = number_pre.split('(')[0]
            number_list.append(util.str2int(number))

            # 取得単価
            unit_price_pre = row['取得単価円換算額']
            unit_price = get_price(unit_price_pre)
            unit_price_list.append(util.str2int(unit_price))

            # 取得金額
            unit_valuation_pre = row['取得金額円換算額']
            unit_valuation = get_price(unit_valuation_pre)

            # 現在値
            price_pre = row['現在値円換算額']
            price = get_price(price_pre)
            price_list.append(util.str2int(price))

            # 損益
            profit_pre = row['外貨建評価損益円換算評価損益 金額 ％']
            profit = get_price(profit_pre)
            profit_list.append(util.str2int(profit))

            # 評価額
            valuation_pre = row['外貨建評価額円換算評価額']
            valuation = get_price(valuation_pre)
            valuation_list.append(util.str2float(valuation))

            # 損益（％）
            profit_rate = (int(valuation.replace(',', '')) / int(unit_valuation.replace(',', '')) - 1) * 100
            profit_rate_list.append(round(profit_rate, 2))

        count += 1

    df_foreign_result = init_df(data_list)
    df_foreign_result['ファンド名'] = name_list
    df_foreign_result['数量'] = number_list
    df_foreign_result['取得単価'] = unit_price_list
    df_foreign_result['現在値'] = price_list
    df_foreign_result['損益'] = profit_list
    df_foreign_result['損益（％）'] = profit_rate_list
    df_foreign_result['評価額'] = valuation_list
    df_foreign_result['code'] = code_list
    print(df_foreign_result)

    # 最新の基準価額に更新する
    df_foreign_result = yahoo.update_foreign_now_value(df_foreign_result)

    # 総合計を算出する
    calc.calc_total(df_foreign_result)

    return df_foreign_result


def get_foreign_data(driver, data_list):
    foreign_path = './foreign.html'

    if driver is not None:
        # 遷移するまで待つ
        # time.sleep(4)

        # ホーム画面に遷移
        driver.find_element(by=By.XPATH, value='//*[@id="navi01P"]/ul/li[1]/a/img').click()

        # 遷移するまで待つ
        # time.sleep(4)

        # 外国株式のページに遷移
        # driver.find_element(by=By.XPATH, value='//*[@id="SUBAREA01"]/div[4]/div/div/ul/li[5]/a').click()
        # https://office54.net/python/scraping/selenium-click-exception
        element = driver.find_element(by=By.XPATH, value='//*[@id="SUBAREA01"]/div[4]/div/div/ul/li[5]/a')
        driver.execute_script("arguments[0].click();", element)
        # 別ウインドウで開かれているため，ウインドウを切り替える
        handle_array = driver.window_handles
        driver.switch_to.window(handle_array[1])

        # 遷移するまで待つ
        # time.sleep(4)

        # 保有証券のページへ移動
        driver.get('https://global.sbisec.co.jp/Fpts/czk/secCashBalance/moveSecCashBalance')

        # 文字コードをUTF-8に変換
        html = driver.page_source.encode('utf-8')
        write_html(foreign_path, driver.page_source)

        # BeautifulSoupでパース
        soup = BeautifulSoup(html, 'html.parser')
    else:
        html = read_html(foreign_path)
        soup = BeautifulSoup(html, 'html.parser')

    # 株式
    table_tag = soup.select_one('#secStockListTable0')
    df = pd.read_html(str(table_tag), header=0)[0]
    # print(df)
    df_foreign_result = format_foreign_data(df, data_list)

    return df_foreign_result


def main():
    pd.set_option('display.max_rows', None)
    pd.set_option('display.max_columns', None)
    pd.set_option('display.max_seq_items', None)
    pd.set_option('display.max_colwidth', 500)
    pd.set_option('expand_frame_repr', True)
    # print時の折り返し幅の拡張
    pd.set_option('display.width', 500)
    # 全角文字幅を考慮して表示
    pd.set_option('display.unicode.east_asian_width', True)

    user_id = os.environ.get('ID')
    user_password = os.environ.get('PASSWORD')
    driver_path = os.environ.get('DRIVER_PATH')
    debug = os.environ.get('DEBUG')
    debug_bool = False
    if debug == 'True':
        debug_bool = True
    if debug_bool:
        driver = None
    else:
        driver = connect_sbi(user_id, user_password, driver_path)

    data_list = ['ファンド名', '数量', '取得単価', '現在値', '前日比', '前日比（％）', '損益', '損益（％）', '評価額']
    df_ja_result = get_ja_data(driver, data_list)
    df_foreign_result = get_foreign_data(driver, data_list)
    df_all = pd.concat([df_ja_result, df_foreign_result])

    # 総合計を算出する
    calc.calc_total(df_all)

    if not debug_bool:
        time.sleep(10000)


if __name__ == '__main__':
    main()
