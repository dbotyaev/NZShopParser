import json
import os
import pickle
import random
import re
import time
import requests

from bs4 import BeautifulSoup
from collections import Counter
from loguru import logger

from authorization import get_response_selenium

from settings.settings import HEADERS, KEYCOOKIES, FILE_FOR_PARSING
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
        self.count_no_auth = 300  # счетчик подсчета открытия страниц без авторизации для завершения парсинга

    @staticmethod
    def _get_data_for_parsing(file):
        with open(os.getcwd() + f'\\{file}', 'r', encoding='utf-8') as file_json:
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
            response = self.session.get(URL_CHECK_AUTH, headers=HEADERS, timeout=30)
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

    # метод записи в файл json результата парсинга ссылок листинга и ссылок на товары
    def save_data_for_parsing_file(self, name_shop):
        def get_valid_filename(s):
            """
            Return the given string converted to a string that can be used for a clean
            filename. Remove leading and trailing spaces; convert other spaces to
            underscores; and remove anything that is not an alphanumeric, dash,
            underscore, or dot.
            get_valid_filename("john's portrait in 2004.jpg")
            'johns_portrait_in_2004.jpg'
            """
            s = str(s).strip().replace(' ', '_')
            return re.sub(r'(?u)[^-\w.]', '', s)

        path = os.getcwd() + '\\shops\\'
        name_file = get_valid_filename(name_shop) + '.json'
        try:
            with open(path + name_file, 'w', encoding='utf-8') as file_json:
                json.dump(self.data_for_parsing, file_json, ensure_ascii=False, indent=4)
                logger.success(f'Данные успешно записаны в файл {name_file}')
        except Exception as ex:
            logger.error(f'Не удалось сохранить файл {name_file} диск {ex}')

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
            response = self.session.get(url, headers=HEADERS, timeout=30)  # переходим на страницу и получаем ответ
        except Exception as ex:
            logger.error(f'Ошибка открытия страницы')
            logger.error(f'Код ошибки {ex}')
            return False

        if response.status_code != 200:
            logger.error(f'Ошибка ответа сервера. Код {response.status_code}')
            return False

        soup = BeautifulSoup(response.text, 'lxml')

        try:
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
                if soup.select_one('a.logged-in__log-out').text.strip() == 'Log out':
                    logger.debug(f'Страница без параметра LOGIN_CHECK')
                    return response
            except AttributeError as ex:
                try:
                    logger.debug(f'Ошибка авторизации на текущей странице {ex}')
                    logger.info(f'Делаем дополнительный запрос на сайт')
                    self.count_no_auth -= 1  # увеличиваем счетчик найденных страниц без авторизации
                    logger.debug(f'Осталось попыток открытия страниц без авторизации {self.count_no_auth}')
                    # возвращаем ответ без параметра headers (с ним проблемы с кодировкой)
                    self.count_requests += 1

                    # возможный вариант получения в режиме имитации действий в браузере
                    # требует корректировки кода, т.к. response не имеет атрибута text
                    # response = get_response_selenium(url=url, session=self.session)

                    response = self.session.get(url, timeout=30)
                    if response.status_code == 200:
                        return response
                    else:
                        return 'STOP'
                except Exception as ex:
                    logger.exception(f'Ошибка при дополнительном запросе на сайт {ex}')
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
                price = price.replace(',', '')
                price = float(re.search('\d+.\d+', price).group(0))
                return price
            except AttributeError:
                pass

            # вариант 2
            try:
                price = s.find('p', class_='tm-buy-now-box__price p-h1').text
                price = price.replace(',', '')
                price = float(re.search('\d+.\d+', price).group(0))
                return price
            except AttributeError:
                pass

            # вариант, который получает цену из dict в html, даже если цена скрыта
            try:
                price = re.search('\"buyNowPrice\": \d+.\d+', text)
                price = re.search('\d+.\d+', price.group(0))
                price = float(price.group(0))
                return price
            except AttributeError:
                pass

            logger.info(f'Ни один из вариантов парсинга price не найден')
            return 0

        # функция получения признака цены
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
        # получаем список ссылок на продукты магазина
        products = self.data_for_parsing[name_shop]['products'].copy()  # получаем список ссылок на продукты магазина

        for url_product, count_product in products.items():
            logger.info(f'Пауза перед началом парсинга')
            time.sleep(random.randrange(3, 6))
            logger.info(f' Открываем ссылку товара {URL_SHOP + url_product}')
            response = self._check_open_url(URL_SHOP + url_product)  # проверка авторизации на странице
            if not response:
                logger.warning(f'Из-за ошибки пропускаем парсинг товара')
                logger.debug(f'Счетчик запросов к сайту {self.count_requests}')
                # TODO возможно нужен алгоритм подсчета кол-ва ошибок и выхода из скрипта при необходимости
                continue
            if response == 'STOP':  # авторизация не успешна
                if self.count_no_auth <= 0:  # проверяем счетчик открытия страниц без авторизации
                    logger.warning(f'Из ошибки авторизации прекращаем парсинг')
                    logger.warning(f'Сохраняем неспарсенные ссылки на товары в файл {name_shop}.json')
                    self.save_data_for_parsing_file(name_shop)
                    self.data_for_parsing = {}  # очищаем словарь для парсинга нового магазина
                    raise  # завершаем парсинг магазина и переходим к следующему
                else:
                    logger.warning(f'Из-за ошибки авторизации пропускаем парсинг товара')
                    logger.debug(f'Счетчик запросов к сайту {self.count_requests}')
                    continue

            soup = BeautifulSoup(response.text, 'lxml')

            product_id = re.search('[0-9]+', url_product).group(0)
            product_count = int(count_product)
            product_url = response.url
            product_title = soup.find('h1').text.strip()
            product_description = _get_description(soup)
            product_price = _get_price(soup, response.text)
            product_price_tag = _get_price_tag(soup)
            logger.debug(f'{product_id}, {product_count}, {product_title}, '
                         f'{"description" if product_description else False},'
                         f' {product_price}, {product_price_tag}')
            # добавляем результат парсинга в список для загрузки в Google-таблицу
            self.result_parsing_products.append([product_id, product_count, product_url,
                                                 product_title, product_description,
                                                 product_price, product_price_tag])

            # в случае успеха парсинга удаляю из словаря ссылку на товар и перезаписываю файл
            # data_for_parsing.json, т.е. после завершения парсинга товаров в файле не будет ссылок на товары,
            # в противном случае останутся неспарсенные товары и можно запустить процедуру парсинга из файла
            self.data_for_parsing[name_shop]['products'].pop(url_product, False)

            # секция для тестирования
            # if self.count_requests > 3:
            #     logger.success(f'Парсинг товаров магазина {name_shop} успешно завершен')
            #     logger.debug(f'Счетчик запросов к сайту {self.count_requests}')
            #     self.save_data_for_parsing_file(name_shop)
            #     self.data_for_parsing = {}
            #     self.count_requests = 0
            #     logger.debug(f'Счетчик запросов к сайту {self.count_requests}')
            #     return

        logger.success(f'Парсинг товаров магазина {name_shop} успешно завершен.')
        logger.info(f'Получено товаров {len(self.result_parsing_products)}')
        self.save_data_for_parsing_file(name_shop)
        self.data_for_parsing = {}  # очищаем словарь для парсинга нового магазина

    def parsing_shop(self, shop):
        """
        Метод парсинга страниц листинга магазина и его товаров.
        В результате выполнения сохраняется информация в файл data_for_parsing.json
        :param shop: Список из Наименования магазина и ссылки на первую страницу листинга
                    или строка Наименования магазина при допарсинге из файла
        :return: сохраняет результат парсинга в словарь self.data_for_parsing и в файл data_for_parsing.json
        """
        def _get_urls_products(s):
            """
            функция получения на странице всех ссылок на товары
            :type s: object Soup
            """
            tag_products = s.find_all('a', href=re.compile('\/Browse\/Listing\.aspx\?id=\d+'))
            for tag in tag_products:
                products.append(tag.get('href'))

        logger.info(f'Пауза перед началом парсинга')
        time.sleep(random.randrange(15, 30))

        # для тестирования
        # self.count_requests = 0

        products = []  # список ссылок на товары одного магазина

        # обычный режим скрипта
        if not FILE_FOR_PARSING:
            urls_listing = set()  # множество уникальных ссылок страниц магазина с товарами
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
                logger.warning(f'Сохраняем имеющиеся результаты в файл {name_shop}.json')
                self.save_data_for_parsing_file(name_shop)
                raise  # завершаем работу скрипта

            try:
                soup = BeautifulSoup(response.text, 'lxml')
            except AttributeError as ex:
                soup = BeautifulSoup(response, 'lxml')  # если response уже в виде текста
                # logger.exception(f'{ex}')

            # with open(os.getcwd() + '\\shops\\shop.html', 'w', encoding='utf-8') as file:
            #     file.write(response.text)

            urls_listing.add(response.url.replace(URL_SHOP, '') + '&type=&page=1')  # текущий адрес страницы добавили в список

            logger.info(f'Получаем все ссылки на страницы листинга')
            # tag_listing = set(soup.find_all('a', href=re.compile('\/stores\/.+\/feedback\?page=\d+')))
            tag_listing = set(
                soup.find_all('a', href=re.compile('Feedback\.aspx\?member=\d+&type=&page=\d+')))

            for tag in tag_listing:
                urls_listing.add('/Members/' + tag.get('href'))

            self.data_for_parsing[name_shop] = {}
            self.data_for_parsing[name_shop]['url-listing'] = list(urls_listing)
            # сортируем список по номеру страницы
            self.data_for_parsing[name_shop]['url-listing'].\
                sort(key=lambda url: int(re.search('\d+', re.search('&page=\d+', url).group(0)).group(0)))
            self.data_for_parsing[name_shop]['products'] = dict(Counter(products))

        # режим работы допарсинга из файла
        else:
            name_shop = shop
            # получаем неспарсенные ссылки на товары и преобразуем в список
            products = list(self.data_for_parsing[name_shop]['products'].keys())

        logger.info(f'Переходим по страницам листинга и получаем ссылки на товары')
        # создаем копию списка для перебора, чтобы можно было перебирать и применять метод pop() в конце цикла
        urls = self.data_for_parsing[name_shop]['url-listing'].copy()
        # счетчик удаления спарсенных ссылок из списка, необходим для правильного определения индекса элемента
        # для удаления элемента, т.к. в цикле есть конструкция continue
        count_pop = 0
        for index, listing in enumerate(urls):
            logger.info(f'Переходим на страницу {listing}')
            response = self._check_open_url(URL_SHOP + listing)  # проверка авторизации на странице

            if not response:
                logger.warning(f'Из-за ошибки пропускаем парсинг страницы')
                logger.debug(f'Счетчик запросов к сайту {self.count_requests}')
                # TODO возможно нужен алгоритм подсчета кол-ва ошибок и выхода из скрипта при необходимости
                continue
            if response == 'STOP':  # авторизация не успешна
                if self.count_no_auth <= 0:
                    logger.warning(f'Из ошибки авторизации прекращаем парсинг')
                    logger.warning(f'Сохраняем имеющиеся результаты в файл {name_shop}.json')
                    self.save_data_for_parsing_file(name_shop)
                    raise  # завершаем работу скрипта
                else:
                    logger.warning(f'Из-за ошибки авторизации пропускаем парсинг страницы')
                    logger.debug(f'Счетчик запросов к сайту {self.count_requests}')
                    continue  # пропускаем парсинг страницы и продолжаем цикл

            try:
                soup = BeautifulSoup(response.text, 'lxml')
            except AttributeError as ex:
                soup = BeautifulSoup(response, 'lxml')  # если response уже в виде текста
                # logger.exception(f'{ex}')

            # получаем ссылки на товары на странице листинга и добавляем в кортеж
            _get_urls_products(soup)
            logger.info(f'Ссылки для парсинга товаров получены')

            self.data_for_parsing[name_shop]['products'] = dict(Counter(products))

            # в случае удачного парсинга ссылок на товары, удаляем ссылку из словаря
            # по окончанию парсинга в словаре не должно остаться страниц с листингами
            # в противном случае данные ссылок на товары не были получены на оставшихся страницах
            self.data_for_parsing[name_shop]['url-listing'].pop(index - count_pop)
            count_pop += 1  # увеличиваем счетчик удаления элементов

            time.sleep(random.randrange(3, 6))

            # секция для тестирования
            # if self.count_requests > 3:
            #     count_products = len(self.data_for_parsing[name_shop]['products'])
            #     logger.success(f'Получено {count_products} ссылки на товары в магазине "{name_shop}"')
            #     logger.debug(f'Счетчик запросов к сайту {self.count_requests}')
            #     self.save_data_for_parsing_file(name_shop)  # записываем результат парсинга в файл
            #     self.count_requests = 0
            #     logger.debug(f'Счетчик запросов к сайту {self.count_requests}')
            #     return

        count_products = len(self.data_for_parsing[name_shop]['products'])  # кол-во уникальных товаров
        logger.success(f'Получено {count_products} ссылки на товары в магазине "{name_shop}"')
        logger.debug(f'Счетчик запросов к сайту {self.count_requests}')

        self.save_data_for_parsing_file(name_shop)  # записываем результат парсинга в файл


