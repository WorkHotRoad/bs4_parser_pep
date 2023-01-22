import logging

from requests import RequestException

from exceptions import ParserFindTagException

from constants import EXPECTED_STATUS


def get_response(session, url):
    try:
        response = session.get(url)
        response.encoding = 'utf-8'
        return response
    except RequestException:
        logging.exception(
            f'Возникла ошибка при загрузке страницы {url}',
            stack_info=True
        )


def find_tag(soup, tag, attrs=None):
    searched_tag = soup.find(tag, attrs=(attrs or {}))
    if searched_tag is None:
        error_msg = f'Не найден тег {tag} {attrs}'
        logging.error(error_msg, stack_info=True)
        raise ParserFindTagException(error_msg)
    return searched_tag


def log_exeption(status_type, status_in_cart, cart_url):
    try:
        logging.info(
            f'\nНесовпадающий статус\n'
            f'{cart_url}\n'
            f'Ожидаемые статусы: {EXPECTED_STATUS[status_type[1:]]}\n'
            f'Статус в карточке: {status_in_cart}\n'
        )
    except KeyError:
        logging.info(
                f'\nОтсутсвие статуса:\n'
                f'{cart_url}\n'
                f'Статуса {status_type} не существует\n'
        )
