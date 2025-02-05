"""
** utf-8 **
"""
import copy
import datetime
from enum import Enum
import os
import re
from typing import Dict
from typing import List
from typing import Optional
from typing import Union
import unicodedata

import requests
from pydantic import BaseModel
from pydantic import Field
from pydantic import field_validator
import yaml


# 1つ上の階層のディレクトリパスを取得
current_dir = os.path.dirname(os.path.abspath(__file__))
config_file_name = 'config.yaml'
config_file_path = os.path.join(current_dir, config_file_name)

"""
*.yaml の仕様で 'No' という文字列は、bool型のFalseに変換するが、データに
'No' というヘッダーがあるので、それを変換しないようにするための設定
"""
class NoLoader(yaml.SafeLoader):
    pass

def no_constructor(loader, node):
    return loader.construct_scalar(node)

NoLoader.add_constructor('tag:yaml.org,2002:bool', no_constructor)

global CONFIG
with open(config_file_path, 'r', encoding='utf-8') as f:
    CONFIG = yaml.load(f, Loader=NoLoader)

# 色設定を取得。
COLORS = CONFIG['colors']


class Formatter(object):
    def __init__(self):
        self.CONFIG = CONFIG['formats']
        self._datetime_fmt = self.CONFIG['datetime_format']
        self._datetime_fmts = self.CONFIG['datetime_formats']
        self._decimal_places_mercator = self.CONFIG['decimal_places']['mercator']
        self._decimal_places_geodetic = self.CONFIG['decimal_places']['geodetic']

    def check_datetime_format(self, value: Union[str, datetime.datetime]) -> datetime.datetime:
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
        raise ValueError(f"Invalid datetime format: {value}. Please use one of {self._datetime_fmts}")

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
    
    def drg_genaration_converter(self, crs_genaration: str, crs_type: str) -> int:
        """
        ## Description:
            Drogger-GPSから出力されたway-pointファイルの座標系をEPSGコードに変換する

        Args:
            crs_genaration(str): 座標系の世代(例: 'The current', 'JGD2011_R')
            crs_type(str): 座標系の種類(例: 'JPN1', 'JPN2')

        Returns:
            int: EPSGコード

        Examples:
            >>> formatter.drg_genaration_converter('The current', 'JPN1')
            >>> formatter.drg_genaration_converter('JGD2011_R', 'JPN1')
            6669
            >>> formatter.drg_genaration_converter('JGD2000_R', 'JPN2')
        """
        if (crs_type is None) or (crs_genaration is None):
            return None
        config = CONFIG['spatial_coordinates_system'].get(crs_genaration, None)
        if config is None:
            return None
        epsg = config.get(crs_type, None)
        if config is None:
            raise ValueError(
                f"Invalid value: {crs_type}. Please use one of"
                 f" {list(CONFIG['spatial_coordinates_system'][crs_genaration].keys())}"
            )
        return epsg
        
    def parse_zen2han(self, sentence: str) -> str:
        """全角文字列を半角文字列に変換"""
        return unicodedata.normalize('NFKC', sentence).replace('．', '.')

    def parse_sentence_in_numeric(self, sentence: str) -> float:
        """文字列を浮動小数点数に変換"""
        sentence = self.parse_zen2han(sentence)
        numeric = re.sub(r'[^0-9\.]', '', sentence)
        if numeric == '':
            return 0.
        else:
            return float(numeric)

formatter = Formatter()


class FieldSpec(BaseModel):
    use_columns_en: List[str]
    add_columns_en: List[str]
    org_columns: List[str]
    en_columns: List[str]
    jp_columns: List[str]
    config: Dict[str, Dict[str, str]]


