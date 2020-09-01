__all__ = ["StructureFile", "StructureFileData"]


from nbtlib import File, CompoundSchema, tag


class StructureFileData(CompoundSchema):
    """Schema that matches the Minecraft structure file format."""

    class BlockState(CompoundSchema):
        schema = {
            "Name": tag.String,
            "Properties": tag.Compound,
        }

    class Block(CompoundSchema):
        schema = {
            "state": tag.Int,
            "pos": tag.List[tag.Int],
            "nbt": tag.Compound,
        }

    class Entity(CompoundSchema):
        schema = {
            "pos": tag.List[tag.Double],
            "blockPos": tag.List[tag.Int],
            "nbt": tag.Compound,
        }

    schema = {
        "DataVersion": tag.Int,
        "author": tag.String,
        "size": tag.List[tag.Int],
        "palette": tag.List[BlockState],
        "palettes": tag.List[tag.List[BlockState]],
        "blocks": tag.List[Block],
        "entities": tag.List[Entity],
    }


class StructureFile(File, CompoundSchema):
    """Class representing a Minecraft structure file."""

    schema = {"": StructureFileData}
    strict = True

    def __init__(self, structure_data=None, *, filename=None):
        super().__init__({"": structure_data or {}}, gzipped=True, filename=filename)

    @classmethod
    def load(cls, filename):
        return super().load(filename, gzipped=True)
