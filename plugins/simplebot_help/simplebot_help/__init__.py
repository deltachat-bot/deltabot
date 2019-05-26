# -*- coding: utf-8 -*-
from simplebot import Plugin
from jinja2 import Environment, PackageLoader, select_autoescape

class Helper(Plugin):

    name = 'Help'
    description = 'Provides the !help command.'
    long_description = 'To learn more about a plugin press the "More" button, to use them press the "Use" button, You will be prompted to use an app, select to always open with Delta Chat.'
    version = '0.2.0'
    author = 'adbenitez'
    author_email = 'adbenitez@nauta.cu'
    cmd = '!help'

    NOSCRIPT = 'You need a browser with JavaScript support for this page to work correctly.'
    # BANNER = 'SimpleBot for Delta Chat.\nInstalled plugins:\n\n'

    @classmethod
    def activate(cls, ctx):
        super().activate(ctx)
        env = Environment(
            loader=PackageLoader('simplebot_ddg', 'templates'),
            autoescape=select_autoescape(['html', 'xml'])
        )
        cls.template = env.get_template('index.html')
        cls.TEMP_FILE = os.path.join(cls.ctx.basedir, cls.name+'.html')
        # if ctx.locale == 'es':
        #     cls.description = 'Provee el comando !help que muestra este mensaje. Ej. !help.'
        #     cls.BANNER = 'SimpleBot para Delta Chat.\nPlugins instalados:\n\n'

    @classmethod
    def process(cls, msg):
        if cls.get_args(cls.cmd, msg.text) is not None:
            with open(cls.TEMP_FILE, 'w') as fd:
                fd.write(cls.template.render(plugin=cls))
            chat = cls.ctx.acc.create_chat_by_message(msg)
            chat.send_file(cls.TEMP_FILE, mime_type='text/html')
            return True
        return False
