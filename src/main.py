import logging
import re
from urllib.parse import urljoin

import requests_cache
from bs4 import BeautifulSoup
from tqdm import tqdm

from configs import configure_argument_parser, configure_logging
from constants import BASE_DIR, EXPECTED_STATUS, MAIN_DOC_URL, MAIN_PEP_URL
from outputs import control_output
from utils import find_tag, get_response


def pep(session):

    def detail_pep(detail_url):
        response = get_response(session, detail_url)
        if response is None:
            return
        soup = BeautifulSoup(response.text, 'lxml')
        main_div = find_tag(soup, 'dl', attrs={'class': 'rfc2822 field-list simple'})
        status = find_tag(main_div, "abbr").text
        return status

    response = get_response(session, MAIN_PEP_URL)
    if response is None:
        return
    soup = BeautifulSoup(response.text, 'lxml')
    main_section = find_tag(soup, 'section', attrs={'id': 'numerical-index'})
    main_section_tbody = find_tag(main_section, 'tbody')
    sections_by_pep = main_section_tbody.find_all("tr")
    pep_real_status = []
    inconsistencies = []
    for i in tqdm(sections_by_pep):
        status_type = find_tag(i, "abbr").text
        detail_url = find_tag(i, "a", attrs={"class": "pep reference internal"})["href"]
        status_in_cart = detail_pep(urljoin(MAIN_PEP_URL, detail_url))
        if status_in_cart not in [x for value in EXPECTED_STATUS.values() for x in value]:
            inconsistencies.append(
                (EXPECTED_STATUS[status_type[1:]],
                status_in_cart,
                urljoin(MAIN_PEP_URL, detail_url)
                )
        )
        pep_real_status.append(status_in_cart)

    if inconsistencies:
        for i in inconsistencies:
            logging.info(
                f'\nНесовпадающий статус\n'
                f'{i[2]}\n'
                f'Ожидаемые статусы: {i[0]}\n'
                f'Статус в карточке: {i[1]}\n'
            )

    results = [('Status', 'Quantity')]
    all_pep = 0
    for i in set(pep_real_status):
        status = pep_real_status.count(i)
        results.append((i, status))
        all_pep += status
    results.append(("Total", all_pep))
    return results

def whats_new(session):
    whats_new_url = urljoin(MAIN_DOC_URL, 'whatsnew/')
    response = get_response(session, whats_new_url)
    if response is None:
        return
    soup = BeautifulSoup(response.text, 'lxml')
    main_div = find_tag(soup, 'section', attrs={'id': 'what-s-new-in-python'})
    div_with_ul = find_tag(main_div, 'div', attrs={'class': 'toctree-wrapper'})
    sections_by_python = div_with_ul.find_all('li', attrs={'class': 'toctree-l1'})
    results = [('Ссылка на статью', 'Заголовок', 'Редактор, Автор')]
    for section in tqdm(sections_by_python):
        version_a_tag = find_tag(section, 'a')
        href = version_a_tag['href']
        version_link = urljoin(whats_new_url, href)
        response = get_response(session, version_link)
        if response is None:
            continue
        soup = BeautifulSoup(response.text, 'lxml')
        h1 = find_tag(soup, 'h1').text.replace("\n", " ")
        dl = find_tag(soup,'dl').text.replace("\n", " ")
        # p = soup.find('p').text
        results.append((version_link, h1, dl))
    return results


def latest_versions(session):
    response = get_response(session, MAIN_DOC_URL)
    if response is None:
        return

    soup = BeautifulSoup(response.text, 'lxml')
    sidebar = find_tag(soup, 'div', attrs={'class': 'sphinxsidebarwrapper'})
    ul_tags = sidebar.find_all("ul")
    for ul in ul_tags:
        if 'All versions' in ul.text:
            a_tags = ul.find_all('a')
            break
        else:
            raise Exception('Ничего не нашлось')

    pattern = r'Python (?P<version>\d\.\d+) \((?P<status>.*)\)'
    results = [('Ссылка на документацию', 'Версия', 'Статус')]
    for a_tag in a_tags:
        link= a_tag["href"]
        text_match = re.search(pattern, str(a_tag))
        if text_match:
            version, status = text_match.groups()
        else:
            version = str(a_tag.text)
            status = ''
        results.append((link, version, status))
    return results

def download(session):
    downloads_url = urljoin(MAIN_DOC_URL, 'download.html')
    response = get_response(session, downloads_url)
    if response is None:
        return

    soup = BeautifulSoup(response.text, 'lxml')
    table_tag = find_tag(soup, 'table', {'class': 'docutils'})

    pdf_a4_tag = find_tag(table_tag, 'a', {'href': re.compile(r'.+pdf-a4\.zip$')})
    pdf_a4_link = pdf_a4_tag['href']
    archive_url = urljoin(downloads_url, pdf_a4_link)
    filename = archive_url.split('/')[-1]
    downloads_dir = BASE_DIR / 'downloads'
    downloads_dir.mkdir(exist_ok=True)
    archive_path = downloads_dir / filename
    response = session.get(archive_url)
    with open(archive_path, 'wb') as file:
        file.write(response.content)
    logging.info(f'Архив был загружен и сохранён: {archive_path}')

MODE_TO_FUNCTION = {
    'whats-new': whats_new,
    'latest-versions': latest_versions,
    'download': download,
    'pep': pep,
}

def main():
    configure_logging()
    logging.info('Парсер запущен!')
    arg_parser = configure_argument_parser(MODE_TO_FUNCTION.keys())
    args = arg_parser.parse_args()
    logging.info(f'Аргументы командной строки: {args}')
    session = requests_cache.CachedSession()
    if args.clear_cache:
        session.cache.clear()
    parser_mode = args.mode
    results = MODE_TO_FUNCTION[parser_mode](session)
    if results is not None:
        control_output(results, args)
    logging.info('Парсер завершил работу.')

if __name__ == '__main__':
    main()
