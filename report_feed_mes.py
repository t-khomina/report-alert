import telegram
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import io #для перенаправления ввода/вывода
import pandas as pd
import pandahouse
from read_db.CH import Getch #коннектор для подключения к БД
import os

sns.set()

def send_plot(bot, chat_id, data, x, y):
    sns.set_style('whitegrid')
    fig, ax = plt.subplots(figsize=(16, 10))
    sns.lineplot(data[x], data[y])
    plt.title(f'{y} за неделю')
    plot_object = io.BytesIO()
    plt.savefig(plot_object)
    plot_object.seek(0) #перенос курсора в начало
    plt.close()
    bot.sendPhoto(chat_id=chat_id, photo=plot_object)

def report_feed_mes(chat=None):
    chat_id = chat or -715060805 #-715060805 746901250
    bot = telegram.Bot(token=os.environ.get("REPORT_BOT_TOKEN")) #os.environ.get("REPORT_BOT_TOKEN")
    
    data = Getch('''SELECT
                          toStartOfDay(time) as ts
                        , toString(toDate(ts)) as date
                        , uniqExact(user_id) as DAU_common
                        , countIf(DISTINCT user_id, action='view' or action='like') as DAU_feed
                        , countIf(DISTINCT user_id, action='message') as DAU_mes
                        , countIf(user_id, action='message') as Messages
                        , countIf(user_id, action='view') as Views
                        , countIf(user_id, action='like') as Likes
                        , round(countIf(user_id, action='like') / countIf(user_id, action ='view'), 2) as CTR
                    FROM     (SELECT user_id, action, time
                              FROM simulator_20220520.feed_actions
                    UNION ALL SELECT user_id, 'message'as action, time
                              FROM simulator_20220520.message_actions) AS virtual_table
                    WHERE (ts >= today() - 7) and (ts < today())
                    GROUP BY ts, date
                    ORDER BY ts DESC''').df
    
    date = data['date'].iloc[0]
    DAU_common = data['DAU_common'].iloc[0]
    DAU_feed = data['DAU_feed'].iloc[0]
    DAU_mes = data['DAU_mes'].iloc[0]
    Messages = data['Messages'].iloc[0]
    Views = data['Views'].iloc[0]
    Likes = data['Likes'].iloc[0]
    CTR = data['CTR'].iloc[0]

    msg = f'''
    Метрики ленты и мессенджера за {date}:
    DAU всего приложения: {DAU_common}
    DAU ленты: {DAU_feed}
    DAU мессенджера: {DAU_mes}
    Сообщения: {Messages}
    Просмотры: {Views}
    Лайки: {Likes}
    CTR из просмотра в лайк: {round(CTR, 2)}'''

    bot.sendMessage(chat_id=chat_id, text=msg)
    
    send_plot(bot, chat_id, data, 'date', 'DAU_common')
    send_plot(bot, chat_id, data, 'date', 'DAU_feed')
    send_plot(bot, chat_id, data, 'date', 'DAU_mes')
    send_plot(bot, chat_id, data, 'date', 'Messages')

try:
    report_feed_mes()
except Exception as e:
    print(e)
