"""
Test for ReadGNSS

Run test:
>>> pytest -v ReadGNSS/_test.py
"""
import datetime
import os
import sys
from typing import NamedTuple
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pyproj
import pytest
import shapely

from apps.geometries import estimate_utm_crs
from apps.geometries import reproject_xy
from apps.config import Formatter
from apps.config import SemiDynamicCorrection
from apps.config import SortFields
from apps.models import DataModel
from apps.models import DataModels
from apps.read_file import _DrgWayPoint
from apps.read_file import read_drg_way_point
from apps.read_file import read_gyoroman_gg2
from apps.web import Coords
from apps.web import fetch_elevation_from_web
from apps.web import fetch_corrected_semidynamic_from_web
global DIR_NAME
DIR_NAME = os.path.dirname(__file__)


"""*****************************************************************************
Test Model
*****************************************************************************"""
class _TestModel(NamedTuple):
    POINT_1_LONLAT = (140.5185138, 40.6924707)
    POINT_2_LONLAT = (137.767306, 35.681236)
    POINT_3_LONLAT = (119.691706, 35.689487)
    E_MSG_OUTSIDE_THE_SCOPE_OF_JAPAN = (
        "Specifies a longitude outside the range of Japan: Argment: "
        "{}, Range: 120 <= lon <= 160"
    )
    TEST_WAY_POINT_FILE1 = os.path.join(DIR_NAME, "data\\test_way-point.gpx")
    # 地殻変動補正補正データ
    TEST_WAY_POINT_FILE2 = os.path.join(DIR_NAME, "data\\test2_way-point.gpx")
    # 地殻変動補正未補正データ
    TEST_GYOROMAN_GG2_FILE = os.path.join(DIR_NAME, "data\\GG-2.csv")
    ADDINFO = {'office': '青森森林管理署', 'branch_office': '三厩', 
               'local_area': '増川山', 'address': '１00い1'}
    SORT_DATA = {
        'models': [DataModel(**data) for data in [
            {'point_name': 1, 'point_number': 1, 'end': '2023-11-09 10:00:00', 'group_name': 'A'},
            {'point_name': 1.1, 'point_number': 2, 'end': '2023-11-09 11:00:00', 'group_name': 'A'},
            {'point_name': 4, 'point_number': 3, 'end': '2023-11-09 12:00:00', 'group_name': 'A'},
            {'point_name': 3, 'point_number': 4, 'end': '2023-11-09 13:00:00', 'group_name': 'A'}
            ]
        ], 
        'sort_column': SortFields.number.value,
        'desending': False
    }
    POINTS = {
        'models': [DataModel(**data) for data in [
                {'point_number': 1,'longitude': 141.0, 'latitude': 40.00, 
                'epsg': 6678, 'transformed_y': 0.0, 'transformed_x': 0.1},
                {'point_number': 2,'longitude': 140.0, 'latitude': 41.00,
                'epsg': 6678, 'transformed_y': 1.0, 'transformed_x': 1.1},
                {'point_number': 3,'longitude': 139.0, 'latitude': 42.00,
                'epsg': 6678, 'transformed_y': 2.0, 'transformed_x': 2.1},
            ]
        ], 
        'sort_column': SortFields.number.value,
        'desending': False
    }
    LONLATS = {
        'models': [DataModel(**data) for data in [
                {'longitude': 141.272242456, 'latitude': 40.924881316},
                {'longitude': 139.815338, 'latitude': 34.976599},
                {'longitude': 133.893986, 'latitude': 34.324441}
            ]
        ],
        'sort_column': SortFields.number.value,
        'desending': False
    }
    NORMAL_DATA = {'sort_index': None, 'start': '2023-11-16T11:06:15.300', 'end': '2023-11-16T11:06:21.700', 'point_name': 1.0, 'point_number': 1.0, 'longitude': 141.304236043, 'latitude': 41.142934835, 'altitude': 279.1861, 'ellipsoid_height': 317.94, 'geoid_height': 38.7539, 'antenna_height': None, 'fix': 'dgps', 'fix_mode': '3D DGNSS', 'epochs': 60.0, 'interval': 1.0, 'pdop': 1.07, 'number_of_satellites': 25.0, 'std_h': 0.037, 'std_v': 0.0715, 'signals': 'L2 L1 E1 E5b B1 B2I ', 'signal_frequencies': None, 'receiver': 'DG-PRO1RWS02 ', 'antenna': None, 'jgd': 'JGD2011_R', 'epsg': 'JPN10', 'transformed_y': 39529.8801, 'transformed_x': 127012.1183}
    STRING_DATA = {'sort_index': '', 'start': '2023-11-16T11:06:15.300', 'end': '2023-11-16T11:06:21.700', 'point_name': '1.0', 'point_number': '1.0', 'longitude': '141.304236043', 'latitude': '41.142934835', 'altitude': '279.1861', 'ellipsoid_height': '317.94', 'geoid_height': '38.7539', 'antenna_height': '', 'fix': 'dgps', 'fix_mode': '3D DGNSS', 'epochs': '60.0', 'interval': '1.0', 'pdop': '1.07', 'number_of_satellites': '25.0', 'std_h': '0.037', 'std_v': '0.0715', 'signals': 'L2 L1 E1 E5b B1 B2I ', 'signal_frequencies': '', 'receiver': 'DG-PRO1RWS02 ', 'antenna': '', 'jgd': 'JGD2011_R', 'epsg': 'JPN10', 'transformed_y': '39529.8801', 'transformed_x': '127012.1183'}
    STRING_DATA_IN_NONE = {'sort_index': 'None', 'start': '2023-11-16T11:06:15.300', 'end': '2023-11-16T11:06:21.700', 'point_name': '1.0', 'point_number': '1.0', 'longitude': '141.304236043', 'latitude': '41.142934835', 'altitude': '279.1861', 'ellipsoid_height': '317.94', 'geoid_height': '38.7539', 'antenna_height': 'None', 'fix': 'dgps', 'fix_mode': '3D DGNSS', 'epochs': '60.0', 'interval': '1.0', 'pdop': '1.07', 'number_of_satellites': '25.0', 'std_h': '0.037', 'std_v': '0.0715', 'signals': 'L2 L1 E1 E5b B1 B2I ', 'signal_frequencies': 'None', 'receiver': 'DG-PRO1RWS02 ', 'antenna': 'None', 'jgd': 'JGD2011_R', 'epsg': 'JPN10', 'transformed_y': '39529.8801', 'transformed_x': '127012.1183'}


