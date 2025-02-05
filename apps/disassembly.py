"""
Note:
    1. Disassembliesの各関数の中身をDictに
    2. Disassembliesの最後の関数はNoneの場合があるのでその処理を

1. geom_disassembly
    shapelyのgeometryを分解する。
"""
from dataclasses import dataclass
import logging
from typing import Any
from typing import Callable
from typing import Iterable
from typing import List
from typing import NamedTuple

import shapely


FORMAT = """________ %(levelname)s LOG ________
    FuncName: %(funcName)s
    Message: %(message)s
    """
logging.basicConfig(format=FORMAT)
logger = logging.getLogger(__name__)


@dataclass
class DisassembledTypes:
    """
    分解後のデータタイプを記述している。
    """
    POINT = 0
    XYZ = 1
    X_Y_Z = 2
    WKT = 3
    WKB = 4
    MERGED_POINT = 5
    MERGED_XYZ = 6
    MERGED_X_Y_Z = 7
    MERGED_WKT = 8
    MERGED_WKB = 9


class XY(NamedTuple):
    x: float | List[float]
    y: float | List[float]


class XYZ(NamedTuple):
    x: float | List[float]
    y: float | List[float]
    z: float | List[float]



class RingsParts(NamedTuple):
    shell: shapely.LinearRing
    holes: List[shapely.LinearRing]


class PolyParts(NamedTuple):
    shell: List[XY | XYZ | shapely.Point]
    holes: List[XY | XYZ | shapely.Point]




class DisassemblyPoint(object):
    """shapely.geometry.Point あるいは shapely.geometry.MultiPoint を分解する。"""
    def xyz_from_point(self, geom: shapely.Point) -> XY | XYZ:
        if shapely.has_z(geom):
            return XYZ(geom.x, geom.y, geom.z)
        return XY(geom.x, geom.y)
    
    def points_from_multi_point(self, geom: shapely.MultiPoint) -> List[shapely.Point]:
        return list(shapely.get_parts(geom))

    def xyz_from_multi_point(self, geom: shapely.MultiPoint) -> List[XY | XYZ]:
        points = []
        for point in geom.geoms:
            xyz = self.xyz_from_point(point)
            points.append(xyz)
        return points
    
    def x_y_z_from_multi_point(self, geom: shapely.MultiPoint) -> XY | XYZ:
        x_lst, y_lst, z_lst = [], [], []
        for xyz in self.xyz_from_multi_point(geom):
            x_lst.append(xyz.x)
            y_lst.append(xyz.y)
            if type(xyz) == XYZ:
                z_lst.append(xyz.z)
        if z_lst:
            return XYZ(x_lst, y_lst, z_lst)
        return XY(x_lst, y_lst)

    def wkt_points_from_multi_point(self, geom: shapely.MultiPoint) -> List[str]:
        return [pt.wkt for pt in list(geom.geoms)]
    
    def wkb_points_from_multi_point(self, geom: shapely.MultiPoint) -> List[bytes]:
        return [pt.wkb for pt in list(geom.geoms)]




