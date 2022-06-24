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

def report(chat=None):
    chat_id = chat
    bot = telegram.Bot(token=os.environ.get("REPORT_BOT_TOKEN")) #os.environ.get("REPORT_BOT_TOKEN")
    
    data = Getch('''SELECT
                          toStartOfDay(time) as ts
                        , toString(toDate(ts)) as date
                        , uniqExact(user_id) as DAU
                        , countIf(user_id, action='view') as Views
                        , countIf(user_id, action='like') as Likes
                        , round(countIf(user_id, action='like') / countIf(user_id, action ='view'), 2) as CTR
                    FROM simulator_20220520.feed_actions
                    WHERE (ts >= today() - 7) and (ts < today())
                    GROUP BY ts, date
                    ORDER BY ts DESC''').df
    
    date = data['date'].iloc[0]
    DAU = data['DAU'].iloc[0]
    Views = data['Views'].iloc[0]
    Likes = data['Likes'].iloc[0]
    CTR = data['CTR'].iloc[0]

    msg = f'''
    Метрики ленты за {date}:
    DAU: {DAU}
    Просмотры: {Views}
    Лайки: {Likes}
    CTR из просмотра в лайк: {round(CTR, 2)}'''

    bot.sendMessage(chat_id=chat_id, text=msg)
    
    send_plot(bot, chat_id, data, 'date', 'DAU')
    send_plot(bot, chat_id, data, 'date', 'Views')
    send_plot(bot, chat_id, data, 'date', 'Likes')
    send_plot(bot, chat_id, data, 'date', 'CTR')

try:
    report()
except Exception as e:
    print(e)
