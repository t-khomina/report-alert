import telegram
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import io # для перенаправления ввода/вывода
import pandas as pd
import pandahouse
from read_db.CH import Getch # коннектор для подключения к БД
import os
from datetime import date
import sys

# алгоритм проверки значения на аномальность методом межквартильного размаха
def check_anomaly(df, metric, a = 3, n = 5): # a - коэффициент для определения ширины интервала допустимых занчений,
                                             # n - количество временных промежутков, используемых для расчёта аномальности
    df['q25'] = df[metric].shift(1).rolling(n).quantile(0.25)
    df['q75'] = df[metric].shift(1).rolling(n).quantile(0.75)
    df['iqr'] = df['q75'] - df['q25']
    df['upper'] = df['q75'] + a * df['iqr']
    df['lower'] = df['q25'] - a * df['iqr']
    
    df['upper'] = df['upper'].rolling(n, center = True, min_periods = 1).mean()
    df['lower'] = df['lower'].rolling(n, center = True, min_periods = 1).mean()
    
    if df[metric].iloc[-1] > df['upper'].iloc[-1] or df[metric].iloc[-1] < df['lower'].iloc[-1]:
        is_alert = 1
    else:
        is_alert = 0

    return is_alert, df


def run_alerts(chat=None):
    chat_id = chat 
    bot = telegram.Bot(token = os.environ.get("REPORT_BOT_TOKEN")) # os.environ.get("REPORT_BOT_TOKEN")

    data = Getch(''' SELECT
                          toStartOfFifteenMinutes(time) as ts
                        , toDate(ts) as date
                        , formatDateTime(ts, '%R') as hm
                        , countIf(DISTINCT user_id, action='view' or action='like') as DAU_feed
                        , countIf(DISTINCT user_id, action='message') as DAU_mes
                        , countIf(user_id, action='view') as Views
                        , countIf(user_id, action='like') as Likes
                        , countIf(user_id, action='message') as Messages
                    FROM     (SELECT user_id, action, time
                              FROM simulator_20220520.feed_actions
                    UNION ALL SELECT user_id, 'message'as action, time
                              FROM simulator_20220520.message_actions) AS virtual_table
                    WHERE ts >=  today() - 1 and ts < toStartOfFifteenMinutes(now())
                    GROUP BY ts, date, hm                    
                    ORDER BY ts''').df

    metrics_list = ['DAU_feed', 'DAU_mes', 'Views', 'Likes', 'Messages']
    for metric in metrics_list:
        df = data[['ts', 'date', 'hm', metric]].copy()
        is_alert, df = check_anomaly(df, metric) # проверка метрики на аномальность
        
        if is_alert == 1:
            msg = '''Метрика {metric}
Текущее значение {current_val:.2f}
Отклонение составляет {prev_val_diff:.2%}
https://superset.lab.karpov.courses/superset/dashboard/953/
@tatiana_khomina'''.format(metric = metric,
                           current_val = df[metric].iloc[-1],
                           prev_val_diff = (df[metric].iloc[-1] / df[metric].iloc[-2]) - 1)

            sns.set(context = 'talk', rc = {'figure.figsize': (16, 10)}) # контекст и размер графика
            sns.set_style('whitegrid') # стиль осей (белый фон без сетки)
            plt.tight_layout()
        
            ax = sns.lineplot(x = df['ts'], y = df[metric], label = metric)
            ax = sns.lineplot(x = df['ts'], y = df['upper'], label = 'upper')
            ax = sns.lineplot(x = df['ts'], y = df['lower'], label = 'lower')

            for ind, label in enumerate(ax.get_xticklabels()): # этот цикл нужен чтобы разрядить подписи координат по оси Х
                if ind % 2 == 0:
                    label.set_visible(True)
                else:
                    label.set_visible(False)
                    
            ax.set(xlabel = 'time') # имя оси Х
            ax.set(ylabel = metric) # имя оси У
            ax.set_title('{}'.format(metric)) # заголовок графика
            ax.set(ylim = (0, None)) # лимит для оси У

            # формирование файлового объекта
            plot_object = io.BytesIO()
            ax.figure.savefig(plot_object)
            plot_object.seek(0) # перенос курсора в начало
            plot_object.name = '{0}.png'.format(metric)
            plt.close()

            bot.sendMessage(chat_id = chat_id, text = msg)
            bot.sendPhoto(chat_id = chat_id, photo = plot_object)

try:
    run_alerts()
except Exception as e:
    print(e)
