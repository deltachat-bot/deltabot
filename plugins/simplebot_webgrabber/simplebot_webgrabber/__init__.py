# -*- coding: utf-8 -*-
from urllib.parse import quote_plus, unquote_plus, quote
import gettext
import os
import re
import mimetypes

from jinja2 import Environment, PackageLoader, select_autoescape
from simplebot import Plugin, Mode, PluginCommand
import bs4
import html2text
import requests


EQUAL_TOKEN = 'simplebot_e_token'
AMP_TOKEN = 'simplebot_a_token'
HEADERS = {
    'user-agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:60.0) Gecko/20100101 Firefox/60.0'}


class WebGrabber(Plugin):

    name = 'WebGrabber'
    version = '0.3.0'

    @classmethod
    def activate(cls, bot):
        super().activate(bot)

        cls.cfg = cls.bot.get_config(__name__)
        if not cls.cfg.get('max-size'):
            cls.cfg['max-size'] = '5242880'
            cls.bot.save_config()

        cls.env = Environment(
            loader=PackageLoader(__name__, 'templates'),
            autoescape=select_autoescape(['html', 'xml'])
        )

        localedir = os.path.join(os.path.dirname(__file__), 'locale')
        lang = gettext.translation('simplebot_webgrabber', localedir=localedir,
                                   languages=[bot.locale], fallback=True)
        lang.install()

        cls.description = _('Access the web using DeltaChat.')
        cls.commands = [
            PluginCommand('/ddg', ['<text>'],
                          _('Search in DuckDuckGo'), cls.ddg_cmd),
            PluginCommand('/wt', ['<text>'],
                          _('Search in Wiktionary'), cls.wt_cmd),
            PluginCommand('/w', ['<text>'],
                          _('Search in Wikipedia'), cls.w_cmd),
            PluginCommand('/wttr', ['<text>'],
                          _('Search weather info from wttr.in'), cls.wttr_cmd),
            PluginCommand('/web', ['<url>'],
                          _('Get a webpage or file'), cls.web_cmd),
            PluginCommand('/url', ['<url>'],
                          _('Get a webpage as text'), cls.url_cmd),
            PluginCommand('/web/app', [], _('Sends an html app to help you to use the plugin.'), cls.app_cmd)]
        cls.bot.add_commands(cls.commands)

        cls.NOSCRIPT = _(
            'You need a browser with JavaScript support for this page to work correctly.')

    @classmethod
    def send_page(cls, chat, url, mode):
        if not url.startswith('http'):
            url = 'http://'+url
        try:
            with requests.get(url, headers=HEADERS, stream=True) as r:
                r.raise_for_status()
                r.encoding = 'utf-8'
                cls.bot.logger.debug(
                    'Content type: {}'.format(r.headers['content-type']))
                if 'text/html' in r.headers['content-type']:
                    soup = bs4.BeautifulSoup(r.text, 'html5lib')
                    [t.extract() for t in soup(
                        ['script', 'iframe', 'noscript', 'link', 'meta'])]
                    soup.head.append(soup.new_tag('meta', charset='utf-8'))
                    [comment.extract() for comment in soup.find_all(
                        text=lambda text: isinstance(text, bs4.Comment))]
                    for t in soup(['img']):
                        src = t.get('src')
                        if src:
                            t.name = 'a'
                            t['href'] = src
                            t.string = '[{}]'.format(t.get('alt', 'IMAGE'))
                            del t['src'], t['alt']

                            parent = t.find_parent('a')
                            if parent:
                                t.extract()
                                parent.insert_before(t)
                                if not parent.contents:
                                    if t.string == '[IMAGE]':
                                        parent.string = '(LINK)'
                                    else:
                                        parent.string = t.string+'(LINK)'
                        else:
                            t.extract()
                    if r.url.startswith('https://www.startpage.com'):
                        for a in soup('a', href=True):
                            url = a['href'].split(
                                'startpage.com/cgi-bin/serveimage?url=')
                            if len(url) == 2:
                                a['href'] = unquote_plus(url[1])
                    for a in soup('a', href=True):
                        if not a['href'].startswith('mailto:'):
                            a['href'] = a['href'].replace('=', EQUAL_TOKEN)
                            a['href'] = a['href'].replace('&', AMP_TOKEN)
                    styles = [str(s) for s in soup.find_all('style')]
                    for t in soup(lambda t: t.has_attr('class') or t.has_attr('id')):
                        classes = []
                        for c in t.get('class', []):
                            for s in styles:
                                if '.'+c in s:
                                    classes.append(c)
                                    break
                        del t['class']
                        if classes:
                            t['class'] = ' '.join(classes)
                        if t.get('id') is not None:
                            for s in styles:
                                if '#'+t['id'] in s:
                                    break
                            else:
                                del t['id']
                    index = r.url.find('/', 8)
                    if index == -1:
                        root = url = r.url
                    else:
                        root = r.url[:index]
                        url = r.url.rsplit('/', 1)[0]
                    t = soup.new_tag('script')
                    t.string = cls.env.get_template('page.js').render(
                        bot_addr=cls.bot.get_address(), root=root, url=url)
                    soup.body.append(t)
                    cls.bot.send_html(
                        chat, str(soup), cls.name, mode)
                else:
                    max_size = cls.cfg.getint('max-size')
                    chunks = b''
                    size = 0
                    for chunk in r.iter_content(chunk_size=10240):
                        chunks += chunk
                        size += len(chunk)
                        if size > max_size:
                            chat.send_text(
                                _('Only files smaller than {} Bytes are allowed').format(max_size))
                            return
                    else:
                        d = r.headers.get('content-disposition')
                        if d is not None:
                            fname = re.findall(
                                "filename=(.+)", d)[0].strip('"')
                        else:
                            fname = r.url.split(
                                '/').pop().split('?')[0].split('#')[0]
                            if '.' not in fname:
                                if not fname:
                                    fname = 'file'
                                ctype = r.headers.get(
                                    'content-type', '').split(';')[0].strip().lower()
                                if 'text/plain' == ctype:
                                    ext = '.txt'
                                elif 'image/jpeg' == ctype:
                                    ext = '.jpg'
                                else:
                                    ext = mimetypes.guess_extension(ctype)
                                if ext:
                                    fname += ext
                        fpath = cls.bot.get_blobpath(fname)
                        with open(fpath, 'wb') as fd:
                            fd.write(chunks)
                        chat.send_file(fpath)
        except Exception as ex:      # TODO: too much generic, change this
            cls.bot.logger.exception(ex)
            chat.send_text(_('Falied to get url:\n{}').format(url))

    @classmethod
    def _send_text(cls, chat, url):
        if not url.startswith('http'):
            url = 'http://'+url
        try:
            with requests.get(url, headers=HEADERS, stream=True) as r:
                r.raise_for_status()
                r.encoding = 'utf-8'
                cls.bot.logger.debug(
                    'Content type: {}'.format(r.headers['content-type']))
                if 'text/html' in r.headers['content-type']:
                    chat.send_text(html2text.html2text(r.text))
        except Exception as ex:      # TODO: too much generic, change this
            cls.bot.logger.exception(ex)
            chat.send_text(_('Falied to get url:\n{}').format(url))

    @classmethod
    def app_cmd(cls, ctx):
        chat = cls.bot.get_chat(ctx.msg)
        template = cls.env.get_template('index.html')
        html = template.render(plugin=cls, bot_addr=cls.bot.get_address())
        cls.bot.send_html(chat, html, cls.name, ctx.mode)

    @classmethod
    def url_cmd(cls, ctx):
        url = ctx.text.replace(EQUAL_TOKEN, '=').replace(AMP_TOKEN, '&')
        cls._send_text(cls.bot.get_chat(ctx.msg), url)

    @classmethod
    def web_cmd(cls, ctx):
        url = ctx.text.replace(EQUAL_TOKEN, '=').replace(AMP_TOKEN, '&')
        cls.send_page(cls.bot.get_chat(ctx.msg), url, ctx.mode)

    @classmethod
    def ddg_cmd(cls, ctx):
        chat = cls.bot.get_chat(ctx.msg)
        url = "https://duckduckgo.com/lite?q={}".format(quote_plus(ctx.text))
        cls.send_page(chat, url, ctx.mode)

    @classmethod
    def w_cmd(cls, ctx):
        chat = cls.bot.get_chat(ctx.msg)
        url = "https://{}.m.wikipedia.org/wiki/?search={}".format(
            ctx.locale, quote_plus(ctx.text))
        cls.send_page(chat, url, ctx.mode)

    @classmethod
    def wt_cmd(cls, ctx):
        chat = cls.bot.get_chat(ctx.msg)
        url = "https://{}.m.wiktionary.org/wiki/?search={}".format(
            ctx.locale, quote_plus(ctx.text))
        cls.send_page(chat, url, ctx.mode)

    @classmethod
    def wttr_cmd(cls, ctx):
        cls.send_page(cls.bot.get_chat(
            ctx.msg), "https://wttr.in/{}_Fnp_lang={}.png".format(quote(ctx.text), ctx.locale), ctx.mode)
