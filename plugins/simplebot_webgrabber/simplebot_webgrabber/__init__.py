# -*- coding: utf-8 -*-
from urllib.parse import quote_plus
import os

from simplebot import Plugin
import bs4
import requests
from jinja2 import Environment, PackageLoader, select_autoescape


def get_page(url):
    headers = {'user-agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:60.0) Gecko/20100101 Firefox/60.0'}
    r = requests.get(url, headers=headers, stream=True)
    if 'text/html' not in r.headers['content-type']:
        r.connection.close()
        return None
    soup = bs4.BeautifulSoup(r.text, 'html.parser')
    for t in soup(['meta']):
        if t.get('http-equiv') != 'content-type':
            t.extract()
    [t.extract() for t in soup(['script', 'iframe', 'noscript', 'link'])]
    comments = soup.find_all(text=lambda text:isinstance(text, bs4.Comment))
    [comment.extract() for comment in comments]
    script = r'for(let a of document.getElementsByTagName("a"))if(a.href&&-1===a.href.indexOf("mailto:")){const b=encodeURIComponent(`${a.getAttribute("href").replace(/^(?!https?:\/\/|\/\/)\.?\/?(.*)/,`${simplebot_url}/$1`)}`);a.href=`mailto:${"' + WebGrabber.ctx.acc.get_self_contact().addr + r'"}?body=%21web%20${b}`}'
    s = soup.new_tag('script')
    index = r.url.find('/', 8)
    if index >= 0:                                
        url = r.url[:index]
    else:
        url = r.url
    s.string = 'var simplebot_url = "{}";'.format(url)+script
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
    NOSCRIPT = 'You need a browser with JavaScript support for this page to work correctly.'

    @classmethod
    def activate(cls, ctx):
        super().activate(ctx)
        cls.TEMP_FILE = os.path.join(cls.ctx.basedir, cls.name+'.html')
        cls.env = Environment(
            loader=PackageLoader(__name__, 'templates'),
            #autoescape=select_autoescape(['html', 'xml'])
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
        req = arg
        for cmd,action in [('!ddg', cls.ddg_cmd), ('!w', cls.w_cmd)]:
            arg = cls.get_args(cmd, req)
            if arg is not None:
                action(msg, arg)
                break
        else:
            chat = cls.ctx.acc.create_chat_by_message(msg)
            if not arg:
                template = cls.env.get_template('index.html')
                with open(cls.TEMP_FILE, 'w') as fd:
                    fd.write(template.render(plugin=cls, bot_addr=cls.ctx.acc.get_self_contact().addr))
                chat.send_file(cls.TEMP_FILE, mime_type='text/html')
            else:
                cls.web_cmd(chat, arg)
        return True

    @classmethod
    def web_cmd(cls, chat, url):
        try:
            if not url.startswith('http'):
                url = 'http://'+url
            page = get_page(url)
            if page is not None:
                with open(cls.TEMP_FILE, 'w') as fd:
                    fd.write(page)
                chat.send_file(cls.TEMP_FILE, mime_type='text/html')
            else:
                chat.send_text(cls.NOT_ALLOWED)
        except Exception as ex:
            cls.ctx.logger.exception(ex)
            chat.send_text(cls.DOWNLOAD_FAILED.format(url))

    @classmethod
    def ddg_cmd(cls, msg, arg):
        chat = cls.ctx.acc.create_chat_by_message(msg)
        cls.web_cmd(chat, "https://duckduckgo.com/lite?q={}".format(quote_plus(arg)))

    @classmethod
    def w_cmd(cls, msg, arg):
        chat = cls.ctx.acc.create_chat_by_message(msg)
        cls.web_cmd(chat, "https://{}.m.wikipedia.org/wiki/?search={}".format(cls.locale, quote_plus(arg)))
