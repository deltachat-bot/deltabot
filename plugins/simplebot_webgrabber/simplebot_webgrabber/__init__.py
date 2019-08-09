# -*- coding: utf-8 -*-
from urllib.parse import quote_plus
import gettext
import os
import re

from simplebot import Plugin
import bs4
import requests
from jinja2 import Environment, PackageLoader, select_autoescape


HEADERS = {
    'user-agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:60.0) Gecko/20100101 Firefox/60.0'}
MAX_SIZE_MB = 5
MAX_SIZE = MAX_SIZE_MB*1024**2


class WebGrabber(Plugin):

    name = 'WebGrabber'
    version = '0.2.0'
    author = 'adbenitez'
    author_email = 'adbenitez@nauta.cu'
    cmd = '!web'

    @classmethod
    def activate(cls, ctx):
        super().activate(ctx)
        cls.TEMP_FILE = os.path.join(cls.ctx.basedir, cls.name+'.html')
        cls.env = Environment(
            loader=PackageLoader(__name__, 'templates'),
            #autoescape=select_autoescape(['html', 'xml'])
        )
        localedir = os.path.join(os.path.dirname(__file__), 'locale')
        try:
            lang = gettext.translation('simplebot_webgrabber', localedir=localedir,
                                       languages=[ctx.locale])
        except OSError:
            lang = gettext.translation('simplebot_webgrabber', localedir=localedir,
                                       languages=['en'])
        lang.install()
        cls.description = _('plugin.description')
        cls.long_description = _('plugin.long_description')
        cls.NOSCRIPT = _('noscript_msg')

    @classmethod
    def process(cls, msg):
        for cmd, action in [('!ddg', cls.ddg_cmd), ('!wt', cls.wt_cmd), ('!w', cls.w_cmd),
                            ('!web', cls.web_cmd)]:
            arg = cls.get_args(cmd, msg.text)
            if arg is not None:
                action(cls.ctx.acc.create_chat_by_message(msg), arg)
                break
        else:
            return False
        return True

    @classmethod
    def send_page(cls, chat, url):
        if not url.startswith('http'):
            url = 'http://'+url
        try:
            with requests.get(url, headers=HEADERS, stream=True) as r:
                r.raise_for_status()
                r.encoding = 'utf-8'
                if 'text/html' in r.headers['content-type']:
                    soup = bs4.BeautifulSoup(r.text, 'html.parser')
                    [t.extract() for t in soup(
                        ['script', 'iframe', 'noscript', 'link', 'meta'])]
                    soup.body.append(soup.new_tag('meta', charset='utf-8'))
                    [comment.extract() for comment in soup.find_all(
                        text=lambda text: isinstance(text, bs4.Comment))]
                    for t in soup(['img']):
                        src = t.get('src')
                        if src:
                            t.name = 'a'
                            t['href'] = src
                            t.string = '[{}]'.format(t.get('alt', 'IMAGE'))
                            del t['src'], t['alt']
                    script = r'for(let a of document.getElementsByTagName("a"))if(a.href&&-1===a.href.indexOf("mailto:")){const b=encodeURIComponent(`${a.getAttribute("href").replace(/^(?!https?:\/\/|\/\/)\.?\/?(.*)/,`${simplebot_url}/$1`)}`);a.href=`mailto:${"' + WebGrabber.ctx.acc.get_self_contact(
                    ).addr + r'"}?body=%21web%20${b}`}'
                    t = soup.new_tag('script')
                    index = r.url.find('/', 8)
                    if index >= 0:
                        url = r.url[:index]
                    else:
                        url = r.url
                    t.string = 'var simplebot_url = "{}";'.format(url)+script
                    soup.body.append(t)
                    with open(cls.TEMP_FILE, 'w') as fd:
                        fd.write(str(soup))
                    chat.send_file(cls.TEMP_FILE, mime_type='text/html')
                else:
                    chunks = r.iter_content(chunk_size=MAX_SIZE)
                    chunk = chunks.__next__()
                    if len(chunk) < MAX_SIZE:
                        d = r.headers.get('content-disposition', None)
                        if d is not None:
                            fname = re.findall(
                                "filename=(.+)", d)[0].strip('"')
                        else:
                            fname = r.url.split('/').pop().split('?')[0]
                        fpath = os.path.join(
                            cls.ctx.basedir, 'account.db-blobs', fname)
                        with open(fpath, 'wb') as fd:
                            fd.write(chunk)
                        chat.send_file(fpath)
                    else:
                        chat.send_text(_('not_allowed').format(MAX_SIZE_MB))
        except Exception as ex:      # TODO: too much generic
            cls.ctx.logger.exception(ex)
            chat.send_text(_('download_failed').format(url))

    @classmethod
    def web_cmd(cls, chat, url):
        if not url:
            template = cls.env.get_template('index.html')
            with open(cls.TEMP_FILE, 'w') as fd:
                fd.write(template.render(
                    plugin=cls, bot_addr=cls.ctx.acc.get_self_contact().addr))
            chat.send_file(cls.TEMP_FILE, mime_type='text/html')
        else:
            cls.send_page(chat, url)

    @classmethod
    def ddg_cmd(cls, chat, arg):
        cls.send_page(
            chat, "https://duckduckgo.com/lite?q={}".format(quote_plus(arg)))

    @classmethod
    def w_cmd(cls, chat, arg):
        cls.send_page(
            chat, "https://{}.m.wikipedia.org/wiki/?search={}".format(cls.ctx.locale, quote_plus(arg)))

    @classmethod
    def wt_cmd(cls, chat, arg):
        cls.send_page(
            chat, "https://{}.m.wiktionary.org/wiki/?search={}".format(cls.ctx.locale, quote_plus(arg)))
