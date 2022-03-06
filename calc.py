# 取得単価の平均を算出する
def calc_unit_price(number1, number2, unit_price1, unit_price2, total_number):
    return (number1 * unit_price1 + number2 * unit_price2) / total_number


# 評価額を算出する
def calc_valuation(number, price):
    return number * price / 10000


# 損益を算出する
def calc_profit(number, unit_price, valuation):
    return valuation - number * unit_price / 10000


# 損益率を算出する
def calc_profit_rate(unit_price, price):
    return (price / unit_price - 1) * 100


# 前日比（金額）を算出する
def calc_change_price(price, number, change_price_rate):
    return change_price_rate / (100 + change_price_rate) * number * price / 10000


# 総合計を算出する
def calc_total(df):
    print('総合計')
    # 評価額総合計
    total_valuation = df['評価額'].sum()
    print(f'評価額: {"{:,.0f}".format(total_valuation)}円')

    # 損益総合計
    total_profit = df['損益'].sum()
    print(f'含み損益: {"{:,.0f}".format(total_profit)}円')

    # 損益（％）総合計
    total_profit_rate = total_profit / (total_valuation - total_profit) * 100
    print(f'含み損益: {round(total_profit_rate, 2)}％')

    # 前日比（金額）総合計
    total_before_ratio_value = df['前日比（金額）'].sum()
    print(f'前日比: {"{:,.0f}".format(total_before_ratio_value)}円')

    # 前日比（％）総合計
    total_before_ratio = total_before_ratio_value / (total_valuation - total_before_ratio_value) * 100
    print(f'前日比: {round(total_before_ratio, 2)}％')
