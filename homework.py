import logging
import os
import time
from logging.handlers import RotatingFileHandler
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = RotatingFileHandler('hw_logger.log', maxBytes=50000000,
                              backupCount=5, encoding='utf-8')
logger.addHandler(handler)

TELEGRAM_RETRY_TIME = 600
ENDPOINT = os.getenv('ENDPOINT')
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICT = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Отправка сообщения в телеграмм."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.info('Начинаем отправку сообщения.')
    except Exception as er:
        raise f'Сообщение не отправлено ошибка: {er}, {type(er)}'


def get_api_answer(current_timestamp):
    """Отправка запроса к сайту Яндекс Практикум."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    except Exception as err:
        raise f'Ошибка при запросе к API: {err}.'
    if response.status_code != HTTPStatus.OK:
        raise f'Ошибка при запросе к API {response.status_code}.'
    return response.json()


def check_response(response):
    """Проверка овтета API."""
    if not isinstance(response, dict):
        raise TypeError('response is not dict')
    homeworks = response.get('homeworks')
    if 'homeworks' not in response or 'current_date' not in response:
        raise Exception('KeyError homeworks')
    if not isinstance(homeworks, list):
        raise TypeError('homeworks is not list')
    return homeworks


def parse_status(homework):
    """Сатус домашней работы."""
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if homework == []:
        return None
    if homework_status == []:
        return None
    if homework_status not in HOMEWORK_VERDICT:
        raise KeyError('Неизвестный статус домашней работы')
    if 'homework_name' not in homework:
        raise KeyError(
            'Отсутствуют ключ "homework_name" : homework = {homework}.')

    verdict = HOMEWORK_VERDICT[homework_status]

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяет доступность переменных окружения."""
    tokens = {
        'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
        'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
        'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID
    }
    for key, value in tokens.items():
        if value is None:
            logger.critical(f'Отсутствует переменная окружения {key}.')
            return False
    return True


def main():
    """Основная логика работы бота."""
    logging.basicConfig(
        level=logging.DEBUG,
        filename='hw.log',
        filemode='w',
        format='%(asctime)s, %(levelname)s, %(message)s, %(name)s',
    )
    if not check_tokens():
        return
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homework = check_response(response)
            message = parse_status(homework)
            current_timestamp = current_timestamp
            if message is not None:
                send_message(bot, message)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)
            bot.send_message(TELEGRAM_CHAT_ID, message)
        except 'homework_name' not in homework:
            raise KeyError('Нет ключа "homework_name": homework = {homework}.')
        time.sleep(TELEGRAM_RETRY_TIME)


if __name__ == '__main__':
    main()