class DisassemblyLineString(object):
    """shapely.geometry.LineString あるいは shapely.geometry.MultiLineString を分解する。"""
    def points_from_line(self, geom: shapely.LineString) -> List[shapely.Point]:
        return [shapely.Point(pt) for pt in list(geom.coords)]

    def wkt_from_line(self, geom: shapely.LineString) -> List[str]:
        return [shapely.Point(pt).wkt for pt in list(geom.coords)]
    
    def wkb_from_line(self, geom: shapely.LineString) -> List[bytes]:
        return [shapely.Point(pt).wkb for pt in list(geom.coords)]

    def xyz_from_line(self, geom: shapely.LineString
    ) -> List[XY[float] | XYZ[float]]:
        lst = []
        for pt in list(geom.coords):
            if len(pt) <= 2:
                lst.append(XY(*pt))
            else:
                lst.append(XYZ(*pt))
        return lst
    
    def x_y_z_from_line(self, geom: shapely.LineString) -> XY | XYZ:
        x_lst, y_lst, z_lst = [], [], []
        for xyz in self.xyz_from_line(geom):
            x_lst.append(xyz.x)
            y_lst.append(xyz.y)
            if type(xyz) == XYZ:
                z_lst.append(xyz.z)
        if z_lst:
            return XYZ(x_lst, y_lst, z_lst)
        return XY(x_lst, y_lst)
    
    def __func_multi_line(self, geom: shapely.MultiLineString, func: Callable
    ) -> List[List[XY | XYZ | shapely.Point]]:
        lst = []
        for line in shapely.get_parts(geom):
            lst.append(func(line))
        return lst

    def points_from_multi_line(self, geom: shapely.MultiLineString
    ) -> List[List[shapely.Point]]:
        return self.__func_multi_line(geom, self.points_from_line)

    def xyz_from_multi_line(self, geom: shapely.MultiLineString
    ) -> List[List[XY | XYZ]]:
        return self.__func_multi_line(geom, self.xyz_from_line)
    
    def x_y_z_from_multi_line(self, geom: shapely.MultiLineString,
    ) -> List[List[XY | XYZ]]:
        return self.__func_multi_line(geom, self.x_y_z_from_line)

    def wkt_from_multi_line(self, geom: shapely.MultiLineString
    ) -> List[List[str]]:
        return self.__func_multi_line(geom, self.wkt_from_line)
    
    def wkb_from_multi_line(self, geom: shapely.MultiLineString
    ) -> List[List[bytes]]:
        return self.__func_multi_line(geom, self.wkb_from_line)

    def __func_merge(self, geom: shapely.MultiLineString, func: Callable
    ) -> List[XY | XYZ | shapely.Point]:
        merged_lst = []
        for lst in func(geom):
            merged_lst += lst
        return merged_lst

    def merged_points_from_multi_line(self, geom: shapely.MultiLineString
    ) -> List[shapely.Point]:
        return self.__func_merge(geom, self.points_from_multi_line)

    def merged_xyz_from_multi_line(self, geom: shapely.MultiLineString
    ) -> List[XY | XYZ]:
        return self.__func_merge(geom, self.xyz_from_multi_line)
    
    def merged_x_y_z_from_multi_line(self, geom: shapely.MultiLineString
    ) -> XY | XYZ:
        x_lst, y_lst, z_lst = [], [], []
        for line in shapely.get_parts(geom):
            xyz = self.x_y_z_from_line(line)
            x_lst += xyz.x
            y_lst += xyz.y
            if type(xyz) == XYZ:
                z_lst += xyz.z
        if z_lst:
            return XYZ(x_lst, y_lst, z_lst)
        return XY(x_lst, y_lst)
        
    def merged_wkt_from_multi_line(self, geom: shapely.MultiLineString
    ) -> List[str]:
        return self.__func_merge(geom, self.wkt_from_multi_line)

    def merged_wkb_from_multi_line(self, geom: shapely.MultiLineString
    ) -> List[bytes]:
        return self.__func_merge(geom, self.wkb_from_multi_line)




