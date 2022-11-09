import re
import os


class Color:
    def __init__(self):
        self.color_names = ["black", "red", "green", "yellow", "blue", "purple", "cyan", "white"]
        self.formatting = 0
        self._filter_pattern = re.compile(r"\033\[\d;\d+m")
        self.reset()

    def black(self, surround=""):
        return self._surround_with_color(0, surround)

    def red(self, surround=""):
        return self._surround_with_color(1, surround)

    def green(self, surround=""):
        return self._surround_with_color(2, surround)

    def yellow(self, surround=""):
        return self._surround_with_color(3, surround)

    def blue(self, surround=""):
        return self._surround_with_color(4, surround)

    def purple(self, surround=""):
        return self._surround_with_color(5, surround)

    def cyan(self, surround=""):
        return self._surround_with_color(6, surround)

    def white(self, surround=""):
        return self._surround_with_color(7, surround)

    def _surround_with_color(self, color_index, surround=""):
        full = self._set_color(self.color_names[color_index])
        if surround:
            full += str(surround) + self.reset()
        return full

    def _set_color(self, name):
        # Windows console does not support colors, possibly try colorama for color support on windows (TODO)
        if os.name == "nt":
            return ""
        else:
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
