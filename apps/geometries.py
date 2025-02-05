from typing import Any
from typing import Dict
from typing import List
from typing import NamedTuple

import pyproj
import pyproj.database
from pydantic import field_validator
from pydantic import BaseModel


class XY(NamedTuple):
    x: float | List[float]
    y: float | List[float]


def estimate_utm_crs(lon: float, lat: float, datum_name: str='JGD2011') -> str:
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
    area_of_interest = (
        pyproj
        .aoi
        .AreaOfInterest(
            west_lon_degree=lon,
            south_lat_degree=lat,
            east_lon_degree=lon,
            north_lat_degree=lat
        )
    )
    utm_crs_lst = (
        pyproj
        .database
        .query_utm_crs_info(
            datum_name=datum_name,
            area_of_interest=area_of_interest
        )
    )
    return pyproj.CRS.from_epsg(utm_crs_lst[0].code).to_wkt()


def reproject_xy(
        xs: float | List[float],
        ys: float | List[float],
        in_crs: str,
        out_crs: str
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
        tf = pyproj.Transformer.from_crs(
            in_crs, out_crs, always_xy=True
        )
        x, y = tf.transform(xs, ys)
        return XY(x, y)

