import os
import sys

from .botbase import BotBase
from .command import CommandHandler

try:
    import pyowm
except ImportError:
    print("PyOWM not installed. Cannot run weatherbot")
    sys.exit(1)

OPENWEATHER_API = os.environ.get('OPENWEATHER_API', None)
if not OPENWEATHER_API:
    print("Please set a valid OPENWEATHER_API environment variable")
    sys.exit(1)


class Runner(BotBase):

    # DC_EVENT_MSGS_CHANGED for unknown contacts
    # DC_EVENT_INCOMING_MSG for known contacts
    in_events = "DC_EVENT_MSGS_CHANGED|DC_EVENT_INCOMING_MSG"

    cmd_handler = CommandHandler('weather')

    def prepare_reply(self, msg, chat):
        args = self.cmd_handler.args 
        city = args[1]
        owm = pyowm.OWM(OPENWEATHER_API)

        try:
            observation = owm.weather_at_place(city)
            w = observation.get_weather()
            simple = w.get_status().lower()
            status = w.get_detailed_status()
            temp = w.get_temperature('celsius')['temp']
            if simple == 'clear':
                icon = '☀️ '
            elif simple == 'haze':
                icon = '🌤️ '
            elif simple == 'clouds':
                icon = '☁️'
            elif simple == 'drizzle':
                icon = '🌧   '
            else:
                icon = ''
            chat.set_reply_text(u"{}{} will have {}\n🌡️  {} C".format(
                icon, city, status, temp))

        except pyowm.exceptions.api_response_error.NotFoundError:
            chat.set_reply_text(u"Cannot find that place 🤔 ")
