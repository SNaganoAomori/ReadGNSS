import csv
from typing import Dict, List, Any
import unicodedata
import xml.etree.ElementTree as ET

from .models import original_data_to
from .models import DataModel
from .config import ADDITIONAL_EN_FIELD_NAMES
from .config import MODEL_EN_FIELD_NAMES
from .config import DRG_RENAME_ORG_TO_EN
from .config import GYORO_RENAME_ORG_TO_EN


class _DrgWayPoint(object):
    def __init__(self, fp: str):
        super().__init__()
        self.trees = [tree for tree in ET.parse(fp).getroot()]

    def _loop(self, tree):
        results = []
        try:
            for node in tree:
                results.append(node)
        except:
            results.append(tree)
            pass
        return results

    def _convert_float(self, value):
        try:
            val = float(value)
        except:
            return value
        else:
            return val

    def _read_coords(self, sentence: str) -> Dict:
        """
        ## Description:
            Droggerのway-pointファイルのcmtタグから座標を取り出す。
        Args:
            sentence(str): cmtタグのテキスト
        Returns:
            Dict: 座標情報
        Example:
            >>> import os
            >>> dir_name = os.path.dirname(__file__)
            >>> file_path = os.path.join(dir_name, 'test', 'test_way-point.gpx')
            >>> drg = _DrgWayPoint(file_path)
            >>> coords = drg._read_coords(TestData._DrgWayPoint__read_coords)
            >>> print(coords == Answer._DrgWayPoint__read_coords)
            True
        """
        coords = dict()
        for sent in sentence.split(" "):
            if "lon" in sent:
                coords["lon"] = float(sent.replace("lon=", ""))
            elif "lat" in sent:
                coords["lat"] = float(sent.replace("lat=", ""))
            elif "ellipsoidHeight" in sent:
                coords["ellipsoidHeight"] = float(sent.replace("ellipsoidHeight=", ""))
        return coords

    def read_items(self):
        """
        Description:
            Gpxファイルの全てのタグを読み込み、辞書化する。
        Returns:
            List[Dict[str, Any]]: 辞書化されたデータ
        Example:
            >>> import os
            >>> dir_name = os.path.dirname(__file__)
            >>> file_path = os.path.join(dir_name, 'test', 'test_way-point.gpx')
            >>> drg = _DrgWayPoint(file_path)
            >>> items = drg.read_items()
            >>> print(items[0] == Answer._DrgWayPoint__read_items)
            True
        """
        results = []
        for tree in self.trees:
            rows = []
            exts = None
            for node in tree:
                resps = self._loop(node)
                if len(resps) == 0:
                    # mainのタグ
                    rows.append(node)
                else:
                    exts = resps
            for node in exts:
                resps = self._loop(node)
                if len(resps) == 0:
                    # extensionsのタグ
                    rows.append(node)
                else:
                    # さらに深いタグ
                    rows += resps
            # まとめて辞書化
            items = dict()
            for row in rows:
                tag = str(row.tag)
                key = tag[tag.find("}") + 1 :]
                items[key] = self._convert_float(row.text)
            # cmtから座標を取り出しitemsに追加
            coors = self._read_coords(items.get("cmt"))
            coors["lon"] = float(tree.get("lon"))
            coors["lat"] = float(tree.get("lat"))
            del items["cmt"]
            items.update(coors)
            results.append(items)
        return results


def _modelling(
    items: List[Dict[str, Any]], rename_dict_by_org_to_en: Dict[str, str]
) -> List[DataModel]:
    """
    ## Description:
        データをDataModelに変換する。
    Args:
        items(List[Dict[str, Any]]): 変換するデータ。これは original_data_to()で変換されたデータ
        rename_dict_by_org_to_en(Dict[str, str]): カラム名の変換辞書. {元のカラム名: 英語のカラム名}
    Returns:
        data_models(List[DataModel]): 変換されたデータ
    Example:
        >>> drg = _DrgWayPoint(file_path)
        >>> org_data = drg.read_items()
        >>> spec =
        >>> data_models = _modelling(org_data, spec)
    """
    _data_models = []
    for data in items:
        data = original_data_to(data, rename_dict_by_org_to_en)
        if data.get(MODEL_EN_FIELD_NAMES.longitude) is None:
            # 緯度経度がないデータは無視
            continue
        data_model = DataModel(**data)
        _data_models.append(data_model)
    # まれに point_name や point_number が入力されていないデータがあるので、修正する
    data_models = []
    for i, data_model in enumerate(_data_models, start=1):
        if data_model.point_name is None:
            data_model.point_name = float(i)
        if data_model.point_number is None:
            data_model.point_number = i
        data_model.make_point()
        data_models.append(data_model)
    return data_models


