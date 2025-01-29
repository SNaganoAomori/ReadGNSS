"""
** utf-8 **


"""
import datetime
from enum import Enum
import math
import os
import re
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Union
import unicodedata

from pydantic import BaseModel
from pydantic import field_validator
import yaml

from _test import TestData, Answer


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
            datetime.datetime(2023, 11, 9, 10, 51, 42)
            >>> formatter.check_datetime_format('2023-11-09 10:51:42')
            datetime.datetime(2023, 11, 9, 10, 51, 42)
            >>> formatter.check_datetime_format('2023/11/09 10:51:42')
            datetime.datetime(2023, 11, 9, 10, 51, 42)
            >>> formatter.check_datetime_format('2023/11/09 10:51')
            datetime.datetime(2023, 11, 9, 10, 51)
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
    pdop = CONFIG['columns']['selects']['pdop']
    number_of_satellites = CONFIG['columns']['selects']['number_of_satellites']
    signal_frequencies = CONFIG['columns']['selects']['signal_frequencies']


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
        return FieldSpec(
            use_columns_en=self.CONFIG['use_cols_en'],
            add_columns_en=self.CONFIG['add_cols_en'],
            org_columns=list(self._drg_wp.keys()),
            en_columns=[self._drg_wp[key]['en'] for key in self._drg_wp.keys()],
            jp_columns=[self._drg_wp[key]['jp'] for key in self._drg_wp.keys()],
            config=self._drg_wp
        )
    
    def get_gyoro_gg_csv_spec(self) -> FieldSpec:
        """
        GyroManのGGファイルの仕様を取得
        """
        return FieldSpec(
            use_columns_en=self.CONFIG['use_cols_en'],
            add_columns_en=self.CONFIG['add_cols_en'],
            org_columns=list(self._gyoro_gg_csv.keys()),
            en_columns=[self._gyoro_gg_csv[key]['en'] for key in self._gyoro_gg_csv.keys()],
            jp_columns=[self._gyoro_gg_csv[key]['jp'] for key in self._gyoro_gg_csv.keys()],
            config=self._gyoro_gg_csv
        )


class SortFields(Enum):
    start = DefaultFields.start.value
    name = DefaultFields.point_name.value
    number = DefaultFields.point_number.value


def original_data_to(dict_data: Dict[str, Any], spec: FieldSpec) -> Dict[str, Any]:
    """
    ## Description:
        データを仕様に従って変換する
    Args:
        dict_data(Dict[str, Any]): 変換前のデータ（way-pointファイルを読み込んだデータなど）
        spec(FieldSpec): 変換仕様

    Returns:
        Dict(str | Any): 変換後のデータ

    Examples:
        >>> drg = _DrgWayPoint(file_path)
        >>> datasets = drg.read_items()
        >>> spec = AppsFields().get_drg_wp_spec()
        >>> renamed_dict_data = original_data_to(datasets[0], spec)
    """
    renamed_dict = dict()
    for org_col, rename_col in zip(spec.org_columns, spec.en_columns):
        renamed_dict[rename_col] = dict_data.get(org_col, None)

    result = dict()
    for use_col in spec.use_columns_en:
        result[use_col] = renamed_dict.get(use_col, None)
    for add_col in spec.add_columns_en:
        if add_col in dict_data:
            result[add_col] = dict_data[add_col]
    return result


class DataModel(BaseModel):
    """
    GNSS測量データのモデル
    """
    sort_index: Optional[int] = None
    start: Optional[datetime.datetime] = None
    end: Optional[datetime.datetime] = None
    point: Optional[str] = None
    group_name: Optional[str] = ''
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
    signal_frequncies: Optional[int] = None
    receiver: Optional[str] = None
    antenna: Optional[str] = None
    jgd: Optional[str] = None
    epsg: Optional[int] = None
    transformed_x: Optional[float] = None
    transformed_y: Optional[float] = None
    office: Optional[str] = None
    branch_office: Optional[str] = None
    local_area: Optional[str] = None
    address: Optional[str] = None
    project_year: Optional[int] = None
    project_name: Optional[str] = None
    surveyor: Optional[str] = None
    label: Optional[str] = None
    point_size: Optional[int] = None

    @field_validator('start', 'end', mode='before')
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
            raise ValueError(f'Invalid datetime format. value: {value}, type: {type(value)}')
    
    @field_validator('point_name', mode='before')
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
            raise ValueError(f'Invalid point name format. value: {value}, type: {type(value)}')

    @field_validator('longitude', 'latitude', mode='before')
    @classmethod
    def check_coords_by_geodetic(cls, value: float) -> float:
        return formatter.check_decimal_places_of_geodetic(value)
    
    @field_validator('transformed_y', 'transformed_x', mode='before')
    @classmethod
    def check_coords_by_mercator(cls, value: float) -> float:
        return formatter.check_decimal_places_of_mercator(value)

    @field_validator('epsg', mode='before')
    @classmethod
    def check_epsg(cls, value: str, values) -> int:
        """
        座標系の種類をEPSGコードに変換する
        """
        if isinstance(value, int):
            return value
        jgd = values.data.get("jgd", None)
        epsg = formatter.drg_genaration_converter(jgd, value)
        return epsg
    
    def __init__(self, **data):
        """
        データが入力されたら、最後に各種のチェックを行う
        """
        super().__init__(**data)
        self.check_signal_frequncies()
        self.check_office()
        self.check_local_area()
        self.check_address()
        self.check_project_name()
        self.make_point()

    def check_signal_frequncies(self) -> None:
        """
        衛星信号の周波数をチェックする
        Returns:
            (None)
        Examples:
            >>> DataModel(signals='L1 E1 E5b L1OF L2OF ').signal_frequncies
            1
            >>> DataModel(signals='L1 L2 E1 E5b L1OF L2OF ').signal_frequncies
            2
            >>> DataModel(signals='L1 L2 L5 L6 E1 E5b L1OF L2OF ').signal_frequncies
            4
        """
        if self.signals is None:
            return None
        signals = self.signals.split(' ')
        referencies = CONFIG['satellites']['signals']
        results = []
        for signal in signals:
            if signal in referencies:
                results.append(signal)
        self.signal_frequncies = len(results)

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
        self.office =  (self
            .office
            .replace('森林管理署', '')
            .replace('署', '')
            .replace('支', '')
            .replace('所', '')
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
        self.local_area = self.local_area.replace('国有林', '')
    
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
        if (self.group_name is None) or (self.group_name == ''):
            group_name = ''
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



if __name__ == "__main__":
    import doctest
    doctest.run_docstring_examples(Formatter.check_datetime_format, globals())
    doctest.run_docstring_examples(Formatter.drg_genaration_converter, globals())
    doctest.run_docstring_examples(DataModel.check_datetime, globals())
    doctest.run_docstring_examples(DataModel.check_point_name, globals())
    doctest.run_docstring_examples(DataModel.check_signal_frequncies, globals())
    doctest.run_docstring_examples(DataModel.check_office, globals())
    doctest.run_docstring_examples(DataModel.check_local_area, globals())
    doctest.run_docstring_examples(DataModel.check_address, globals())
    doctest.run_docstring_examples(DataModel.make_point, globals())