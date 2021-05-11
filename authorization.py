"""
Иммитация действий пользователя в браузере, используя библиотеку selenium.
Переходим на страницу авторизации, проходим ее, получаем cookies для дальнейшего использования
Логин и пароль подставляются в форму авторизации автоматически
Вручную необходимо решить recaptcha в течении 60 секунд и авторизоваться
"""
import os
import time
import random

from loguru import logger
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException

from settings.settings import URL_SHOP, USERNAME, PASSWORD


# функция для закрытия браузера
def close_browser(browser):
    logger.info(f'Закрытие браузера')
    browser.close()
    browser.quit()


# функция проверяет по xpath существует ли элемент на странице
def xpath_exists(browser, path):
    try:
        browser.find_element_by_xpath(path)
        return True
    except NoSuchElementException:
        return False


def get_cookies():
    """
    :return: Список словарей с именами и значениями cookies после авторизации на сайте
    """
    options = webdriver.ChromeOptions()
    # отключение режима Webdriver
    # for ChromeDriver version 79.0.3945.16 or over
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument(
        f'--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)'
        f' Chrome/87.0.4280.88 Safari/537.36')
    driver_file = os.getcwd() + f'\\chromedriver\\chromedriver.exe'  # path to ChromeDriver
    browser = webdriver.Chrome(driver_file, options=options)

    logger.info(f'Открываем браузер и переходим на сайт {URL_SHOP}')
    browser.get(URL_SHOP)
    # страница проверки отключения режима Webdriver для тестирования
    # browser.get('https://intoli.com/blog/not-possible-to-block-chrome-headless/chrome-headless-test.html')
    # browser.set_window_size(768, 704)

    time.sleep(random.randrange(1, 3))

    # Ищем на странице ссылку для авторизации
    if xpath_exists(browser, '//*[@id="LoginLink"]'):
        logger.info(f'Переходим на страницу для авторизации')
        browser.find_element_by_xpath('//*[@id="LoginLink"]').click()
    else:
        logger.error(f'Не найдена на странице ссылка для авторизации')
        close_browser(browser)
        return []  # выходим из функции

    time.sleep(10)

    try:
        logger.info(f'Автоматически вводим логин и пароль')
        username_input = browser.find_element_by_name('Email')
        username_input.clear()
        username_input.send_keys(USERNAME)

        time.sleep(random.randrange(1, 3))

        password_input = browser.find_element_by_name('Password')
        password_input.clear()
        password_input.send_keys(PASSWORD)
    except NoSuchElementException:
        logger.info(f'Ошибка! Не найдены на странице поля для вввода логина и пароля')
        close_browser(browser)
        return []  # выходим из функции

    logger.warning(f'Ожидаем ручного решения recaptcha и авторизации в ручном режиме')
    time.sleep(60)

    cookies = browser.get_cookies()
    if cookies:
        logger.success(f'Список Cookies для дальнейшей работы получен')
        close_browser(browser)
        return cookies


def get_response_selenium(url, session):
    # получение html-страницы для разбора
    logger.info(f'Открываем браузер в скрытом режиме и переходим на сайт {url}')
    options = webdriver.ChromeOptions()
    # запуск браузера в скрытом режиме
    options.add_argument('--headless')
    # отключение режима Webdriver for ChromeDriver version 79.0.3945.16 or over
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument(
        f'--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)'
        f' Chrome/87.0.4280.88 Safari/537.36')
    driver_file = os.getcwd() + f'\\chromedriver\\chromedriver.exe'  # path to ChromeDriver
    browser = webdriver.Chrome(driver_file, options=options)

    browser.get(url=url)  # открываем страницу с товаром

    # достаем cookies из текущей сессии и добавляем в браузер
    for cookie in session.cookies:
        browser.add_cookie(
            {
                'name': cookie.name,
                'value': cookie.value,
                'domain': cookie.domain,
                'path': cookie.path,
                'secure': cookie.secure,
            }
        )

    browser.refresh()  # обновляем страницу
    print('после обновления страницы')
    response_selenium = browser.page_source

    # для отладки
    # with open(os.getcwd() + '\\shops\\log-out.html', 'w', encoding='utf-8') as file:
    #     file.write(response_selenium)

    # time.sleep(15)
    close_browser(browser=browser)

    # результат отдается уже в виде текста
    return response_selenium


if __name__ == '__main__':
    pass
    # print(get_cookies())
