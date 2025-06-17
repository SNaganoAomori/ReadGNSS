# GNSS測量データの簡易的な後処理ツール

このパッケージは、GNSS測量データの簡易的な後処理を行うためのツールです。主に``Drogger-GPS``のアプリケーションから出力された"xxx_way-point.gpx"ファイルを処理して、国有林の測量データを管理するための情報を抽出します。

## 1. Drogger-GPS
---
### Drogger-GPSとは
Drogger-GPSは、GNSS測量データを収集するためのスマホのアプリケーションです。ユーザーは、GNSS受信機を使用して位置情報を取得し、そのデータを"xxx_way-point.gpx"形式で保存します。このツールは、GNSS測量データの後処理を簡単に行うことができます。

### GPXファイルの形式
GPXファイルは、XML形式で位置情報を記録するための標準フォーマットです。Drogger-GPSから出力されるGPXファイルには、座標やタイムスタンプなどの情報が含まれています。このツールは、GPXファイルを解析し、必要な情報を抽出して後処理を行います。

## 2. GPXファイルの読み込みとモデル化

### GPXファイルの読み込み
GPXファイルを読み込むためには``read_drg_way_point``メソッドを使用します。このメソッドは、指定されたGPXファイルを読み込み、モデル化されたデータを返します。
モデルは単点ごとの位置情報を含むリストで、各要素は以下の属性を持ちます。
- sort_index(Optional[int]): 並べ替え用のインデックス
- start(Optional[datetime.datetime]): 測定開始時間
- end(Optional[datetime.datetime]): 測定終了時間
- measurement_time(Optional[int]): 測定時間（秒）
- point(Optional[str]): ポイントの識別子
- group_name(Optional[str]): グループ名
- point_name(Optional[float]): 測点名
- point_number(Optional[int]): 測点番号
- longitude(Optional[float]): 経度（10進数度表記）
- latitude(Optional[float]): 緯度（10進数度表記）
- altitude(Optional[float]): 標高（メートル）
- ellipsoid_height(Optional[float]): 楕円体高（メートル）
- geoid_height(Optional[float]): ジオイド高（メートル）
- fix(Optional[str]): 測位の状態（例: "FIX", "FLOAT", "3D GNSS"）
- fix_mode(Optional[str]): 測位モード（例: "RTK", "DGPS"）
- epochs(Optional[int]): 測定回数
- interval(Optional[float]): 測定間隔（秒）
- pdop(Optional[float]): PDOP値
- number_of_satellites(Optional[int]): 使用衛星数
- std_h(Optional[float]): 水平標準偏差（メートル）
- std_v(Optional[float]): 垂直標準偏差（メートル）
- signals(Optional[str]): 使用された信号
- signal_frequencies(Optional[int]): 使用された信号周波数
- receiver(Optional[str]): 受信機のモデル
- antenna(Optional[str]): アンテナのモデル
- jgd(Optional[str]): JGDバージョン
- epsg(Optional[int]): EPSGコード
- transformed_X(Optional[float]): 変換後のX座標（メートル）
- transformed_Y(Optional[float]): 変換後のY座標（メートル）
- office(Optional[str]): 森林管理署名
- branch_office(Optional[str]): 森林事務所名
- local_area(Optional[str]): 国有林名
- address(Optional[str]): 林小班名
- project_year(Optional[int]): プロジェクト年
- project_name(Optional[str]): プロジェクト名
- surveyor(Optional[str]): 測量者名
- label(Optional[str]): 図面表示ラベル
- point_size(Optional[int]): 図面マーカーサイズ
- label_cds(Optional[str]): 図面表示ラベルの表示位置


```python
>>> from apps.read_drg_way_point import read_drg_way_point
>>> model_list = read_drg_way_point("path/to/your/xxx_way-point.gpx")
>>> print(type(model_list))
<class 'apps.models.DataModel'>
```

## **3. DataModel**のメソッド


### 3-1. geometry
座標を取得するためのメソッドです。
座標は、WKT形式、平面直角座標系、またはUTM座標系で取得できます。
```python
"""----- geometryメソッドの使用例 -----"""
>>> geom = model.geometry(
...     wkt = False, # WKT形式で取得するかどうか
...     jgd = False, # 平面直角座標系で取得するかどうか。
...     utm = False, # UTM座標系を推定するかどうか。
...     datum_name = "JGD2011", # 使用するデータム名（例: "JGD2011", "WGS84"）
... )
>>> print(geom)
<Point (139.123456, 35.123456)>
```

### 3-2. calc_distance
2つの``DataModel``オブジェクト間の距離を計算。
平面直角座標系の情報がない場合は、UTM座標系を推定して計算します。
```python
"""----- calc_distanceメソッドの使用例 -----"""
>>> distance = model1.calc_distance(model2)
>>> print(distance)
42.0  # 距離はメートル単位で返されます。
```

### 3-3. calc_slope_distance
2つの``DataModel``オブジェクト間の斜距離を計算。
平面直角座標系の情報がない場合は、UTM座標系を推定して計算します。

