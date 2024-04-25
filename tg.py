import threading
import time

import telebot
from threading import Thread
from selenium import webdriver as wb
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from datetime import datetime
import os

log_mutex = threading.Lock()
dict_mutex = threading.Lock()
log_flag = False
log_file = open("log.txt", "w")
data_was_rewrited = False


def log(message):
    global log_mutex
    log_mutex.acquire()
    now = datetime.now()
    if not log_flag:
        print(now.strftime("%H:%M:%S"), message)
    else:
        log_file.write(now.strftime("%H:%M:%S") + " " + str(message) + "\n")
        log_file.flush()
    log_mutex.release()


TOKEN = "6124554756:AAFV8RWJt8iBnKECXRsb7j7NQkMmEdlap7M"
bot = telebot.TeleBot(TOKEN)


@bot.message_handler(content_types=['text'])
def text_handler(message):
    userID = message.chat.id
    if message.text.lower() == "/start":
        log("/start command was got")
        msg = bot.send_message(userID,
                               "Введите город отправления, город прибытия, дату отправления, дату возвращения и номер поезда в формате\n"
                               "City1 City2 08.06.2023 25.06.2023 083М")
        bot.register_next_step_handler(msg, parsing)


def parsing(message):
    global data_was_rewrited
    userID = message.chat.id
    splittedText = message.text.split()
    log("Data from user " + str(userID) + " is " + str(splittedText))
    log("Parsing data")
    dict_mutex.acquire()
    data_was_rewrited = True
    with open("dict.txt", "r") as file:
        currentDict = eval(file.readline())
        currentDict[userID] = splittedText
        currentDict[userID].append(False)
        currentDict[userID].append(False)
        log("New line was added to dict")
    with open("dict.txt", "w") as file:
        file.seek(0)
        file.truncate()
        file.write(str(currentDict))
        log("dict.txt was updated")
    dict_mutex.release()
    bot.send_message(userID, "Успешно занесено. Если необходимо поменять какие-то данные,"
                             " введите /start и пройдите регистрацию заново.")


def send_message_periodically():
    global data_was_rewrited
    parser = Parser()
    while True:
        log("New iteration")
        dict_mutex.acquire()
        with open("dict.txt", "r") as file2:
            dicti = eval(file2.readline())
        dict_mutex.release()
        log("Dict was loaded")
        delete = []
        for id, val in dicti.items():
            log(val)
            if len(val) != 0:
                try:
                    if not val[5]:
                        parser.setData(val[0], val[1], val[2], val[4])
                        info = parser.getInfo()
                        if info:
                            log(f"The train on {val[2]} has been found!")
                            bot.send_message(id, "Найден билет на дату " + val[2] + f", поезд {val[4]}."
                                                                                    f" Направление {val[0]} - {val[1]}."
                                                                                    f"\nПоиск приостановлен."
                                                                                    f" Если требуется продолжить,"
                                                                                    f" зарегистрируйтесь повторно,"
                                                                                    f" прописав /start.")
                            log("Message: Найден билет на дату " + val[2] + f", поезд {val[4]}."
                                                                            f" Направление {val[0]} - {val[1]}."
                                                                            f"\nПоиск приостановлен."
                                                                            f" Если требуется продолжить,"
                                                                            f" зарегистрируйтесь повторно,"
                                                                            f" прописав /start. Was send to user " + str(id))
                            val[5] = True
                    if not val[6]:
                        parser.setData(val[1], val[0], val[3], val[4])
                        info = parser.getInfo()
                        if info:
                            log(f"The train on {val[3]} has been found!")
                            bot.send_message(id, "Найден билет на дату " + val[3] + f", поезд {val[4]}."
                                                                                    f" Направление {val[1]} - {val[0]}."
                                                                                    f"\nПоиск приостановлен."
                                                                                    f" Если требуется продолжить,"
                                                                                    f" зарегистрируйтесь повторно,"
                                                                                    f" прописав /start.")

                            log("Message: Найден билет на дату " + val[3] + f", поезд {val[4]}."
                                                                            f" Направление {val[1]} - {val[0]}."
                                                                            f"\nПоиск приостановлен."
                                                                            f" Если требуется продолжить,"
                                                                            f" зарегистрируйтесь повторно,"
                                                                            f" прописав /start. Was send to user " + str(id))
                            val[6] = True
                    if val[5] and val[6]:
                        delete.append(id)
                except Exception as err:
                    log(err)
                    continue
            else:
                log("Error while parsing of the second page")
            for i in delete:
                del dicti[i]
        
        dict_mutex.acquire()
        if not data_was_rewrited:
            dicti[id] = val
            with open("dict.txt", "w") as file2:
                file2.seek(0)
                file2.truncate()
                file2.write(str(dicti))
        else:
            log("Won't update the dict.txt file - it was updated by user")
        data_was_rewrited = False
        dict_mutex.release()
        time.sleep(30)


class Parser:
    def __init__(self):
        self.city_from = ""
        self.city_to = ""
        self.date = ""
        self.train = ""
        chrome_options = Options()
        chrome_options.add_argument('headless')
        chrome_options.add_argument(
            'user-agent=Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/113.0')
        self.driver = wb.Chrome("/usr/bin/chromedriver", options=chrome_options)

    def setData(self, city_from, city_to, date, train):
        self.city_from = city_from
        self.city_to = city_to
        self.date = date
        self.train = train

    def getInfo(self):
        log("Getting main page")
        self.driver.get('https://rzd.ru')
        place_to = self.driver.find_element("id", "direction-to")
        log("Pressing city-to")
        place_to.send_keys(self.city_to)
        time.sleep(1)
        log("Pressing keys after city-to")
        place_to.send_keys(Keys.DOWN, Keys.DOWN, Keys.ENTER)
        time.sleep(1)

        place_from = self.driver.find_element("id", "direction-from")
        log("Pressing from")
        place_from.send_keys(self.city_from)
        time.sleep(1)
        log("Pressing keys after from")
        place_from.send_keys(Keys.DOWN, Keys.DOWN, Keys.ENTER)
        time.sleep(1)

        date_picker_from = self.driver.find_element("id", "datepicker-from")
        log("Setting date from")
        date_picker_from.send_keys(self.date)
        date_picker_from.send_keys(Keys.TAB)

        date_picker_to = self.driver.find_element("id", "datepicker-to")
        log("Setting date to")
        date_picker_to.send_keys(self.date)
        date_picker_to.send_keys(Keys.TAB, Keys.ENTER)
        time.sleep(15)
        elems = self.driver.find_elements(By.XPATH,
                                          "//*[@class='container card card--train tst-searchTransport-railway-cardListItem']")
        if len(elems) == 0:
            log("Error while parsing")
            return False
        trains = elems[0].find_elements(By.XPATH, "//*[@class='card-header__title ng-star-inserted']")
        all_trains = []
        log(f"Iterate through trains {len(trains)}")
        for train in trains:
            if " " not in train.text:
                all_trains.append(train.text)
        if self.train in all_trains:
            return True
        return False


def main(event, context):
    global log_flag, data_was_rewrited
    if not os.path.exists("dict.txt"):
        file = open("dict.txt", "w")
        file.seek(0)
        file.truncate()
        file.write("{}")
        log("File dict.txt was created")
        file.close()
    if not os.path.exists("log_flag.txt"):
        file = open("log_flag.txt", "w")
        file.write("False")
        file.close()
    with open("log_flag.txt", "r") as file:
        log_flag = eval(file.readline())
    log("Log flag was obtained")
    data_was_rewrited = False
    message_thread = Thread(target=send_message_periodically)
    message_thread.start()

    bot.polling()


main(12, 3)
