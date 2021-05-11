import os
import sys

from loguru import logger

import authorization
from googlesheetbot import GSheetsBot
from settings.settings import FILE_FOR_PARSING
from trademebot import TrademeParserBot

if __name__ == '__main__':
    path_log = os.getcwd() + f'\\logs\\debug.log'
    logger.add(path_log, level='DEBUG', compression="zip", rotation="9:00", retention="3 days", encoding='utf-8')

    logger.info(f'Запуск скрипта')
    cookies_selenium = authorization.get_cookies()  # в ручном режиме получаем Cookies

    if not cookies_selenium:
        logger.error(f'Cookies для дальнейшей работы не получены, завершаем программу')
        sys.exit(1)

    if not FILE_FOR_PARSING:  # обычный режим работы скрипта
        parser = TrademeParserBot(cookies=cookies_selenium)  # file_for_parsing='data_for_parsing.json')
        logger.info(f'Создана сессия для парсинга и добавлены Cookies для авторизации')
    else:
        parser = TrademeParserBot(cookies=cookies_selenium, file_for_parsing=FILE_FOR_PARSING)
        name_shop = list(parser.data_for_parsing.keys())[0]
        logger.warning(f'Запущен режим допарсинга из файла по магазину {name_shop}')
        logger.info(f'Создана сессия для парсинга и добавлены Cookies для авторизации')

    logger.info(f'Проверяем авторизацию в текущей сессии после добавления Cookies')
    if not parser.check_auth():
        logger.error(f'Работа скрипта завершена из-за ошибки авторизации')
        logger.error(f'Попробуйте позже или обратитесь к разработчику')
        logger.debug(f'Счетчик запросов к сайту {parser.count_requests}')
        sys.exit(1)

    if not FILE_FOR_PARSING:
        shops = []  # список названий магазинов и ссылок на их листинг из Google-таблицы
        try:
            logger.info(f'Открываем Google-таблицу и получаем список магазинов')
            gsheet = GSheetsBot()
            shops = gsheet.shops  # получаем список магазинов
            logger.info(f'Выбрано для парсинга {len(shops)} магазин(a/ов)')
        except Exception as ex:
            logger.error(f'Работа скрипта завершена из-за ошибки {ex}')
            logger.error(f'Попробуйте позже или обратитесь к разработчику')
            sys.exit(1)

    logger.info(f'НАЧИНАЕМ ПАРСИНГ!')

    parser.count_requests = 0  # для тестирования

    try:
        if not FILE_FOR_PARSING:
            for shop in shops:
                parser.parsing_shop(shop)  # получение ссылок на товары магазина
                name_shop = shop[0].strip('\r')
                try:
                    parser.parsing_products(name_shop)  # парсинг данных страниц товаров
                    result_parsing = parser.result_parsing_products
                    logger.info(f'Начинаем запись товаров в Google таблицу по магазину {name_shop}')
                    gsheet.save_result_parsing(name_shop, result_parsing)
                    logger.success(f'В Google-таблицу или csv-файл успешно записаны все товары')
                except Exception as ex:
                    logger.error(f'Ошибка {ex}. Обратитесь к разработчику')
                    # из-за ошибки сохраняем в Google-таблицу только часть данных парсинга товаров
                    result_parsing = parser.result_parsing_products
                    gsheet.save_result_parsing(name_shop, result_parsing)
                    logger.warning(f'В Google-таблицу или csv-файл по магазину {name_shop} записаны НЕ все товары')

        else:
            try:
                # допарсинг товаров из файла
                parser.parsing_shop(name_shop)  # допарсинг страниц листинга и получение ссылок на товары
                parser.parsing_products(name_shop)  # допарсинг данных страниц товаров
                result_parsing = parser.result_parsing_products
                gsheet = GSheetsBot()
                logger.info(f'Начинаем запись товаров в Google таблицу по магазину {name_shop}')
                gsheet.save_result_parsing(name_shop, result_parsing)
                logger.success(f'В Google-таблицу или csv-файл успешно записаны все товары')
            except Exception as ex:
                logger.error(f'Ошибка {ex}. Обратитесь к разработчику')
                # из-за ошибки сохраняем в Google-таблицу только часть данных парсинга товаров
                result_parsing = parser.result_parsing_products
                gsheet = GSheetsBot()
                gsheet.save_result_parsing(name_shop, result_parsing)
                logger.warning(f'В Google-таблицу или csv-файл по магазину {name_shop} записаны НЕ все товары')

    except Exception as ex:
        logger.error(f'Работа скрипта завершена из-за ошибки {ex}')
        logger.error(f'Необходимо заново запустить скрипт и пройти процедуру авторизации')
        logger.debug(f'Счетчик запросов к сайту {parser.count_requests}')
        sys.exit(1)
