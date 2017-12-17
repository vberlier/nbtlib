from nbtlib import *


LevelData = schema('LevelData', {
    'DataVersion': Int,
    'DimensionData': schema('DimensionData', {
        '1': schema('EndData', {
            'DragonFight': schema('DragonFight', {
                'ExitPortalLocation': schema('ExitPortalLocation', {
                    'X': Byte,
                    'Y': Byte,
                    'Z': Byte
                }),
                'Gateways': List[Int],
                'DragonKilled': Byte,
                'DragonUUIDLeast': Long,
                'DragonUUIDMost': Long,
                'PreviouslyKilled': Byte
            })
        })
    }),
    'version': Int,
    'initialized': Byte,
    'LevelName': String,
    'generatorName': String,
    'generatorVersion': Int,
    'generatorOptions': String,
    'RandomSeed': Long,
    'MapFeatures': Byte,
    'LastPlayed': Long,
    'SizeOnDisk': Long,
    'allowCommands': Byte,
    'hardcore': Byte,
    'GameType': Int,
    'Difficulty': Byte,
    'DifficultyLocked': Byte,
    'Time': Long,
    'DayTime': Long,
    'SpawnX': Int,
    'SpawnY': Int,
    'SpawnZ': Int,
    'BorderCenterX': Double,
    'BorderCenterZ': Double,
    'BorderSize': Double,
    'BorderSafeZone': Double,
    'BorderWarningBlocks': Double,
    'BorderWarningTime': Double,
    'BorderSizeLerpTarget': Double,
    'BorderSizeLerpTime': Long,
    'BorderDamagePerBlock': Double,
    'raining': Byte,
    'rainTime': Int,
    'thundering': Byte,
    'thunderTime': Int,
    'clearWeatherTime': Int,
    'Player': Compound,
    'GameRules': schema('Gamerules', {
        'announceAdvancements': String,
        'commandBlockOutput': String,
        'disableElytraMovementCheck': String,
        'doDaylightCycle': String,
        'doEntityDrops': String,
        'doFireTick': String,
        'doLimitedCrafting': String,
        'doMobLoot': String,
        'doMobSpawning': String,
        'doTileDrops': String,
        'doWeatherCycle': String,
        'keepInventory': String,
        'logAdminCommands': String,
        'maxCommandChainLength': String,
        'maxEntityCramming': String,
        'mobGriefing': String,
        'naturalRegeneration': String,
        'randomTickSpeed': String,
        'reducedDebugInfo': String,
        'sendCommandFeedback': String,
        'showDeathMessages': String,
        'spawnRadius': String,
        'spectatorsGenerateChunks': String,
    }),
    'Version': schema('Version', {
        'Id': Int,
        'Name': String,
        'Snapshot': Byte
    }),
    'DataPacks': schema('DataPacks', {
        'Enabled': List[String],
        'Disabled': List[String]
    })
})


LevelFileSchema = schema('LevelFileSchema', {
    '': schema('LevelFileRoot', {
        'Data': LevelData
    })
})


class LevelFile(File, LevelFileSchema):
    @property
    def data(self):
        """The level data tag."""
        return self.root['Data']

    @data.setter
    def data(self, value):
        self.root['Data'] = value

    @classmethod
    def load(cls, filename):
        return super().load(filename, True)

    def __enter__(self):
        return self.data
