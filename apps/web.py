import time
import datetime
from pprint import pprint
from typing import Dict
from typing import List
from typing import NamedTuple
from typing import Union

import asyncio
import aiohttp
from pydantic import ValidationError

from .config import Web
from .config import SemiDynamicCorrection

web = Web()


# ***********************************************************************
# **************** 地理院APIで標高値を取得する非同期処理 ****************
# ***********************************************************************
async def fetch_elevation(
    session: aiohttp.client.ClientSession,
    index: int,
    lon: float,
    lat: float,
    max_retry: int = 5,
    time_out: int = 10,
) -> Dict[int, float]:
    """
    ## Description:
        地理院APIで標高値を取得する
    Args:
        session(aiohttp.client.ClientSession): セッション
        index(int): インデックス
        lon(float): 経度
        lat(float): 緯度
        max_retry(int): リトライ回数
        time_out(int): タイムアウト
    Returns:
        Dict[int, float]: {index: elevation}
    """
    headers = web.dummy_user_agent()
    url = web.elevation_url(lon, lat)
    for _ in range(max_retry):
        try:
            async with session.get(url, headers=headers, timeout=time_out) as response:
                data = await response.json()
                if data.get("ErrMsg") is None:
                    print(
                        f"Idx: {index}  標高: {data['elevation']}m (lon: {lon}, lat: {lat})"
                    )
                    return {index: data["elevation"]}
                else:
                    print("サーバーが混みあっています。")
        except aiohttp.ClientError:
            print(
                f"リクエストに失敗しました (Index: {index}, lon: {lon}, lat: {lat})。再試行中..."
            )
    return {index: None}


async def fetch_elevation_main(
    idxs: List[int], lons: List[float], lats: List[float], time_sleep: int = 10
) -> List[Dict[int, float]]:
    """
    ## Description:
        地理院APIで標高値を取得するメイン処理
    Args:
        idxs(List[int]): インデックス
        lons(List[float]): 経度
        lats(List[float]): 緯度
        time_sleep(int): 待ち時間。地理院APIのリクエスト制限による
    Returns:
        List[Dict[int, float]]: [{index: elevation}]
    """
    results = []
    async with aiohttp.ClientSession() as session:
        tasks = []
        for idx, lon, lat in zip(idxs, lons, lats):
            task = fetch_elevation(session, idx, lon, lat)
            tasks.append(task)
            if len(tasks) == 10:
                results += await asyncio.gather(*tasks)
                tasks = []
                time.sleep(time_sleep)
        if tasks:
            results += await asyncio.gather(*tasks)
    return results


def fetch_elevation_from_web(lons: List[float], lats: List[float]) -> List[float]:
    """
    ## Description:
        非同期処理により、地理院APIで標高値を取得する
    Args:
        lons(List[float]): 10進経度
        lats(List[float]): 10進緯度
    Returns:
        List[float]: 標高値
    Examples:
        >>> lons = [141.272242456]
        >>> lats = [40.924881316]
        >>> fetch_elevation_from_web(lons, lats)
        Idx: 0  標高: 84m (lon: 141.272242456, lat: 40.924881316)
        [84]
    """
    idxs = list(range(len(lons)))
    resps_lst = asyncio.run(fetch_elevation_main(idxs, lons, lats))
    _data = {}
    for resp in resps_lst:
        _data.update(resp)
    sorted_keys = sorted(_data.keys())
    sorted_elev = [_data[key] for key in sorted_keys]
    return sorted_elev


# ***********************************************************************
# **************** 地理院APIでセミダイナミック補正を行う ****************
# ***********************************************************************
class Coords(NamedTuple):
    longitude: float
    latitude: float
    altitude: float