"""*****************************************************************************
test file => ./apps/geometries.py 
*****************************************************************************"""
# The test is function of 'estimate_utm_crs'.
def test_estimete_utm_crs():
    # Test for estimate_utm_crs
    wkt_crs1 = estimate_utm_crs(*_TestModel.POINT_1_LONLAT)
    epsg1 = pyproj.CRS(wkt_crs1).to_epsg()
    assert epsg1 == 6691

    wkt_crs2 = estimate_utm_crs(*_TestModel.POINT_2_LONLAT)
    epsg2 = pyproj.CRS(wkt_crs2).to_epsg()
    assert epsg2 == 6690

    EMSG = _TestModel.E_MSG_OUTSIDE_THE_SCOPE_OF_JAPAN.format(_TestModel.POINT_3_LONLAT[0])
    with pytest.raises(ValueError, match=EMSG):
        estimate_utm_crs(*_TestModel.POINT_3_LONLAT)

# The test is function of 'reproject_xy'.
def test_reproject_xy():
    # Test for reproject_xy
    LON_LIST = [_TestModel.POINT_1_LONLAT[0], _TestModel.POINT_2_LONLAT[0]]
    LAT_LIST = [_TestModel.POINT_1_LONLAT[1], _TestModel.POINT_2_LONLAT[1]]
    IN_CRS = pyproj.CRS.from_epsg(4326).to_wkt()
    OUT_CRS = pyproj.CRS.from_epsg(6678).to_wkt()
    EXPECTATION_XS = [-26607.487649235947, -277567.4749967285]
    EXPECTATION_YS = [76932.81546059267, -474973.027032275]
    xy = reproject_xy(LON_LIST, LAT_LIST, IN_CRS, OUT_CRS)
    assert xy.x == EXPECTATION_XS
    assert xy.y == EXPECTATION_YS



