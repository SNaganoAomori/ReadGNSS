from matplotlib.colors import to_rgba, to_hex

from .config import COLORS


class Colors(object):
    def __init__(self):
        self.config = COLORS
        self.hex_colors = [
            self.red("hex"),
            self.green("hex"),
            self.blue("hex"),
            self.orange("hex"),
            self.limegreen("hex"),
            self.skyblue("hex"),
            self.pink("hex"),
            self.olive("hex"),
            self.violet("hex"),
            self.gold("hex"),
        ]
        self.kml_colors = [
            self.red(),
            self.green(),
            self.blue(),
            self.orange(),
            self.limegreen(),
            self.skyblue(),
            self.pink(),
            self.olive(),
            self.violet(),
            self.gold(),
        ]

    def get(self, hex: str, type_: str = "rgb", alpha: float = 1.0):
        rgba = to_rgba(hex, alpha)
        if type_ == "rgb":
            return rgba
        elif type_ == "hex":
            if alpha < 1.0:
                return to_hex(rgba, keep_alpha=True)
            return to_hex(rgba)
        elif type_ == "kml":
            r = self.bit16(rgba[0])
            g = self.bit16(rgba[1])
            b = self.bit16(rgba[2])
            a = self.bit16(rgba[3])
            return a + b + g + r

    def bit16(self, val):
        val = f"{int(val * 255):x}"
        if len(val) == 1:
            return "0" + val
        return val

    def red(self, type_: str = "kml", alpha: float = 1.0):
        return self.get(self.config.get("red"), type_, alpha)

    def green(self, type_: str = "kml", alpha: float = 1.0):
        return self.get(self.config.get("green"), type_, alpha)

    def blue(self, type_: str = "kml", alpha: float = 1.0):
        return self.get(self.config.get("blue"), type_, alpha)

    def orange(self, type_: str = "kml", alpha: float = 1.0):
        return self.get(self.config.get("orange"), type_, alpha)

    def limegreen(self, type_: str = "kml", alpha: float = 1.0):
        return self.get(self.config.get("limegreen"), type_, alpha)

    def skyblue(self, type_: str = "kml", alpha: float = 1.0):
        return self.get(self.config.get("skyblue"), type_, alpha)

    def pink(self, type_: str = "kml", alpha: float = 1.0):
        return self.get(self.config.get("pink"), type_, alpha)

    def olive(self, type_: str = "kml", alpha: float = 1.0):
        return self.get(self.config.get("olive"), type_, alpha)

    def violet(self, type_: str = "kml", alpha: float = 1.0):
        return self.get(self.config.get("violet"), type_, alpha)

    def gold(self, type_: str = "kml", alpha: float = 1.0):
        return self.get(self.config.get("gold"), type_, alpha)
