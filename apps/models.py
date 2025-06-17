import datetime
import json
import math
from typing import Any, Dict, List, Optional, TypeAlias, Union

import fastkml
import fastkml.data
import fastkml.enums
import fastkml.geometry
import fastkml.kml
import fastkml.styles
import pandas as pd
import pygeoif
import pyproj
import shapely
from matplotlib.colors import to_rgba
from pydantic import BaseModel, field_validator, model_validator

from apps.chiriin.drawer import chiriin_drawer
from apps.config import (
    MODEL_EN_FIELD_NAMES,
    MODEL_RENAME_EN_TO_JA,
    SIGNALS,
    GoogleIcons,
    Label,
    OptionalFieldNames,
    formatter,
)
from apps.geometries import Labeling, estimate_utm_crs, reproject_xy
from apps.kml import append_closed_document_style

GeoJSON: TypeAlias = Dict[str, Any]
Kml: TypeAlias = str


def original_data_to(
    dict_data: Dict[str, Any],
    data_spac: Dict[str, str],  # {org_col: rename_col}
) -> Dict[str, Any]:
    """
    ## Description:
        データを仕様に従って変換する
    Args:
        dict_data(Dict[str, Any]): 変換前のデータ（way-pointファイルを読み込んだデータなど）

    Returns:
        Dict(str | Any): 変換後のデータ

    Examples:
        >>> drg = _DrgWayPoint(file_path)
        >>> datasets = drg.read_items()
        >>> spec = AppsFields().get_drg_wp_spec()
        >>> renamed_dict_data = original_data_to(datasets[0], spec)
    """
    renamed_dict = dict()
    for org_col, rename_col in data_spac.items():
        renamed_dict[rename_col] = dict_data.get(org_col, None)

    result = dict()
    for use_col in MODEL_EN_FIELD_NAMES.model_dump().values():
        result[use_col] = renamed_dict.get(use_col, None)
    return result


def hex_to_abgr(hex_str: str, alpha: float = 1.0):
    """Convert hex to ABGR."""

    def func(v):
        return f"{int(v * 255):x}".zfill(2)

    r, g, b, a = [func(v) for v in to_rgba(hex_str, alpha)]
    return "".join([a, b, g, r])


