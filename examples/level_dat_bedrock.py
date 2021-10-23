from io import BytesIO

from nbtlib import CompoundSchema, File, schema
from nbtlib.tag import (
    INT,
    Byte,
    Float,
    Int,
    List,
    Long,
    String,
    read_numeric,
    write_numeric,
)

# fmt: off
BedrockLevelData = schema("BedrockLevelData", {
    "CenterMapsToOrigin": Byte,
    "Difficulty": Int,
    "FlatWorldLayers": String,
    "ForceGameType": Byte,
    "GameType": Int,
    "Generator": Int,
    "InventoryVersion": String,
    "LANBroadcast": Byte,
    "LastPlayed": Long,
    "LevelName": String,
    "LimitedWorldOriginX": Int,
    "LimitedWorldOriginY": Int,
    "LimitedWorldOriginZ": Int,
    "MultiplayerGame": Byte,
    "NetherScale": Int,
    "NetworkVersion": Int,
    "Platform": Int,
    "PlatformBroadcast": Byte,
    "PlatformBroadcastMode": Int,
    "RandomSeed": Long,
    "SpawnX": Int,
    "SpawnY": Int,
    "SpawnZ": Int,
    "StorageVersion": Int,
    "Time": Long,
    "XBLBroadcast": Byte,
    "XBLBroadcastIntent": Byte,
    "XBLBroadcastMode": Int,
    "abilities": schema("Abilities", {
        "attackmobs": Byte,
        "attackplayers": Byte,
        "buildandmine": Byte,
        "doorsandswitches": Byte,
        "flySpeed": Float,
        "flying": Byte,
        "instabuild": Byte,
        "invulnerable": Byte,
        "lightning": Byte,
        "mayfly": Byte,
        "op": Byte,
        "opencontainers": Byte,
        "permissionsLevel": Int,
        "playerPermissionsLevel": Int,
        "teleport": Byte,
        "walkSpeed": Float,
    }),
    "bonusChestEnabled": Byte,
    "bonusChestSpawned": Byte,
    "commandblockoutput": Byte,
    "commandsEnabled": Byte,
    "currentTick": Long,
    "dodaylightcycle": Byte,
    "doentitydrops": Byte,
    "dofiretick": Byte,
    "domobloot": Byte,
    "domobspawning": Byte,
    "dotiledrops": Byte,
    "doweathercycle": Byte,
    "drowningdamage": Byte,
    "eduLevel": Byte,
    "educationFeaturesEnabled": Byte,
    "experimentalgameplay": Byte,
    "falldamage": Byte,
    "firedamage": Byte,
    "hasBeenLoadedInCreative": Byte,
    "hasLockedBehaviorPack": Byte,
    "hasLockedResourcePack": Byte,
    "immutableWorld": Byte,
    "isFromLockedTemplate": Byte,
    "keepinventory": Byte,
    "lastOpenedWithVersion": List[Int],
    "lightningLevel": Float,
    "lightningTime": Int,
    "maxcommandchainlength": Int,
    "mobgriefing": Byte,
    "naturalregeneration": Byte,
    "prid": String,
    "pvp": Byte,
    "rainLevel": Float,
    "rainTime": Int,
    "sendcommandfeedback": Byte,
    "serverChunkTickRange": Int,
    "showcoordinates": Byte,
    "spawnMobs": Byte,
    "startWithMapEnabled": Byte,
    "texturePacksRequired": Byte,
    "tntexplodes": Byte,
    "worldStartCount": Long,
})
# fmt: on


class BedrockLevelFile(File, CompoundSchema):
    schema = {"": BedrockLevelData}

    def __init__(
        self, level_data=None, version=8, *, gzipped=False, byteorder="little"
    ):
        super().__init__({"": level_data or {}}, gzipped=gzipped, byteorder=byteorder)
        self.version = version

    @classmethod
    def parse(cls, buff, byteorder="little"):
        version = read_numeric(INT, buff, byteorder)
        _length = read_numeric(INT, buff, byteorder)
        self = super().parse(buff, byteorder)
        self.version = version
        return self

    def write(self, buff, byteorder="little"):
        tmp = BytesIO()
        super().write(tmp, byteorder)
        tmp.seek(0)
        data = tmp.read()

        write_numeric(INT, self.version, buff, byteorder)
        write_numeric(INT, len(data), buff, byteorder)
        buff.write(data)

    @classmethod
    def from_buffer(cls, buff, byteorder="little"):
        return super().from_buffer(buff, byteorder)

    @classmethod
    def load(cls, filename, gzipped=False, byteorder="little"):
        return super().load(filename, gzipped, byteorder)
