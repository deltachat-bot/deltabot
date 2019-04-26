
class CommandHandler:

    def __init__(self, cmd):
        self.cmd = cmd.lower()
        self.args = []

    def is_valid_cmd(self, msg):
        self._process(msg)
        if self.args:
            return self.args[0].lower() == self.cmd

    def _process(self, msg):
        self.args = msg.lines[0].split()