class DataModel(BaseModel):
    """
    GNSS測量データのモデル
    """

    sort_index: Optional[int] = None
    start: Optional[datetime.datetime] = None
    end: Optional[datetime.datetime] = None
    measurement_time: Optional[int] = None
    point: Optional[str] = None
    group_name: Optional[str] = ""
    point_name: Optional[float] = None
    point_number: Optional[int] = None
    longitude: Optional[float] = None
    latitude: Optional[float] = None
    altitude: Optional[float] = None
    ellipsoid_height: Optional[float] = None
    geoid_height: Optional[float] = None
    fix: Optional[str] = None
    fix_mode: Optional[str] = None
    epochs: Optional[int] = None
    interval: Optional[float] = None
    pdop: Optional[float] = None
    number_of_satellites: Optional[int] = None
    std_h: Optional[float] = None
    std_v: Optional[float] = None
    signals: Optional[str] = None
    signal_frequencies: Optional[int] = None
    receiver: Optional[str] = None
    antenna: Optional[str] = None
    jgd: Optional[str] = None
    epsg: Optional[int] = None
    transformed_X: Optional[float] = None
    transformed_Y: Optional[float] = None
    office: Optional[str] = None
    branch_office: Optional[str] = None
    local_area: Optional[str] = None
    address: Optional[str] = None
    project_year: Optional[int] = None
    project_name: Optional[str] = None
    surveyor: Optional[str] = None
    label: Optional[str] = None
    point_size: Optional[int] = None
    label_cds: Optional[str] = None

    @model_validator(mode="before")
    def parse_fields(cls, values: dict[str, Any]) -> dict[str, Any]:
        """
        ## Description:
            フィールドの値を変換する。たまに数値型の場所に文字列があり、単純に変換できない場合があるのでこのメソッドを使う。
        Args:
            values(dict[str, Any]): フィールドの値
        Returns:
            dict[str, Any]: 変換後の値
        """
        # 処理したくないフィールドを避けておく
        pop_names = ["start", "end", "epsg"]
        vaults = [values.pop(field_, None) for field_ in pop_names]
        for field_name, field_value in values.items():
            field_type = cls.__annotations__.get(field_name)
            try:
                if field_value is None:
                    continue
                elif field_value == "None":
                    values[field_name] = None
                elif field_type == Optional[int]:
                    values[field_name] = int(float(field_value))
                elif field_type == Optional[float]:
                    values[field_name] = float(field_value)
                elif field_type == Optional[str]:
                    values[field_name] = str(field_value)
            except (ValueError, TypeError):
                values[field_name] = None
        # 避けておいたフィールドを戻す
        for field_name, field_value in zip(pop_names, vaults, strict=False):
            values[field_name] = field_value
        return values

    @field_validator("start", "end", mode="before")
    @classmethod
    def check_datetime(cls, value: str) -> datetime.datetime:
        """
        日時データのフォーマットをチェックし、datetime型に変換する
        Args:
            value(str): 日時データ
        Returns:
            (datetime.datetime): "YYYY-MM-DDT HH:MM:SS"形式の日時データ
        Examples:
            >>> DataModel.check_datetime('2023-11-09T10:51:42.000')
            datetime.datetime(2023, 11, 9, 10, 51, 42)
            >>> DataModel.check_datetime('2023-11-09 10:51:42')
            datetime.datetime(2023, 11, 9, 10, 51, 42)
            >>> DataModel.check_datetime('2023/11/09 10:51:42')
            datetime.datetime(2023, 11, 9, 10, 51, 42)
            >>> DataModel.check_datetime('2023/11/09 10:51')
            datetime.datetime(2023, 11, 9, 10, 51)
        """
        if isinstance(value, datetime.datetime):
            return value.replace(microsecond=0)
        elif value is None:
            return None
        try:
            try:
                return datetime.datetime.fromisoformat(value).replace(microsecond=0)
            except:
                return formatter.check_datetime_format(value)
        except:
            raise ValueError(
                f"Invalid datetime format. value: {value}, type: {type(value)}"
            )

    @field_validator("point_name", mode="before")
    @classmethod
    def check_point_name(cls, value: Union[str, float, int]) -> float:
        """
        測点名を必ずFloat型に変換する
        Args:
            value(str | float | int): 測点名
        Returns:
            (float): 測点名
        Examples:
            >>> DataModel.check_point_name('1')
            1.0
            >>> DataModel.check_point_name(1)
            1.0
            >>> DataModel.check_point_name(1.0)
            1.0
            >>> DataModel.check_point_name('BP')
            0.0
        """
        if value is None:
            return None
        try:
            value = formatter.parse_sentence_in_numeric(value)
        except:
            pass
        try:
            return float(value)
        except:
            raise ValueError(
                f"Invalid point name format. value: {value}, type: {type(value)}"
            )

    @field_validator("longitude", "latitude", mode="before")
    @classmethod
    def check_coords_by_geodetic(cls, value: float) -> float:
        return formatter.check_decimal_places_of_geodetic(value)

    @field_validator(
        MODEL_EN_FIELD_NAMES.transformed_y,
        MODEL_EN_FIELD_NAMES.transformed_x,
        mode="before",
    )
    @classmethod
    def check_coords_by_mercator(cls, value: float) -> float:
        return formatter.check_decimal_places_of_mercator(value)

    @field_validator("epsg", mode="before")
    @classmethod
    def check_epsg(cls, value: str, values) -> int:
        """
        座標系の種類をEPSGコードに変換する
        """
        if isinstance(value, int):
            return value
        jgd = values.data.get("jgd", None)
        epsg = formatter.drg_generation_converter(jgd, value)
        return epsg

    def __init__(self, **data):
        """
        データが入力されたら、最後に各種のチェックを行う
        """
        super().__init__(**data)
        self.calc_measurement_time()
        self.check_signal_frequencies()
        self.check_office()
        self.check_branch_office()
        self.check_local_area()
        self.check_address()
        self.check_project_name()
        self.make_point()

    def calc_measurement_time(self) -> None:
        """
        測定時間を計算する
        Returns:
            (None)
        Examples:
            >>> DataModel(start='2023-11-09T10:51:42.000', end='2023-11-09T11:51:42.000').measurement_time
            3600
            >>> DataModel(start='2023-11-09T10:51:42.000', end='2023-11-09T10:51:42.000').measurement_time
            0
        """
        if self.start is None or self.end is None:
            return None
        self.measurement_time = int((self.end - self.start).total_seconds()) + 1

    def check_signal_frequencies(self) -> None:
        """
        衛星信号の周波数をチェックする
        Returns:
            (None)
        Examples:
            >>> DataModel(signals='L1 E1 E5b L1OF L2OF ').signal_frequencies
            1
            >>> DataModel(signals='L1 L2 E1 E5b L1OF L2OF ').signal_frequencies
            2
            >>> DataModel(signals='L1 L2 L5 L6 E1 E5b L1OF L2OF ').signal_frequencies
            4
        """
        if self.signals is None:
            return None
        signals = list(set(self.signals.split(" ")))
        results = []
        for signal in signals:
            if signal in SIGNALS:
                results.append(signal)
        self.signal_frequencies = len(results)

    def check_office(self) -> None:
        """
        森林管理署の名称に無駄な文字が含まれている場合は削除する
        Returns:
            (None)
        Examples:
            >>> DataModel(office='青森森林管理署').office
            '青森'
            >>> DataModel(office='岩手南部').office
            '岩手南部'
            >>> DataModel(office='遠野支署').office
            '遠野'
        """
        if self.office is None:
            return None
        self.office = (
            self.office.replace("森林管理署", "")
            .replace("署", "")
            .replace("支", "")
            .replace("所", "")
        )

    def check_branch_office(self) -> None:
        """
        森林事務所の名称に無駄な文字が含まれている場合は削除する
        Returns:
            (None)
        Examples:
            >>> DataModel(branch_office='三厩担当区').branch_office
            '三厩'
            >>> DataModel(branch_office='遠野森林事務所').branch_office
            '遠野'
        """
        if self.branch_office is None:
            return None
        self.branch_office = self.branch_office.replace("森林事務所", "").replace(
            "担当区", ""
        )

    def check_local_area(self) -> None:
        """
        国有林名に無駄な文字が含まれている場合は削除する
        Returns:
            (None)
        Examples:
            >>> DataModel(local_area='国有林').local_area
            ''
            >>> DataModel(local_area='増川山国有林').local_area
            '増川山'
        """
        if self.local_area is None:
            return None
        self.local_area = self.local_area.replace("国有林", "")

    def check_address(self) -> None:
        """
        住所に全角文字が含まれている場合は半角文字に変換する
        Returns:
            (None)
        Examples:
            >>> DataModel(address='100い1').address
            '100い1'
            >>> DataModel(address='100い１').address
            '100い1'
        """
        if self.address is None:
            return None
        self.address = formatter.parse_zen2han(self.address)

    def check_project_name(self) -> None:
        if self.project_name is None:
            return None
        self.project_name = formatter.parse_zen2han(self.project_name)

    def make_point(self) -> None:
        """
        測点名を作成する
        Returns:
            (None)
        Examples:
            >>> DataModel(group_name='A', point_name=1.0).point
            'A-1'
            >>> DataModel(point_name=1.5).point
            '1.5'
            >>> DataModel(point_name='BP').point
            '0'
        """
        if self.point_name is None:
            self.point = None
            return None
        if (self.group_name is None) or (self.group_name == ""):
            group_name = ""
        else:
            group_name = f"{self.group_name}-"
        try:
            decimal, integer = math.modf(self.point_name)
            if decimal == 0:
                point_name = str(int(integer))
            else:
                point_name = str(self.point_name)
            self.point = f"{group_name}{point_name}"
        except:
            self.point = None

    def geometry(
        self,
        wkt: bool = False,
        jgd: bool = False,
        utm: bool = False,
        datum_name: str = "JGD2011",
    ) -> Union[shapely.Point, str]:
        """
        Description:
            Pointを作成する
        Args:
            wkt(bool): WKT形式で出力するかどうか
            jgd(bool): 平面直角座標系で出力するか。
            utm(bool): UTM座標系で出力するか。`utm`よりも`jgd`が優先される。
        Returns:
            shapely.Point | str: Point
        Example:
            >>> point = DataModel(longitude=140.0, latitude=40.0).point()
        """
        pnt = (self.longitude, self.latitude, self.altitude)
        if (jgd == True) and (self.epsg is not None):
            pnt = (self.transformed_Y, self.transformed_X, self.altitude)
        elif utm:
            in_crs = pyproj.CRS.from_epsg(4326).to_wkt()
            utm_crs = estimate_utm_crs(self.longitude, self.latitude, datum_name)
            xy = reproject_xy(
                xs=self.longitude, ys=self.latitude, in_crs=in_crs, out_crs=utm_crs
            )
            pnt = (xy.x, xy.y, self.altitude)
        pnt = shapely.Point(*pnt)
        if wkt:
            return pnt.wkt
        return pnt

    def calc_distance(self, model: "DataModel") -> float:
        """
        Description:
            測点間の水平距離を計算する
        Args:
            model(DataModel): 比較する測点
        Returns:
            float: 測点間の距離
        Example:
            >>> point1 = DataModel(longitude=140.0, latitude=40.0)
            >>> point2 = DataModel(longitude=141.0, latitude=41.0)
            >>> distance = point1.distance(point2)
        """
        pnt_1 = self.geometry(utm=True) if self.epsg is None else self.geometry(jgd=True)
        pnt_2 = (
            model.geometry(utm=True) if model.epsg is None else model.geometry(jgd=True)
        )
        return round(pnt_1.distance(pnt_2), 3)

    def calc_slope_distance(self, model: "DataModel") -> float:
        """
        Description:
            測点間の斜距離を計算する
        Args:
            model(DataModel): 比較する測点
        Returns:
            float: 測点間の距離
        Example:
            >>> point1 = DataModel(longitude=140.0, latitude=40.0)
            >>> point2 = DataModel(longitude=141.0, latitude=41.0)
            >>> distance = point1.calc_slope_distance(point2)
        """
        pnt_1 = self.geometry(utm=True) if self.epsg is None else self.geometry(jgd=True)
        pnt_2 = (
            model.geometry(utm=True) if model.epsg is None else model.geometry(jgd=True)
        )
        distance = pnt_1.distance(pnt_2)
        height = abs(pnt_1.z - pnt_2.z)
        return round(math.sqrt(distance**2 + height**2), 3)

    def calc_angle_deg(self, model: "DataModel") -> float:
        """
        Description:
            測点間の傾斜角を計算する
        Args:
            model(DataModel): 比較する測点
        Returns:
            float: 測点間の傾斜角
        Example:
            >>> point1 = DataModel(longitude=140.0, latitude=40.0)
            >>> point2 = DataModel(longitude=141.0, latitude=41.0)
            >>> angle = point1.calc_angle_deg(point2)
        """
        pnt_1 = self.geometry(utm=True) if self.epsg is None else self.geometry(jgd=True)
        pnt_2 = (
            model.geometry(utm=True) if model.epsg is None else model.geometry(jgd=True)
        )
        height = abs(pnt_1.z - pnt_2.z)
        distance = pnt_1.distance(pnt_2)
        theta_rad = math.atan(height / distance)
        theta_deg = math.degrees(theta_rad)
        return round(theta_deg, 2)

    def calc_azimuth_deg(self, model: "DataModel", mag: bool = True) -> float:
        """
        Description:
            測点間の方位角を計算する
        Args:
            model(DataModel):
                比較する測点
            mag(bool):
                真北を磁北に変換するかどうか。Trueの場合は、磁北に変換する。
        Returns:
            float: 測点間の方位角
        Example:
            >>> point1 = DataModel(longitude=140.0, latitude=40.0)
            >>> point2 = DataModel(longitude=141.0, latitude=41.0)
            >>> azimuth = point1.calc_azimuth_deg(point2)
        """
        g = pyproj.Geod(ellps="GRS80")
        result = g.inv(self.longitude, self.latitude, model.longitude, model.latitude)
        azimuth = result[0]
        if mag:
            delta = self.magnetic_declination()
            azimuth -= delta
        if azimuth < 0:
            azimuth += 360
        return round(azimuth, 2)

    def get_properties(self, lang: str = "en") -> Dict[str, Any]:
        """
        Description:
            プロパティを取得する。プロパティはGeoJSONライクなデータに変換するため
            に使用されが、datetime型のデータは文字列に変換される。
        Args:
            lang(str): Field名の設定. 'ja' or 'en'
        Returns:
            Dict[str, Any]: プロパティ
        """
        properties = self.__dict__
        for field_ in [MODEL_EN_FIELD_NAMES.start, MODEL_EN_FIELD_NAMES.end]:
            datetime_val = properties.get(field_, None)
            # "start"と"end"は`datetime.datetime`型なので、文字列に変換する
            if isinstance(datetime_val, datetime.datetime):
                properties[field_] = datetime_val.strftime(formatter._datetime_fmt)
        if lang == "ja":
            rename_dict = MODEL_RENAME_EN_TO_JA
            properties = {rename_dict.get(k, k): v for k, v in properties.items()}
        return properties

    def geojson_like(self, lang: str = "en") -> Dict[str, Any]:
        """
        Description:
            GeoJSONライクなデータを作成する。GeoJSOn
            RFC7946により、GeoJSONの投影法はEPSG:4326に固定されたので、それに従
            っている。
        Args:
            lang(str): Field名の設定. 'ja' or 'en'
        Returns:
            Dict[str, Any]: GeoJSONライクなデータ
        Example:
            >>> geojson = DataModel(longitude=140.0, latitude=40.0).geojson_like()
        """
        return {
            "type": "Feature",
            "geometry": shapely.geometry.mapping(self.geometry()),
            "properties": self.get_properties(lang=lang),
        }

    def kml_like_properties(self, lang: str = "en") -> fastkml.data.ExtendedData:
        """
        Description:
            KMLで使用される<ExtendedData>を作成する。
        Returns:
            fastkml.data.ExtendedData: KMLで使用される<ExtendedData>
        Example:
            >>> kml = DataModel(longitude=140.0, latitude=40.0).kml_like_properties()
        """
        data_list = []
        ja_keys = self.get_properties(lang="ja")
        for ja_key, (en_key, val) in zip(
            ja_keys, self.get_properties(lang="en").items(), strict=False
        ):
            if lang == "en":
                # 英語の場合は日本語のキーを削除する
                ja_key = en_key
            # fastkml.data.Data は value(str) である必要がある。
            if val is None:
                val = ""
            elif not isinstance(val, str):
                val = str(val)
            data = fastkml.data.Data(display_name=ja_key, name=en_key, value=val)
            data_list.append(data)
        return fastkml.data.ExtendedData(elements=data_list)

    def kml_like_geometry(self) -> fastkml.geometry.Point:
        """
        Description:
            KMLで使用される<Point>を作成する。
        Returns:
            fastkml.kml.Point: KMLで使用される<Point>
        """
        return fastkml.geometry.create_kml_geometry(
            extrude=False,
            altitude_mode=fastkml.geometry.AltitudeMode.clamp_to_ground,
            geometry=pygeoif.shape(self.geometry()),
        )  # type: ignore

    def kml_like_placemark(
        self, lang: str = "ja", style_url: Optional[str] = None
    ) -> fastkml.kml.Placemark:
        """
        Description:
            KMLで使用される<Placemark>を作成する。
        Returns:
            fastkml.kml.Placemark: KMLで使用される<Placemark>Object
        """
        placemark = fastkml.kml.Placemark(
            id=f"placemark_{self.project_name}",
            name=str(self.label),
            kml_geometry=self.kml_like_geometry(),
            extended_data=self.kml_like_properties(lang=lang),
        )
        if style_url:
            placemark.style_url = fastkml.styles.StyleUrl(url=f"#{style_url}")
        return placemark

    def magnetic_declination(self) -> float:
        """
        ## Description:
            測点の地磁気値偏角を取得する
        Returns:
            (float): 地磁気値偏角
        """
        mag = chiriin_drawer.magnetic_declination(self.longitude, self.latitude)
        return mag

    def __str__(self) -> str:
        properties = self.get_properties(lang="en")
        return json.dumps(properties, indent=4, ensure_ascii=False)


