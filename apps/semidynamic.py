"""
セミダイナミック補正による
"""

import datetime
import requests
from typing import NamedTuple, Union

import numpy as np
import pandas as pd

from apps.config import SEMIDYNA_FILES, MeshDesign, Delta
from apps.mesh import MeshCode


def datetime_formatter(dt: datetime.datetime | str) -> datetime.datetime:
    fmts = [
        # データがこのフォーマットに合致するかチェック
        # 変換でエラーが生じた場合は、このフォーマットに新しく追加する
        # 2023-11-16T11:06:21.700+09:00
        "%Y-%m-%dT%H:%M:%S.%f+%z",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M",
        "%Y-%m-%d %H:%M:%S",
        "%Y/%m/%d %H:%M:%S",
        "%Y/%m/%d %H:%M",
    ]
    if isinstance(dt, datetime.datetime):
        return dt.replace(microsecond=0)
    elif isinstance(dt, str):
        for fmt in fmts:
            # 各フォーマットで変換を試みる
            try:
                return datetime.datetime.strptime(dt, fmt).replace(microsecond=0)
            except Exception:
                continue
        try:
            return datetime.datetime.fromisoformat(dt).replace(
                tzinfo=None, microsecond=0
            )
        except Exception:
            raise ValueError(f"Unsupported datetime format: {dt}")
    raise TypeError(f"Expected datetime or str, got {type(dt)}")


