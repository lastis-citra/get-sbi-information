import os
import time
import datetime
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome import service as cs
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup


# 参考: https://hato.yokohama/scraping_sbi_investment/
def connect_sbi(user_id, user_password, driver_path):
    options = Options()
    service = cs.Service(executable_path=driver_path)
    # ヘッドレスモード(chromeを表示させないモード)
    # options.add_argument('--headless')
    driver = webdriver.Chrome(options=options, service=service)

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
    pd.set_option('display.max_rows', None)
    pd.set_option('display.max_columns', None)
    print(df)

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


# ポートフォリオページから保有中の株・投資信託情報を取得
def get_ja_data(driver):
    path = './portfolio.html'

    if driver is not None:
        # 遷移するまで待つ
        time.sleep(4)

        # ポートフォリオの画面に遷移
        driver.find_element(by=By.XPATH, value='//*[@id="link02M"]/ul/li[1]/a/img').click()

        # 文字コードをUTF-8に変換
        html = driver.page_source.encode('utf-8')
        write_html(path, driver.page_source)

        # BeautifulSoupでパース
        soup = BeautifulSoup(html, 'html.parser')
    else:
        html = read_html(path)
        soup = BeautifulSoup(html, 'html.parser')

    # 株式
    # table_tags = soup.find_all('table', bgcolor='#9fbf99', cellpadding='4', cellspacing='1', width='100%')
    # # print(table_tags)
    table_tags = soup.select('td[class="mtext"][align="left"]')

    # 初期化
    data_list = ['ファンド名', '数量', '取得単価', '現在値', '前日比', '前日比（％）', '損益', '損益（％）', '評価額']
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
    # df_ja_result['date'] = datetime.date.today()
    print(df_ja_result)


def main():
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
    get_ja_data(driver)

    if not debug_bool:
        time.sleep(10000)


if __name__ == '__main__':
    main()
