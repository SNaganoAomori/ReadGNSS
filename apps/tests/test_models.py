import os
import pickle
import random

import fastkml
import pytest
import shapely

from apps.config import SortFields
from apps.models import DataModel, DataModels, hex_to_abgr
from apps.read_file import read_drg_way_point

file_path = os.path.join(os.path.dirname(__file__), "data", "readed_way_point_file.pkl")
with open(file_path, "rb") as f:
    ORIGINAL_DATA_LIST = pickle.load(f)

gpx_file_path = os.path.join(
    os.path.dirname(__file__), "data", "2024_六ヶ所_1166ほ__way-point.gpx"
)
global KWARGS
KWARGS = {
    "office": "三八上北",
    "branch_office": "室ノ久保",
    "local_area": "鷹架",
    "address": "100い1",
    "project_year": 2024,
    "project_name": "三八上北1-1",
    "surveyor": "テスト太郎",
    "group_name": "",
}


@pytest.mark.parametrize(
    "hex_color, expected",
    [
        ("#FF0000", "ff0000ff"),
        ("#00FF00", "ff00ff00"),
        ("#0000FF", "ffff0000"),
    ],
)
def test_hex_to_abgr(hex_color, expected):
    """
    Test the hex_to_abgr function to ensure it correctly converts
    hex color codes to ABGR format.
    """
    # Example hex color
    result = hex_to_abgr(hex_color)
    assert isinstance(result, str)
    assert result == expected


def test_data_model():
    data_models = read_drg_way_point(fp=gpx_file_path, **KWARGS)
    assert isinstance(data_models, list)
    for data_model in data_models:
        assert isinstance(data_model, DataModel)


def test_geometry_from_data_model():
    data_model = read_drg_way_point(fp=gpx_file_path, **KWARGS)[0]
    assert isinstance(data_model, DataModel)
    # shapely.Point
    pnt = data_model.geometry
    assert isinstance(pnt(), shapely.Point)
    # WKT-like string
    assert isinstance(pnt(wkt=True), str)
    # Reprojected estimate utm crs
    assert pnt(utm=True) != pnt()


def test_calc_distance_from_data_model():
    data_models = read_drg_way_point(fp=gpx_file_path, **KWARGS)
    model1 = data_models[0]
    model2 = data_models[1]
    assert isinstance(model1, DataModel)
    assert isinstance(model2, DataModel)
    distance = model1.calc_distance(model2)
    assert isinstance(distance, float)
    assert 0.0 < distance


def test_calc_slope_distance_from_data_model():
    data_models = read_drg_way_point(fp=gpx_file_path, **KWARGS)
    model1 = data_models[0]
    model2 = data_models[1]
    assert isinstance(model1, DataModel)
    assert isinstance(model2, DataModel)
    level_distance = model1.calc_distance(model2)
    slope_distance = model1.calc_slope_distance(model2)
    assert isinstance(slope_distance, float)
    assert 0.0 < slope_distance
    assert level_distance <= slope_distance


def test_calc_angle_deg_from_data_model():
    data_models = read_drg_way_point(fp=gpx_file_path, **KWARGS)
    model1 = data_models[0]
    model2 = data_models[1]
    assert isinstance(model1, DataModel)
    assert isinstance(model2, DataModel)
    angle = model1.calc_angle_deg(model2)
    assert isinstance(angle, float)
    assert -180.0 <= angle <= 180.0


def test_calc_azimuth_deg_from_data_model():
    data_models = read_drg_way_point(fp=gpx_file_path, **KWARGS)
    model1 = data_models[0]
    model2 = data_models[1]
    assert isinstance(model1, DataModel)
    assert isinstance(model2, DataModel)
    azimuth = model1.calc_azimuth_deg(model2, mag=False)
    assert isinstance(azimuth, float)
    assert 0.0 <= azimuth < 360.0
    azimuth2 = model1.calc_azimuth_deg(model2, mag=True)
    assert azimuth != azimuth2


def test_get_properties_from_data_model():
    data_models = read_drg_way_point(fp=gpx_file_path, **KWARGS)
    model1 = data_models[0]
    assert isinstance(model1, DataModel)
    properties1 = model1.get_properties()
    assert isinstance(properties1, dict)
    properties2 = model1.get_properties(lang="ja")
    assert isinstance(properties2, dict)
    for value1, value2 in zip(properties1.values(), properties2.values(), strict=False):
        assert value1 == value2


