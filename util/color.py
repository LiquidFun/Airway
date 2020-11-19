import regex as re


class Color:
    def __init__(self):
        self.color_names = ["black", "red", "green", "yellow", "blue", "purple", "cyan", "white"]
        self.formatting = 0
        self._filter_pattern = re.compile(r"\033\[\d;\d+m")
        self.reset()

    def black(self): return self._set_color("black")
    def red(self): return self._set_color("red")
    def green(self): return self._set_color("green")
    def yellow(self): return self._set_color("yellow")
    def blue(self): return self._set_color("blue")
    def purple(self): return self._set_color("purple")
    def cyan(self): return self._set_color("cyan")
    def white(self): return self._set_color("black")

    def _set_color(self, name):
        self._prev_color = name
        return f"\033[{self.formatting};3{self.color_names.index(name)}m"

    def bold(self):
        return self._set_formatting(1)

    def underline(self):
        return self._set_formatting(4)

    def reset(self):
        self._set_color("white")
        return self._set_formatting(0)

    def _set_formatting(self, num):
        self.formatting = num
        return self._set_color(self._prev_color)

    def filter_color_codes(self, text):
        return self._filter_pattern.sub("", text)


