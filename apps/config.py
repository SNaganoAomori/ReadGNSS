from dataclasses import dataclass
import datetime
from enum import Enum
import os
import re
from typing import Optional
from typing import Union, NamedTuple
import unicodedata

from glob import glob
import pandas as pd
from pydantic import BaseModel
from pydantic import field_validator
import shapely
import yaml

# 地磁気値（偏角）を記録したcsvファイルを読み込む
mag_df = pd.read_csv(r"./apps/user/mag_2020.csv")
mag_df["mesh_code"] = mag_df["mesh_code"].astype(int).astype(str)
MAG_DATA = {
    mesh_code: mag_value
    for mesh_code, mag_value in zip(mag_df["mesh_code"], mag_df["mag"])
}

current_dir = os.path.dirname(os.path.abspath(__file__))
config_file = os.path.join(current_dir, "user\\config.yaml")

# セミダイナミック補正のパラメーターファイル
SEMIDYNA_FILES = glob(os.path.join(current_dir, "user", "SemiDyna*.par"))


class NoLoader(yaml.SafeLoader):
    pass


def no_constructor(loader, node):
    return loader.construct_scalar(node)


NoLoader.add_constructor("tag:yaml.org,2002:bool", no_constructor)

global CONFIG
with open(config_file, "r", encoding="utf-8") as f:
    CONFIG = yaml.load(f, Loader=NoLoader)

COLORS = CONFIG["colors"]
SIGNALS = ["L1", "L2", "L5", "L6"]


class DefaultFieldNames(BaseModel):
    start: Optional[str] = None
    end: Optional[str] = None
    measurement_time: Optional[str] = None
    point_name: Optional[str] = None
    point_number: Optional[str] = None
    longitude: Optional[str] = None
    latitude: Optional[str] = None
    altitude: Optional[str] = None
    ellipsoid_height: Optional[str] = None
    geoid_height: Optional[str] = None
    fix: Optional[str] = None
    fix_mode: Optional[str] = None
    epochs: Optional[str] = None
    interval: Optional[str] = None
    pdop: Optional[str] = None
    number_of_satellites: Optional[str] = None
    std_h: Optional[str] = None
    std_v: Optional[str] = None
    signals: Optional[str] = None
    receiver: Optional[str] = None
    antenna: Optional[str] = None
    jgd: Optional[str] = None
    epsg: Optional[str] = None
    transformed_x: Optional[str] = None
    transformed_y: Optional[str] = None


class AdditionalFieldNames(BaseModel):
    sort_index: Optional[str] = None
    signal_frequencies: Optional[str] = None
    point: Optional[str] = None
    office: Optional[str] = None
    branch_office: Optional[str] = None
    local_area: Optional[str] = None
    address: Optional[str] = None
    project_year: Optional[str] = None
    project_name: Optional[str] = None
    surveyor: Optional[str] = None
    group_name: Optional[str] = None
    label: Optional[str] = None
    point_size: str


class ModelFieldNames(DefaultFieldNames, AdditionalFieldNames):
    pass


@dataclass
class OptionalFieldNames:
    area: str = "shape_area"
    length: str = "shape_length"
    slope_length: str = "slope_length"


def _get_default_field_names(
    conf=CONFIG["default"], category="drg-gps"
) -> DefaultFieldNames:
    default_keys = list(DefaultFieldNames.model_fields.keys())
    data = {}
    for key, items in conf.items():
        if key in default_keys:
            data[key] = items.get(category, None)
    return DefaultFieldNames(**data)


# **************************** Drogger-GPS ****************************
# Drogger-GPSの`way-point`に記録されている要素名
DRG_DEFAULT_FIELD_NAMES = _get_default_field_names()  # DefaultFieldNames

# Drogger-GPSから分かりやすい名前に変更したデータ(EN)
DRG_EN_FIELD_NAMES = _get_default_field_names(category="en")  # DefaultFieldNames

