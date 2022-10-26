# cython: language_level=3


__all__ = ["TagIndex"]


from cpython.mem cimport PyMem_Malloc, PyMem_Free
from libc.stdint cimport uint16_t, uint32_t

from .error import NbtEOFError, NbtTypeError, NbtDepthError


cdef extern from "nbtlib.h":
    cdef enum NBTLIB_TAG:
        NBTLIB_TAG_END
        NBTLIB_TAG_BYTE
        NBTLIB_TAG_SHORT
        NBTLIB_TAG_INT
        NBTLIB_TAG_LONG
        NBTLIB_TAG_FLOAT
        NBTLIB_TAG_DOUBLE
        NBTLIB_TAG_BYTE_ARRAY
        NBTLIB_TAG_STRING
        NBTLIB_TAG_LIST
        NBTLIB_TAG_COMPOUND
        NBTLIB_TAG_INT_ARRAY
        NBTLIB_TAG_LONG_ARRAY

    cdef enum NBTLIB_ERROR:
        NBTLIB_ERROR_EOF
        NBTLIB_ERROR_TYPE
        NBTLIB_ERROR_DEPTH
        NBTLIB_ERROR_MEMORY

    ctypedef struct nbtlib_tag_t:
        const char *payload
        uint32_t children
        uint16_t name_length
        char type

    ctypedef struct nbtlib_index_t:
        nbtlib_tag_t *tags
        uint32_t tags_count
        bint native

    int nbtlib_scan(
        const char *buffer,
        size_t buffer_size,
        char *stack,
        size_t stack_size,
        char byteorder,
        nbtlib_index_t *index
    )


cdef class TagIndex:
    cdef const char[::1] obj
    cdef nbtlib_index_t data

    def __init__(self, const char[::1] obj not None, str byteorder not None, size_t stack_size):
        self.obj = obj
        self.data.tags = NULL
        self.data.tags_count = 0
        self.data.native = False

        cdef char *stack = <char *>PyMem_Malloc(stack_size)
        if not stack:
            raise MemoryError(f"Couldn't allocate {stack_size} bytes for the nbt scanner.")

        status = nbtlib_scan(
            &obj[0],
            obj.shape[0],
            stack,
            stack_size,
            b"<" if byteorder == "little" else b">",
            &self.data
        )

        if not status:
            return

        if status in [NBTLIB_ERROR_EOF, NBTLIB_ERROR_TYPE] and byteorder not in ["big", "little"]:
            status = nbtlib_scan(
                &obj[0],
                obj.shape[0],
                stack,
                stack_size,
                b"<",
                &self.data
            )

        PyMem_Free(stack)

        if status == NBTLIB_ERROR_EOF:
            raise NbtEOFError("Unexpected end of input.")
        elif status == NBTLIB_ERROR_TYPE:
            raise NbtTypeError("Invalid tag type.")
        elif status == NBTLIB_ERROR_DEPTH:
            raise NbtDepthError("Excessively nested input. Try using a bigger stack_size.")
        elif status == NBTLIB_ERROR_MEMORY:
            raise MemoryError("Couldn't allocate enough space to hold the tag index.")

    def __dealloc__(self):
        PyMem_Free(self.data.tags)