"""*****************************************************************************
test file => ./apps/config.py
*****************************************************************************"""
# The test is function of 'check_datetime_format' in Formatter.
def test_strptime_from_formatter():
    # Test for .apps.config.Formatter.check_datetime_format
    formatter = Formatter()
    EXPECTATION = datetime.datetime(2023, 11, 9, 10, 51, 42)
    # Format is '%Y-%m-%dT%H:%M:%S.%f'
    FMT1 = '2023-11-09T10:51:42.000'
    result1 = formatter.check_datetime_format(FMT1)
    assert result1 == EXPECTATION
    # Format is '%Y-%m-% %H:%M:%S'
    FMT2 = '2023-11-09 10:51:42'
    result2 = formatter.check_datetime_format(FMT2)
    assert result2 == EXPECTATION
    # Format is '%Y/%m/%d %H:%M:%S'
    FMT3 = '2023/11/09 10:51:42'
    result3 = formatter.check_datetime_format(FMT3)
    assert result3 == EXPECTATION
    # Format is '%Y/%m/%d %H:%M'
    FMT4 = '2023/11/09 10:51'
    result4 = formatter.check_datetime_format(FMT4)
    assert result4 == datetime.datetime(2023, 11, 9, 10, 51)

# The test is function of 'generation_converter' in Formatter.
def test_genaration_converter_from_formatter():
    # Test for .apps.config.Formatter.generation_converter
    formatter = Formatter()
    DATA1 = ('The current', 'JPN1')
    assert formatter.drg_genaration_converter(*DATA1) == None
    DATA2 = ('JGD2011_R', 'JPN1')
    assert formatter.drg_genaration_converter(*DATA2) == 6669
    DATA3 = ('JGD2011', 'JPN10')
    assert formatter.drg_genaration_converter(*DATA3) == None
    DATA4 = ('JGD2011_R', 'JPN10')
    assert formatter.drg_genaration_converter(*DATA4) == 6678
    
# The test is generating url of 'SemiDynamicCorrection'.
def test_semidynamic_url():
    # Test for .apps.config.SemiDynamicCorrection.url
    DATA = {'correction_year': 2023,'longitude': 141.304236043,
            'latitude': 41.142934835}
    semidyna = SemiDynamicCorrection(**DATA)
    EXPECTATION = (
        "http://vldb.gsi.go.jp/sokuchi/surveycalc/semidyna/web/semidyna_r.php?"
        "outputType=json&chiiki=SemiDyna{}.par&sokuchi=1&Place=0&Hosei_J=2&"
        "latitude=41.142934835&longitude=141.304236043&altitude=0"
    )
    assert semidyna.url == EXPECTATION.format(2023)
    
    DATA['correction_year'] = datetime.datetime(2023, 11, 9, 10, 51, 42)
    semidyna = SemiDynamicCorrection(**DATA)
    assert semidyna.url == EXPECTATION.format(2023)
    # 期末が3月末日なので、2022年の補正値を取得する
    DATA['correction_year'] = datetime.datetime(2023, 3, 9, 10, 51, 42)
    semidyna = SemiDynamicCorrection(**DATA)
    assert semidyna.url == EXPECTATION.format(2022)


"""*****************************************************************************
test file => ./apps/web.py
*****************************************************************************"""
# The test is function of 'fetch_elevation_from_web'.
def test_fetch_elevation_from_web():
    # Test for .apps.web.fetch_elevation_from_web
    LON = [_TestModel.POINT_1_LONLAT[0], _TestModel.POINT_2_LONLAT[0]]
    LAT = [_TestModel.POINT_1_LONLAT[1], _TestModel.POINT_2_LONLAT[1]]
    EXPECTATION = [15.5, 1658.9]
    result = fetch_elevation_from_web(LON, LAT)
    assert result == EXPECTATION

# The test is function of 'fetch_corrected_semidynamic_from_web'.
def test_fetch_corrected_semidynamic_from_web():
    # Test for .apps.web.fetch_corrected_semidynamic_from_web
    LON = [_TestModel.POINT_1_LONLAT[0], _TestModel.POINT_2_LONLAT[0]]
    LAT = [_TestModel.POINT_1_LONLAT[1], _TestModel.POINT_2_LONLAT[1]]
    EXPECTATION = [
        Coords(longitude='140.518507322', latitude='40.692475450', altitude=0.0), 
        Coords(longitude='137.767302200', latitude='35.681237147', altitude=0.0)
    ]
    assert fetch_corrected_semidynamic_from_web(2024, LON, LAT) == EXPECTATION