class DisassemblyPolygon(DisassemblyLineString):
    """shapely.geometry.Polygon あるいは shapely.geometry.MultiPolygon を分解する。"""
    def _single_disassembly(self, geom: shapely.Polygon) -> RingsParts:
        outer = geom.exterior
        inners = list(shapely.get_parts(geom.interiors))
        return RingsParts(outer, inners)

    def __func_single_poly(self, geom: shapely.Polygon, func: Callable
    ) -> PolyParts:
        rings_parts = self._single_disassembly(geom)
        shell = func(rings_parts.shell)
        holes = []
        if rings_parts.holes:
            for line in rings_parts.holes:
                holes.append(func(line))
        return PolyParts(shell, holes)

    def points_from_poly(self, geom: shapely.Polygon) -> PolyParts:
        return self.__func_single_poly(geom, self.points_from_line)
    
    def xyz_from_poly(self, geom: shapely.Polygon) -> PolyParts:
        return self.__func_single_poly(geom, self.xyz_from_line)
    
    def x_y_z_from_poly(self, geom: shapely.Polygon) -> PolyParts:
        return self.__func_single_poly(geom, self.x_y_z_from_line)
    
    def wkt_from_poly(self, geom: shapely.Polygon) -> PolyParts:
        return self.__func_single_poly(geom, self.wkt_from_line)
    
    def wkb_from_poly(self, geom: shapely.Polygon) -> PolyParts:
        return self.__func_single_poly(geom, self.wkb_from_line)

    def __func_multi_poly(self, geom: shapely.MultiPolygon, func: Callable
    ) -> List[PolyParts]:
        poly_parts_lst = []
        for poly in shapely.get_parts(geom):
            poly_parts_lst.append(self.__func_single_poly(poly, func))
        return poly_parts_lst

    def points_from_multi_poly(self, geom: shapely.MultiPolygon
    ) -> List[PolyParts]:
        return self.__func_multi_poly(geom, self.points_from_line)
    
    def xyz_from_multi_poly(self, geom: shapely.MultiPolygon) -> List[PolyParts]:
        return self.__func_multi_poly(geom, self.xyz_from_line)
    
    def x_y_z_from_multi_poly(self, geom: shapely.MultiPolygon
    ) -> List[PolyParts]:
        return self.__func_multi_poly(geom, self.x_y_z_from_line)

    def wkt_from_multi_poly(self, geom: shapely.MultiPolygon
    ) -> List[PolyParts]:
        return self.__func_multi_poly(geom, self.wkt_points_from_line)

    def wkb_from_multi_poly(self, geom: shapely.MultiPolygon
    ) -> List[PolyParts]:
        return self.__func_multi_poly(geom, self.wkb_from_line)
    
    def __func_merge_poly(self, geom: shapely.MultiPolygon, func: Callable
    ) -> List[Any]:
        lst = []
        for poly_parts in func(geom):
            lst += poly_parts.shell
            if poly_parts.holes:
                for hole in poly_parts.holes:
                    lst += hole
        return lst

    def merged_points_from_multi_poly(self, geom: shapely.MultiPolygon
    ) -> List[shapely.Point]:
        return self.__func_merge_poly(geom, self.points_from_multi_poly)
        
    def merged_xyz_from_multi_poly(self, geom: shapely.MultiPolygon
    ) -> List[XY | XYZ]:
        return self.__func_merge_poly(geom, self.xyz_from_multi_poly)
    
    def merged_x_y_z_from_multi_poly(self, geom: shapely.MultiPolygon
    ) -> XY | XYZ:
        x_lst, y_lst, z_lst = [], [], []
        for xyz in self.merged_xyz_from_multi_poly(geom):
            x_lst.append(xyz.x)
            y_lst.append(xyz.y)
            if type(XYZ) == XYZ:
                z_lst.append(xyz.z)
        if z_lst:
            return XYZ(x_lst, y_lst, z_lst)
        return XY(x_lst, y_lst)
    
    def merged_wkt_from_multi_poly(self, geom: shapely.MultiPolygon) -> List[str]:
        return self.__func_merge_poly(geom, self.wkt_from_multi_poly)

    def merged_wkb_from_multi_poly(self, geom: shapely.MultiPolygon) -> List[bytes]:
        return self.__func_merge_poly(geom, self.wkb_from_multi_poly)




