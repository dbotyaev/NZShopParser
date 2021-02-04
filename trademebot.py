import json
import os
import pickle
import random
import re
import time
import requests

from bs4 import BeautifulSoup
from loguru import logger

from settings.settings import HEADERS, KEYCOOKIES
from settings.settings import URL_CHECK_AUTH, LOGIN_CHECK, URL_SHOP


class TrademeParserBot:
    """TrademeShopBot Parser
    Класс для парсинга сайта www.trademe.co.nz с использованием библиотек requests и BeautifulSoup
    Результаты парсинга первой страницы листинга и ссылок на товары сохраняются в файл data_for_parsing.json
    При успешном парсинге страниц товаров информация удаляется. Т.е. по факту там будет информация, которую
    при неудачном завершении необходимо спарсить
    #TODO При необходимости можно сделать функцию парсинга из файла
    """

    def __init__(self, cookies=None, session=None, file_for_parsing=None):
        if cookies is None:
            pass
        else:
            self.cookies = self._edit_cookies(cookies)
        if session is None:
            self.session = self._create_session_cookies(self.cookies)
        else:
            self.session = session
        if file_for_parsing is None:
            self.data_for_parsing = {}  # словарь для парсинга товаров
        else:
            self.data_for_parsing = self._get_data_for_parsing(file_for_parsing)  # получаем словарь из файла
        self.count_requests = 0  # общий счетчик запросов к сайту
        self.result_parsing_products = []  # динамический результат парсинга товаров

    @staticmethod
    def _get_data_for_parsing(file):
        with open(os.getcwd() + f'\\shops\\{file}', 'w', encoding='utf-8') as file_json:
            return json.load(file_json)

    @staticmethod
    def _edit_cookies(cookies_selenium):
        # оставляем в списке словарей Cookies только значения по ключам из списка KEYCOOKIES
        key_cookies = KEYCOOKIES
        for cook in cookies_selenium:
            for key in list(cook.keys()):
                if key not in key_cookies:
                    cook.pop(key)
        return cookies_selenium

    @staticmethod
    def _create_session_cookies(cookies):
        # создаем ссесию и добавляем Cookies из selenium
        session = requests.Session()
        for cookie in cookies:
            session.cookies.set(**cookie)
        return session

    def check_auth(self):
        # проверка авторизации в сессии с помощью Cookies
        logger.info(f'Открываем страницу после авторизации {URL_CHECK_AUTH}')
        try:
            self.count_requests += 1
            response = self.session.get(URL_CHECK_AUTH, headers=HEADERS)
        except Exception as ex:
            logger.info(f'Ошибка открытия страницы. {ex}')
            return False

        if response.status_code != 200:
            logger.error(f'Ошибка ответа сервера. Код {response.status_code}')
            return False
        try:
            soup = BeautifulSoup(response.text, 'lxml')
            login = soup.find('form', action="/Members/Logout.aspx").text.strip()
            if login == LOGIN_CHECK:
                logger.success(f'Авторизация успешна')
                with open(os.getcwd() + '\\pickles\\session.pickle', 'wb') as file:
                    pickle.dump(self.session, file)
                    logger.info(f'Успешная сессия сохранена в служебный файл session.pickle')
                return True
            else:
                logger.error(f'Пользователь на странице {login} не совпал с ключевым словом авторизации {LOGIN_CHECK}')
                return False
        except AttributeError as ex:
            logger.error(f'Ошибка авторизации с использованием Cookies {ex}')
            return False

    def save_data_for_parsing_file(self):
        # метод записи в файл json результата парсинга ссылок листинга и ссылок на товары
        with open(os.getcwd() + '\\shops\\data_for_parsing.json', 'w', encoding='utf-8') as file_json:
            json.dump(self.data_for_parsing, file_json, ensure_ascii=False, indent=4)
            logger.success(f'Данные успешно записаны в файл data_for_parsing.json')

    def _check_open_url(self, url):
        """
        метод проверки открытия ссылки, возвращает объект response для парсинга, False или 'STOP' в случае ошибки
        :param url: ссылка для проверки
        :return: объект response, если авторизация на странице успешна
                 False, если страница не открылась, или ключевое слово авторизации не совпало с установленным,
                        или сервер вернул не 200-й код
                 'STOP', если авторизации нет на странице
        """
        try:
            self.count_requests += 1
            response = self.session.get(url, headers=HEADERS)  # переходим на страницу и получаем ответ
        except Exception as ex:
            logger.error(f'Ошибка открытия страницы')
            logger.error(f'Код ошибки {ex}')
            return False

        if response.status_code != 200:
            logger.error(f'Ошибка ответа сервера. Код {response.status_code}')
            return False
        try:
            soup = BeautifulSoup(response.text, 'lxml')
            login = soup.find('form', action="/Members/Logout.aspx").text.strip()  # ищем признак авторизации
            if login == LOGIN_CHECK:
                logger.success(f'Авторизация на текущей странице подтверждена')
                with open(os.getcwd() + '\\pickles\\session.pickle', 'wb') as file:
                    pickle.dump(self.session, file)
                    logger.success(f'Успешная сессия сохранена в служебный файл session.pickle')
                return response
            else:
                logger.error(f'Пользователь на странице {login} не совпал с ключевым словом авторизации {LOGIN_CHECK}')
                return False
        except AttributeError:
            # дополнительная проверка на наличие авторизации при парсинге товаров без LOGIN_CHECK
            try:
                soup = BeautifulSoup(response.text, 'lxml')
                if soup.find('a', class_='logged-in__log-out').text.strip() == 'Log out':
                    logger.debug(f'Страница без параметра LOGIN_CHECK')
                    return response
            except AttributeError as ex:
                logger.error(f'Ошибка авторизации на текущей странице {ex}')
                return 'STOP'

    def parsing_products(self, name_shop):
        """
        метод парсинга товаров
        :return: self.result_parsing_products
        """

        # функция получения описания товара, используя различную структуру возможных html-страниц товара
        def _get_description(s):
            # вариант 1
            try:
                html = s.find('div', id=re.compile('\w+ContentBoxdescription'))
                description = ''
                for string in html.stripped_strings:
                    description += string + '\n'
                return description
            except AttributeError:
                pass

            # вариант 2
            try:
                html = s.find('div', class_='tm-markdown')
                description = ''
                for string in html.stripped_strings:
                    description += string + '\n'
                return description
            except AttributeError:
                pass

            logger.error(f'Ни один из вариантов парсинга description не найден')
            return ''

        # функция получения цены товара, используя различную структуру возможных html-страниц товара
        def _get_price(s, text):
            # вариант 1
            try:
                price = s.find('div', id='BuyNow_BuyNow').text
                price = float(re.search('\d+.\d+', price).group(0))
                return price
            except AttributeError:
                pass

            # вариант 2
            try:
                price = s.find('p', class_='tm-buy-now-box__price p-h1').text
                price = float(re.search('\d+.\d+', price).group(0))
                return price
            except AttributeError:
                pass

            # вариант последний
            try:
                price = re.search('\"buyNowPrice\": \d+.\d+', text)
                price = re.search('\d+.\d+', price.group(0))
                price = float(price.group(0))
                return price
            except AttributeError:
                pass

            logger.info(f'Ни один из вариантов парсинга price не найден')
            return 0

        # функция получения признака цене
        def _get_price_tag(s):
            # вариант пока единственный
            try:
                price_tag = s.find('span', class_='tm-buy-now-box__label').text
                return price_tag
            except AttributeError:
                pass

            logger.info(f'Ни один из вариантов парсинга price_tag не найден')
            return ''

        logger.info(f'Начинаем парсинг товаров магазина "{name_shop}"')
        # обнуляем список списков с результатом парсинга страниц товаров магазина для загрузки в Google-таблицы
        self.result_parsing_products = []
        products = self.data_for_parsing[name_shop]['products']  # получаем список ссылок на продукты магазина
        for url_product in products:
            logger.info(f'Пауза перед началом парсинга')
            time.sleep(random.randrange(10, 20))
            logger.info(f' Открываем ссылку товара {URL_SHOP + url_product}')
            response = self._check_open_url(URL_SHOP + url_product)  # проверка авторизации на странице
            if not response:
                logger.warning(f'Из-за ошибки пропускаем парсинг товара')
                logger.debug(f'Счетчик запросов к сайту {self.count_requests}')
                # TODO возможно нужен алгоритм подсчета кол-ва ошибок и выхода из скрипта при необходимости
                continue
            if response == 'STOP':  # авторизация не успешна
                logger.warning(f'Из ошибки авторизации прекращаем парсинг товаров')
                logger.warning(f'Сохраняем неспарсенные ссылки на товары в файл data_for_parsing.json')
                self.save_data_for_parsing_file()
                raise

            soup = BeautifulSoup(response.text, 'lxml')
            product_id = re.search('[0-9]+', url_product).group(0)
            product_url = response.url
            product_title = soup.find('h1').text
            product_description = _get_description(soup)
            product_price = _get_price(soup, response.text)
            product_price_tag = _get_price_tag(soup)
            logger.debug(f'{product_id}, {product_title}, '
                         f'{"description" if product_description else False},'
                         f' {product_price}, {product_price_tag}')
            # добавляем результат парсинга в список для загрузки в Google-таблицу
            self.result_parsing_products.append([product_id, product_url, product_title, product_description,
                                                 product_price, product_price_tag])

            # в случае успеха парсинга удаляю из словаря ссылку на товар и перезаписываю файл
            # data_for_parsing.json, т.е. после завершения парсинга товаров в файле не будет ссылок на товары,
            # в противном случае останутся неспарсенные товары и можно запустить процедуру парсинга из файла
            self.data_for_parsing[name_shop]['products'].pop(0)

            # секция для тестирования
            # if self.count_requests == 3:
            #     logger.success(f'Парсинг товаров магазина {name_shop} успешно завершен')
            #     logger.debug(f'Счетчик запросов к сайту {self.count_requests}')
            #     self.save_data_for_parsing_file()
            #     self.count_requests = 0
            #     logger.debug(f'Счетчик запросов к сайту {self.count_requests}')
            #     return

        logger.success(f'Парсинг товаров магазина {name_shop} успешно завершен.')
        logger.info(f'Получено товаров {len(self.result_parsing_products)}')
        self.save_data_for_parsing_file()

    def parsing_shop(self, shop):
        """
        Метод парсинга страниц листинга магазина и его товаров.
        В результате выполнения сохраняется информация в файл data_for_parsing.json
        :param shop: Список из Наименования магазина и ссылки на первую страницу листинга
        :return: сохраняет результат парсинга в словарь self.data_for_parsing и в файл data_for_parsing.json
        """
        def _get_urls_products(s):
            """
            функция получения на странице всех ссылок на товары
            :type s: object Soup
            """
            tag_products = s.find_all('a', href=re.compile('\/Browse\/Listing\.aspx\?id=\d+'))
            for tag in tag_products:
                products.add(tag.get('href'))

        logger.info(f'Пауза перед началом парсинга')
        time.sleep(random.randrange(30, 90))

        urls_listing = set()  # множество уникальных ссылок страниц магазина с товарами
        products = set()  # множество уникальных ссылок на товары одного магазина
        name_shop = shop[0].strip('\r')  # Наименование магазина
        url_shop = shop[1]  # ссылка на листинг магазина

        logger.info(f'Начинаем парсинг листинга магазина "{name_shop}"')
        logger.info(f' Открываем ссылку магазина {url_shop}')

        response = self._check_open_url(url_shop)  # проверка авторизации на странице
        if not response:
            logger.warning(f'Из-за ошибки пропускаем парсинг листинга магазина "{name_shop}"')
            logger.debug(f'Счетчик запросов к сайту {self.count_requests}')
            return
        if response == 'STOP':  # авторизация не успешна, завершаем работу скрипта
            logger.warning(f'Сохраняем имеющиеся результаты в файл')
            self.save_data_for_parsing_file()
            raise

        soup = BeautifulSoup(response.text, 'lxml')
        urls_listing.add(response.url.replace(URL_SHOP, ''))  # текущий адрес страницы добавили в список

        logger.info(f'Получаем все ссылки на страницы листинга')
        tag_listing = set(soup.find_all('a', href=re.compile('\/stores\/.+\/feedback\?page=\d+')))
        for tag in tag_listing:
            urls_listing.add(tag.get('href'))

        self.data_for_parsing[name_shop] = {}
        self.data_for_parsing[name_shop]['url-listing'] = list(urls_listing)

        logger.info(f'Переходим по страницам листинга и получаем ссылки на товары')
        for listing in urls_listing:
            logger.info(f'Переходим на страницу {listing}')
            response = self._check_open_url(URL_SHOP + listing)  # проверка авторизации на странице

            if not response:
                logger.warning(f'Из-за ошибки пропускаем парсинг страницы')
                logger.debug(f'Счетчик запросов к сайту {self.count_requests}')
                # TODO возможно нужен алгоритм подсчета кол-ва ошибок и выхода из скрипта при необходимости
                continue
            if response == 'STOP':  # авторизация не успешна, завершаем работу скрипта
                logger.warning(f'Сохраняем имеющиеся результаты в файл')
                self.save_data_for_parsing_file()
                raise

            soup = BeautifulSoup(response.text, 'lxml')
            # получаем ссылки на товары на странице листинга и добавляем в кортеж
            _get_urls_products(soup)
            logger.info(f'Ссылки для парсинга товаров получены')
            self.data_for_parsing[name_shop]['products'] = list(products)

            time.sleep(random.randrange(4, 11))

            # секция для тестирования
            # if self.count_requests >= 2:
            #     logger.success(f'Получено {len(products)} ссылки на товары в магазине "{name_shop}"')
            #     logger.debug(f'Счетчик запросов к сайту {self.count_requests}')
            #     self.save_data_for_parsing_file()  # записываем результат парсинга в файл
            #     self.count_requests = 0
            #     logger.debug(f'Счетчик запросов к сайту {self.count_requests}')
            #     return

        logger.success(f'Получено {len(products)} ссылки на товары в магазине "{name_shop}"')
        logger.debug(f'Счетчик запросов к сайту {self.count_requests}')

        self.save_data_for_parsing_file()  # записываем результат парсинга в файл


if __name__ == '__main__':
    pass

    # with open(os.getcwd() + '\\pickles\\session.pickle', 'rb') as file:
    #     session = pickle.load(file)

    # url = 'https://www.trademe.co.nz/Browse/Listing.aspx?id=2930701065'
    # try:
    #     response = session.get(url, headers=HEADERS)
    #     print('url', response.url)
    #
    #     with open(os.getcwd() + '\\html\\2930701065.html', 'w') as file:
    #         file.write(response.text)
    # except Exception as ex:
    #     logger.error(f'{ex}')
    #
    # print(response.text)

    # with open(os.getcwd() + '\\html\\2934511811.html', 'r') as file:
    #     response = file.read()
    # soup = BeautifulSoup(response, 'lxml')