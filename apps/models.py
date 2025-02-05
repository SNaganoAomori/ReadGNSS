import datetime
import math
import time
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import TypeAlias
from typing import Union

import fastkml
from pydantic import BaseModel
from pydantic import field_validator
from pydantic import model_validator
import pyproj
import shapely

from .config import AppsFields
from .config import CONFIG
from .config import DefaultFields
from .config import formatter
from .config import FieldSpec
from .geometries import estimate_utm_crs
from .geometries import reproject_xy
from .web import fetch_elevation_from_web
from .web import Coords
from .web import fetch_corrected_semidynamic_from_web
GeoJSON: TypeAlias = Dict[str, Any]
Kml: TypeAlias = str


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
    signal_frequencies: Optional[int] = None
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

    @model_validator(mode='before')
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
        pop_names = ['start', 'end', 'epsg']
        vaults = [values.pop(field_, None) for field_ in pop_names]
        for field_name, field_value in values.items():
            field_type = cls.__annotations__.get(field_name)
            try:
                if field_value is None:
                    continue
                elif field_value == 'None':
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
        for field_name, field_value in zip(pop_names, vaults):
            values[field_name] = field_value
        return values

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
        self.check_signal_frequencies()
        self.check_office()
        self.check_branch_office()
        self.check_local_area()
        self.check_address()
        self.check_project_name()
        self.make_point()

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
        signals = list(set(self.signals.split(' ')))
        referencies = CONFIG['satellites']['signals']
        results = []
        for signal in signals:
            if signal in referencies:
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
        self.office =  (self
            .office
            .replace('森林管理署', '')
            .replace('署', '')
            .replace('支', '')
            .replace('所', '')
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
        self.branch_office = (self
            .branch_office
            .replace('森林事務所', '')
            .replace('担当区', '')
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

    def geometry(self, wkt: bool=False) -> Union[shapely.Point, str]:
        """
        Description:
            Pointを作成する
        Args:
            wkt(bool): WKT形式で出力するかどうか
        Returns:
            shapely.Point | str: Point
        Example:
            >>> point = DataModel(longitude=140.0, latitude=40.0).point()
        """
        if wkt:
            return f"POINT ({self.longitude} {self.latitude})"
        return shapely.Point(self.longitude, self.latitude)
    
    def rename_dict_en_to_jp(self) -> Dict[str, Any]:
        fields = AppsFields()
        rename_dict = {}
        for item in fields.get_drg_wp_spec().config.values():
            rename_dict[item['en']] = item['jp']
        for item in fields.get_gyoro_gg_csv_spec().config.values():
            if item['en'] not in rename_dict:
                rename_dict[item['en']] = item['jp']
        return rename_dict
    
    def rename_dict_jp_to_en(self) -> Dict[str, Any]:
        rename_dict = self.rename_dict_en_to_jp()
        return {v: k for k, v in rename_dict.items()}

    def get_properties(self, lang: str='jp') -> Dict[str, Any]:
        """
        Description:
            プロパティを取得する。プロパティはGeoJSONライクなデータに変換するため
            に使用されが、datetime型のデータは文字列に変換される。
        """
        properties = self.__dict__
        for field_ in [DefaultFields.start.value, DefaultFields.end.value]:
            datetime_val = properties.get(field_, None)
            # "start"と"end"は`datetime.datetime`型なので、文字列に変換する
            if isinstance(datetime_val, datetime.datetime):
                fmt = CONFIG['formats']['datetime_format']
                properties[field_] = datetime_val.strftime(fmt)
        if lang == 'jp':
            rename_dict = self.rename_dict_en_to_jp()
            properties = {rename_dict.get(k, k): v for k, v in properties.items()}
        return properties

    def geojson_like(self, lang: str='jp') -> Dict[str, Any]:
        """
        Description:
            GeoJSONライクなデータを作成する。GeoJSOn
            RFC7946により、GeoJSONの投影法はEPSG:4326に固定されたので、それに従
            っている。
        Args:
            lang(str): Field名の設定. 'jp' or 'en'
        Returns:
            Dict[str, Any]: GeoJSONライクなデータ
        Example:
            >>> geojson = DataModel(longitude=140.0, latitude=40.0).geojson_like()
        """
        return {
            'type': 'Feature',
            'geometry': shapely.geometry.mapping(self.geometry()),
            'properties': self.get_properties(lang=lang)
        }

    def kml_like_properties(self, lang: str='jp') -> fastkml.data.ExtendedData:
        """
        Description:
            KMLで使用される<ExtendedData>を作成する。
        Returns:
            fastkml.data.ExtendedData: KMLで使用される<ExtendedData>
        Example:
            >>> kml = DataModel(longitude=140.0, latitude=40.0).kml_like_properties()
        """
        data_list = []
        jp_keys = self.get_properties(lang='jp')
        for jp_key, (en_key, val) in zip(jp_keys, self.get_properties(lang='en').items()):
            if lang == 'en':
                # 英語の場合は日本語のキーを削除する
                jp_key = en_key
            # fastkml.data.Data は value(str) である必要がある。
            if val is None:
                val = ''
            elif not isinstance(val, str):
                val = str(val)
            data = fastkml.data.Data(display_name=jp_key, name=en_key, value=val)
            data_list.append(data)
        return fastkml.data.ExtendedData(elements=data_list)



class DataModels(BaseModel):
    models: List[DataModel]
    sort_column: str # SortFields.name.value | SortFields.number.value | SortFields.start.value
    desending: Optional[bool] = False
    datum_name: Optional[str] = 'JGD2011'

    def __init__(self, **data):
        super().__init__(**data)
        self.reassignment_point_numbers()
        self.reassignment_point_names()
        self.sort()
        

    def reassignment_point_numbers(self) -> None:
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
    
    def reassignment_point_names(self) -> None:
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
            >>> sort = SortFields.end.value
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
            >>> sort_column = SortFields.start.value
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
            >>> sort_column = SortFields.start.value
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
            >>> sort_column = SortFields.start.value
            >>> datasets = DatasetsModel(models=data_models, sort_column=sort_column)
            >>> datasets.delete_model(idx=10)
        """
        if len(self.models) < idx:
            raise ValueError("idx is out of range.")
        self.models.pop(idx)

    def add_models(self, models: Union[DataModel | List[DataModel]]) -> None:
        """
        Description:
            DataModelを追加する
        Args:
            models(DataModel | List[DataModel]): 追加するDataModel
        Returns:
            None
        Example:
            >>> sort_column = SortFields.start.value
            >>> datasets = DatasetsModel(models=data_models, sort_column=sort_column)
            >>> datasets.add_models(models=[data_model])
        """
        if isinstance(models, DataModel):
            self.models.append(models)
        elif isinstance(models, list):
            self.models.extend(models)
        else:
            raise ValueError("models must be DataModel or List[DataModel].")

    def labeling(self, step: int=5, last: bool=True, **kwargs) -> None:
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
        base_size = kwargs.get('base_size', 2)
        step_size = kwargs.get('step_size', 4)
        first_size = kwargs.get('first_size', 6)
        # DataModelにLabelを付与する
        for i in range(len(self.models)):
            model = self.models[i]
            num = i + 1
            if num % step == 0:
                model.label = model.point
                model.point_size = step_size
            else:
                model.label = ''
                model.point_size = base_size
        # 最初のDataModelには必ずLabelを付与する
        self.models[0].label = self.models[0].point
        self.models[0].point_size = first_size
    
        if last:
            # 最後のDataModelにLabelを付与する
            self.models[-1].label = self.models[-1].point
            self.models[-1].point_size = step_size
    
    def points(self, 
        wkt: bool=False,
        jgd: bool=False,
        utm: bool=False
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
            X = [model.transformed_x for model in self.models]
            Y = [model.transformed_y for model in self.models]
            points = [shapely.Point(x, y) for x, y in zip(Y, X)]
        elif utm:
            in_crs = pyproj.CRS.from_epsg(4326).to_wkt()
            utm_crs = estimate_utm_crs(points[0].x, points[0].y, self.datum_name)
            xy = reproject_xy(
                xs=[point.x for point in points],
                ys=[point.y for point in points],
                in_crs=in_crs,
                out_crs=utm_crs
            )
            points = [shapely.Point(x, y) for x, y in zip(xy.x, xy.y)]
        if wkt:
            return [f"POINT({point.x} {point.y})" for point in points]
        return points
    
    def linestring(self, 
        wkt: bool=False,
        jgd: bool=False, 
        utm: bool=False
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

    def polygon(self, 
        wkt: bool=False,
        jgd: bool=False, 
        utm: bool=False
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
        
    def fetch_elevation_from_web(self, max_retry: int=5, time_sleep: int=10) -> List[float]:
        """
        ## Description:
            地理院APIで標高値を取得する
        Args:
            max_retry(int): リトライ回数
            time_sleep(int): リトライ時の待ち時間
        Returns:
            List[float]: 標高値のリスト
        Example:
            >>> datasets = DatasetsModel(models=data_models, sort_column=sort_column)
            >>> elevations = datasets.fetch_elevation_from_web()
        """
        # 経緯度のリストを作成する
        points = self.points()
        lons = [point.x for point in points]
        lats = [point.y for point in points]
        try:
            # 地理院APIで標高値を取得する
            resps = fetch_elevation_from_web(lons, lats)
            # Noneのインデックスを取得する
            none_indices = [i for i, v in enumerate(resps) if v is None]
            retry = 0
            while True:
                if max_retry < retry:
                    break
                # 取得できなかった標高値はもう一度取得を試みる
                if none_indices:
                    lons = [lons[i] for i in none_indices]
                    lats = [lats[i] for i in none_indices]
                    resps2 = fetch_elevation_from_web(lons, lats)
                    for i, idx in enumerate(none_indices):
                        resps.pop(idx)
                        resps.insert(idx, resps2.pop(i))
                else:
                    break
                none_indices = [i for i, v in enumerate(resps) if v is None]
                if none_indices:
                    retry += 1
                    time.sleep(int(retry + time_sleep))
        except:
            resps = [None] * len(lons)
        return resps

    def fetch_corrected_semidynamic_from_web(self, 
        max_retry: int=5,
        time_sleep: int=10
    ) -> List[Coords]:
        """
        ## Description:
            地理院APIでセミダイナミック補正を行う
        Args:
            max_retry(int): リトライ回数
            time_sleep(int): リトライ時の待ち時間
        Returns:
            List[Coords]: NamedTuple(longitude: float, latitude: float, altitude: float))
        """
        points = self.points()
        correction_datetime = self.models[0].end
        lons = [point.x for point in points]
        lats = [point.y for point in points]
        try:
            resps = fetch_corrected_semidynamic_from_web(correction_datetime, lons, lats)
            none_indices = [i for i, v in enumerate(resps) if v is None]
            retry = 0
            while True:
                if max_retry < retry:
                    break
                if none_indices:
                    lons = [lons[i] for i in none_indices]
                    lats = [lats[i] for i in none_indices]
                    resps2 = fetch_corrected_semidynamic_from_web(correction_datetime, lons, lats)
                    for i, idx in enumerate(none_indices):
                        resps.pop(idx)
                        resps.insert(idx, resps2.pop(i))
                else:
                    break
                none_indices = [i for i, v in enumerate(resps) if v is None]
                if none_indices:
                    retry += 1
                    time.sleep(int(retry + time_sleep))
        except:
            resps = [None] * len(lons)
        return resps

    def models_dump(self, lang: str='jp') -> Dict[int, Any]:
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
    
    def models_dump_geojson_by_point(self, lang='en') -> GeoJSON:
        data = {
            'type': 'FeatureCollection',
            'features': []
        }
        for model in self.models:
            data['features'].append(model.geojson_like(lang=lang))
        return data
            
    def models_dump_kml_by_point(self, lang: str='en') -> Kml:
        """
        ## Description:
            DataModelをKML形式に変換する
        Args:
            lang(str): Field名の設定. 'jp' or 'en'
        Returns:
            str: KML形式のデータ
        Example:
            >>> datasets = DatasetsModel(models=data_models, sort_column=sort_column)
            >>> kml = datasets.models_dump_kml()
        """
        kml = fastkml.kml.KML()
        doc = fastkml.kml.Document(
            id='gnsspoint',
            name='',
            description='Surveying GNSS Points.'
        )
        kml.append(doc)
        folder = fastkml.kml.Folder(
            id='gnsspoint',
            name='Surveying GNSS',
            description='Surveying GNSS Points.'
        )

        