class SemiDynamicCorrection(object):
    def __init__(self, datetime: datetime.datetime):
        """
        ## Description:
            セミダイナミック補正のパラメータを読み込み、指定された経緯度に対して補正を行う。
        Args:
            lon (float | list[float]):
                ターゲットの経度（10進法）または経度のリスト
            lat (float | list[float]):
                ターゲットの緯度（10進法）または緯度のリスト
            datetime (datetime.datetime):
                セミダイナミック補正の対象となる日時
        """
        self._datetime = datetime_formatter(datetime)
        if 4 <= self._datetime.month:
            # 4月以降は新年度となり、当年のデータを使用する
            self.year = self._datetime.year
        else:
            # 3月以前は前年のデータを使用する
            self.year = self._datetime.year - 1
        self._file_path = [file for file in SEMIDYNA_FILES if str(self.year) in file][0]
        self._param_df = self.read_parameters(self._file_path)

    def read_parameters(self, file_path: str) -> pd.DataFrame:
        """
        ## Description:
            セミダイナミック補正のパラメータを読み込む。
            パラメータは16行目から定義されている。
        Args:
            file_path (str):
                セミダイナミック補正のパラメータファイルのパス
        Returns:
            pd.DataFrame:
                セミダイナミック補正のパラメータを含むDataFrame
        """
        with open(file_path, mode="r") as f:
            # 16行目からパラメータが定義されている。
            lines = f.readlines()[15:]
            headers = self._clean_line(lines[0].split(" "))
            data = [self._clean_line(line.split(" ")) for line in lines[1:]]
            df = pd.DataFrame(data, columns=headers)
        # Breedte（緯度）Lengte（経度）
        df = df.rename(
            columns={"dB(sec)": "delta_y", "dL(sec)": "delta_x", "dH(m)": "delta_z"}
        )
        return df.set_index("MeshCode")

    def _clean_line(self, line: list[str]) -> list[list[str]]:
        """
        ## Description:
            セミダイナミック補正のパラメータを読み込む際に、行ごとに読み込んでいるが
            その際に改行文字を削除し、数値に変換できるものは変換する為の関数。
        Args:
            line (list[str]):
                セミダイナミック補正のパラメータの行
        Returns:
            list[list[str]]:
                改行文字を削除し、数値に変換できるものは変換したリスト
        Example:
            >>> line = ['MeshCode', 'dB(sec)', '', 'dL(sec)', 'dH(m)\n']
            >>> xxx._clean_line(line)
            ['MeshCode', 'dB(sec)', 'dL(sec)', 'dH(m)']
            >>> line = ['36230600', '', '-0.05708', '', '', '0.04167', '', '', '0.05603\n']
            >>> xxx._clean_line(line)
            ['36230600', -0.05708, 0.04167, 0.05603]
        """
        result = []
        for txt in line:
            # 改行文字を削除
            txt = txt.replace("\n", "") if "\n" in txt else txt
            try:
                if "." in txt:
                    # 小数点が含まれている場合はfloatに変換
                    result.append(float(txt))
                else:
                    # 小数点が含まれていない場合はintに変換
                    result.append(int(txt))
            except Exception:
                # 変換できない場合はそのまま文字列として追加
                if txt == "":
                    # 空文字は無視
                    pass
                else:
                    result.append(txt)
        return result

    def semidynamic_mesh_design(self, lon: float, lat: float) -> dict[str, MeshDesign]:
        """
        ## Description:
            補正したいターゲットの経緯度（10進法）を受け取り、補正に必要な情報を計算
            する為の関数。
        Args:
            lon (float):
                ターゲットの経度（10進法）
            lat (float):
                ターゲットの緯度（10進法）
        Returns:
            dict[str, MeshDesign]:
                補正に必要な情報を含む辞書。
                MeshDesign(name, lon, lat, standard_mesh_code)
        """
        lon_param = 225
        lat_param = 150
        lower_left_sec_lon = round(lon * 3600, 1)
        lower_left_sec_lat = round(lat * 3600, 1)
        m = int(lower_left_sec_lon / lon_param)
        n = int(lower_left_sec_lat / lat_param)
        lower_left_sec_lon = m * lon_param
        lower_left_sec_lat = n * lat_param
        lower_left_deg_lon = lower_left_sec_lon / 3600
        lower_left_deg_lat = lower_left_sec_lat / 3600
        try:
            # Create MeshCode and MeshDesign for lower left corner
            lower_left_mesh_code = MeshCode(lower_left_deg_lon, lower_left_deg_lat)
            lower_left_design = MeshDesign(
                "lower_left",
                lower_left_sec_lon,
                lower_left_sec_lat,
                lower_left_mesh_code.standard_mesh_code,
            )
            lower_right_design = self._adjust_mesh_code(
                lower_left_sec_lon, lower_left_sec_lat, lon_param, 0, "lower_right"
            )
            upper_left_design = self._adjust_mesh_code(
                lower_left_sec_lon, lower_left_sec_lat, 0, lat_param, "upper_left"
            )
            upper_right_design = self._adjust_mesh_code(
                lower_left_sec_lon,
                lower_left_sec_lat,
                lon_param,
                lat_param,
                "upper_right",
            )
        except Exception:
            return False
        else:
            return {
                "lower_left": lower_left_design,
                "lower_right": lower_right_design,
                "upper_left": upper_left_design,
                "upper_right": upper_right_design,
            }

    def _adjust_mesh_code(
        self,
        lower_left_sec_lon: float,
        lower_left_sec_lat,
        lon_param: int = 225,
        lat_param: int = 150,
        name: str = "lower_right",
    ) -> MeshDesign:
        """
        ## Description:
            セミダイナミック補正のメッシュコードを調整する。
        Args:
            lower_left_sec_lon (float):
                左下の経度（秒単位）
            lower_left_sec_lat (float):
                左下の緯度（秒単位）
            lon_param (int, optional):
                経度のパラメータ。デフォルトは225。
            lat_param (int, optional):
                緯度のパラメータ。デフォルトは150。
            name (str, optional):
                メッシュの名前。デフォルトは'lower_right'。
        Returns:
            MeshDesign:
                調整されたメッシュコードを含むMeshDesignオブジェクト。
                - name: メッシュの名前
                - lon: 調整後の経度（秒単位）
                - lat: 調整後の緯度（秒単位）
                - standard_mesh_code: 標準メッシュコード
        """
        sec_lon = lower_left_sec_lon + lon_param
        sec_lat = lower_left_sec_lat + lat_param
        deg_lon = sec_lon / 3600
        deg_lat = sec_lat / 3600
        return MeshDesign(
            name=name,
            lon=sec_lon,
            lat=sec_lat,
            standard_mesh_code=MeshCode(deg_lon, deg_lat).standard_mesh_code,
        )

    def _get_delta_sets(self, mesh_designs: dict[str, MeshDesign]) -> dict[str, Delta]:
        """
        ## Description:
            セミダイナミック補正のパラメータから4方向のDeltaを取得する。
        Args:
            mesh_designs (dict[str, MeshDesign]):
                メッシュデザインを含む辞書
        Returns:
            DeltaSet:
                4方向のDeltaを含むDeltaSetオブジェクト
        """
        lower_left_delta = self._get_delta(
            mesh_designs["lower_left"].standard_mesh_code
        )
        lower_right_delta = self._get_delta(
            mesh_designs["lower_right"].standard_mesh_code
        )
        upper_left_delta = self._get_delta(
            mesh_designs["upper_left"].standard_mesh_code
        )
        upper_right_delta = self._get_delta(
            mesh_designs["upper_right"].standard_mesh_code
        )
        return {
            "lower_left": lower_left_delta,
            "lower_right": lower_right_delta,
            "upper_left": upper_left_delta,
            "upper_right": upper_right_delta,
        }

    def _get_delta(self, mesh_code: str) -> Delta:
        """
        ## Description:
            セミダイナミック補正のパラメータからDeltaを取得する。
        Args:
            param_df (pd.DataFrame):
                セミダイナミック補正のパラメータを含むDataFrame
            mesh_code (str):
                メッシュコード
        Returns:
            Delta:
                Deltaオブジェクト
        """
        try:
            row = self._param_df.loc[int(mesh_code)]
        except KeyError:
            raise KeyError(f"Mesh code {mesh_code} not found in parameters.")
        return Delta(
            delta_x=row["delta_x"], delta_y=row["delta_y"], delta_z=row["delta_z"]
        )

    def _correction_2d(
        self, lon: float, lat: float, return_to_original: bool = True
    ) -> dict[str, float]:
        """
        ## Description:
            経緯度（10進法）を受け取り、セミダイナミック補正を行う。
        Args:
            lon (float):
                ターゲットの経度（10進法）
            lat (float):
                ターゲットの緯度（10進法）
            return_to_original (bool, optional):
                Trueは今期から元期への補正を行う。Falseは元期から今期への補正を行う。
        Returns:
            dict[str, float]:
                補正後の経度と緯度を含む辞書。
                {'lon': 経度, 'lat': 緯度}
        """
        _lon = lon
        _lat = lat
        mesh_designs = self.semidynamic_mesh_design(lon, lat)
        if not mesh_designs:
            return {"lon": False, "lat": False}
        # 経度と緯度を秒単位に変換
        lon = lon * 3600
        lat = lat * 3600
        # MeshDesign(name, lon, lat, standard_mesh_code)
        lower_left_design = mesh_designs["lower_left"]
        lower_right_design = mesh_designs["lower_right"]
        upper_left_design = mesh_designs["upper_left"]
        # Delta(delta_x, delta_y, delta_z)
        delta_sets = self._get_delta_sets(mesh_designs)
        lower_left_delta = delta_sets["lower_left"]
        lower_right_delta = delta_sets["lower_right"]
        upper_left_delta = delta_sets["upper_left"]
        upper_right_delta = delta_sets["upper_right"]
        # バイリニア補間により補正値を計算
        x_norm = (lon - lower_left_design.lon) / (
            lower_right_design.lon - lower_left_design.lon
        )
        y_norm = (lat - lower_left_design.lat) / (
            upper_left_design.lat - lower_left_design.lat
        )
        delta_lon_p = (
            (1 - y_norm) * (1 - x_norm) * lower_left_delta.delta_x
            + y_norm * (1 - x_norm) * lower_right_delta.delta_x
            + y_norm * x_norm * upper_right_delta.delta_x
            + (1 - y_norm) * x_norm * upper_left_delta.delta_x
        )
        delta_lat_p = (
            (1 - y_norm) * (1 - x_norm) * lower_left_delta.delta_y
            + y_norm * (1 - x_norm) * lower_right_delta.delta_y
            + y_norm * x_norm * upper_right_delta.delta_y
            + (1 - y_norm) * x_norm * upper_left_delta.delta_y
        )
        # 元期から今期へのパラメーターなので、今期から元期へは -1 を掛ける
        if return_to_original:
            delta_lon_p *= -1
            delta_lat_p *= -1
        corrected_lon = float(_lon + (delta_lon_p / 3600))
        corrected_lat = float(_lat + (delta_lat_p / 3600))
        return {
            "lon": corrected_lon,
            "lat": corrected_lat,
        }

    def correction_2d(
        self,
        lon: float | list[float],
        lat: float | list[float],
        return_to_original: bool = True,
    ) -> dict[str, Union[float, list[float]]]:
        """
        ## Description:
            セミダイナミック補正を行い、結果を返す。
        Args:
            lon (float | list[float]):
                ターゲットの経度（10進法）または経度のリスト
            lat (float | list[float]):
                ターゲットの緯度（10進法）または緯度のリスト
            return_to_original (bool, optional):
                Trueは今期から元期への補正を行う。Falseは元期から今期への補正を行う。
        Returns:
            dict[str, Union[float, list[float]]]:
                補正後の経度と緯度を含む辞書。
                {'lon': 経度または経度のリスト, 'lat': 緯度または緯度のリスト}
        """
        if isinstance(lon, list) and isinstance(lat, list):
            results = []
            for lon, lat in zip(lon, lat):
                results.append(self._correction_2d(lon, lat, return_to_original))
            return {
                "lon": [result["lon"] for result in results],
                "lat": [result["lat"] for result in results],
            }
        else:
            return self._correction_2d(lon, lat, return_to_original)


if __name__ == "__main__":
    """
    current_lat = 40.832835180
    current_lon = 140.728866813
    current_alti = 1.9
    # 2024.par
    expected_lat = 40.832839878
    expected_lon = 140.728861558
    expected_alti = 1.842
    """
    file = SEMIDYNA_FILES[-2]

    print(f"file: {file}")
    semi_dynamic = SemiDynamicCorrection()
    df = semi_dynamic.read_parameters(file)
