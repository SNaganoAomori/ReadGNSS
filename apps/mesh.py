import math


def dms_to_degree(dms: float, digits: int = 10) -> float:
    """
    ## Description:
        度分秒形式の経緯度を10進経緯度に変換する。
    Args:
        dms(float):
            度分秒形式の経緯度
        digits(int):
            小数点以下の桁数。デフォルトは10桁。
    Returns:
        float:
            10進経緯度
    Examples:
        >>> dms_to_degree(140516.27814)
        140.08785504166664
        >>> dms_to_degree(36103600.00000)
        36.103774791666666
    """
    dms_str = str(dms)
    sep = "."
    sep_idx = dms_str.find(sep)
    micro_sec = float(f"0.{dms_str[sep_idx + 1:]}")
    integer = dms_str[:sep_idx]
    sec = int(integer[-2:]) + micro_sec
    min_ = int(integer[-4:-2])
    deg = int(integer[:-4])
    return round(deg + (min_ / 60) + (sec / 3600), digits)


class MeshCode(object):
    def __init__(self, lon: float, lat: float):
        mesh = self._mesh_code(lon, lat)
        self.first_mesh_code = mesh["first_mesh_code"]
        self.secandary_mesh_code = mesh["secandary_mesh_code"]
        self.standard_mesh_code = mesh["standard_mesh_code"]
        self.half_mesh_code = mesh["half_mesh_code"]
        self.quarter_mesh_code = mesh["quarter_mesh_code"]

    def _mesh_code(self, lon: float, lat: float) -> dict[str, str]:
        """
        この計算に使用されている1文字の変数名は[地域メッシュ統計の特質・沿革 p12](https://www.stat.go.jp/data/mesh/pdf/gaiyo1.pdf)を参考にしています。
        """
        # latitude
        p, a = divmod(lat * 60, 40)
        q, b = divmod(a, 5)
        r, c = divmod(b * 60, 30)
        s, d = divmod(c, 15)
        t, e = divmod(b, 7.5)
        first_lat_code = str(int(p))
        secandary_lat_code = str(int(q))
        standard_lat_code = str(int(r))
        # longitude
        f, i = math.modf(lon)
        u = int(i - 100)
        v, g = divmod(f * 60, 7.5)
        w, h = divmod(g * 60, 45)
        x, j = divmod(h, 22.5)
        y, j = divmod(j, 11.25)
        first_lon_code = str(int(u))
        secandary_lon_code = str(int(v))
        standard_lon_code = str(int(w))
        m = str(int((s * 2) + (x + 1)))
        n = str(int((t * 2) + (y + 1)))
        first_mesh_code = first_lat_code + first_lon_code
        secandary_mesh_code = first_mesh_code + secandary_lat_code + secandary_lon_code
        standard_mesh_code = secandary_mesh_code + standard_lat_code + standard_lon_code
        half_mesh_code = standard_mesh_code + m
        quarter_mesh_code = half_mesh_code + n
        return {
            "first_mesh_code": first_mesh_code,
            "secandary_mesh_code": secandary_mesh_code,
            "standard_mesh_code": standard_mesh_code,
            "half_mesh_code": half_mesh_code,
            "quarter_mesh_code": quarter_mesh_code,
        }

    def __repr__(self) -> str:
        txt = f"""
First Mesh Code: {self.first_mesh_code}
Second Mesh Code: {self.secandary_mesh_code}
Standard Mesh Code: {self.standard_mesh_code}
Half Mesh Code: {self.half_mesh_code}
Quarter Mesh Code: {self.quarter_mesh_code}
"""
        return txt


class ReverseMeshCode(object):
    def __init__(self, mesh_code: str):
        if isinstance(mesh_code, int or float):
            mesh_code = str(mesh_code)
        self.mesh_code = mesh_code
        lonlat = self._calc_lonlat()
        self.lon = lonlat["lon"]
        self.lat = lonlat["lat"]

    def _calc_lonlat(self):
        first_lonlat = self._mesh_to_first_lonlat()
        second_lonlat = self._mesh_to_seccandary_lonlat()
        standard_lonlat = self._mesh_to_standard_lonlat()
        lon = first_lonlat["lon"] + second_lonlat["lon"] + standard_lonlat["lon"]
        lat = first_lonlat["lat"] + second_lonlat["lat"] + standard_lonlat["lat"]
        return {"lon": lon, "lat": lat}

    def _mesh_to_first_lonlat(self):
        # 第一次メッシュコードから経緯度を取得
        code_first_two = self.mesh_code[0:2]
        code_last_two = self.mesh_code[2:4]
        code_first_two = int(code_first_two)
        code_last_two = int(code_last_two)
        lon = code_last_two + 100
        lat = code_first_two * 2 / 3
        return {"lon": lon, "lat": lat}

    def _mesh_to_seccandary_lonlat(self):
        # 第二次メッシュコードから経緯度を取得
        code_fifth = self.mesh_code[4:5]
        code_sixth = self.mesh_code[5:6]
        code_fifth = int(code_fifth)
        code_sixth = int(code_sixth)
        lon = code_sixth / 8
        lat = code_fifth * 2 / 3 / 8
        return {"lon": lon, "lat": lat}

    def _mesh_to_standard_lonlat(self):
        # 標準メッシュコードから経緯度を取得
        code_seventh = self.mesh_code[6:7]
        code_eighth = self.mesh_code[7:8]
        code_seventh = int(code_seventh)
        code_eighth = int(code_eighth)
        lon = code_eighth / 8 / 10
        lat = code_seventh * 2 / 3 / 8 / 10
        return {"lon": lon, "lat": lat}

    def __repr__(self) -> str:
        return (
            f"MeshCode: {self.mesh_code}, Longitude: {self.lon}, Latitude: {self.lat}"
        )


if __name__ == "__main__":
    current_lat = 40.832835180
    current_lon = 140.728866813
    mesh_code = MeshCode(current_lon, current_lat)
    standard_mesh_code = mesh_code.standard_mesh_code

    reverse_mesh_code = ReverseMeshCode(standard_mesh_code)
    print(reverse_mesh_code)
