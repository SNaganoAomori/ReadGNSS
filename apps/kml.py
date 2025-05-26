from xml.etree import ElementTree as ET


def make_style():
    style = ET.Element("Style")
    list_style = ET.SubElement(style, "ListStyle")
    list_item_type = ET.SubElement(list_style, "listItemType")
    list_item_type.text = "checkHideChildren"
    return style


def append_closed_document_style(func):
    def decorator(*args, **kwargs):
        kml = func(*args, **kwargs)
        if "closed_document" not in kwargs:
            return kml
        elif kwargs["closed_document"] is False:
            return kml
        style = make_style()
        # kmlを文字列に変換
        kml_string = kml.to_string(prettyprint=True)
        # kml_stringをxml形式で解析
        root = ET.fromstring(kml_string)
        for doc in root.findall(".//{http://www.opengis.net/kml/2.2}Document"):
            doc.append(style)
        # rootを文字列に変換
        result_string = (
            ET.tostring(root, encoding="utf-8", xml_declaration=True)
            .decode("utf-8")
            .replace("ns0:", "")
            .replace(":ns0", "")
            .replace("</ListStyle></Style>", "</ListStyle></Style>\n")
        )
        return result_string

    return decorator
