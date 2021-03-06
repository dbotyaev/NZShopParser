import csv
import os
import pygsheets

from loguru import logger

from settings.settings import SERVICE_ACCOUNT_FILE, SHEET_SHOPS, URL_GSHEET
from settings.settings import START_ADDR, END_ADDR, ROW_START, ROW_END


class GSheetsBot:
    """
    Класс для работы с google-таблицей, содержащей ссылки на магазины.
    По результатам парсинга на каждый магазин создается отдельный лист.
    Если лист с названием магазина существует, он будет удален перед загрузкой
    данных результатов парсинга
    """

    def __init__(self):
        try:
            self._path_api = os.getcwd() + SERVICE_ACCOUNT_FILE
            self.client = pygsheets.authorize(service_account_file=self._path_api)
            self.google_sheet = self.client.open_by_url(URL_GSHEET)
            self.worksheet_urls_shops = self.google_sheet.worksheet_by_title(SHEET_SHOPS)
            self.shops = self.worksheet_urls_shops.get_values(
                start=START_ADDR, end=END_ADDR, returnas='matrix')[ROW_START-1:ROW_END]
        except Exception as ex:
            logger.error(f'Ошибка при открытии Google-таблицы {ex}')
            raise

    # метода сохранения результата парсинга в Google-таблицу
    def save_result_parsing(self, name_shop: str, result: list):
        if not result:
            logger.debug(f'Результат парсинга пустой список, сохранять в Google-таблицу нечего.')
            return
        title = ['№ Листинга', 'Кол-во', 'Ссылка на листинг',	'Товар', 'Описание', 'Цена', 'Признак цены']
        result.insert(0, title)  # Добавляем заголовок таблицы
        try:
            try:  # если лист найден
                sheet_shop = self.google_sheet.worksheet_by_title(name_shop)
                logger.info(f'Лист магазина в Google таблице уже существует. Поэтому данные будут объединены')
                # получаем индекс последней непустой строки
                lastrow = len(sheet_shop.get_all_values(include_tailing_empty_rows=False))
                # дополняем Google-таблицу новыми значениями
                sheet_shop.update_values(crange='A' + str(lastrow + 1), values=result, extend=True)
                sheet_shop.adjust_column_width(start=1, end=7, pixel_size=170)  # установка ширины столбцов
                sheet_shop.adjust_column_width(start=5, end=5, pixel_size=500)
                sheet_shop.adjust_column_width(start=2, end=2, pixel_size=80)
                # установка высоты строк
                sheet_shop.adjust_row_height(start=lastrow + 2, end=lastrow + 2 + len(result), pixel_size=90)
            except pygsheets.exceptions.WorksheetNotFound:  # если лист не найден, создается новый
                sheet_shop = self.google_sheet.add_worksheet(name_shop)
                # записываем значения в Google-таблицу
                sheet_shop.update_values('A1', result, extend=True)
                sheet_shop.adjust_column_width(start=1, end=7, pixel_size=170)  # установка ширины столбцов
                sheet_shop.adjust_column_width(start=5, end=5, pixel_size=500)
                sheet_shop.adjust_column_width(start=2, end=2, pixel_size=80)
                sheet_shop.adjust_row_height(start=2, end=len(result), pixel_size=90)  # установка высоты строк
        except Exception as ex:
            logger.error(f'Возникла ошибка при записи в Google-таблицу {ex}')
            logger.warning(f'Результат парсинга будет сохранен в файл {name_shop}.csv')
            with open(os.getcwd() + f'\\csv\\{name_shop}.csv', "w", encoding='utf-8') as file_csv:
                file_writer = csv.writer(file_csv, delimiter=";", lineterminator="\r")
                file_writer.writerows(result)
            logger.success(f'Данные успешно сохранены в файл в папку csv')


if __name__ == '__main__':
    pass
