import os
import sys
from typing import Optional

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pyproj
import shapely
from apps.chiriin._drawer import _ChiriinDrawer
from apps.chiriin.chiriin.config import FigureSize, Icons, PaperSize, Scope, TileUrls
from apps.chiriin.chiriin.formatter import (
    crs_formatter,
    type_checker_crs,
    type_checker_float,
)
from apps.chiriin.chiriin.geometries import (
    estimate_utm_crs,
    get_geometry_center,
    transform_geometry,
)
from apps.chiriin.chiriin.utils import dimensional_count
from matplotlib import pyplot as plt
from matplotlib.ticker import ScalarFormatter
from shapely.geometry.base import BaseGeometry

chiriin_drawer = _ChiriinDrawer()
paper_size = PaperSize()


class MapEditor(PaperSize):
    """
    ## Summary:
        地図編集用のクラス。matplotlibを使用して地図を作成し、ジオメトリを描画する。
    Args:
        geometry (BaseGeometry | list[BaseGeometry]):
            描画するジオメトリ。単一のジオメトリまたは複数のジオメトリのリストを指定できます。
        in_crs (str | int | pyproj.CRS):
            入力CRS（座標参照系）。デフォルトは"EPSG:4326"（WGS 84）。
        out_crs (Optional[str | int | pyproj.CRS]):
            出力CRS。指定しない場合は、UTM座標系を推定します。
        paper_size (str):
            使用する紙のサイズ。デフォルトは"portrait_a4"。
        **kwargs:
            - left_cm (float): 左余白の幅（センチメートル単位）。
            - right_cm (float): 右余白の幅（センチメートル単位）。
            - bottom_cm (float): 下余白の高さ（センチメートル単位）。
            - top_cm (float): 上余白の高さ（センチメートル単位）。
    Instance Attributes:
        fig (plt.Figure):
            作成されたmatplotlibのFigureオブジェクト。
        ax (plt.Axes):
            作成されたmatplotlibのAxesオブジェクト。
        fig_size (FigureSize):
            使用する紙のサイズをインチ単位で表すタプル。
        map_width (float):
            地図の幅（センチメートル単位）。この中には余白は含まれません。
        map_height (float):
            地図の高さ（センチメートル単位）。この中には余白は含まれません。
        out_crs (pyproj.CRS):
            投影する座標参照系（CRS）。地図作成の為に、座標の単位はメートルでなければなりません。
        org_geometry (BaseGeometry | list[BaseGeometry]):
            元のジオメトリ。
        metre_geometry (BaseGeometry | list[BaseGeometry]):
            メートル単位に変換されたジオメトリ。
        geom_scope (Scope):
            ジオメトリの範囲を表すScopeオブジェクト。
        valid_scales (dict[int, Scope]):
            投影可能な縮尺とその範囲を表す辞書。keyは縮尺(int)で、値は``Scope``オブジェクト。
            Scopeオブジェクトは余白を含まない地図の表示範囲を表します。
    """

    @type_checker_crs(arg_index=2, kward="in_crs")
    def __init__(
        self,
        geometry: BaseGeometry | list[BaseGeometry],
        in_crs: str | int | pyproj.CRS,
        out_crs: Optional[str | int | pyproj.CRS] = None,
        paper_size: str = "portrait_a4",
        describe_crs: bool = True,
        **kwargs,
    ):
        super().__init__()
        self._is_iterable = False
        # 指定された用紙の大きさに合わせたFigureとAxesを作成
        self.fig_size = self.get_parper_size(paper_size)
        self.fig, self.ax = self.make_sheet(paper_size)
        # 余白を設定
        self._left_cm = kwargs.get("left_cm", 1.2)
        self._right_cm = kwargs.get("right_cm", 1.2)
        self._bottom_cm = kwargs.get("bottom_cm", 2.5)
        self._top_cm = kwargs.get("top_cm", 2.0)
        self.set_margin(
            self.fig_size, self._left_cm, self._right_cm, self._bottom_cm, self._top_cm
        )
        # 実際に地図として使用する部分の幅と高さを計算
        self.map_width = round(
            self.fig_size.width * 2.54 - (self._left_cm + self._right_cm), 2
        )
        self.map_height = round(
            self.fig_size.height * 2.54 - (self._bottom_cm + self._top_cm), 2
        )
        # out_crsが指定されていない場合はUTM座標系を推定
        self.in_crs = in_crs
        if out_crs is None:
            center = get_geometry_center(geometry, in_crs=in_crs, out_crs="EPSG:4326")
            self.out_crs = estimate_utm_crs(center.x, center.y, datum_name="JGD2011")
        else:
            self.out_crs = crs_formatter(out_crs)
        assert self.out_crs.axis_info[0].unit_name == "metre", (
            "The output CRS must use metres as the unit. "
            f"Received {self.out_crs.axis_info[0].unit_name}."
        )
        # ``geometry``を"metre"単位に変換し、その範囲を取得する
        self.org_geometry = geometry
        self.metre_geometry = self._transform_geometry(
            geometry=geometry,
            in_crs=in_crs,
            out_crs=out_crs,
        )
        if self._is_iterable:
            self.geom_scope = Scope(*shapely.union_all(self.metre_geometry).bounds)
        else:
            self.geom_scope = Scope(*self.metre_geometry.bounds)
        # 地図の範囲と``geometry``の範囲から、投影可能な縮尺を計算する
        self.valid_scales = self._calc_valid_scales()
        if describe_crs:
            # CRSの種類をマップに記載
            self._describe_crs(
                self.out_crs, left_cm=1.5, bottom_cm=1.8, fontsize=7, va="top"
            )

    def make_sheet(self, size: str = "portrait_a4") -> tuple[plt.Figure, plt.Axes]:
        """
        ## Summary:
            matplotlibのFigureとAxesを作成する。
        Args:
            size (str):
                使用する紙のサイズ。
                - 'portrait_a4'
                - 'landscape_a4',
                - 'portrait_a3'
                - 'landscape_a3'
        Returns:
            tuple[plt.Figure, plt.Axes]:
                作成されたFigureとAxesのタプル。
        """
        fig_size = self.get_parper_size(size)
        # FigureとAxesを作成
        fig, ax = plt.subplots(figsize=fig_size)
        return fig, ax

    def get_parper_size(self, size: str = "portrait_a4") -> FigureSize:
        """
        ## Summary:
            印刷用紙のサイズをインチ単位で取得する。戻り値のタプルは
            (幅, 高さ)の順で、matplotlibのfigsizeで使用できる。
        Args:
            size (str):
                使用する紙のサイズ。
                - 'portrait_a4'
                - 'landscape_a4'
                - 'portrait_a3'
                - 'landscape_a3'
        Returns:
            FigureSize:
                A4用紙の縦向きのサイズを計算したタプル。
                幅と高さをmatplotlibのFigureオブジェクトとして設定できるタプル。
                - width (float): 幅（インチ単位）
                - height (float): 高さ（インチ単位）
        """
        ps = {
            "portrait_a4": paper_size.portrait_a4_size(),
            "landscape_a4": paper_size.landscape_a4_size(),
            "portrait_a3": paper_size.portrait_a3_size(),
            "landscape_a3": paper_size.landscape_a3_size(),
        }.get(size, None)
        if ps is None:
            raise ValueError(
                f"Invalid paper size: {size}. Choose from 'portrait_a4', 'lands"
                "cape_a4', 'portrait_a3', 'landscape_a3'."
            )
        return ps

    @type_checker_float(arg_index=2, kward="left_cm")
    @type_checker_float(arg_index=3, kward="right_cm")
    @type_checker_float(arg_index=4, kward="bottom_cm")
    @type_checker_float(arg_index=5, kward="top_cm")
    def set_margin(
        self,
        figsize: FigureSize,
        left_cm: float,
        right_cm: float,
        bottom_cm: float,
        top_cm: float,
    ) -> None:
        """
        ## Summary:
            用紙の余白を設定する。
        Args:
            figsize (FigureSize): matplotlibのFigureオブジェクトのサイズ。
            left_cm (float): 左余白の幅（センチメートル単位）。
            right_cm (float): 右余白の幅（センチメートル単位）。
            bottom_cm (float): 下余白の高さ（センチメートル単位）。
            top_cm (float): 上余白の高さ（センチメートル単位）。
        Returns:
            None
        """
        # センチメートルからインチに変換
        left_inch = left_cm / 2.54
        right_inch = right_cm / 2.54
        bottom_inch = bottom_cm / 2.54
        top_inch = top_cm / 2.54
        # 余白を計算
        left = left_inch / figsize.width
        right = 1 - right_inch / figsize.width
        bottom = bottom_inch / figsize.height
        top = 1 - top_inch / figsize.height
        self.fig.subplots_adjust(left=left, right=right, bottom=bottom, top=top)

    def _calc_valid_scales(self) -> dict[int, Scope]:
        """
        ## Summary:
            用紙のサイズとジオメトリの範囲から、投影可能な縮尺を計算する。
        Returns:
            dict[int, Scope]:
                投影可能な縮尺とその範囲を表す辞書。
                キーは縮尺(int)で、値は``Scope``オブジェクト。
        """
        # 100mが何センチメートルかを計算
        valid_scales = {}
        scales = []
        scales += list(range(1_000, 5_500, 500))
        scales += list(range(6_000, 11_000, 1_000))
        scales += list(range(10_000, 55_000, 5_000))
        scales += list(range(60_000, 110_000, 10_000))
        for scale in scales:
            # 1cmあたりのメートル数を計算
            unit = scale / 100.0
            # geometryの範囲を取得
            geom_width = self.geom_scope.x_max - self.geom_scope.x_min
            geom_height = self.geom_scope.y_max - self.geom_scope.y_min
            # geometry が設定された範囲に収まるかを確認
            checked_width = geom_width <= unit * self.map_width
            checked_height = geom_height <= unit * self.map_height
            if checked_width and checked_height:
                # 有効な縮尺ならば、geometry.boundsの中心を取得し、マップ範囲を計算する
                pnt = shapely.box(*self.geom_scope).centroid
                x_unit = unit * self.map_width / 2
                y_unit = unit * self.map_height / 2
                x_min = pnt.x + x_unit * -1
                x_max = pnt.x + x_unit
                y_min = pnt.y + y_unit * -1
                y_max = pnt.y + y_unit
                scope = Scope(*[round(v, 2) for v in [x_min, y_min, x_max, y_max]])
                try:
                    assert scope.x_min <= self.geom_scope.x_min
                    assert self.geom_scope.x_max <= scope.x_max
                    assert scope.y_min <= self.geom_scope.y_min
                    assert self.geom_scope.y_max <= scope.y_max
                except AssertionError:
                    # geometryの範囲が設定された範囲に収まらない場合はスキップ
                    continue
                else:
                    valid_scales[scale] = scope
        return valid_scales

    @type_checker_crs(arg_index=2, kward="in_crs")
    def _transform_geometry(
        self,
        geometry: BaseGeometry | list[BaseGeometry],
        in_crs: str | int | pyproj.CRS,
        out_crs: Optional[pyproj.CRS] = None,
        datum_name: str = "JGD2011",
    ) -> BaseGeometry | list[BaseGeometry]:
        """
        ## Summary:
            入力されたCRSから出力CRSに変換する。
        Args:
            in_crs (str | int | pyproj.CRS):
                ``geometry``のCRS。
            out_crs (Optional[str | int | pyproj.CRS]):
                出力CRS。指定しない場合はUTM座標系を推定する。
        Returns:
            BaseGeometry | list[BaseGeometry]:
                変換後のジオメトリ。
        """
        if out_crs is None:
            center = get_geometry_center(geometry, in_crs=in_crs, out_crs="EPSG:4326")
            out_crs = estimate_utm_crs(center.x, center.y, datum_name=datum_name)
        else:
            out_crs = crs_formatter(out_crs)
        # 図面の作成はメートル単位で行うため、出力CRSがメートル単位であることを確認
        if out_crs.axis_info[0].unit_name != "metre":
            # 出力CRSがメートル単位でない場合はエラーを投げる
            raise ValueError(
                "The output CRS must use metres as the unit. "
                f"Received {out_crs.axis_info[0].unit_name}."
            )
        # 次元数を数える
        dim_count = dimensional_count(geometry)
        if dim_count == 0:
            # ジオメトリが単一のジオメトリの場合
            geom = transform_geometry(
                geometry=geometry,
                in_crs=in_crs,
                out_crs=out_crs,
            )
            self._is_iterable = False
            return geom
        elif dim_count == 1:
            # ジオメトリが複数のジオメトリの場合
            geom_list = []
            for geom in geometry:
                geom = transform_geometry(
                    geometry=geom,
                    in_crs=in_crs,
                    out_crs=out_crs,
                )
                geom_list.append(geom)
            self._is_iterable = True
            return geom_list
        else:
            raise ValueError(
                "Geometry must be a Point, LineString, Polygon, or Multi* type."
                f"The number of dimensions sought is 0, 1. Received {dim_count} "
                "dimensions."
            )

    def set_scope(
        self,
        x_min: float,
        y_min: float,
        x_max: float,
        y_max: float,
    ) -> None:
        """
        ## Summary:
            地図の表示範囲を設定する。これは一番最後に呼び出す事で、縮尺の誤差
            を最小限に抑えることができる。ここで指定する範囲は、``self._calc_valid_scales()``
            で計算された範囲を利用する事で、印刷時の縮尺の誤差を最小限に抑えることができる。
        Args:
            x_min (float): X軸の最小値。
            y_min (float): Y軸の最小値。
            x_max (float): X軸の最大値。
            y_max (float): Y軸の最大値。
        Returns:
            None
        """
        self.ax.set_xlim([x_min, x_max])
        self.ax.set_ylim([y_min, y_max])

    def set_lims(
        self,
        x_min: float,
        y_min: float,
        x_max: float,
        y_max: float,
        major_tick: int = 500,
        major_grid: bool = True,
        minor_grid: bool = True,
    ) -> None:
        """
        ## Summary:
            地図の表示範囲とXY軸の目盛りを設定する。地図の表示範囲は、``set_scope()``で
            設定された範囲を利用する。目盛りは指定された間隔で設定され、グリッド線も
            オプションで表示される。
        Args:
            x_min (float): X軸の最小値。
            x_max (float): X軸の最大値。
            y_min (float): Y軸の最小値。
            y_max (float): Y軸の最大値。
        Returns:
            None
        """
        # XY軸のラベルを設定
        x_tick_labels = np.arange(x_min, x_max + major_tick, major_tick)
        y_tick_labels = np.arange(y_min, y_max + major_tick, major_tick)
        self.ax.set_xticks(x_tick_labels)
        self.ax.set_yticks(y_tick_labels)
        # ラベルの位置を調整
        for label in self.ax.get_xticklabels():
            label.set_horizontalalignment("left")
            label.set_fontsize(5)
        for label in self.ax.get_yticklabels():
            label.set_verticalalignment("bottom")
            label.set_rotation(90)
            label.set_fontsize(5)
        # 指数表記を無効化
        xfmt = ScalarFormatter(useOffset=False, useMathText=False)
        xfmt.set_scientific(False)
        self.ax.xaxis.set_major_formatter(xfmt)
        yfmt = ScalarFormatter(useOffset=False, useMathText=False)
        yfmt.set_scientific(False)
        self.ax.yaxis.set_major_formatter(yfmt)
        # Gridの設定
        if major_grid:
            self.ax.grid(
                which="major", color="#949495", linestyle="-", linewidth=0.5, zorder=0
            )
        if minor_grid:
            self.ax.minorticks_on()
            self.ax.grid(
                which="minor", color="#dcdddd", linestyle="--", linewidth=0.1, zorder=0
            )

    def remove_axis_grid(self) -> None:
        """
        ## Summary:
            地図の軸を削除する。これにより、地図の表示がよりクリーンになります。
        Returns:
            None
        """
        self.ax.spines["bottom"].set_visible(False)
        self.ax.spines["top"].set_visible(False)
        self.ax.spines["left"].set_visible(False)
        self.ax.spines["right"].set_visible(False)
        self.ax.tick_params(
            axis="both",
            which="both",
            bottom=False,
            top=False,
            left=False,
            right=False,
            labelbottom=False,
            labelleft=False,
        )

    def add_txt(
        self,  #
        txt: str,
        left_cm: float = 2.0,
        bottom_cm: float = 1.0,
        **kwargs,
    ) -> None:
        """
        ## Summary:
            ``Figure``の指定された位置にテキストを追加する。
        Args:
            txt (str): 追加するテキスト。
            left_cm (float): 左下からのテキスト位置（センチメートル単位）。
            bottom_cm (float): 左下からのテキスト位置（センチメートル単位）。
            **kwargs:
                - ha (str): テキストの水平位置（'left', 'center', 'right'）。
                - va (str): テキストの垂直位置（'bottom', 'center', 'top'）。
                - fontsize (int): テキストのフォントサイズ（デフォルトは9）。
                - bbox (dict): テキストの背景ボックスの設定。
                                dict(facecolor="white", edgecolor="none", pad=0))
        Returns:
            None
        """
        x = left_cm / 2.54 / self.fig_size.width
        y = bottom_cm / 2.54 / self.fig_size.height
        options = {
            "ha": kwargs.get("ha", "left"),
            "va": kwargs.get("va", "bottom"),
            "fontsize": kwargs.get("fontsize", 9),
            "bbox": kwargs.get("bbox", dict(facecolor="white", edgecolor="none", pad=0)),
        }
        if kwargs.get("url"):
            # URLが指定されている場合は、リンクを追加
            options["url"] = kwargs["url"]
        self.fig.text(
            x,
            y,
            txt,
            **options,
        )

    def _describe_crs(
        self,  #
        crs: pyproj.CRS,
        left_cm: float,
        bottom_cm: float,
        **kwargs,
    ) -> None:
        """
        ## Summary:
            CRSの情報をFigureに追加する。
        Args:
            crs (pyproj.CRS): CRSオブジェクト。
            left_cm (float): テキストの幅（センチメートル単位）。
            bottom_cm (float): テキストの高さ（センチメートル単位）。
            kwargs:
                - ha (str): テキストの水平位置（'left', 'center', 'right'）。
                - va (str): テキストの垂直位置（'bottom', 'center', 'top'）。
                - fontsize (int): テキストのフォントサイズ（デフォルトは9）。
                - bbox (dict): テキストの背景ボックスの設定。
                               dict(facecolor="white", edgecolor="none", pad=0))
        Returns:
            None
        """
        txt = f"座標参照系      {crs.name}\n"
        txt += f"EPSGコード   {crs.to_epsg()}\n"
        scope = Scope(*[round(v, 3) for v in self.geom_scope])
        txt += f"表示範囲         x min: {scope.x_min},  y min: {scope.y_min},  "
        txt += f"x max: {scope.x_max},  y max: {scope.y_max}"
        self.add_txt(txt, left_cm, bottom_cm, **kwargs)

    def add_scale_txt(
        self, scale: int, left_cm: float = 1.5, bottom_cm: float = 0.7, **kwargs
    ) -> None:
        """
        ## Summary:
            地図の縮尺をFigureに追加する。
        Args:
            scale (int): 縮尺の値。例えば、1000は1:1000を意味します。
            left_cm (float): テキストの左下からの位置（センチメートル単位）。
            bottom_cm (float): テキストの左下からの位置（センチメートル単位）。
            **kwargs:
                - fontsize (int): テキストのフォントサイズ（デフォルトは7）。
                - va (str): テキストの垂直位置（'bottom', 'center', 'top'）。
                - bbox (dict): テキストの背景ボックスの設定。
                               dict(facecolor="none", edgecolor="none", pad=0))
        Returns:
            None
        """
        self.add_txt(
            txt=f"縮尺                1:{scale}",
            left_cm=left_cm,
            bottom_cm=bottom_cm,
            fontsize=kwargs.get("fontsize", 7),
            va=kwargs.get("va", "bottom"),
            bbox=kwargs.get("bbox", dict(facecolor="none", edgecolor="none", pad=0)),
        )

    def add_basemap(
        self,  #
        x_min: float,
        y_min: float,
        x_max: float,
        y_max: float,
        map_name: str = "standard",
        zl: int = 15,
    ) -> None:
        """
        ## Summary:
            地図の範囲に該当するタイルを取得して、ベースマップとして追加する。
            大きな範囲を指定し、ZoomLevelを上げるとデータ取得に時間がかかる場合があります。
        Args:
            map_name (str):
                使用する地図の種類。
                - 'standard': 標準地図（ZL = 5 ~ 18）
                - 'pale': 淡色地図（ZL = 5 ~ 18）
                - 'photo': 航空写真（ZL = 2 ~ 18)
                - 'slope': 傾斜図（ZL = 3 ~ 15）
            zl (int):
                ズームレベル。デフォルトは15。
        Returns:
            None
        """
        # 地図の種類に応じたタイル取得関数とソースURLを設定
        source = TileUrls()._chiriin_source
        data = {
            "standard": {
                "func": chiriin_drawer.fetch_img_tile_geometry_with_standard_map,
                "source": source,
            },
            "pale": {
                "func": chiriin_drawer.fetch_img_tile_geometry_with_pale_map,
                "source": source,
            },
            "photo": {
                "func": chiriin_drawer.fetch_img_tile_geometry_with_photo_map,
                "source": source,
            },
            "slope": {
                "func": chiriin_drawer.fetch_img_tile_geometry_with_slope_map,
                "source": source,
            },
        }.get(map_name.lower(), None)
        if data is None:
            raise ValueError(
                f"Invalid map name: {map_name}. Choose from 'standard', 'photo', 'slope'."
            )
        # タイルの取得範囲を計算
        metre_bbox = shapely.box(*(x_min, y_min, x_max, y_max))
        tile_datasets = data["func"](
            geometry=metre_bbox, in_crs=self.out_crs, zoom_level=zl
        )
        for tile_data in tile_datasets:
            trg_bbox = transform_geometry(
                shapely.box(*tile_data.tile_scope),
                in_crs=tile_data.crs,
                out_crs=self.out_crs,
            )
            trg_scope = Scope(*trg_bbox.bounds)
            self.ax.imshow(
                tile_data.ary,
                extent=(
                    trg_scope.x_min,
                    trg_scope.x_max,
                    trg_scope.y_min,
                    trg_scope.y_max,
                ),
            )
        self.add_txt(
            data["source"] + f"  zl: {zl}",
            left_cm=self._left_cm + 0.3,
            bottom_cm=self._bottom_cm + 0.3,
            fontsize=8,
            va="bottom",
            bbox=dict(facecolor="none", edgecolor="none", pad=0),
            url="https://maps.gsi.go.jp/development/ichiran.html",
        )

    def add_icon(
        self,
        img_path: str,
        img_size: float,
        left_cm: float,
        bottom_cm: float,
    ) -> None:
        """
        ## Summary:
            地図上にアイコンを追加する。
        Args:
            img_path (str):
                アイコンの画像ファイルのパス。
            img_size (float):
                アイコンのサイズ（センチメートル単位）。
            left_cm (float):
                アイコンの左下の位置（センチメートル単位）。
            bottom_cm (float):
                アイコンの左下の位置（センチメートル単位）。
        Returns:
            None
        """
        icon = plt.imread(img_path)
        icon_size = img_size / 2.54  # センチメートルからインチに変換
        fig_width, fig_height = self.fig.get_size_inches()
        left = left_cm / 2.54 / fig_width
        bottom = bottom_cm / 2.54 / fig_height
        ax_width = icon_size / fig_width
        ax_height = icon_size / fig_height
        ax_img = self.fig.add_axes([left, bottom, ax_width, ax_height])
        ax_img.imshow(icon)
        ax_img.axis("off")

    def add_icon_of_true_north(self, img_size: float = 1.5) -> None:
        """
        ## Summary:
            地図上にTrue Northのアイコンを追加する。
        Returns:
            None
        """
        self.add_icon(
            img_path=Icons().true_north,
            img_size=img_size,
            left_cm=self._left_cm + self.map_width - img_size - 0.2,
            bottom_cm=self._bottom_cm + self.map_height - img_size - 0.7,
        )

    def add_icon_of_compass(self, img_size: float = 1.5) -> None:
        """
        ## Summary:
            地図上にコンパスのアイコンを追加する。
        Returns:
            None
        """
        self.add_icon(
            img_path=Icons().compass,
            img_size=img_size,
            left_cm=self._left_cm + self.map_width - img_size - 0.7,
            bottom_cm=self._bottom_cm + self.map_height - img_size - 0.7,
        )

    def add_icon_of_simple_compass(self, img_size: float = 1.5) -> None:
        """
        ## Summary:
            地図上にシンプルなコンパスのアイコンを追加する。
        Returns:
            None
        """
        self.add_icon(
            img_path=Icons().simple_compass,
            img_size=img_size,
            left_cm=self._left_cm + self.map_width - img_size - 0.7,
            bottom_cm=self._bottom_cm + self.map_height - img_size - 0.7,
        )
