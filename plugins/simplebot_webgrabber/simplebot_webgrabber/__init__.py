# -*- coding: utf-8 -*-
from urllib.request import quote

from simplebot import Plugin
import bs4
import requests
from jinja2 import Environment, PackageLoader, select_autoescape


def get_page(url, script=None):
    headers = {'user-agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:60.0) Gecko/20100101 Firefox/60.0'}
    r = requests.get(url, headers=headers, stream=True)
    if 'text/html' not in r.headers['content-type']:
        r.connection.close()
        return None
    r.encoding = 'utf-8'
    soup = bs4.BeautifulSoup(r.text, 'html.parser')
    [t.extract() for t in soup(['script', 'meta', 'iframe', 'noscript', 'link'])]
    comments = soup.find_all(text=lambda text:isinstance(text, bs4.Comment))
    [comment.extract() for comment in comments]
    if script is not None:
        s = soup.new_tag('script')
        s.string = script
        soup.body.append(s)
    return str(soup)


class WebGrabber(Plugin):

    name = 'WebGrabber'
    description = 'Provides the !web <url> command.'
    long_description = 'Ex. !web http://delta.chat'
    version = '0.2.0'
    author = 'adbenitez'
    author_email = 'adbenitez@nauta.cu'
    cmd = '!web'

    NOT_ALLOWED = 'Only html pages are allowed'
    DOWNLOAD_FAILED = 'Falied to get the url: "{}"'

    @classmethod
    def activate(cls, ctx):
        super().activate(ctx)
        cls.TEMP_FILE = os.path.join(cls.ctx.basedir, cls.name+'.html')
        cls.env = Environment(
            loader=PackageLoader(__name__, 'templates'),
            autoescape=select_autoescape(['html', 'xml'])
        )
        # if ctx.locale == 'es':
        #     cls.description = 'Provee el comando `!web <url>` el cual permite obtener la página web con la url dada. Ej. !web http://delta.chat.'
        #     cls.NOT_ALLOWED = 'Solo está permitido descargar páginas web'
        #     cls.DOWNLOAD_FAILED = 'No fue posible obtener la url: "{}"'

    @classmethod
    def process(cls, msg):
        arg = cls.get_args('!web', msg.text)
        if arg is None:
            return False
        chat = cls.ctx.acc.create_chat_by_message(msg)
        if not arg:
            template = cls.env.get_template('index.html')
            with open(cls.TEMP_FILE, 'w') as fd:
                fd.write(template.render(plugin=cls, bot_addr=cls.ctx.acc.get_self_contact().addr))
            chat.send_file(cls.TEMP_FILE, mime_type='text/html')
        else:
            try:
                if not arg.startswith('http'):
                    arg = 'http://'+arg
                script = r'for(let e of document.getElementsByTagName("a")){const h=e.href;h&&-1===h.indexOf("mailto:")&&(e.href="mailto:' + cls.ctx.acc.get_self_contact().addr + r'?subject=!web&body="+encodeURI(`${h}`))}'
                page = get_page(arg, script)
                if page is not None:
                    # for a in soup.find_all('a', attrs={'href':True}):
                    #     if a['href'].startswith('/'):
                    #         index = r.url.find('/', 8)
                    #         if index >= 0:                                
                    #             a['href'] = r.url[:index]+a['href']
                    #         else:
                    #             a['href'] = r.url+a['href']
                    #     a['href'] = 'mailto:{}?subject={}&body={}'.format(cls.ctx.acc.get_self_contact().addr, quote('!web '), quote(a['href'], safe=''))
                    with open(cls.TEMP_FILE, 'w') as fd:
                        fd.write(page)
                    chat.send_file(cls.TEMP_FILE, mime_type='text/html')
                else:
                    chat.send_text(cls.NOT_ALLOWED)
            except Exception as ex:
                cls.ctx.logger.exception(ex)
                chat.send_text(cls.DOWNLOAD_FAILED.format(arg))
        return True
