import math


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