class DataModels(BaseModel):
    models: List[DataModel]
    sort_column: str  # SortFields.name | SortFields.number | SortFields.start
    desending: Optional[bool] = False
    datum_name: Optional[str] = "JGD2011"
    label_points: Optional[list] = None

    def __init__(self, **data):
        super().__init__(**data)
        self.reset_point_numbers()
        self.reset_point_names()
        self.sort()

    def __str__(self) -> str:
        models = {}
        for model in self.models:
            properties = model.get_properties(lang="en")
            key = properties.get(self.sort_column)
            models[key] = properties
        return json.dumps(models, indent=4, ensure_ascii=False)

    def set_office(self, office: str) -> None:
        """
        ## Description:
            測点に森林管理署を割り当てる
        Args:
            office(str): 森林管理署名
        Returns:
            None
        """
        for model in self.models:
            model.office = office

    def set_branch_office(self, branch_office: str) -> None:
        """
        ## Description:
            測点に森林事務所を割り当てる
        Args:
            branch_office(str): 森林事務所名
        Returns:
            None
        """
        for model in self.models:
            model.branch_office = branch_office

    def set_local_area(self, local_area: str) -> None:
        """
        ## Description:
            測点に国有林名を割り当てる
        Args:
            local_area(str): 国有林名
        Returns:
            None
        """
        for model in self.models:
            model.local_area = local_area

    def set_address(self, address: str) -> None:
        """
        ## Description:
            測点に住所を割り当てる
        Args:
            address(str): 住所
        Returns:
            None
        """
        for model in self.models:
            model.address = address

    def set_project_year(self, project_year: int) -> None:
        """
        ## Description:
            測点に調査年を割り当てる
        Args:
            project_year(int): 調査年
        Returns:
            None
        """
        for model in self.models:
            model.project_year = project_year

    def set_project_name(self, project_name: str) -> None:
        """
        ## Description:
            測点に調査名を割り当てる
        Args:
            project_name(str): 調査名
        Returns:
            None
        """
        for model in self.models:
            model.project_name = project_name

    def set_surveyor(self, surveyor: str) -> None:
        """
        ## Description:
            測点に測量士を割り当てる
        Args:
            surveyor(str): 測量士名
        Returns:
            None
        """
        for model in self.models:
            model.surveyor = surveyor

    def set_group_name(self, group_name: str) -> None:
        """
        ## Description:
            測点にグループ名を割り当てる
        Args:
            group_name(str): グループ名
        Returns:
            None
        """
        for model in self.models:
            model.group_name = group_name
        self.reset_point_names()

    def reset_point_numbers(self) -> None:
        """
        ## Description:
            測点番号がないものは、既にある番号の最大値に1を加えて再割り当てする。
        Args:
            None
        Returns:
            None
        """
        numbers = [model.point_number for model in self.models]
        no_numbers_idxs = [i for i, num in enumerate(numbers) if num is None]
        not_none_numbers = [num for num in numbers if num is not None]
        max_number = max(not_none_numbers) if not_none_numbers else -1
        if no_numbers_idxs:
            for i in no_numbers_idxs:
                max_number += 1
                self.models[i].point_number = max_number

    def reset_point_names(self) -> None:
        """
        ## Description:
            測点名がないものは、再割り当てする。
        Args:
            None
        Returns:
            None
        """
        numbers = [model.point_name for model in self.models]
        no_numbers_idxs = [i for i, num in enumerate(numbers) if num is None]
        not_none_numbers = [num for num in numbers if num is not None]
        max_number = max(not_none_numbers) if not_none_numbers else -1
        if no_numbers_idxs:
            for i in no_numbers_idxs:
                max_number += 1
                self.models[i].point_name = max_number
        for model in self.models:
            model.make_point()

    def sort(self) -> None:
        """
        Description:
            Listに格納されたDataModelをソートする
        Args:
            None
        Returns:
            None
        Example:
            >>> file_path = ".\\test\\point.gpx"
            >>> add_info = {'office': '青森', 'branch_office': '三厩', 'address': '100い1'}
            >>> data_models = read_drg_way_point(file_path, **add_info)
            >>> sort = SortFields.end
            >>> descending = False
            >>> datasets = DatasetsModel(models=data_models, sort_column=sort, desending=descending)
            >>> datasets.sort()
        """
        # Making dictionary. key: sort_col, value: index
        data = {}
        for i, model in enumerate(self.models):
            data[model.model_dump().get(self.sort_column)] = i
        # Sorting dictionary
        sorted_keys = sorted(data.keys(), reverse=self.desending)
        sorting_idx = [data[key] for key in sorted_keys]
        # Sorting DataModel
        sorted_models = []
        for i, idx in enumerate(sorting_idx):
            _data_model = self.models[idx]
            _data_model.sort_index = i
            sorted_models.append(_data_model)
        self.models = sorted_models

    def sort_models(self, idx_list: List[int]) -> None:
        """
        Description:
            指定したindexのDataModelをソートする
        Args:
            idx_list(List[int]): ソートするDataModelのindex.これは models の
                                長さと同じでなければならない。
        Returns:
            None
        Example:
            >>> sort_column = SortFields.start
            >>> datasets = DatasetsModel(models=data_models, sort_column=sort_column)
            >>> datasets.sort_models(idx_list=[0, 2, 1, 3])
        """
        # IndexのリストがmodelsのIndexと一致しているかチェック
        if set(idx_list) != set(range(len(self.models))):
            raise ValueError(
                "The length of idx_list must be the same as the length of models."
                "And Index must be the same value."
            )
        # 間違いなくソートされるように、idx_listをint型に変換
        idx_list = [int(idx) for idx in idx_list]
        if len(set(idx_list)) != len(idx_list):
            # 重複する値がある場合はエラー
            raise ValueError("There are duplicate values in idx_list.")

        sorted_models = []
        for i, idx in enumerate(idx_list):
            _data_model = self.models[idx]
            _data_model.sort_index = i
            sorted_models.append(_data_model)
        self.models = sorted_models

    def replacing_order(self, get: int, insert: int) -> None:
        """
        Description:
            指定したindexのDataModelを入れ替える
        Args:
            get(int): 入れ替えるDataModelのindex
            insert(int): 入れ替え先のindex
        Returns:
            None
        Example:
            >>> sort_column = SortFields.start
            >>> datasets = DatasetsModel(models=data_models, sort_column=sort_column)
            >>> datasets.replacing_order(get=10, insert5)
        """
        if get == insert:
            raise ValueError("get and insert are the same value.")
        elif len(self.models) < get or len(self.models) < insert:
            raise ValueError("get or insert is out of range.")

        get_model = self.models.pop(get)
        self.models.insert(insert, get_model)

    def delete_model(self, idx: int) -> None:
        """
        Description:
            指定したindexのDataModelを削除する
        Args:
            idx(int): 削除するDataModelのindex
        Returns:
            None
        Example:
            >>> sort_column = SortFields.start
            >>> datasets = DatasetsModel(models=data_models, sort_column=sort_column)
            >>> datasets.delete_model(idx=10)
        """
        if len(self.models) < idx:
            raise ValueError("idx is out of range.")
        self.models.pop(idx)

    def add_models(self, models: Union[DataModel, List[DataModel]]) -> None:
        """
        Description:
            DataModelを追加する
        Args:
            models(DataModel | List[DataModel]): 追加するDataModel
        Returns:
            None
        Example:
            >>> sort_column = SortFields.start
            >>> datasets = DatasetsModel(models=data_models, sort_column=sort_column)
            >>> datasets.add_models(models=[data_model])
        """
        if isinstance(models, DataModel):
            self.models.append(models)
        elif isinstance(models, list):
            self.models.extend(models)
        else:
            raise ValueError("models must be DataModel or List[DataModel].")

    def labeling(self, step: int = 5, last: bool = True, **kwargs) -> None:
        """
        Description:
            DataModelにLabelを付与する。Labelはstepごとに付与される。
        Args:
            step(int): Labelを付与する間隔
            last(bool): 最後のDataModelにLabelを付与するかどうか
            **kwargs:
                - base_size(int): Labelの基本サイズ (default: 2)
                - step_size(int): Labelの増加サイズ (default: 4)
                - first_size(int): 最初のLabelのサイズ (default: 6)
        Returns:
            None
        Example:
            >>> datasets = DatasetsModel(models=data_models, sort_column=sort_column)
            >>> datasets.labeling(step=5, last=True)
            >>> for model in datasets.models:
            >>>     print(model.label, model.point_size)
            A-1 6
                2
                2
                2
            A-5 4
        """
        base_size = kwargs.get("base_size", 2)
        step_size = kwargs.get("step_size", 4)
        first_size = kwargs.get("first_size", 6)
        # DataModelにLabelを付与する
        for i in range(len(self.models)):
            model = self.models[i]
            num = i + 1
            if num % step == 0:
                model.label = model.point
                model.point_size = step_size
            else:
                model.label = ""
                model.point_size = base_size
        # 最初のDataModelには必ずLabelを付与する
        self.models[0].label = self.models[0].point
        self.models[0].point_size = first_size

        if last:
            # 最後のDataModelにLabelを付与する
            self.models[-1].label = self.models[-1].point
            self.models[-1].point_size = step_size
        # 各ラベルを表示する座標を計算する

    def calculate_label_positions(
        self, buffer: float = 100, distance: float = 20
    ) -> list[Label]:
        """
        Description:
            各ラベルを表示する座標を計算する。座標はなるべく区画の外側になるように計算される。
        Args:
            buffer(float): バッファーの距離
            distance(float): ラベルの間隔
        Returns:
            list[Label]: ラベルの座標
                - label(str): ラベル名
                - coordinate(shapely.Point): ラベルの座標
                - size(float): ラベルのサイズ
        """
        model = self.models[0]
        if model.epsg:
            in_epsg = 4326
        else:
            in_epsg = model.epsg
        labeling = Labeling(
            labels=[model.label for model in self.models],
            points=self.points(),
            in_epsg=in_epsg,
        )
        labels = []
        for label, model in zip(
            labeling.calculate_label_positions(buffer, distance),
            self.models,
            strict=False,
        ):
            label.size = model.point_size
            labels.append(label)
        return labels

    def points(
        self, wkt: bool = False, jgd: bool = False, utm: bool = False
    ) -> Union[List[shapely.Point], List[str]]:
        """
        ## Description:
            DataModelからPointを作成する
        Args:
            wkt(bool): WKT形式で出力するかどうか
            jgd(bool): 平面直角座標系で出力するか。
            utm(bool): UTM座標系で出力するか。`utm`よりも`jgd`が優先される。
        Returns:
            List[shapely.Point] | List[str]: Pointのリスト
        Example:
            >>> datasets = DatasetsModel(models=data_models, sort_column=sort_column)
            >>> points = datasets.points()
            >>> points = datasets.points(utm=True)
        """
        # List[DataModel]からList[shapely.Point]を作成する
        points = []
        for model in self.models:
            points.append(shapely.Point(model.longitude, model.latitude))
        if (jgd == True) and (self.models[0].epsg is not None):
            X = [model.transformed_X for model in self.models]
            Y = [model.transformed_Y for model in self.models]
            points = [shapely.Point(x, y) for x, y in zip(Y, X, strict=False)]
        elif utm:
            in_crs = pyproj.CRS.from_epsg(4326).to_wkt()
            utm_crs = estimate_utm_crs(points[0].x, points[0].y, self.datum_name)
            xy = reproject_xy(
                xs=[point.x for point in points],
                ys=[point.y for point in points],
                in_crs=in_crs,
                out_crs=utm_crs,
            )
            points = [shapely.Point(x, y) for x, y in zip(xy.x, xy.y, strict=False)]
        if wkt:
            return [f"POINT({point.x} {point.y})" for point in points]
        return points

    def linestring(
        self, wkt: bool = False, jgd: bool = False, utm: bool = False
    ) -> Union[shapely.LineString, str]:
        """
        ## Description:
            DataModelからLineStringを作成する
        Args:
            wkt(bool): WKT形式で出力するかどうか
            jgd(bool): 平面直角座標系で出力するか
            utm(bool): UTM座標系で出力するか。`utm`よりも`jgd`が優先される
        Returns:
            shapely.LineString | str: LineString
        Example:
            >>> datasets = DatasetsModel(models=data_models, sort_column=sort_column)
            >>> linestrings = datasets.linestring()
            >>> linestrings = datasets.linestring(utm=True)
        """
        # List[DataModel]からList[shapely.Point]を作成する
        points = self.points(jgd=jgd, utm=utm)
        linestring = shapely.LineString(points)
        if wkt:
            return linestring.wkt
        return linestring

    def polygon(
        self, wkt: bool = False, jgd: bool = False, utm: bool = False
    ) -> Union[shapely.Polygon, str]:
        """
        ## Description:
           DataModelからPolygonを作成する
        Args:
            wkt(bool): WKT形式で出力するかどうか
            jgd(bool): 平面直角座標系で出力するか
            utm(bool): UTM座標系で出力するか。`utm`よりも`jgd`が優先される
        Returns:
            shapely.Polygon | str: Polygon
        Example:
            >>> datasets = DatasetsModel(models=data_models, sort_column=sort_column)
            >>> polygons = datasets.polygon()
            >>> polygons = datasets.polygon(utm=True)
        """
        # List[DataModel]からList[shapely.Point]を作成する
        points = self.points(jgd=jgd, utm=utm)
        polygon = shapely.Polygon(points)
        if wkt:
            return polygon.wkt
        return polygon

    def fetch_elevation_from_web(self, max_retry: int = 5, time_sleep: int = 10):
        pass

    def fetch_corrected_semidynamic_from_web(
        self, max_retry: int = 5, time_sleep: int = 10
    ):
        """
        ## Description:
            地理院APIでセミダイナミック補正を行う
        Args:

        """
        pass

    def static_property(self, lang: str = "en") -> Dict[str, Any]:
        properties = [model.get_properties() for model in self.models]
        df = pd.DataFrame(properties)
        start_time = str(pd.to_datetime(df[MODEL_EN_FIELD_NAMES.start]).min())
        end_time = str(pd.to_datetime(df[MODEL_EN_FIELD_NAMES.end]).max())
        data = {
            MODEL_EN_FIELD_NAMES.start: start_time,
            MODEL_EN_FIELD_NAMES.end: end_time,
            MODEL_EN_FIELD_NAMES.point: len(df),
            MODEL_EN_FIELD_NAMES.epochs: float(
                round(df[MODEL_EN_FIELD_NAMES.epochs].mean(), 2)
            ),
            MODEL_EN_FIELD_NAMES.interval: float(
                round(df[MODEL_EN_FIELD_NAMES.interval].mean(), 1)
            ),
            MODEL_EN_FIELD_NAMES.pdop: float(
                round(df[MODEL_EN_FIELD_NAMES.pdop].mean(), 2)
            ),
            MODEL_EN_FIELD_NAMES.number_of_satellites: float(
                round(df[MODEL_EN_FIELD_NAMES.number_of_satellites].mean(), 2)
            ),
            MODEL_EN_FIELD_NAMES.receiver: df[MODEL_EN_FIELD_NAMES.receiver].iloc[0],
            MODEL_EN_FIELD_NAMES.surveyor: df[MODEL_EN_FIELD_NAMES.surveyor].iloc[0],
            MODEL_EN_FIELD_NAMES.office: df[MODEL_EN_FIELD_NAMES.office].iloc[0],
            MODEL_EN_FIELD_NAMES.branch_office: df[
                MODEL_EN_FIELD_NAMES.branch_office
            ].iloc[0],
            MODEL_EN_FIELD_NAMES.local_area: df[MODEL_EN_FIELD_NAMES.local_area].iloc[0],
            MODEL_EN_FIELD_NAMES.address: df[MODEL_EN_FIELD_NAMES.address].iloc[0],
            MODEL_EN_FIELD_NAMES.project_year: df[MODEL_EN_FIELD_NAMES.project_year].iloc[
                0
            ],
            MODEL_EN_FIELD_NAMES.project_name: df[MODEL_EN_FIELD_NAMES.project_name].iloc[
                0
            ],
        }
        if lang == "ja":
            rename_dict = MODEL_RENAME_EN_TO_JA
            data = {rename_dict.get(k, k): v for k, v in data.items()}
        return data

    def calculate_area(self) -> float:
        """
        ## Description:
            ポリゴンの面積を計算する
        Returns:
            float: 面積(ha)
        Example:
            >>> datasets = DatasetsModel(models=data_models, sort_column=sort_column)
            >>> area = datasets.calculate_area()
        """
        if self.models[0].epsg is None:
            return round(self.polygon(utm=True).area / 10_000, 5)
        return round(self.polygon(jgd=True).area / 10_000, 5)

    def calculate_length(self) -> float:
        """
        ## Description:
            ポリゴンの長さを計算する
        Returns:
            float: 長さ(m)
        Example:
            >>> datasets = DatasetsModel(models=data_models, sort_column=sort_column)
            >>> length = datasets.calculate_length()
        """
        if self.models[0].epsg is None:
            return round(self.linestring(utm=True).length, 3)
        return round(self.linestring(jgd=True).length, 3)

    def calculate_slope_length(self) -> float:
        """
        ## Description:
            ポリゴンの斜距離を計算する
        Returns:
            float: 斜距離(m)
        Example:
            >>> datasets = DatasetsModel(models=data_models, sort_column=sort_column)
            >>> slope_length = datasets.calculate_slope_length()
        """
        length = 0
        for current, forward in zip(self.models[:-1], self.models[1:], strict=False):
            length += current.calc_slope_distance(forward)
        return round(length, 3)

    def make_discription(self, title: str = "Point Geometry") -> str:
        stats = self.static_property()
        today = datetime.datetime.now().strftime(formatter._datetime_fmt)
        txt = f"""<h3><b><font color='#191970'>{title}</font></b></h3>
----------------------------------------
森林管理署: {stats[MODEL_EN_FIELD_NAMES.office]}
森林事務所: {stats[MODEL_EN_FIELD_NAMES.branch_office]}
国有林名  : {stats[MODEL_EN_FIELD_NAMES.local_area]}
林小班    : {stats[MODEL_EN_FIELD_NAMES.address]}
----------------------------------------
測量開始              : {stats[MODEL_EN_FIELD_NAMES.start]}
測量終了              : {stats[MODEL_EN_FIELD_NAMES.end]}
測点数                : {stats[MODEL_EN_FIELD_NAMES.point]}
計測インターバル（秒）: {stats[MODEL_EN_FIELD_NAMES.interval]}
計測点数（平均）      : {stats[MODEL_EN_FIELD_NAMES.epochs]}
PDOP（平均）          : {stats[MODEL_EN_FIELD_NAMES.pdop]}
衛星数（平均）        : {stats[MODEL_EN_FIELD_NAMES.number_of_satellites]}
計測機器              : {stats[MODEL_EN_FIELD_NAMES.receiver]}
----------------------------------------
データ作成日: {today}
（一財）日本森林林業振興会
"""
        return txt

    def models_dump(self, lang: str = "ja") -> Dict[int, Any]:
        """
        ## Description:
            DataModelを辞書化する
        Args:
            None
        Returns:
            List[Dict[str, Any]]: 辞書化されたDataModel
        Example:
            >>> datasets = DatasetsModel(models=data_models, sort_column=sort_column)
            >>> data = datasets.model_dump()
        """
        models = []
        for model in self.models:
            models.append(model.get_properties(lang=lang))
        return models

    def _relative_coords(self, mag: bool = True, slope: bool = True) -> Dict[str, Any]:
        """
        ## Description:
            測点間の相対座標を計算する
        Args:
            mag(bool):
                真北を磁北に変換するかどうか。Trueの場合は、磁北に変換する。
            slope(bool):
                傾斜角を計算するかどうか。Trueの場合は、傾斜角を計算し、斜距離にする。
        Returns:
            Dict[str, Any]: 測点間の相対座標
                - name_list: 測点名のリスト
                - azimuth_list: 測点間の方位角のリスト
                - angle_list: 測点間の傾斜角のリスト
                - distance_list: 測点間の距離のリスト
        """
        pnt_names = [model.point for model in self.models]
        azimuth_list = []
        angle_list = []
        distance_list = []
        current_models = self.models
        forward_models = self.models[1:] + [self.models[0]]
        for current, forward in zip(current_models, forward_models, strict=False):
            azimuth_list.append(current.calc_azimuth_deg(forward, mag=mag))
            if slope:
                angle_list.append(current.calc_angle_deg(forward))
                distance_list.append(current.calc_slope_distance(forward))
            else:
                angle_list.append(0.0)
                distance_list.append(current.calc_distance(forward))
        return {
            "name_list": pnt_names,
            "azimuth_list": azimuth_list,
            "angle_list": angle_list,
            "distance_list": distance_list,
        }

    def models_dump_csv(self, mag: bool = True, slope: bool = True) -> str:
        """
        ## Description:
            測点間の相対座標をCSV形式で出力する
        Args:
            slope(bool): 傾斜角を計算するかどうか
        Returns:
            str: CSV形式のデータ
                - index: 測点のindex
                - name: 測点名
                - azimuth: 測点間の方位角
                - angle: 測点間の傾斜角
                - distance: 測点間の距離
        """
        cds = self._relative_coords(mag=mag, slope=slope)
        txt = "index,name,azimuth,angle,distance\n"
        zipper = zip(
            cds["name_list"],
            cds["azimuth_list"],
            cds["angle_list"],
            cds["distance_list"],
            strict=False,
        )
        for i, (name, azimuth, angle, distance) in enumerate(zipper):
            txt += f"{i},{name},{azimuth},{angle},{distance}\n"
        return txt

    def models_dump_dta(self, mag: bool = True, slope: bool = True) -> str:
        cds = self._relative_coords(mag=mag, slope=slope)
        zipper = zip(
            cds["name_list"],
            cds["azimuth_list"],
            cds["angle_list"],
            cds["distance_list"],
            strict=False,
        )
        indent = " "
        tab = " " * 2
        txt = f"{indent}0{tab}0{tab}0{tab}0{tab}\n"
        for i, (name, azimuth, angle, distance) in enumerate(zipper):
            txt += f"{indent}{i + 1}({name}){tab}{azimuth}{tab}{angle}{tab}{distance}\n"
        return txt

    def models_dump_dxf_by_point(self):
        pass

    def models_dump_dxf_by_linestring(self):
        pass

    def models_dump_dxf_by_polygon(self):
        pass

    def models_dump_geojson_by_point(self, lang="en") -> GeoJSON:
        data = {"type": "FeatureCollection", "features": []}
        for model in self.models:
            data["features"].append(model.geojson_like(lang=lang))
        return data

    def models_dump_geojson_by_linestring(self, lang="en") -> GeoJSON:
        geometry = self.linestring()
        properties = self.static_property(lang=lang)
        properties[OptionalFieldNames.length] = self.calculate_length()
        properties[OptionalFieldNames.slope_length] = self.calculate_slope_length()
        return {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": shapely.geometry.mapping(geometry),
                    "properties": properties,
                }
            ],
        }

    def models_dump_geojson_by_polygon(self, lang="en") -> GeoJSON:
        geometry = self.polygon()
        properties = self.static_property(lang=lang)
        properties[OptionalFieldNames.area] = self.calculate_area()
        properties[OptionalFieldNames.length] = self.calculate_length()
        properties[OptionalFieldNames.slope_length] = self.calculate_slope_length()
        return {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": shapely.geometry.mapping(geometry),
                    "properties": properties,
                }
            ],
        }

    @append_closed_document_style
    def models_dump_kml_by_point(
        self,
        lang: str = "ja",
        color: str = "#ff0000",
        alpha: float = 1.0,
        icon_url: Optional[str] = None,
        return_document: bool = False,
        **kwargs,
    ) -> str:
        """
        ## Description:
            KMLのオブジェクトを作成する
        Args:
            lang(str):
                言語. ja | en
            color(str):
                hex形式. 例: '#ff0000' (赤色)
            alpha(float):
                透明度. 0.0~1.0の範囲で指定する。デフォルトは1.0
            icon_url(str):
                アイコンのURL(https://kml4earth.appspot.com/icons.html)
            return_document(bool):
                kml.Document で返すか、kml.KMLで返すか
            kwargs:
                - closed_document(bool): default: False
        Returns:
            fastkml.kml.KML:
                KMLのオブジェクト. kml.to_string()で文字列に変換できる。
        Example:
            >>> datasets = DatasetsModel(models=data_models, sort_column=sort_column)
            >>> kml = datasets.models_dump_kml_by_point(lang='ja')
            >>> with open('point.kml', 'w', encoding='utf-8') as f:
            >>>     f.write(kml.to_string(prettyprint=True))
        """
        self.labeling()
        model = self.models[0]
        doc = fastkml.kml.Document(
            id="gnss_point",
            name=f"GNSS測量点 {model.office} {model.branch_office} {model.address}",
            description=self.make_discription(),
        )
        folder = fastkml.kml.Folder(
            id="gnss_point_folder",
            name=f"GNSS測量点-{model.office}/{model.branch_office}/{model.address}",
            description="GNSSによる測量点のデータ",
            isopen=False,
        )
        # KMLのスタイルを設定
        styles = self._kml_point_styles(color=color, alpha=alpha, icon_url=icon_url)
        start_style = styles.get("start")
        emphasis_style = styles.get("emphasis")
        normal_style = styles.get("normal")
        doc.append(start_style)
        doc.append(emphasis_style)
        doc.append(normal_style)
        # KMLのPlacemarkを作成
        for i, model in enumerate(self.models):
            # get style id
            if i == 0:
                style_id = start_style.id
            elif model.label != "":
                style_id = emphasis_style.id
            else:
                style_id = normal_style.id
            placemark = model.kml_like_placemark(lang=lang, style_url=style_id)
            folder.append(placemark)
        doc.append(folder)
        if return_document:
            return doc
        kml = fastkml.kml.KML()
        kml.append(doc)
        return kml

    @append_closed_document_style
    def models_dump_kml_by_linestring(
        self,
        color: str = "#ff0000",
        alpha: float = 1.0,
        width: float = 2.5,
        return_document: bool = False,
        **kwargs,
    ) -> fastkml.kml.KML:
        """ """
        model = self.models[0]
        doc = fastkml.kml.Document(
            id="gnss_line",
            name=f"GNSS測量線 {model.office} {model.branch_office} {model.address}",
            description=self.make_discription("LineString Geometry"),
        )
        folder = fastkml.kml.Folder(
            id="gnss_line_folder",
            name=f"GNSS測量線-{model.office}/{model.branch_office}/{model.address}",
            description="GNSSによる測量線のデータ",
        )
        # KMLのスタイルを設定
        style = self._kml_linestring_style(color, alpha, width)
        # KMLのPlacemarkを作成
        geometry = fastkml.geometry.create_kml_geometry(
            tessellate=True,
            altitude_mode=fastkml.enums.AltitudeMode.clamp_to_ground,
            geometry=pygeoif.shape(self.linestring()),
        )
        placemark = fastkml.kml.Placemark(
            id="gnss_line_placemark",
            name="GNSS測量線",
            kml_geometry=geometry,
            extended_data=self.static_properties_kml(),
        )
        placemark.style_url = fastkml.styles.StyleUrl(url=f"#{style.id}")
        folder.append(placemark)
        doc.append(style)
        doc.append(folder)
        if return_document:
            return doc
        kml = fastkml.kml.KML()
        kml.append(doc)
        return kml

    @append_closed_document_style
    def models_dump_kml_by_polygon(
        self,
        color: str = "#ff0000",
        alpha: float = 1.0,
        width: float = 2.5,
        return_document: bool = False,
        **kwargs,
    ) -> fastkml.kml.KML:
        """ """
        model = self.models[0]
        doc = fastkml.kml.Document(
            id="gnss_polygon",
            name=f"GNSS測量線 {model.office} {model.branch_office} {model.address}",
            description=self.make_discription("Polygon Geometry"),
        )
        folder = fastkml.kml.Folder(id="gnss_line_folder", name="GNSS測量区画")
        # KMLのスタイルを設定
        style = self._kml_poly_style(color, alpha, width)
        # KMLのPlacemarkを作成
        geometry = fastkml.geometry.create_kml_geometry(
            tessellate=True,
            altitude_mode=fastkml.enums.AltitudeMode.clamp_to_ground,
            geometry=pygeoif.shape(self.polygon()),
        )
        placemark = fastkml.kml.Placemark(
            id="gnss_poly_placemark",
            name="GNSS測量区画",
            kml_geometry=geometry,
            extended_data=self.static_properties_kml(),
        )
        placemark.style_url = fastkml.styles.StyleUrl(url=f"#{style.id}")
        folder.append(placemark)
        doc.append(style)
        doc.append(folder)
        if return_document:
            return doc
        kml = fastkml.kml.KML()
        kml.append(doc)
        return kml

    def models_dump_kmz(
        self,
        point: bool = True,
        linestring: bool = False,
        polygon: bool = True,
        **kwargs,
    ) -> str:
        kmls = []
        if point:
            pnt = self.models_dump_kml_by_point(
                lang=kwargs.get("lang", "ja"),
                color=kwargs.get("point_color", "#ff0000"),
                alpha=kwargs.get("point_alpha", 1.0),
                return_document=True,
            )
            kmls.append(pnt)
        if linestring:
            line = self.models_dump_kml_by_linestring(
                color=kwargs.get("line_color", "#ff0000"),
                alpha=kwargs.get("line_alpha", 1.0),
                width=kwargs.get("line_width", 2.5),
                return_document=True,
            )
            kmls.append(line)
        if polygon:
            poly = self.models_dump_kml_by_polygon(
                color=kwargs.get("polygon_color", "#ff0000"),
                alpha=kwargs.get("polygon_alpha", 1.0),
                return_document=True,
            )
            kmls.append(poly)
        kml = fastkml.kml.KML()
        folder = fastkml.kml.Folder(id="gnss_kmz_folder", name="GNSS測量データ")
        for k in kmls:
            folder.append(k)
        kml.append(folder)
        return self._add_closed_doc_text(kml.to_string(prettyprint=True))

    def static_properties_kml(self) -> fastkml.data.ExtendedData:
        data_list = []
        ja_data = self.static_property(lang="ja")
        ja_data["水平距離(m)"] = self.calculate_length()
        ja_data["斜距離(m)"] = self.calculate_slope_length()
        ja_data["面積(ha)"] = self.calculate_area()
        en_keys = list(self.static_property(lang="en").keys())
        en_keys += [
            OptionalFieldNames.length,
            OptionalFieldNames.slope_length,
            OptionalFieldNames.area,
        ]
        for en_key, (key, val) in zip(en_keys, ja_data.items(), strict=False):
            if val is None:
                val = ""
            elif not isinstance(val, str):
                val = str(val)
            data = fastkml.data.Data(display_name=key, name=en_key, value=val)
            data_list.append(data)
        return fastkml.data.ExtendedData(elements=data_list)

    def _kml_point_styles(
        self, color: str = "#ff0000", alpha: float = 1.0, icon_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        ## Description:
            KML-Pointのスタイルを作成する。スタイルは最初の測点が一番大きく、5で
            割り切れる測点が次に大きく、その他の測点は一番小さくなる。
        Args:
            color(str):
                hex形式. 例: '#ff0000' (赤色)
            alpha(float):
                透明度. 0.0~1.0の範囲で指定する。デフォルトは1.0
            icon_url(str):
                アイコンのURL(https://kml4earth.appspot.com/icons.html)
        """
        start_style = fastkml.styles.Style(id="start_pnt_style")
        start_style.styles.append(
            fastkml.styles.IconStyle(
                color=hex_to_abgr(color, alpha=alpha),
                scale=1.2,
                icon_href=icon_url if icon_url else GoogleIcons.placemark_circle,
            )
        )
        emphasis_style = fastkml.styles.Style(id="emphasis_pnt_style")
        emphasis_style.styles.append(
            fastkml.styles.IconStyle(
                color=hex_to_abgr(color, alpha=alpha),
                scale=0.9,
                icon_href=icon_url if icon_url else GoogleIcons.placemark_circle,
            )
        )
        normal_style = fastkml.styles.Style(id="normal_pnt_style")
        normal_style.styles.append(
            fastkml.styles.IconStyle(
                color=hex_to_abgr(color, alpha=alpha),
                scale=0.7,
                icon_href=icon_url if icon_url else GoogleIcons.placemark_circle,
            )
        )
        return {
            "start": start_style,
            "emphasis": emphasis_style,
            "normal": normal_style,
        }

    def _kml_linestring_style(
        self, color: str = "#ff0000", alpha: float = 1.0, width: float = 2.5
    ) -> fastkml.styles.Style:
        """
        ## Description:
            KML-LineStringのスタイルを作成する。
        Args:
            color(str):
                hex形式. 例: '#ff0000' (赤色)
            alpha(float):
                透明度. 0.0~1.0の範囲で指定する。デフォルトは1.0
            width(float):
                線の太さ. デフォルトは1.5
        """
        style = fastkml.styles.Style(id="line_style")
        style.styles.append(
            fastkml.styles.LineStyle(
                color=hex_to_abgr(color, alpha=alpha),
                width=width,
            )
        )
        return style

    def _kml_poly_style(
        self, color: str = "#ff0000", alpha: float = 1.0, width: float = 2.5
    ) -> fastkml.styles.Style:
        """
        ## Description:
            KML-LineStringのスタイルを作成する。
        Args:
            color(str):
                hex形式. 例: '#ff0000' (赤色)
            alpha(float):
                透明度. 0.0~1.0の範囲で指定する。デフォルトは1.0
            width(float):
                線の太さ. デフォルトは1.5
        """
        style = fastkml.styles.Style(id="poly_style")
        style.styles.append(
            fastkml.styles.PolyStyle(
                color=hex_to_abgr(color, alpha=alpha),
                fill=False,
                outline=True,
            )
        )
        style.styles.append(
            fastkml.styles.LineStyle(
                color=hex_to_abgr(color, alpha=alpha),
                width=width,
            )
        )
        return style

    def _add_closed_doc_text(self, kml_string: str) -> str:
        return kml_string.replace(
            "</Document>",
            "<Style><ListStyle><listItemType>checkHideChildren</listItemType></ListStyle></Style>\n</Document>",
        )
