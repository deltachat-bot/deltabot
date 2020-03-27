
from deltabot import deltabot_hookimpl

@deltabot_hookimpl
def deltabot_configure(bot, trans):
    bot.add_command(
        name="/mycalc",
        version="1.0",
        description=trans('caculcates result of arithmetic integer expression'),
        long_description=trans(
            'send "/calc 23+20" to the bot to get the result "43" back'),
        func=process_command_mycalc
    )


def process_command_mycalc(command):
    assert command.arg0 == "/mycalc"
    text = command.payload

    # don't directly use eval() as it could execute arbitrary code
    parts = text.split("+-*/")
    try:
        for part in parts:
            int(part.strip())
    except ValueError:
        reply = "ExpressionError: {!r}".format(text)
    else:
        # now it's safe to use eval
        reply = "result of {!r}: {}".format(text, eval(text))

    return reply


def test_bot_mycalc(testbot):
    cmd = testbot.make_command("/mycalc 23+20-1")
    res = process_command_mycalc(cmd)
    assert res == "42"
