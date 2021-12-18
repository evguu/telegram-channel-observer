# Импорты
import psycopg2
import urllib.parse as urlparse
import os
import telebot
import threading
from telethon.sync import TelegramClient
from telethon import events


# Конфигурационные константы
# ----------------------------

# Здесь вставляется токен бота от BotFather
BOT_TOKEN = "" 

# Здесь указыватся ссылка на бота (без @).
bot_id = ""

# Здесь указывается ID пользователя, который будет получать уведомления. Он должен предварительно инициировать диалог с ботом.
# Скорее всего это произойдет при вызове команды /id для получения его ID.
RECIPIENT_ID = ""

# Две следующих переменных получаются путем создания приложения Telegram.
# https://docs.telethon.dev/en/latest/basic/signing-in.html
api_id = ""
api_hash = ""

# Имя сессии. Влияет только на имя файла сессии. Если сменить, потребуется повторная авторизация. Можно не менять.
username = "Username"

# Идентификатор канала, за которым осуществляется слежение.
# Авторизовавшийся пользователь должен быть подписан на канал (скорее всего).
# Для получения списка каналов установите переменную list_all_channels_on_start_and_terminate = True
# При установке этой переменной данные связанные с ботом не потребуются.
# Пример: -1001234567890
channel = ""
list_all_channels_on_start_and_terminate = False

# Эту строку можно использовать вместо строк ниже, если все данные аутентификации postgres фиксированы и известны.
# Если эта строка расскомментирована, строки ниже должны быть закомментированы.
conn = psycopg2.connect(database="observer",host="localhost",user="postgres",password="itransition")

# Эти строки подключат базу данных на Heroku.
# Предварительно нужно подключить аддон postgres к приложению.
"""
url = urlparse.urlparse(os.environ['DATABASE_URL'])
conn = psycopg2.connect(
  database=url.path[1:],
  user=url.username,
  password=url.password,
  host=url.hostname,
  port=url.port)
"""

# ----------------------------
# Конец конфигурационных констант

"""
Перед конфигурацией необходимо установить зависимости из Pipfile или requirements.txt.

Порядок конфигурации:
1. Создать бота и получить его токен. Записать его в переменную BOT_TOKEN. Записать ссылку на бота в переменную bot_id.
2. Создать приложение Telegram. Записать его ID и хэш в переменные api_id и api_hash.
3. Внести данные о базе данных в переменную conn согласно ее комментарию.
4. Подписаться на нужный канал. Установить list_all_channels_on_start_and_terminate = True. Запустить программу.
   Найти необходимый канал и записать его идентификатор в переменную channel. Закрыть программу. Установить переменную list_all_channels_on_start_and_terminate = False.
5. Запустить программу. Написать боту с аккаунта пользователя команду /id. Закрыть программу. Внести ответ в переменную RECIPIENT_ID.
6. Запустить программу. Бот запущен. 
   Можно добавить слова для отслеживания используя команду /add. 
   Можно удалить слова используя команду /remove.

Для удобства настройки рекомендуется запускать программу через start python script.py. Это упрощает ее закрытие и повторный запуск, так как на Ctrl+Z, Ctrl+C и другие сочетания она не реагирует.
После конфигурации можно запускать программу на сервере. Необходимо убедиться, что данные для базы данных действительны для сервера, а также что файл сессии загружен вместе с кодом.
"""


class KeywordManager:
  @staticmethod
  def init_table():
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS watchword (watchstr varchar(100) NOT NULL, PRIMARY KEY (watchstr))")
    cur.close()
    conn.commit()

  @staticmethod
  def get_keywords():
    cur = conn.cursor()
    cur.execute("SELECT watchstr FROM watchword")
    records = cur.fetchall()
    cur.close()
    return [a[0] for a in records]

  @staticmethod
  def add_keyword(wd):
    cur = conn.cursor()
    cur.execute("INSERT INTO watchword (watchstr) VALUES (%s)", (wd,))
    cur.close()

  @staticmethod
  def remove_keyword(wd):
    cur = conn.cursor()
    cur.execute("DELETE FROM watchword WHERE watchstr=%s", (wd,))
    cur.close()



KeywordManager.init_table()
words = KeywordManager.get_keywords()

bot = telebot.TeleBot(BOT_TOKEN)

@bot.message_handler(commands=['echo_to_recipient'])
def send_welcome(message):
  arg = message.text.split("/echo_to_recipient ")
  if(len(arg) > 1):
    bot.send_message(RECIPIENT_ID, arg[1])

@bot.message_handler(commands=['add'])
def add(message):
  arg = message.text.split("/add ")
  if(len(arg) > 1):
    if arg[1] not in words:
      words.append(arg[1])
      KeywordManager.add_keyword(arg[1])
      conn.commit()
    bot.reply_to(message, str(words))
  else:
    bot.reply_to(message, "No word provided")

@bot.message_handler(commands=['remove'])
def remove(message):
  arg = message.text.split("/remove ")
  if(len(arg) > 1):
    if arg[1] in words:
      words.remove(arg[1])
      KeywordManager.remove_keyword(arg[1])
      conn.commit()
    bot.reply_to(message, str(words))
  else:
    bot.reply_to(message, "No word provided")

@bot.message_handler(commands=['id'])
def get_id(message):
  bot.reply_to(message, message.chat.id)

client = TelegramClient(username, api_id, api_hash).start()
client.start()

@client.on(events.NewMessage())
async def print_new_messages(event):
  message = event.message.message
  if any([word in message for word in words]) and str(event.message.chat_id) == channel:
    print(message)
    await client.send_message(bot_id, "/echo_to_recipient " + message)
  

def list_all_channels():
  res = ""
  for chat in client.get_dialogs():
    print('{0} ||| {1}'.format(chat.name,chat.id))

if (list_all_channels_on_start_and_terminate):
  list_all_channels()
  os.system("pause")
else:
  threading.Thread(target=bot.infinity_polling).start()
  client.run_until_disconnected()