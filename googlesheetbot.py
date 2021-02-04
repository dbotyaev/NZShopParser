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
            logger.error(f'Ошибка при открытии Google-таблицы и получении списка магазинов. {ex}')
            raise

    # метода сохрания результат парсинга в Google-таблицу
    def save_result_parsing(self, name_shop: str, result: list):
        title = ['№ Листинга', 'Ссылка на листинг',	'Товар', 'Описание', 'Цена', 'Признак цены']
        result.insert(0, title)  # Добавляем заголовок таблицы
        try:
            try:  # если лист найден
                sheet_shop = self.google_sheet.worksheet_by_title(name_shop)
                logger.info(f'Лист магазина в Google таблице уже существует. Поэтому данные будут объединены')
                # получаем индекс последней непустой строки
                lastrow = len(sheet_shop.get_all_values(include_tailing_empty_rows=False))
                # добавляем значения в Google-таблицу
                sheet_shop.update_values('A' + str(lastrow + 1), result)  # дополняем таблицу новыми значениями
                sheet_shop.adjust_column_width(start=1, end=6, pixel_size=170)  # установка ширины столбцов
                sheet_shop.adjust_column_width(start=4, end=4, pixel_size=500)
                # установка высоты строк
                sheet_shop.adjust_row_height(start=lastrow + 2, end=lastrow + 2 + len(result), pixel_size=90)
            except pygsheets.exceptions.WorksheetNotFound:  # если лист не найден, создается новый
                sheet_shop = self.google_sheet.add_worksheet(name_shop)
                # записываем значения в Google-таблицу
                sheet_shop.update_values('A1', result)
                sheet_shop.adjust_column_width(start=1, end=6, pixel_size=170)  # установка ширины столбцов
                sheet_shop.adjust_column_width(start=4, end=4, pixel_size=500)
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
    # gsheet = GSheetsBot()