# Droger-GPSのオリジナル要素名から分かりやすい名前に変更する為のDict
_drg_en_field_dict = DRG_EN_FIELD_NAMES.model_dump()
DRG_RENAME_ORG_TO_EN = {
    org_name: _drg_en_field_dict.get(base_key)
    for base_key, org_name in DRG_DEFAULT_FIELD_NAMES.model_dump().items()
}  # {'org_name': 'en_name'}

# Drogger-GPSから分かりやすい名前に変更したデータ(JA)
DRG_JA_FIELD_NAMES = _get_default_field_names(category="ja")  # DefaultFieldNames


# **************************** Gyoroman-GG ****************************
# Gyoroman-GGの`csv`に記録されている要素名
GYORO_DEFAULT_FIELD_NAMES = _get_default_field_names(category="gyoroman-gg")

# Gyoroman-GGから分かりやすい名前に変更したデータ(EN)
GYORO_EN_FIELD_NAMES = _get_default_field_names(category="en")

# Gyoroman-GGのオリジナル要素名から分かりやすい名前に変更する為のDict
_gyro_en_field_dict = GYORO_EN_FIELD_NAMES.model_dump()
GYORO_RENAME_ORG_TO_EN = {
    org_name: _gyro_en_field_dict.get(base_key)
    for base_key, org_name in GYORO_DEFAULT_FIELD_NAMES.model_dump().items()
}  # {'org_name': 'en_name'}

# Gyoroman-GGから分かりやすい名前に変更したデータ(JA)
GYORO_JA_FIELD_NAMES = _get_default_field_names(category="ja")


# **********************************************************************
# ***************************** Additional *****************************
# オリジナルデータにはないが、ユーザーが追加した列名
def _get_additional_field_names(
    conf=CONFIG["default"], category="en"
) -> AdditionalFieldNames:
    additional_keys = list(AdditionalFieldNames.model_fields.keys())
    data = {}
    for key, items in conf.items():
        if key in additional_keys:
            data[key] = items[category]
    return AdditionalFieldNames(**data)


# ユーザーが追加した列名(EN)
ADDITIONAL_EN_FIELD_NAMES = _get_additional_field_names()  # AdditionalFieldNames

# ユーザーが追加した列名(JA)
ADDITIONAL_JA_FIELD_NAMES = _get_additional_field_names(
    category="ja"
)  # AdditionalFieldNames

# 使用する全ての列名（EN)
MODEL_EN_FIELD_NAMES = ModelFieldNames(
    **{**DRG_EN_FIELD_NAMES.model_dump(), **ADDITIONAL_EN_FIELD_NAMES.model_dump()}
)

# 使用する全ての列名（JA)
MODEL_JA_FIELD_NAMES = ModelFieldNames(
    **{**DRG_JA_FIELD_NAMES.model_dump(), **ADDITIONAL_JA_FIELD_NAMES.model_dump()}
)


MODEL_RENAME_EN_TO_JA = {
    en_name: ja_name
    for en_name, ja_name in zip(
        MODEL_EN_FIELD_NAMES.model_dump().values(),
        MODEL_JA_FIELD_NAMES.model_dump().values(),
    )
}

MODEL_RENAME_JP_TO_EN = {
    jp_name: en_name
    for en_name, jp_name in zip(
        MODEL_EN_FIELD_NAMES.model_dump().values(),
        MODEL_JA_FIELD_NAMES.model_dump().values(),
    )
}


class SortFields(Enum):
    end: str = MODEL_EN_FIELD_NAMES.end
    name: str = MODEL_EN_FIELD_NAMES.point_name
    number: str = MODEL_EN_FIELD_NAMES.point_number