```python
"""----- calc_slope_distanceメソッドの使用例 -----"""
>>> slope_distance = model1.calc_slope_distance(model2)
>>> print(slope_distance)
42.0  # 斜距離はメートル単位で返されます。
```

### 3-4. calc_angle_deg
2つの``DataModel``オブジェクト間の傾斜角を計算。

```python
"""----- calc_angle_degメソッドの使用例 -----"""
>>> angle_deg = model1.calc_angle_deg(model2)
>>> print(angle_deg)
20.0  # 傾斜角は度単位で返されます。
```

### 3-5. calc_azimuth_deg
2つの``DataModel``オブジェクト間の方位角を計算。
```python
"""----- calc_azimuth_degメソッドの使用例-----"""
>>> azimuth_deg = model1.calc_azimuth_deg(model2)
>>> print(azimuth_deg)
180.0  # 方位角は度単位で返されます。
```

### 3-6. get_properties
プロパティはGeoJSONライクなデータに変換するために使用されが、datetime型のデータは文字列に変換される。
戻り値は、辞書形式。
"lang"引数は'ja'（日本語）または'en'（英語）を指定でき、デフォルトは'en'です。
```python
"""----- get_propertiesメソッドの使用例 -----"""
>>> properties = model.get_properties(lang="ja")
```

### 3-7. geojson_like
GeoJSONライクなデータを取得するためのメソッドです。
戻り値は、辞書形式で、"type"、"geometry"、"properties"のキーを持ちます。
"lang"引数は'ja'（日本語）または'en'（英語）を指定でき、デフォルトは'en'です。
```python
"""----- geojson_likeメソッドの使用例 -----"""
>>> geojson_data = model.geojson_like()
```

### 3-8. kml_like_placemark
KML形式のPlacemarkデータを取得するためのメソッドです。戻り値は``fastkml.features.Placemark``オブジェクトです。``fastkml.features.Placemark``には、GeometryとPropertiesが含まれており、引数としては、"lang"（'ja'または'en'）を指定できます。他にも"style_url"を指定することで、KMLのスタイルを設定できます。デフォルトでは、"style_url"はNoneです。
```python
"""----- kml_like_placemarkメソッドの使用例 -----"""
>>> placemark = model.kml_like_placemark()
```


## 4. **DataModels**オブジェクト
``DataModel``オブジェクトを結合したオブジェクトです。``DataModels``オブジェクトでは、複数の``DataModel``を一括で管理する事で、"Point"だけでなく、"LineString"や"Polygon"などのジオメトリを扱うことができます。

### 4-1. DataModelsのインスタンス化
``DataModels``オブジェクトは、``DataModel``のリストと並べ替えのための列を指定してインスタンス化します。

```python
"""----- sort_modelsメソッドの使用例 -----"""
>>> from apps.models import DataModels
>>> from apps.config import SortFields
>>> data_models = DataModels(models=[model1, model2, model3], sort_column=SortFields.name)
```


### 4-2. sort_models
``DataModels``オブジェクトを"list[int]"で指定されたインデックス順に並べ替えます。
```python
"""----- sort_modelsメソッドの使用例 -----"""
>>> data_models.sort_models([2, 0, 1])
```

### 4-3. replacing_order
"get"で指定した位置の``DataModel``を、"insert"で指定した位置に移動します。
```python
"""----- replacing_orderメソッドの使用例 -----"""
>>> data_models.replacing_order(get=1, insert=0)
```

### 4-4. delete_model
指定したインデックスの``DataModel``を削除します。
```python
"""----- delete_modelメソッドの使用例 -----"""
>>> data_models.delete_model(0)
```

### 4-5. add_models
``DataModel``を追加します。引数は、単一の``DataModel``または``DataModel``のリストを指定できます。
```python
"""----- add_modelsメソッドの使用例 -----"""
>>> data_models.add_models(model4)
>>> data_models.add_models([model5, model6])
```

### 4-6. labeling
``DataModels``オブジェクトの各``DataModel``にラベルを付けるためのメソッドです。引数"step"で指定した位置にラベルを付けます。
```python
"""----- labelingメソッドの使用例 -----"""
>>> data_models.labeling()
```


### 4-7. calculate_label_positions
ラベルの位置を計算するためのメソッドです。なるべく"Polygon"の外側にラベルを配置するように計算します。
```python
"""----- calculate_label_positionsメソッドの使用例 -----"""
>>> data_models.calculate_label_positions()
```

### 4-8. points
``shapely.Point``のリストを取得するためのメソッドです。
```python
"""----- pointsメソッドの使用例 -----"""
>>> points = data_models.points()
>>> print(points)
[<shapely.geometry.Point object at 0x...>, ...]
```

### 4-9. linestring
``shapely.LineString``を取得するためのメソッドです。
```python
"""----- linesメソッドの使用例 -----"""
>>> line = data_models.linestring()
```

### 4-10. polygon
``shapely.Polygon``を取得するためのメソッドです。
```python
"""----- polygonメソッドの使用例 -----"""
>>> polygon = data_models.polygon()
```
### 4-11. geojson_like