if __name__ == '__main__':
    pass

    # with open(os.getcwd() + '\\pickles\\session.pickle', 'rb') as file:
    #     session = pickle.load(file)
    #
    # url = 'https://www.trademe.co.nz/Browse/Listing.aspx?id=2961967160'
    # url = 'https://www.trademe.co.nz/a/motors/car-parts-accessories/radar-detectors/listing/2961967160?bof=NGey1jYX'
    # url = 'https://www.trademe.co.nz/Browse/Listing.aspx?id=2948594669'
    # url = 'https://www.trademe.co.nz/home-living/security-locks-alarms/security-cameras/other/listing-2971335364.htm'
    # try:
    #     response = requests.post(url, headers=HEADERS)
    # response = requests.post(url, headers=HEADERS, stream=True, allow_redirects=True)
    #     print('url', response.url)
    #     print(response.encoding)
    #     with open(os.getcwd() + '\\shops\\listing.html', 'w', encoding='utf-8') as file:
    #         file.write(response.text)
    # except Exception as ex:
    #     logger.error(f'{ex}')
    #
    # print(response.text)
    #
    # with open(os.getcwd() + '\\shops\\listing.html', 'r', encoding='utf-8') as file:
    #     response = file.read()
    # soup = BeautifulSoup(response, 'lxml')

    # soup = BeautifulSoup(response.text, 'lxml')
    # print(soup.find('h1').text.strip())
