# -*- coding: utf-8 -*-
from urllib.request import urlopen
from urllib.parse import quote_plus
import os

from simplebot import Plugin
import bs4
from jinja2 import Environment, PackageLoader, select_autoescape
import requests


def get_page(url, script=None):
    headers = {'user-agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:60.0) Gecko/20100101 Firefox/60.0'}
    r = requests.get(url, headers=headers, stream=True)
    if 'text/html' not in r.headers['content-type']:
        r.connection.close()
        return None
    soup = bs4.BeautifulSoup(r.text, 'html.parser')
    [t.extract() for t in soup(['script', 'meta', 'iframe', 'noscript', 'link'])]
    meta = soup.new_tag('meta', name="viewport", content="width=device-width, initial-scale=1.0")
    soup.head.insert(1, meta)
    if script is not None:
        s = soup.new_tag('script')
        s.string = script
        soup.body.append(s)
    return str(soup)


class DuckDuckGo(Plugin):

    name = 'DuckDuckGo'
    description = 'Allows to use DuckDuckGo to search the web.'
    long_description = 'Examples:<ul><li>!ddg Delta Chat</li><li>!ddg riseup provider site:support.delta.chat</li></ul>'
    version = '0.2.0'
    author = 'adbenitez'
    author_email = 'adbenitez@nauta.cu'

    NOSCRIPT = 'You need a browser with JavaScript support for this page to work correctly.'
    SEARCH = 'Search'

    @classmethod
    def activate(cls, ctx):
        super().activate(ctx)
        cls.env = Environment(
            loader=PackageLoader(__name__, 'templates'),
            autoescape=select_autoescape(['html', 'xml'])
        )

        cls.TEMP_FILE = os.path.join(cls.ctx.basedir, cls.name+'.html')
        if ctx.locale == 'es':
            cls.description = 'Permite buscar en Internet con el motor de búsquedas DuckDuckGo.'
            cls.long_description = 'Puedes usarlo directamente con el comando !ddg <texto>, por ejemplo:<p>!ddg Cuba site:es.wikipedia.org</p>.'
            cls.NOSCRIPT = 'Necesitas un navegador que soporte JavaScript para poder usar esta funcionalidad.'
            cls.SEARCH = 'Buscar'

    @classmethod
    def process(cls, msg):
        arg = cls.get_args('!ddg', msg.text)
        if arg is None:
            return False
        if arg:
            script = r'for(let a of document.getElementsByTagName("a"))if(a.href&&-1===a.href.indexOf("mailto:")){const b=encodeURIComponent(`${a.getAttribute("href").replace(/^(?!https?:\/\/|\/\/)\.?\/?(.*)/,`${"https://duckduckgo.com"}/$1`)}`);a.href=`mailto:${"' + cls.ctx.acc.get_self_contact().addr + r'"}?subject=%21web%20&body=${b}`}'
            html = get_page('https://duckduckgo.com/lite?q={}'.format(quote_plus(arg)), script)
        else:
            template = cls.env.get_template('index.html')
            html = template.render(plugin=cls, bot_addr=cls.ctx.acc.get_self_contact().addr)
        with open(cls.TEMP_FILE, 'w') as fd:
            fd.write(html)
        chat = cls.ctx.acc.create_chat_by_message(msg)
        chat.send_file(cls.TEMP_FILE, mime_type='text/html')
        return True