class Disassemblies(DisassemblyPoint, DisassemblyPolygon):
    def __init__(self, geom: Any, response_type: int):
        super().__init__()
        self.geom = geom
        self.geom_id = self.check_geometry_type
        self.response_type = response_type
        self.disassembled = self.geom_disassembly
    
    @property
    def check_geometry_type(self) -> int:
        try:
            geom_id = shapely.get_type_id(self.geom)
            if 0 <= geom_id < 7:
                return geom_id
            else:
                logger.error("Geometry type that cannot be processed.")
                return None
        except:
            logger.error("Non-geometry was passed as an argument.")
            return None

    def _points_from(self) -> Any:
        funcs = {
            1: self.points_from_line,
            2: self.points_from_line,
            3: self.points_from_poly,
            4: self.points_from_multi_point,
            5: self.points_from_multi_line,
            6: self.points_from_multi_poly
        }
        func = funcs.get(self.geom_id)
        if funcs is None:
            return None
        return func(self.geom)
    
    def _xyz_from(self) -> Any:
        funcs = {
            1: self.xyz_from_line,
            2: self.xyz_from_line,
            3: self.xyz_from_poly,
            4: self.xyz_from_multi_point,
            5: self.xyz_from_multi_line,
            6: self.xyz_from_multi_poly
        }
        func = funcs.get(self.geom_id)
        if funcs is None:
            return None
        return func(self.geom)
    
    def _x_y_z_from(self) -> Any:
        funcs = {
            1: self.x_y_z_from_line,
            2: self.x_y_z_from_line,
            3: self.x_y_z_from_poly,
            4: self.x_y_z_from_multi_point,
            5: self.x_y_z_from_multi_line,
            6: self.x_y_z_from_multi_poly
        }
        func = funcs.get(self.geom_id)
        if funcs is None:
            return None
        return func(self.geom)
    
    def _wkt_from(self) -> Any:
        funcs = {
            1: self.wkt_from_line,
            2: self.wkt_from_line,
            3: self.wkt_from_poly,
            4: self.wkt_from_multi_point,
            5: self.wkt_from_multi_line,
            6: self.wkt_from_multi_poly
        }
        func = funcs.get(self.geom_id)
        if funcs is None:
            return None
        return func(self.geom)
    
    def _wkb_from(self) -> Any:
        funcs = {
            1: self.wkb_from_line,
            2: self.wkb_from_line,
            3: self.wkb_from_poly,
            4: self.wkb_from_multi_point,
            5: self.wkb_from_multi_line,
            6: self.wkb_from_multi_poly
        }
        func = funcs.get(self.geom_id)
        if funcs is None:
            return None
        return func(self.geom)
    
    def _merged_points_from(self) -> Any:
        funcs = {
            1: self.points_from_line,
            2: self.points_from_line,
            3: self.points_from_poly,
            4: self.points_from_multi_point,
            5: self.merged_points_from_multi_line,
            6: self.merged_points_from_multi_poly
        }
        func = funcs.get(self.geom_id)
        if funcs is None:
            return None
        return func(self.geom)

    def _merged_xyz_from(self) -> Any:
        funcs = {
            1: self.xyz_from_line,
            2: self.xyz_from_line,
            3: self.xyz_from_poly,
            4: self.xyz_from_multi_point,
            5: self.merged_xyz_from_multi_line,
            6: self.merged_xyz_from_multi_poly
        }
        func = funcs.get(self.geom_id)
        if funcs is None:
            return None
        return func(self.geom)
    
    def _merged_x_y_z_from(self) -> Any:
        funcs = {
            1: self.x_y_z_from_line,
            2: self.x_y_z_from_line,
            3: self.x_y_z_from_poly,
            4: self.x_y_z_from_multi_point,
            5: self.merged_x_y_z_from_multi_line,
            6: self.merged_x_y_z_from_multi_poly
        }
        func = funcs.get(self.geom_id)
        if funcs is None:
            return None
        return func(self.geom)

    def _merged_wkt_from(self) -> Any:
        funcs = {
            1: self.wkt_from_line,
            2: self.wkt_from_line,
            3: self.wkt_from_poly,
            4: self.wkt_from_multi_point,
            5: self.merged_wkt_from_multi_line,
            6: self.merged_wkt_from_multi_poly
        }
        func = funcs.get(self.geom_id)
        if funcs is None:
            return None
        return func(self.geom)
    
    def _merged_wkb_from(self) -> Any:
        funcs = {
            1: self.wkb_from_line,
            2: self.wkb_from_line,
            3: self.wkb_from_poly,
            4: self.wkb_from_multi_point,
            5: self.merged_wkb_from_multi_line,
            6: self.merged_wkb_from_multi_poly
        }
        func = funcs.get(self.geom_id)
        if funcs is None:
            return None
        return func(self.geom)

    @property
    def geom_disassembly(self) -> Any:
        funcs = {
            0: self._points_from,
            1: self._xyz_from,
            2: self._x_y_z_from,
            3: self._wkt_from,
            4: self._wkb_from,
            5: self._merged_points_from,
            6: self._merged_xyz_from,
            7: self._merged_x_y_z_from,
            8: self._merged_wkt_from,
            9: self._merged_wkb_from
        }
        func = funcs.get(self.response_type)
        if func is None:
            sentence = "A non-existent return value was specified."
            sentence += f"Geometry type ID: {self.geom_id}, "
            sentence += f"Request return type: {self.response_type}"
            logger.error(sentence)
            return None
        return func()
        