"""*****************************************************************************
test file => ./apps/read_file.py
*****************************************************************************"""
# The test is function of 'read_items' in _DrgWayPoint.
def test_read_xml():
    drg_xml = _DrgWayPoint(_TestModel.TEST_WAY_POINT_FILE1)
    items = drg_xml.read_items()
    item = items[0]
    assert type(item) == dict


def _read(data_models):
    assert isinstance(data_models, list)
    data_model = data_models[0]
    assert isinstance(data_model.end, datetime.datetime)
    assert isinstance(data_model.point, str)
    assert isinstance(data_model.point_name, float)
    assert data_model.longitude is not None
    assert data_model.latitude is not None
    assert data_model.office == '青森'
    assert data_model.address == '100い1'

# The test is function of 'read_drg_way_point'.
def test_read_drg_way_point():
    # Test for .apps.read_file.read_drg_way_point
    data_models = read_drg_way_point(_TestModel.TEST_WAY_POINT_FILE1, **_TestModel.ADDINFO)
    _read(data_models)
    assert data_models[0].jgd == 'The current'
    assert data_models[0].epsg == None
    data_models2 = read_drg_way_point(_TestModel.TEST_WAY_POINT_FILE2, **_TestModel.ADDINFO)
    _read(data_models2)
    assert data_models2[0].jgd == 'JGD2011_R'
    assert data_models2[0].epsg == 6678
    # 通常のデータをモデル化
    data_model = DataModel(**_TestModel.NORMAL_DATA)
    assert isinstance(data_model.point_number, int)
    # 一部数値が入る場所に空文字列が入力されたデータをモデル化
    data_model = DataModel(**_TestModel.STRING_DATA)
    assert isinstance(data_model.point_number, int)
    # Noneが'None'と文字列で入力されたデータをモデル化
    data_model = DataModel(**_TestModel.STRING_DATA_IN_NONE)
    assert data_model.sort_index == None

# The test is function of 'read_gyoroman_gg2'.
def test_read_gyoroman_gg2():
    # Test for .apps.read_file.read_gyoroman_gg2
    data_models = read_gyoroman_gg2(_TestModel.TEST_GYOROMAN_GG2_FILE, **_TestModel.ADDINFO)
    assert data_models[0].jgd == None
    assert data_models[0].epsg == None


"""*****************************************************************************
test file => ./apps/models.py
*****************************************************************************"""


# The test is function of 'check_signal_frequncies' in DataModel.
def test_check_signal_frequncies_from_data_model():
    DATA1 = {'signals': 'L1 E1 E5b B1 B2I '}
    model1 = DataModel(**DATA1)
    assert model1.signal_frequncies == 1
    DATA2 = {'signals': 'L2 L1 E1 E2 E5b B1 B2I '}
    model2 = DataModel(**DATA2)
    assert model2.signal_frequncies == 2
    DATA3 = {'signals': 'L1 L2 L5 L6 E1 E5b L1OF L2OF '}
    model3 = DataModel(**DATA3)
    assert model3.signal_frequncies == 4

# The test is function of 'check_add_info' in DataModel.
def _check_add_info(data_model):
    assert data_model.office == '青森'
    assert data_model.branch_office == '三厩'
    assert data_model.local_area == '増川山'
    assert data_model.address == '100い1'

# The test is function of `check_office` and `check_branch_office` and `check_local_area` and `check_address` in DataModel.
def test_check_office_from_data_model():
    DATA = _TestModel.ADDINFO
    _check_add_info(DataModel(**DATA))
    # 森林管理署が入力されている場合
    DATA['office'] = '青森森林管理署'
    _check_add_info(DataModel(**DATA))
    # 森林事務所が入力されている場合
    DATA['branch_office'] = '三厩森林事務所'
    _check_add_info(DataModel(**DATA))
    # 林小班が全角入力されている場合
    DATA['address'] = '１００い１'
    _check_add_info(DataModel(**DATA))