class DefaultFields(Enum):
    sort_index = CONFIG['columns']['selects']['sort_index']
    start = CONFIG['columns']['selects']['start']
    end = CONFIG['columns']['selects']['end']
    point = CONFIG['columns']['selects']['point']
    group_name = CONFIG['columns']['selects']['group_name']
    point_name = CONFIG['columns']['selects']['point_name']
    point_number = CONFIG['columns']['selects']['point_number']
    longitude = CONFIG['columns']['selects']['longitude']
    latitude = CONFIG['columns']['selects']['latitude']
    altitude = CONFIG['columns']['selects']['altitude']
    fix_mode = CONFIG['columns']['selects']['fix_mode']
    epochs = CONFIG['columns']['selects']['epochs']
    interval = CONFIG['columns']['selects']['interval']
    pdop = CONFIG['columns']['selects']['pdop']
    number_of_satellites = CONFIG['columns']['selects']['number_of_satellites']
    signals = CONFIG['columns']['selects']['signals']
    signal_frequencies = CONFIG['columns']['selects']['signal_frequencies']
    receiver = CONFIG['columns']['selects']['receiver']
    antenna = CONFIG['columns']['selects']['antenna']
    office = CONFIG['columns']['selects']['office']
    branch_office = CONFIG['columns']['selects']['branch_office']
    local_area = CONFIG['columns']['selects']['local_area']
    address = CONFIG['columns']['selects']['address']
    project_year = CONFIG['columns']['selects']['project_year']
    project_name = CONFIG['columns']['selects']['project_name']
    surveyor = CONFIG['columns']['selects']['surveyor']




class AppsFields(object):
    def __init__(self):
        self.CONFIG = CONFIG['columns']
        self._drg_wp = self.CONFIG['drogger_gps']
        self._gyoro_gg_csv = self.CONFIG['gyoroman_gg_csv']
        self.defaults = DefaultFields

    def get_drg_wp_spec(self) -> FieldSpec:
        """
        Drogger-GPSのway-pointファイルの仕様を取得
        """
        config = copy.deepcopy(self._drg_wp)
        config.update(self.CONFIG['add_cols'])
        return FieldSpec(
            use_columns_en=self.CONFIG['use_cols_en'],
            add_columns_en=list(self.CONFIG['add_cols'].keys()),
            org_columns=list(self._drg_wp.keys()),
            en_columns=[self._drg_wp[key]['en'] for key in self._drg_wp.keys()],
            jp_columns=[self._drg_wp[key]['jp'] for key in self._drg_wp.keys()],
            config=config
        )
    
    def get_gyoro_gg_csv_spec(self) -> FieldSpec:
        """
        GyroManのGGファイルの仕様を取得
        """
        config = copy.deepcopy(self._gyoro_gg_csv)
        config.update(self.CONFIG['add_cols'])
        return FieldSpec(
            use_columns_en=self.CONFIG['use_cols_en'],
            add_columns_en=list(self.CONFIG['add_cols'].keys()),
            org_columns=list(self._gyoro_gg_csv.keys()),
            en_columns=[self._gyoro_gg_csv[key]['en'] for key in self._gyoro_gg_csv.keys()],
            jp_columns=[self._gyoro_gg_csv[key]['jp'] for key in self._gyoro_gg_csv.keys()],
            config=config
        )


class SortFields(Enum):
    end = DefaultFields.end.value
    name = DefaultFields.point_name.value
    number = DefaultFields.point_number.value


class Web(object):
    def __init__(self):
        self.CONFIG = CONFIG['web']

    def dummy_user_agent(self) -> str:
        """
        ## Description:
            ダミーのユーザーエージェントを取得
        """
        return {'User-Agent': self.CONFIG['dummy']}
    
    def elevation_url(self, lon: float, lat: float) -> str:
        """
        ## Description:
            地理院APIで標高値を取得するためのURLを生成する
        """
        return self.CONFIG['elevation'].format(lon, lat)


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

    @field_validator('correction_year', mode='before')
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
        url = CONFIG['web']['semi_dynamic']
        url += f'outputType=json&'
        url += f'chiiki={self.param_file_name}&'
        url += f'sokuchi={self.SOKUCHI}&'
        url += f'Place={self.PLACE}&'
        url += f'Hosei_J={self.HOSEI_J}&'
        url += f'latitude={self.latitude}&'
        url += f'longitude={self.longitude}&'
        url += f'altitude={0}'
        return url
    