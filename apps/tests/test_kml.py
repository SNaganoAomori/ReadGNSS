from apps.kml import make_style, append_closed_document_style


def test_make_style():
    """make_styleが正しいXMLを返すかテスト"""
    style = make_style()
    # タグ名の確認
    assert style.tag == "Style"
    # ListStyleが子要素にあるか
    list_style = style.find("ListStyle")
    assert list_style is not None
    # listItemTypeが正しいか
    list_item_type = list_style.find("listItemType")
    assert list_item_type is not None
    assert list_item_type.text == "checkHideChildren"


def test_append_closed_document_style_closed(monkeypatch):
    """append_closed_document_styleがclosed_document=Trueでstyleを追加するかテスト"""

    class DummyKML:
        def to_string(self, prettyprint=True):
            # KMLのDocument要素を含む最小限のXML
            return (
                '<?xml version="1.0" encoding="utf-8"?>'
                '<kml xmlns="http://www.opengis.net/kml/2.2">'
                "<Document></Document></kml>"
            )

    def dummy_func(*args, **kwargs):
        return DummyKML()

    decorated = append_closed_document_style(dummy_func)
    result = decorated(closed_document=True)
    # 追加されたStyle要素が含まれているか
    assert "<Style>" in result
    assert "<listItemType>checkHideChildren</listItemType>" in result