# The test is function of 'make_point' in DataModel.
# `make_point` is a merged of 'point_name' and 'group_name'.
def test_make_point_from_data_model():
    DATA1 = DataModel(**{'point_name': 1.0})
    assert DATA1.point == '1'
    DATA2 = DataModel(**{'point_name': 1.0, 'group_name': 'A'})
    assert DATA2.point == 'A-1'
    DATA3 = DataModel(**{'point_name': 1.1, 'group_name': 'A'})
    assert DATA3.point == 'A-1.1'
    DATA4 = DataModel(**{'point_name': None, 'group_name': 'A'})
    assert DATA4.point == None

# The test is function of 'geometry' in DataModel.
def test_geometry_from_data_model():
    DATA = DataModel(**{'longitude': _TestModel.POINT_1_LONLAT[0], 
                        'latitude': _TestModel.POINT_1_LONLAT[1]})
    # Test for geometry of DataModel. Geometry is a shapely.geometry.Point.
    assert DATA.geometry()
    geom = DATA.geometry()
    assert geom.x == _TestModel.POINT_1_LONLAT[0]
    assert geom.y == _TestModel.POINT_1_LONLAT[1]
    # Test for geometry of DataModel. Geometry is a WKT-Point.
    EXPECTATION = f'POINT ({_TestModel.POINT_1_LONLAT[0]} {_TestModel.POINT_1_LONLAT[1]})'
    assert DATA.geometry(wkt=True) == EXPECTATION

# The test is function of 'sort' in DataModels.
def test_sort_from_data_models():
    assert DataModels(**_TestModel.SORT_DATA)
    # Test for ascending order by 'point_number'
    dms = DataModels(**_TestModel.SORT_DATA)
    dms.sort()
    EXPECTATION = [1, 2, 3, 4]
    assert [m.point_number for m in dms.models] == EXPECTATION
    # Test for descending order by 'point_number'
    dms = DataModels(**_TestModel.SORT_DATA)
    dms.desending = True
    dms.sort()
    EXPECTATION = [4, 3, 2, 1]
    assert [m.point_number for m in dms.models] == EXPECTATION
    # Test for ascending order by 'point_name'
    dms.sort_column = SortFields.name.value
    dms.desending = False
    dms.sort()
    EXPECTATION = [1, 1.1, 3, 4]
    assert [m.point_name for m in dms.models] == EXPECTATION
    # Test for descending order by 'point_name'
    dms.sort_column = SortFields.end.value
    dms.sort()
    EXPECTATION = [1, 2, 3, 4]
    assert [m.point_number for m in dms.models] == EXPECTATION
    
# The test is function of 'sort_models' in DataModels.
def test_sort_models_from_data_models():
    # Test for decending order by index in list.
    INDEX = [0, 1, 2, 3]
    dms = DataModels(**_TestModel.SORT_DATA)
    dms.sort_models(INDEX)
    dms.sort()
    assert [m.point_number for m in dms.models] == [1, 2, 3, 4]
    # Test for ascending order by index in list.
    INDEX = [3, 2, 1, 0]
    dms = DataModels(**_TestModel.SORT_DATA)
    dms.sort_models(INDEX)
    assert [m.point_number for m in dms.models] == [4, 3, 2, 1]
    # Test for random order by index in list.
    INDEX = [2, 1, 3, 0]
    dms = DataModels(**_TestModel.SORT_DATA)
    dms.sort_models(INDEX)
    assert [m.point_number for m in dms.models] == [3, 2, 4, 1]
    # Test for the length of idx_list is not the same as the length of models.
    INDEX = [2, 1, 3, 4]
    dms = DataModels(**_TestModel.SORT_DATA)
    emsg = (
        "The length of idx_list must be the same as the length of models."
        "And Index must be the same value."
    )
    with pytest.raises(ValueError, match=emsg):
        dms.sort_models(INDEX)
    INDEX = [2, 1, 3]
    with pytest.raises(ValueError, match=emsg):
        dms.sort_models(INDEX)

# The test is function of 'replacing_order' in DataModels.
def test_replace_order_from_data_models():
    dms = DataModels(**_TestModel.SORT_DATA)
    dms.replacing_order(get=0, insert=2)
    EXPECTATION = [2, 3, 1, 4]
    assert [m.point_number for m in dms.models] == EXPECTATION
    dms.replacing_order(get=2, insert=0)
    EXPECTATION = [1, 2, 3, 4]
    assert [m.point_number for m in dms.models] == EXPECTATION