"""
--------------------------------------------------------------------------------
******************* 以下はGNSS計測データの読み込み関数 *************************
新しいデータフォーマットを追加する場合は以下の手順で追加してください。
1. config.yaml の `columns` に新しいデータフォーマットのカラム名を追加。
   現在は以下のデータフォーマットに対応しています。
    - drogger_gps
    - gyoroman_gg2

   上記のデータフォーマットが変更になった場合も同じ場所で変更してください。
   `en` と `ja` のカラム名は現在登録されているカラム名と同じにしてください。
    
2. config.py の `AppsFields` に上記で作成した設定を読み込むメソッドを追加。

3. Data型が特殊で読み込み時に処理が必要な場合は、`DataModel`で validation を行うメソッドを追加。

4. 日時のフォーマットが異なる場合は、config.yaml の `[formats][datetime_formats]` 
   に新しいフォーマットを追加。

5. 最後に下に新しい関数を追加してください。
--------------------------------------------------------------------------------
"""


def read_drg_way_point(fp: str, **kwargs) -> List[DataModel]:
    """
    ## Description:
        Droggerのway-pointファイルを読み込む。
    Args:
        fp(str): ファイルパス
        **kwargs:
            - office(str): 森林管理署（例: 青森）
            - branch_office(str): 森林事務所（例: 三厩）
            - local_area(str): 国有林（例: 増川山）
            - address(str): 林小班（例: 100い1）
            - project_year(int): 事業年度（例: 2021）
            - project_name(str): 事業名（例: 青森 1-2）
            - surveyor(str): 測量者（例: 山田太郎）
            - group_name(str): 班名（例: B）
    Returns:
        List[DataModel]: モデリングされたデータ。設定は`config.py`の`DataModel`を参照
    Example:
        >>> file_path = ".\\test\\point.gpx"
        >>> add_info = {'office': '青森', 'branch_office': '三厩', 'address': '100い1'}
        >>> data_models = read_drg_way_point(file_path, **add_info)
    """
    # WayPointの読み込み
    drg = _DrgWayPoint(fp)
    # 追加情報の取得
    add_dict = dict()
    for add_col in ADDITIONAL_EN_FIELD_NAMES.model_dump().values():
        add_dict[add_col] = kwargs.get(add_col, None)
    # WayPointデータと追加情報を結合してDataModelに変換
    drg_items = [dict(**item, **add_dict) for item in drg.read_items()]
    data_models = _modelling(drg_items, DRG_RENAME_ORG_TO_EN)
    return data_models


def read_gyoroman_gg2(fp: str, **kwargs) -> List[DataModel]:
    """
    ギョロマン GG-2のCSVファイルを読み込む
    Args:
        fp(str): ファイルパス
        **kwargs:
            - office(str): 森林管理署（例: 青森）
            - branch_office(str): 森林事務所（例: 三厩）
            - local_area(str): 国有林（例: 増川山）
            - address(str): 林小班（例: 100い1）
            - project_year(int): 事業年度（例: 2021）
            - project_name(str): 事業名（例: 青森 1-2）
            - surveyor(str): 測量者（例: 山田太郎）
            - group_name(str): 班名（例: B）
    Returns:
        List[DataModel]: モデリングされたデータ。設定は`config.py`の`DataModel`を参照。
    Example:
        >>> file_path = ".\\test\\114林班GG2無線RTK_.csv"
        >>> add_info = {'office': '青森', 'branch_office': '三厩', 'address': '100い1'}
        >>> data_models = read_gyoroman_gg2(file_path, **add_info)
    """
    # CSVファイルの読み込み
    with open(fp, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = [col.replace("\ufeff", "") for col in next(reader)]
        data = [row for row in reader]
        results = []
        for row in data:
            items = dict()
            for i, key in enumerate(header):
                if "" == key:
                    pass
                else:
                    items[key] = unicodedata.normalize("NFKC", row[i])
            results.append(items)
    # 追加情報の取得
    add_dict = dict()
    for add_col in ADDITIONAL_EN_FIELD_NAMES.model_dump().values():
        add_dict[add_col] = kwargs.get(add_col, None)
    # CSVデータと追加情報を結合してDataModelに変換
    drg_items = [dict(**item, **add_dict) for item in results]
    # DataModelに変換
    data_models = _modelling(drg_items, GYORO_RENAME_ORG_TO_EN)
    return data_models
