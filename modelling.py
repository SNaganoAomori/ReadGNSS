import datetime
import json
import os
from typing import List, Dict, Any, Optional, Union, NamedTuple

import geopandas as gpd
import fastkml
import ezdxf
from ezdxf import recover
from ezdxf.addons.drawing import RenderContext, Frontend
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
from matplotlib import pyplot as plt
import shapely
from shapely.plotting import plot_polygon, plot_points, plot_line
from xml.dom import minidom
import xml.etree.ElementTree as ET
import pandas as pd

# from apps.read_file import read_drg_way_point, _DrgWayPoint
# from apps.models import DataModels, DataModel, hex_to_abgr, original_data_to
# from apps.config import (
#     SortFields,
#     Formatter,
#     Web,
#     SemiDynamicCorrection,
#     ADDITIONAL_EN_FIELD_NAMES,
#     ADDITIONAL_JA_FIELD_NAMES,
#     DRG_RENAME_ORG_TO_EN,
#     DRG_DEFAULT_FIELD_NAMES,
#     DRG_EN_FIELD_NAMES,
#     DRG_JA_FIELD_NAMES,
# )
from apps.geometries import degree_to_dms, dms_to_degree
# from apps.semidynamic import SemiDynamicCorrection, datetime_formatter
# from apps.mesh import MeshCode, ReverseMeshCode


if __name__ == "__main__":
    file = r"C:\Users\chousa08\Downloads\prefecture_pnt.csv"
    df = pd.read_csv(file, encoding="utf-8")
    print(degree_to_dms(40.85253225))
    print(dms_to_degree(405109.1161))
    # for i, row in df.iterrows():
    #     lon = row['longitude']
    #     lat = row['latitude']

    #     dms_lon = degree_to_dms(lon)
    #     dms_lat = degree_to_dms(lat)
    #     pref = row['prefecture']
    #     print(f"([({lon}, {lat})], [XY(x={dms_lon}, y={dms_lat})])")
    #     if i == 4:
    #         break

    # for i, row in df.iterrows():
    #     lon = row['longitude']
    #     dms_lon = degree_to_dms(lon)
    #     pref = row['prefecture']
    #     print(f"{pref} {lon}, {dms_lon}")
    
