__all__ = [
    "NbtError",
    "NbtEOFError",
    "NbtTypeError",
    "NbtDepthError",
]


class NbtError(Exception):
    """Base class for all nbtlib errors."""


class NbtEOFError(NbtError):
    """Raised when nbt input ends unexpectedly."""


class NbtTypeError(NbtError):
    """Raised when nbt input contains an invalid tag type."""


class NbtDepthError(NbtError):
    """Raised when nbt input is too nested."""