def test_geojson_like_from_data_model():
    data_models = read_drg_way_point(fp=gpx_file_path, **KWARGS)
    model1 = data_models[0]
    assert isinstance(model1, DataModel)
    geojson_like = model1.geojson_like()
    assert isinstance(geojson_like, dict)
    assert "type" in geojson_like
    assert "geometry" in geojson_like
    assert "properties" in geojson_like


def test_kml_like_from_data_model():
    data_models = read_drg_way_point(fp=gpx_file_path, **KWARGS)
    model1 = data_models[0]
    assert isinstance(model1, DataModel)
    kml_like = model1.kml_like_properties()
    assert isinstance(kml_like, fastkml.data.ExtendedData)


def test_kml_like_geometry_from_data_model():
    data_models = read_drg_way_point(fp=gpx_file_path, **KWARGS)
    model1 = data_models[0]
    assert isinstance(model1, DataModel)
    kml_like_geometry = model1.kml_like_geometry()
    assert isinstance(kml_like_geometry, fastkml.geometry.Point)


def test_kml_like_placemark_from_data_model():
    data_models = read_drg_way_point(fp=gpx_file_path, **KWARGS)
    model1 = data_models[0]
    assert isinstance(model1, DataModel)
    placemark = model1.kml_like_placemark(style_url="#style1")
    assert isinstance(placemark, fastkml.kml.Placemark)
    assert placemark.style_url is not None
    assert placemark.kml_geometry is not None
    assert placemark.extended_data is not None


def test_data_models():
    models = read_drg_way_point(fp=gpx_file_path, **KWARGS)
    assert isinstance(models, list)
    data_models = DataModels(models=models, sort_column=SortFields.name)
    assert isinstance(data_models, DataModels)
    print(data_models)


def test_set_from_data_models():
    models = read_drg_way_point(fp=gpx_file_path, **KWARGS)
    assert isinstance(models, list)
    data_models = DataModels(models=models, sort_column=SortFields.name)
    assert isinstance(data_models, DataModels)
    # 森林管理署名の変更
    model = models[0]
    data_models.set_office("青森")
    assert data_models.models[0] != model.office
    # 森林事務所名の変更
    data_models.set_branch_office("六ヶ所")
    assert data_models.models[0] != model.branch_office
    # 地域名の変更
    data_models.set_local_area("尾駮")
    assert data_models.models[0] != model.local_area
    # 住所の変更
    data_models.set_address("1166ほ")
    assert data_models.models[0] != model.address
    # 調査年度の変更
    data_models.set_project_year(2024)
    assert data_models.models[0] != model.project_year
    # 調査名の変更
    data_models.set_project_name("三八上北1-2")
    assert data_models.models[0] != model.project_name
    # 調査員の変更
    data_models.set_surveyor("テスト次郎")
    assert data_models.models[0] != model.surveyor
    # グループ名の変更
    data_models.set_group_name("A")
    assert data_models.models[0] != model.group_name


def test_sort_models_from_data_models():
    models = read_drg_way_point(fp=gpx_file_path, **KWARGS)
    assert isinstance(models, list)
    data_models = DataModels(models=models, sort_column=SortFields.name)
    assert isinstance(data_models, DataModels)
    point_names = [model.point_name for model in data_models.models]
    sort_idxs = list(range(len(point_names)))
    random.shuffle(sort_idxs)
    data_models.sort_models(sort_idxs)
    for expected_idx, model in zip(sort_idxs, data_models.models, strict=False):
        assert model.point_name == expected_idx + 1


def test_replacing_order_from_data_models():
    models = read_drg_way_point(fp=gpx_file_path, **KWARGS)
    assert isinstance(models, list)
    data_models = DataModels(models=models, sort_column=SortFields.name)
    assert isinstance(data_models, DataModels)
    org_idxs = [model.point_name for model in data_models.models]
    data_models.replacing_order(0, 10)
    data_models.replacing_order(1, 14)
    sorted_idxs = [model.point_name for model in data_models.models]
    assert not all(
        [
            org_idx == sorted_idx
            for org_idx, sorted_idx in zip(org_idxs, sorted_idxs, strict=False)
        ]
    )


def test_delete_model_from_data_models():
    models = read_drg_way_point(fp=gpx_file_path, **KWARGS)
    assert isinstance(models, list)
    data_models = DataModels(models=models, sort_column=SortFields.name)
    assert isinstance(data_models, DataModels)
    org_len = len(data_models.models)
    next_point_name = data_models.models[1].point_name
    data_models.delete_model(0)
    assert len(data_models.models) == org_len - 1
    assert data_models.models[0].point_name == next_point_name