async def fetch_corrected_semidynamic(
    session: aiohttp.client.ClientSession,
    index: int,
    correction_datetime: Union[str, int, datetime.datetime],
    lon: float,
    lat: float,
    alti: float = 0.0,
    max_retry: int = 5,
    time_out: int = 10,
) -> Dict[int, float]:
    """
    ## Description:
        地理院APIでセミダイナミック補正を行う
    Args:
        session(aiohttp.client.ClientSession): セッション
        index(int): インデックス
        correction_datetime(Union[str, int, datetime.datetime]): 補正日時
        lon(float): 経度
        lat(float): 緯度
        alti(float): 標高。標高は指定しなくとも問題はない。
        max_retry(int): リトライ回数
        time_out(int): タイムアウト
    Returns:
        Dict[int, float]: {index: Coords}
            - Coords: NamedTuple(longitude: float, latitude: float, altitude: float))
    """
    headers = web.dummy_user_agent()
    try:
        semidyna = SemiDynamicCorrection(
            correction_year=correction_datetime,
            longitude=lon,
            latitude=lat,
            altitude=alti,
        )
    except ValidationError as e:
        pprint(e.errors())
    url = semidyna.url
    for _ in range(max_retry):
        try:
            async with session.get(url, headers=headers, timeout=time_out) as response:
                data = await response.json()
                if data.get("ErrMsg") is None:
                    data = data.get("OutputData")
                    if data.get("altitude") == {}:
                        data["altitude"] = 0.0
                    data["longitude"] = float(data["longitude"])
                    data["latitude"] = float(data["latitude"])
                    data = Coords(**data)
                    print(
                        f"Request   => Lon: {lon}, Lat: {lat}, Alt: {alti}m\n"
                        f"Corrected => Lon: {data.longitude}, Lat: {data.latitude}, Alt: {data.altitude}m\n"
                    )
                    return {index: data}
                else:
                    print(f'サーバーが混みあっています。ErrMsg: {data.get("ErrMsg")}')
        except aiohttp.ClientError:
            print(
                f"リクエストに失敗しました (Index: {index}, lon: {lon}, lat: {lat})。再試行中..."
            )
    return {index: None}


async def fetch_corrected_semidynamic_main(
    idxs: List[int],
    correction_datetime: Union[str, int, datetime.datetime],
    lons: List[float],
    lats: List[float],
    altis: List[float] = None,
    time_sleep: int = 10,
) -> List[Dict[int, float]]:
    """
    ## Description:
        地理院APIでセミダイナミック補正を行うメイン処理
    Args:
        idxs(List[int]): インデックス
        correction_datetime(Union[str, int, datetime.datetime]): 補正日時
        lons(List[float]): 経度
        lats(List[float]): 緯度
        altis(List[float]): 標高
        time_sleep(int): 待ち時間。地理院APIのリクエスト制限による
    Returns:
        List[Dict[int, float]]: [{index: Coords}]
            - Coords: NamedTuple(longitude: float, latitude: float, altitude: float))
    """
    if altis is None:
        # 標高が指定されていない場合は、0.0mとする。問題はない
        altis = [0.0] * len(lons)

    results = []
    async with aiohttp.ClientSession() as session:
        tasks = []
        for idx, lon, lat, alti in zip(idxs, lons, lats, altis):
            task = fetch_corrected_semidynamic(
                session, idx, correction_datetime, lon, lat, alti
            )
            tasks.append(task)
            if len(tasks) == 10:
                results += await asyncio.gather(*tasks)
                tasks = []
                time.sleep(time_sleep)
        if tasks:
            results += await asyncio.gather(*tasks)
    return results


def fetch_corrected_semidynamic_from_web(
    correction_datetime: Union[str, int, datetime.datetime],
    lons: List[float],
    lats: List[float],
    altis: List[float] = None,
) -> List[Coords]:
    """
    ## Description:
        非同期処理により、地理院APIでセミダイナミック補正を行う。
        これは今期から元期への2次元補正を行う。2025/4以降に測量を行ったものでは
        通常2024年を元期とするが、2024年以前に測量を行ったものでは2011年を元期とする。
    Args:
        correction_datetime(Union[str, int, datetime.datetime]): 補正日時
        lons(List[float]): 10進経度
        lats(List[float]): 10進緯度
        altis(List[float]): 標高
    Returns:
        List[Coords]: NamedTuple(longitude: float, latitude: float, altitude: float))
    """
    idxs = list(range(len(lons)))
    resps_lst = asyncio.run(
        fetch_corrected_semidynamic_main(idxs, correction_datetime, lons, lats, altis)
    )
    _data = {}
    for resp in resps_lst:
        _data.update(resp)
    sorted_keys = sorted(_data.keys())
    sorted_coords = [_data[key] for key in sorted_keys]
    return sorted_coords
