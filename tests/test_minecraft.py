import pytest

from nbtlib.contrib.minecraft import StructureFile


def test_structure_file(tmp_path):
    structure = StructureFile(
        {
            "DataVersion": 1139,
            "author": "dinnerbone",
            "size": [1, 2, 1],
            "palette": [
                {
                    "Name": "minecraft:dirt",
                }
            ],
            "blocks": [
                {"pos": [0, 0, 0], "state": 0},
                {"pos": [0, 1, 0], "state": 0},
            ],
            "entities": [],
        }
    )

    structure.save(tmp_path / "foo.nbt")

    assert structure == StructureFile.load(tmp_path / "foo.nbt")


@pytest.mark.parametrize(
    "filename",
    [
        "igloo/top.nbt",
        "igloo/middle.nbt",
        "igloo/bottom.nbt",
        "pillager_outpost/watchtower.nbt",
        "village/plains/houses/plains_temple_3.nbt",
        "woodland_mansion/entrance.nbt",
    ],
)
def test_minecraft_structures(minecraft_data_pack, filename):
    StructureFile.load(
        minecraft_data_pack / "data" / "minecraft" / "structures" / filename
    )
