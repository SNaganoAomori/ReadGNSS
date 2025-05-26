import math
from typing import List
from typing import NamedTuple

import geopandas as gpd
import pyproj
import pyproj.database
import shapely

from apps.config import Label


class XY(NamedTuple):
    x: float | List[float]
    y: float | List[float]


def estimate_utm_crs(lon: float, lat: float, datum_name: str = "JGD2011") -> str:
    """
    ## Description:
        経度、緯度からUTM座標系のCRSを推定する
    Args:
        lon(float): 経度
        lat(float): 緯度
        datum_name(str): 測地系名。'WGS84', 'JGD2000', 'JGD2011' ...
    Returns:
        str: UTM座標系のWKT形式のCRS
    Examples:
        >>> estimate_utm_crs(132.0, 36)
    """
    if (lon < 120) or (lon > 160):
        raise ValueError(
            "Specifies a longitude outside the range of Japan: "
            f"Argment: {lon}, Range: 120 <= lon <= 160"
        )
    area_of_interest = pyproj.aoi.AreaOfInterest(
        west_lon_degree=lon,
        south_lat_degree=lat,
        east_lon_degree=lon,
        north_lat_degree=lat,
    )
    utm_crs_lst = pyproj.database.query_utm_crs_info(
        datum_name=datum_name, area_of_interest=area_of_interest
    )
    return pyproj.CRS.from_epsg(utm_crs_lst[0].code).to_wkt()


def reproject_xy(
    xs: float | List[float], ys: float | List[float], in_crs: str, out_crs: str
) -> XY:
    """
    XYの投影変換
    Args:
        xs(float | List[float]): x座標
        ys(float | List[float]): y座標
        in_crs(str): 入力のWKT-CRS
        out_crs(str): 出力のWKT-CRS
    Returns:
        List[List[float], List[float]]: (x座標, y座標)
    Examples:
        >>> xs = [139.00, 140.00]
        >>> ys = [35.00, 36.00]
        >>> in_crs = pyproj.CRS.from_epsg(4326).to_wkt()
        >>> out_crs = pyproj.CRS.from_epsg(6678).to_wkt()
        >>> x, y = reproject_xy(xs, ys, in_crs, out_crs)
    """
    tf = pyproj.Transformer.from_crs(in_crs, out_crs, always_xy=True)
    x, y = tf.transform(xs, ys)
    return XY(x, y)


class Labeling(object):
    """
    ## Description:
        ラベルの位置を計算するクラス
    """

    def __init__(
        self,
        labels: list[str],
        points: list[shapely.Point],
        in_epsg: int,
    ):
        self._labels = labels
        self._points = points
        self._polygon = None
        self._in_epsg = pyproj.CRS.from_epsg(in_epsg)
        self._check_mercator()
        self._check_labels()

    def _check_mercator(self) -> None:
        """
        ## Description:
            メルカトル図法かどうかチェックする
        """
        if self._in_epsg.is_projected:
            self._polygon = shapely.Polygon(self._points)
        else:
            utm_crs = estimate_utm_crs(self._points[0].x, self._points[0].y)
            gs = gpd.GeoSeries(self._points, crs=self._in_epsg).to_crs(utm_crs)
            self._points = [geom for geom in gs.geometry]
            self._polygon = shapely.Polygon(self._points)

    def _check_labels(self) -> None:
        if len(self._labels) != len(self._points):
            raise ValueError(
                f"Labels and points length mismatch: "
                f"{len(self._labels)} != {len(self._points)}"
            )
        for i, label in enumerate(self._labels):
            if label is None:
                self._labels[i] = ""
            if not isinstance(label, str):
                self._labels[i] = str(label)

    def calculate_label_positions(
        self, buffer: float = 100, distance: float = 20
    ) -> list[shapely.Point]:
        labels = []
        for point, label in zip(self._points, self._labels):
            pnt = self._recalc_label_coords(point, self._polygon, buffer, distance)
            labels.append(Label(label, pnt, 0))
        return labels

    def _calc_new_point(
        self, point: shapely.geometry.Point, distance: float, angle: float
    ) -> shapely.geometry.Point:
        angle_rad = math.radians(angle)
        x = point.x + distance * math.sin(angle_rad)
        y = point.y + distance * math.cos(angle_rad)
        destination = (x, y)
        return shapely.geometry.Point(destination)

    def _calc_angle(
        self, point: shapely.geometry.Point, base_point: shapely.geometry.Point
    ) -> float:
        dy = point.y - base_point.y
        dx = point.x - base_point.x
        angle = math.degrees(math.atan2(dx, dy))
        if angle < 0:
            angle += 360
        return angle

    def _get_center_pt(
        self,
        point: shapely.geometry.Point,
        poly_geom: shapely.geometry.Polygon | shapely.geometry.MultiPolygon,
        buffer: float,
    ) -> shapely.geometry.Point:
        buff = point.buffer(buffer)
        intersection = buff.intersection(poly_geom)
        center = intersection.centroid
        return center

    def _recalc_label_coords(
        self,
        point: shapely.geometry.Point,
        poly_geom: shapely.geometry.Polygon | shapely.geometry.MultiPolygon,
        buffer: float = 100,
        distance: float = 20,
    ) -> shapely.geometry.Point:
        center_point = self._get_center_pt(point, poly_geom, buffer)
        angle = self._calc_angle(point, center_point)
        new_point = self._calc_new_point(point, distance, angle)
        return new_point
