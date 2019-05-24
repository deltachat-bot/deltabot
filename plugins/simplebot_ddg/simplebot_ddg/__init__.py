# -*- coding: utf-8 -*-
from urllib.request import urlopen
from urllib.parse import quote_plus

from simplebot import Plugin
import bs4
from jinja2 import Environment, PackageLoader, select_autoescape
import requests


env = Environment(
    loader=PackageLoader('simplebot_ddg', 'templates'),
    autoescape=select_autoescape(['html', 'xml'])
)


def get_page(url, script=None):
    headers = {'user-agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:60.0) Gecko/20100101 Firefox/60.0'}
    r = requests.get(url, headers=headers, stream=True)
    if 'text/html' not in r.headers['content-type']:
        r.connection.close()
        return None
    soup = bs4.BeautifulSoup(r.text, 'html.parser')
    [t.extract() for t in soup(['script', 'meta', 'iframe', 'noscript', 'link'])]
    comments = soup.find_all(text=lambda text:isinstance(text, bs4.Comment))
    [comment.extract() for comment in comments]
    if script is not None:
        s = soup.new_tag('script')
        s.string = script
        soup.body.append(s)
    return str(soup)


class DuckDuckGo(Plugin):

    name = 'DuckDuckGo'
    description = 'Provides the !ddg command to search in DuckDuckGo.'
    long_description = 'Examples:\n!ddg Delta Chat\n!ddg riseup provider site:support.delta.chat'
    version = '0.2.0'
    author = 'adbenitez'
    author_email = 'adbenitez@nauta.cu'
    NOT_FOUND = 'No results found for: "{}"'
    TEMP_FILE = name+'.html'

    @classmethod
    def activate(cls, ctx):
        super().activate(ctx)
        if ctx.locale == 'es':
            cls.description = 'Provee el comando `!ddg <texto>` para buscar en DuckDuckGo(buscador de Internet). Ej. !ddg que es software libre?.'
            cls.NOT_FOUND = 'No se encontraron resultados para: "{}"'

    @classmethod
    def process(cls, msg):
        arg = cls.get_args('!ddg', msg.text)
        if arg is None:
            return False
        if arg:
            script = r'alert("hi");for(let a of document.getElementsByTagName("a"))if(a.href&&-1===a.href.indexOf("mailto:")){const b=encodeURIComponent(`${a.getAttribute("href").replace(/^(?!https?:\/\/|\/\/)\.?\/?(.*)/,`${"https://duckduckgo.com"}/$1`)}`);a.href=`mailto:${"' + cls.ctx.acc.get_self_contact().addr + r'"}?subject=%21web%20&body=${b}`}'
            text = get_page('https://duckduckgo.com/lite?q={}'.format(quote_plus(arg)), script)
            #results = page.find_all('div', class_='result')
            # if not results:
            #     text = cls.NOT_FOUND.format(arg)
            # template = env.get_template('index.html')
            # text = template.render(plugin=cls, results=results)
            # for r in results:
            #     text += r.h2.a.get_text().strip() + '\n'
            #     text += r.find('a', class_='result__url').get_text().strip()+'\n'
            #     text += r.find('a', class_='result__snippet').get_text() +'\n\n'
        else:
            template = env.get_template('help.html')
            text = template.render(plugin=cls)
        with open(cls.TEMP_FILE, 'w') as fd:
            fd.write(text)
        chat = cls.ctx.acc.create_chat_by_message(msg)
        chat.send_file(cls.TEMP_FILE, mime_type='text/html')
        return True