class Formatter(object):
    def __init__(self):
        self._datetime_fmt = "%Y-%m-%d %H:%M:%S"
        self._datetime_fmts = [
            # データがこのフォーマットに合致するかチェック
            # 変換でエラーが生じた場合は、このフォーマットに新しく追加する
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M",
            "%Y-%m-%d %H:%M:%S",
            "%Y/%m/%d %H:%M:%S",
            "%Y/%m/%d %H:%M",
        ]
        self._decimal_places_mercator = 4
        self._decimal_places_geodetic = 11
        self.jgd_data = {
            "JGD2011_R": {
                "JPN1": 6669,
                "JPN2": 6670,
                "JPN3": 6671,
                "JPN4": 6672,
                "JPN5": 6673,
                "JPN6": 6674,
                "JPN7": 6675,
                "JPN8": 6676,
                "JPN9": 6677,
                "JPN10": 6678,
                "JPN11": 6679,
                "JPN12": 6680,
                "JPN13": 6681,
                "JPN14": 6682,
                "JPN15": 6683,
                "JPN16": 6684,
                "JPN17": 6685,
                "JPN18": 6686,
                "JPN19": 6687,
                "UTM51": 6688,
                "UTM52": 6689,
                "UTM53": 6690,
                "UTM54": 6691,
                "UTM55": 6692,
            }
        }

    def check_datetime_format(
        self, value: Union[str, datetime.datetime]
    ) -> datetime.datetime:
        """
        ## Description:
            日時データのフォーマットをチェックし、datetime型に変換する

        Args:
            value(str | datetime.datetime): 日時データ

        Returns:
            datetime.datetime: "YYYY-MM-DDT HH:MM:SS"形式の日時データ

        Examples:
            >>> formatter.check_datetime_format('2023-11-09T10:51:42.000')
        """
        if value is None:
            return None
        if isinstance(value, datetime.datetime):
            # datetime型であっても、指定のフォーマットに揃える
            return value.replace(microsecond=0)
        for fmt in self._datetime_fmts:
            # 設定ファイルに書いてあるフォーマットで変換
            try:
                return datetime.datetime.strptime(value, fmt).replace(microsecond=0)
            except ValueError:
                pass
        # どのフォーマットにも当てはまらない場合はエラー.
        raise ValueError(
            f"Invalid datetime format: {value}. Please use one of {self._datetime_fmts}"
        )

    def check_decimal_places_of_mercator(self, value: float) -> float:
        """
        投影座標系の座標の小数点以下の桁数を設定する
        Args:
            value(float): 座標値
        Returns:
            float: 小数点以下の桁数を設定した座標値
        """
        if value is None:
            return None
        return round(float(value), self._decimal_places_mercator)

    def check_decimal_places_of_geodetic(self, value: float) -> float:
        """
        地理座標系の座標の小数点以下の桁数を設定する
        Args:
            value(float): 座標値
        Returns:
            float: 小数点以下の桁数を設定した座標値
        """
        if value is None:
            return None
        return round(float(value), self._decimal_places_geodetic)

    def drg_generation_converter(self, crs_generation: str, crs_type: str) -> int:
        """
        ## Description:
            Drogger-GPSから出力されたway-pointファイルの座標系をEPSGコードに変換する

        Args:
            crs_generation(str): 座標系の世代(例: 'The current', 'JGD2011_R')
            crs_type(str): 座標系の種類(例: 'JPN1', 'JPN2')

        Returns:
            int: EPSGコード

        Examples:
            >>> formatter.drg_generation_converter('The current', 'JPN1')
            >>> formatter.drg_generation_converter('JGD2011_R', 'JPN1')
            6669
            >>> formatter.drg_generation_converter('JGD2000_R', 'JPN2')
        """
        if (crs_type is None) or (crs_generation is None):
            return None
        config = self.jgd_data.get(crs_generation, None)
        if config is None:
            return None
        epsg = config.get(crs_type, None)
        return epsg

    def parse_zen2han(self, sentence: str) -> str:
        """全角文字列を半角文字列に変換"""
        return unicodedata.normalize("NFKC", sentence).replace("．", ".")

    def parse_sentence_in_numeric(self, sentence: str) -> float:
        """文字列を浮動小数点数に変換"""
        sentence = self.parse_zen2han(sentence)
        numeric = re.sub(r"[^0-9\.]", "", sentence)
        if numeric == "":
            return 0.0
        else:
            return float(numeric)


formatter = Formatter()