# The test is function of 'delete_model' in DataModels.
def test_delete_model_from_data_models():
    dms = DataModels(**_TestModel.SORT_DATA)
    dms.delete_model(1)
    EXPECTATION = [1, 3, 4]
    assert [m.point_number for m in dms.models] == EXPECTATION

# The test is function of 'add_models' in DataModels.
def test_add_models_from_data_models():
    dms = DataModels(**_TestModel.SORT_DATA)
    dms.sort_column = SortFields.name.value
    dms.sort()
    ADD_DATA = [
        DataModel(**{'point_name': 5, 'point_number': 5, 'end': '2023-11-09 14:00:00'}),
        DataModel(**{'point_name': 1.2, 'point_number': 6, 'end': '2023-11-09 15:00:00'})
    ]
    dms.add_models(ADD_DATA)
    print([m.point_number for m in dms.models])
    EXPECTATION = [1, 2, 4, 3, 5, 6]
    assert [m.point_number for m in dms.models] == EXPECTATION
    dms.sort()
    EXPECTATION = [1, 2, 6, 4, 3, 5]
    assert [m.point_number for m in dms.models] == EXPECTATION

# The test is function of 'labeling' in DataModels.
def test_labeling_from_data_models():
    dms = DataModels(**_TestModel.SORT_DATA)
    dms.sort_column = SortFields.name.value
    dms.sort()
    ADD_DATA = [
        DataModel(**{'point_name': 5, 'point_number': 5, 'end': '2023-11-09 14:00:00', 'group_name': 'A'}),
        DataModel(**{'point_name': 1.2, 'point_number': 6, 'end': '2023-11-09 15:00:00', 'group_name': 'A'})
    ]
    dms.add_models(ADD_DATA)
    dms.sort()
    dms.labeling()
    EXPECTATION = ['A-1', '', '', '', 'A-4', 'A-5']
    assert [m.label for m in dms.models] == EXPECTATION
    dms.labeling(last=False)
    EXPECTATION = ['A-1', '', '', '', 'A-4', '']
    assert [m.label for m in dms.models] == EXPECTATION
    dms.labeling(step=2, last=False)
    EXPECTATION = ['A-1', 'A-1.1', '', 'A-3', '', 'A-5']
    assert [m.label for m in dms.models] == EXPECTATION

# The test is function of 'points' in DataModels.
def test_points_from_data_models():
    dms = DataModels(**_TestModel.POINTS)
    points = dms.points()
    assert isinstance(points, list)
    assert isinstance(points[0], shapely.Point)
    assert points[0].x == 141.0
    points = dms.points(jgd=True)
    assert points[0].x == 0.0
    assert points[0].y == 0.1
    points = dms.points(utm=True)
    assert points[0].x == 500000.00000000215
    assert points[0].y == 4427757.218624494
    points = dms.points(utm=True, jgd=True)
    assert points[0].x == 0.0
    assert points[0].y == 0.1

# The test is function of 'linestring' in DataModels.
def test_linestring_from_data_models():
    dms = DataModels(**_TestModel.POINTS)
    line = dms.linestring()
    assert isinstance(line, shapely.LineString)
    wkt_line = dms.linestring(wkt=True)
    assert isinstance(wkt_line, str)

# The test is function of 'polygon' in DataModels.
def test_polygon_from_data_models():
    dms = DataModels(**_TestModel.POINTS)
    poly = dms.polygon()
    assert isinstance(poly, shapely.Polygon)
    wkt_poly = dms.polygon(wkt=True)
    assert isinstance(wkt_poly, str)

# The test is function of 'fetch_elevation_from_web' in DataModels.
def test_fetch_elevation_from_web_from_data_models():
    dms = DataModels(**_TestModel.LONLATS)
    elevations = dms.fetch_elevation_from_web()
    assert elevations == [84, 12.3, 4.5]

"""
# DataModel
- rename_dict_en_to_jp
- rename_dict_jp_to_en
- get_properties
- geojson_like
- kml_like

# DataModels
- fetch_corrected_semidynamic_from_web
- models_dump
- models_dump_geojson_by_point
"""