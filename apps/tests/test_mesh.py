import pytest

from apps.mesh import MeshCode


@pytest.mark.parametrize(
    "lon, lat, mc1d, mc2d, mc3d, mc4d",
    [
        (140.5555, 40.001, "6040", "604004", "60400404", "604004041"),
        (140.74128, 40.82416, "6140", "614015", "61401589", "614015893"),
        (141.1592, 39.7002, "5941", "594141", "59414142", "594141422"),
        (140.8755, 38.2678, "5740", "574037", "57403720", "574037201"),
    ],
)
def test_mesh_code(lon, lat, mc1d, mc2d, mc3d, mc4d):
    mesh = MeshCode(lon=lon, lat=lat)
    assert mesh.first_mesh_code == mc1d
    assert mesh.secandary_mesh_code == mc2d
    assert mesh.standard_mesh_code == mc3d
    assert mesh.half_mesh_code == mc4d
    print(mesh)