def repair_and_disassemble(func):
    """"""
    class Geometries(NamedTuple):
        parts: List[Any]
        no_collection_exists: bool

    def validation(geom):
        try:
            if shapely.is_missing(geom):
                return None
            if shapely.is_valid(geom):
                return geom
        except:
            return None
        return shapely.make_valid(geom) 

    def is_geometry(value):
        geometries = (
            shapely.Point,
            shapely.LineString,
            shapely.LinearRing,
            shapely.Polygon,
            shapely.MultiPoint,
            shapely.MultiLineString,
            shapely.MultiPolygon,
            shapely.GeometryCollection
        )
        return isinstance(value, geometries)

    def disassembly_is_unnecessary(geom):
        if 0 <= shapely.get_type_id(geom) < 7:
            return True
        return False

    def disassemble_collection(geom_lst):
        result = []
        exists = False
        for geom in geom_lst:
            if shapely.get_type_id(geom) != 7:
                result.append(validation(geom))
            elif shapely.get_type_id(geom) == 7:
                result += [validation(g) for g in shapely.get_parts(geom)]
                exists = True
        return Geometries(result, exists)

    def select_poly(geom_lst):
        selected = []
        for geom in geom_lst:
            id_ = shapely.get_type_id(geom)
            if (id_ == 3) | (id_ == 6):
                selected.append(geom)
        return selected

    def select_and_merge_poly(geom_lst):
        geoms = select_poly(geom_lst)
        if geoms:
            return shapely.union_all(geoms)
        return None

    def _repair_and_disassemble(collection: Any):
        geometries = collection
        if is_geometry(collection):
            if shapely.is_valid(collection) == False:
                collection = shapely.make_valid(collection)
            if disassembly_is_unnecessary(collection):
                return collection
            parts = []
            if shapely.get_type_id(collection) == 7:
                parts = list(shapely.get_parts(collection))
                geometries = disassemble_collection(parts)
        elif isinstance(collection, Iterable):
            geometries = disassemble_collection(collection)
        else:
            return None
        if geometries.no_collection_exists:
            return _repair_and_disassemble(geometries.parts)
        else:
            return select_and_merge_poly(geometries.parts)
    
    def wrapper(*args, **kwargs):
        args_lst = [v for v in args]
        geom = args_lst[0]
        args_lst[0] = _repair_and_disassemble(geom)
        return func(*args_lst, **kwargs)
    return wrapper



@repair_and_disassemble
def geom_disassembly(geom: Any, response_type: int) -> Any:
    """
    Args:
        geom(shapely.geometry.XXX): 
        response_type(int): \n
            DisassembledTypesのクラスを用意しているのでそちらを使用するのが簡単です。\n
            -------------------------------------\n
            DisassembledTypes.POINT = 0     \n
            DisassembledTypes.XYZ = 1     \n
            DisassembledTypes.X_Y_Z = 2     \n
            DisassembledTypes.WKT = 3     \n
            DisassembledTypes.WKB = 4     \n
            DisassembledTypes.MERGED_POINT = 5     \n
            DisassembledTypes.MERGED_XYZ = 6     \n
            DisassembledTypes.MERGED_X_Y_Z = 7     \n
            DisassembledTypes.MERGED_WKT = 8     \n
            DisassembledTypes.MERGED_WKB = 9
    Returns:
        shapely.Point as pt     \n
        request_type=0 : \n
            List[pt] | List[List[pt]] | PolyParts(outer=[pt], inners[[pt]])
        request_type=1 : \n
            List[(x,y,z)] | List[List[(x,y,z)]] | PolyParts(outer=[(x,y,z)], inners[[(x,y,z)], ])
        request_type=2 : \n
            List[pt] |  | PolyParts(outer=[pt], inners[[pt], ])
        request_type=3 : 
        request_type=4 : 
        request_type=5 : 
        request_type=6 : 
        request_type=7 : 
        request_type=8 : 
        request_type=9 : 
    """
    disassemblies = Disassemblies(geom, response_type)
    return disassemblies.disassembled


"""
Note:
    merge 関連のモジュールが動作しない。
    repair_and_disassembleでは現在Polygonを返す事しか想定していない。
    Point、Line、Polygonそれぞれ選択できるのがベスト
"""