class Web(object):
    def dummy_user_agent(self) -> str:
        """
        ## Description:
            ダミーのユーザーエージェントを取得
        """
        return {
            "User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:47.0) Gecko/20100101 Firefox/47.0"
        }

    def elevation_url(self, lon: float, lat: float) -> str:
        """
        ## Description:
            地理院APIで標高値を取得するためのURLを生成する
        """
        url = (
            "https://cyberjapandata2.gsi.go.jp/general/dem/scripts/getelevation.php?"
            "lon={lon}&lat={lat}&outtype=JSON"
        )
        return url.format(lon=lon, lat=lat)


class SemiDynamicCorrection(BaseModel):
    """
    ### Description:
            地理院のAPIで地殻変動補正を取得するためのURLを生成するクラス
    ### Args:
            correction_year(Union[int, str, datetime.datetime]): 補正年度
            longitude(float): 経度
            latitude(float): 緯度
            altitude(Optional[float]): 標高
            SOKUCHI(int): 測地系(https://vldb.gsi.go.jp/sokuchi/surveycalc/api_help.html)
            PLACE(int): 地点(https://vldb.gsi.go.jp/sokuchi/surveycalc/api_help.html)
            HOSEI_J(int): 補正情報(https://vldb.gsi.go.jp/sokuchi/surveycalc/api_help.html)
    ### Examples:
            >>> data = {
            ...     'correction_year': 2023,
            ...     'longitude': 141.304236043,
            ...     'latitude': 41.142934835,
            ... }
            >>> semidynamic = SemiDynamicCorrection(**data)
            >>> semidynamic.url
            'http://vldb.gsi.go.jp/sokuchi/surveycalc/semidyna/web/semidyna_r.php?outputType=json&chiiki=SemiDyna2023.par&sokuchi=1&Place=0&Hosei_J=2&latitude=41.142934835&longitude=141.304236043&altitude=0'
    """

    correction_year: Union[int, str, datetime.datetime]
    longitude: float
    latitude: float
    altitude: Optional[float] = 0
    SOKUCHI: int = 1
    PLACE: int = 0
    HOSEI_J: int = 2
    url: Optional[str] = None

    @field_validator("correction_year", mode="before")
    @classmethod
    def check_correction_year(cls, value: Union[int, str, datetime.datetime]) -> int:
        """
        ## Description:
            日時データを受け取り、その日時の年度を返す。補正情報は、その年度の
            4月1日から適用されるので、3月31日までのデータは、前年度の補正情報を
            取得する必要がある。
        ### Args:
            value(Union[int, str, datetime.datetime]): 日時データ
        ### Returns:
            int: 年度
        ### Examples:
            >>> SemiDynamicCorrection.check_correction_year('2023-11-09T10:51:42.000')
            2023
        """
        if isinstance(value, int):
            return value
        datetime_ = formatter.check_datetime_format(value)
        year = datetime_.year
        month = datetime_.month
        if month <= 3:
            return year - 1
        else:
            return year

    def __init__(self, **data):
        super().__init__(**data)
        self.url = self.get_correction_url()

    @property
    def param_file_name(self) -> str:
        return f"SemiDyna{self.correction_year}.par"

    def get_correction_url(self):
        url = "http://vldb.gsi.go.jp/sokuchi/surveycalc/semidyna/web/semidyna_r.php?"
        url += "outputType=json&"
        url += f"chiiki={self.param_file_name}&"
        url += f"sokuchi={self.SOKUCHI}&"
        url += f"Place={self.PLACE}&"
        url += f"Hosei_J={self.HOSEI_J}&"
        url += f"latitude={self.latitude}&"
        url += f"longitude={self.longitude}&"
        url += f"altitude={0}"
        return url


_google_icon_dir = "https://maps.google.com/mapfiles/kml/shapes/"


@dataclass
class GoogleIcons:
    placemark_circle: str = _google_icon_dir + "placemark_circle.png"
    placemark_square: str = _google_icon_dir + "placemark_square.png"


@dataclass
class Label:
    label: str
    coordinate: shapely.geometry.Point
    size: float


class MeshDesign(NamedTuple):
    name: str
    lon: float
    lat: float
    standard_mesh_code: str


class Delta(NamedTuple):
    delta_x: float
    delta_y: float
    delta_z: float
