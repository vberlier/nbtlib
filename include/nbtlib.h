#ifndef NBTLIB_H
#define NBTLIB_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdlib.h>

#ifdef _MSC_VER

#define bswap_16(x) _byteswap_ushort(x)
#define bswap_32(x) _byteswap_ulong(x)
#define bswap_64(x) _byteswap_uint64(x)

#elif defined(__APPLE__)

#include <libkern/OSByteOrder.h>
#define bswap_16(x) OSSwapInt16(x)
#define bswap_32(x) OSSwapInt32(x)
#define bswap_64(x) OSSwapInt64(x)

#else

#include <byteswap.h>

#endif

#define NBTLIB_TAG_END 0
#define NBTLIB_TAG_BYTE 1
#define NBTLIB_TAG_SHORT 2
#define NBTLIB_TAG_INT 3
#define NBTLIB_TAG_LONG 4
#define NBTLIB_TAG_FLOAT 5
#define NBTLIB_TAG_DOUBLE 6
#define NBTLIB_TAG_BYTE_ARRAY 7
#define NBTLIB_TAG_STRING 8
#define NBTLIB_TAG_LIST 9
#define NBTLIB_TAG_COMPOUND 10
#define NBTLIB_TAG_INT_ARRAY 11
#define NBTLIB_TAG_LONG_ARRAY 12

#define NBTLIB_OP_SET_NAME (1 << 8)
#define NBTLIB_OP_EXTEND_LIST (2 << 8)
#define NBTLIB_OP_EXTEND_COMPOUND (3 << 8)

#define NBTLIB_ERROR_EOF 1
#define NBTLIB_ERROR_TYPE 2
#define NBTLIB_ERROR_DEPTH 3
#define NBTLIB_ERROR_MEMORY 4

// Scanning nbt returns an index of tags which aren't fully realized yet but instead
// contain all the information necessary to unpack them as needed by the higher-level API.
//
// Note that the order of fields in the tag struct matters. For example, placing the tag
// type first would create a lot of unnecessary padding.
typedef struct
{
    // We keep a pointer to the payload of the tag in the original buffer.
    //
    // The pointer is used to unpack the tag and also in a fast path during serialization
    // to reuse parts of the original buffer.
    const char *payload;

    // The children field is used differently depending on the tag type.
    //
    // For compound tags we store the number of nested tags. This includes the number of
    // immediate children but also their recursive children as well. This is useful as it
    // makes it possible to use the value as an offset to the compound tag's next sibling.
    //
    // List tags are similar to compound tags as they also store the number of immediate
    // and recursive children. However, lists of numeric tags benefit from an optimization
    // that avoids creating actual nested tags for its children as you only need to know
    // the list subtype and its length to unpack any of its elements.
    //
    // String and array tags use the children field to store their length. The field is
    // unused for numeric tags.
    uint32_t children;

    // If the tag has an associated name, the name_length field is used to store the
    // length of the name. Otherwise it's initialized to 0.
    uint16_t name_length;

    // We store the type of the tag using one of the NBTLIB_TAG_* values.
    char type;
} nbtlib_tag_t;

// The tag index emitted by the scanner.
//
// It holds a pointer to the first element of the tag vector, the number of tags, and a
// boolean indicating whether the values should be byteswapped when unpacking.
//
// Unless the scan returns a non-zero status the calling code should make sure to free the
// tags pointer.
typedef struct
{
    nbtlib_tag_t *tags;
    uint32_t tags_count;
    bool native;
} nbtlib_index_t;

static inline int nbtlib_scan(const char *buffer, size_t buffer_size, char *stack,
                              size_t stack_size, char byteorder, nbtlib_index_t *index)
{
#ifndef NBTLIB_USE_LIBC_MALLOC
    // Use Python's memory utilities if not compiling with NBTLIB_USE_LIBC_MALLOC. This
    // way it works with the Cython module out of the box but it's also possible to use
    // the function in a standalone program (for testing).
    void *PyMem_Realloc(void *p, size_t n);
    void PyMem_Free(void *p);
#endif

    // Vector for accumulating tags.
    nbtlib_tag_t *tags = NULL;
    uint32_t tags_count = 0;
    uint32_t tags_capacity = 0;

    // Determine if the byteorder is native. The 16-bit integer 0x3e3c corresponds to
    // "><" or "<>" depending on platform endianness. The byteorder argument is '<' for
    // little-endian and '>' for big-endian so the byteorder is native if the first byte
    // matches the argument.
    uint16_t endian_check = 0x3e3c;
    bool native = *(char *)&endian_check == byteorder;

    // Lookup table for getting the payload size of numeric tags.
    const uint8_t numeric_sizes[] = {
        [NBTLIB_TAG_BYTE] = 1,       [NBTLIB_TAG_SHORT] = 2,
        [NBTLIB_TAG_INT] = 4,        [NBTLIB_TAG_LONG] = 8,
        [NBTLIB_TAG_FLOAT] = 4,      [NBTLIB_TAG_DOUBLE] = 8,
        [NBTLIB_TAG_BYTE_ARRAY] = 1, [NBTLIB_TAG_INT_ARRAY] = 4,
        [NBTLIB_TAG_LONG_ARRAY] = 8};

    // Running index for reading data from the buffer.
    size_t i = 0;

    // Status code. It's either 0 or one of the NBTLIB_ERROR_* values.
    int status = 0;

    // The current tag.
    nbtlib_tag_t current = {NULL, 0, 0, NBTLIB_TAG_END};

    // Fixed-sized stack machine.
    //
    // The backing memory is provided by the calling code. This makes it possible to
    // control the maximum nesting allowed.
    //
    // The operations are represented by NBTLIB_TAG_* values to signify that a tag of a
    // specific type should be emitted and with additional NBTLIB_OP_* values for handling
    // tag names and collecting nested tags for list and compound tags.
    //
    // The operations for extending list and compound tags require some additional
    // arguments like the index of the parent tag. These are pushed to the stack just
    // below NBTLIB_OP_EXTEND_LIST or NBTLIB_OP_EXTEND_COMPOUND.
    uint32_t *ops = (uint32_t *)stack;
    uint32_t ops_count = 0;
    uint32_t ops_capacity = stack_size / sizeof(uint32_t);

    // We initialize the top of the stack with NBTLIB_OP_SET_NAME to indicate that we
    // should start by processing a standalone tag. Of course when pushing anything on
    // the stack we need to make sure that we're not running out of space. If there's no
    // room left we return NBTLIB_ERROR_DEPTH.

    if (ops_count + 1 > ops_capacity)
    {
        return NBTLIB_ERROR_DEPTH;
    }

    ops[ops_count++] = NBTLIB_OP_SET_NAME;

    // The main loop driving the stack machine.
    while (ops_count > 0)
    {
        // Pop the top of the stack. This returns either a tag id matching one of the
        // NBTLIB_TAG_* values or a special NBTLIB_OP_* value. The operation can also be
        // an invalid tag id (12 < op < 256) in case the input buffer is invalid or being
        // read with the wrong byteorder.
        uint32_t op = ops[--ops_count];

        if (op >= NBTLIB_TAG_BYTE && op <= NBTLIB_TAG_DOUBLE)
        {
            // For all numeric tags we just need to skip the payload.

            current.payload = buffer + i;
            current.children = 0;
            i += numeric_sizes[op];
        }

        else if (op == NBTLIB_TAG_STRING)
        {
            // For string tags we first extract the length and then skip all the
            // characters of the string.

            if (i + 2 > buffer_size)
            {
                status = NBTLIB_ERROR_EOF;
                break;
            }

            uint16_t string_length =
                native ? *(uint16_t *)&buffer[i] : bswap_16(*(uint16_t *)&buffer[i]);

            current.payload = buffer + i + 2;
            current.children = string_length;

            i += 2 + string_length;
        }

        else if (op == NBTLIB_TAG_BYTE_ARRAY || op == NBTLIB_TAG_INT_ARRAY ||
                 op == NBTLIB_TAG_LONG_ARRAY)
        {
            // For array tags we extract the length and then skip all the elements. The
            // length of arrays is supposed to be a signed 32-bit integer but in practice
            // because the size can't be negative it's ok to parse it as unsigned.

            if (i + 4 > buffer_size)
            {
                status = NBTLIB_ERROR_EOF;
                break;
            }

            uint32_t array_length =
                native ? *(uint32_t *)&buffer[i] : bswap_32(*(uint32_t *)&buffer[i]);

            current.payload = buffer + i + 4;
            current.children = array_length;

            i += 4 + array_length * numeric_sizes[op];
        }

        else if (op == NBTLIB_TAG_LIST)
        {
            // For list tags we figure out the subtype and the length. If we have a list
            // of numeric tags we skip them right away. Otherwise, if we have a list with
            // dynamically sized elements we push NBTLIB_OP_EXTEND_LIST on the stack.

            if (i + 5 > buffer_size)
            {
                status = NBTLIB_ERROR_EOF;
                break;
            }

            uint32_t subtype = buffer[i];
            uint32_t list_length = native ? *(uint32_t *)&buffer[i + 1]
                                          : bswap_32(*(uint32_t *)&buffer[i + 1]);

            current.payload = buffer + i + 5;

            if (subtype <= NBTLIB_TAG_DOUBLE)
            {
                current.children = list_length;

                i += 5 + list_length * numeric_sizes[subtype];
            }
            else
            {
                if (ops_count + 4 > ops_capacity)
                {
                    status = NBTLIB_ERROR_DEPTH;
                    break;
                }

                current.children = 0;

                i += 5;

                ops[ops_count++] = tags_count;
                ops[ops_count++] = subtype;
                ops[ops_count++] = list_length;
                ops[ops_count++] = NBTLIB_OP_EXTEND_LIST;
            }
        }

        else if (op == NBTLIB_OP_EXTEND_LIST)
        {
            // Lists with dynamically sized elements are assembled with repeated
            // NBTLIB_OP_EXTEND_LIST operations. Below the actual operation, the stack
            // will hold the remaining number of elements to collect, the list subtype,
            // and the index of the original list tag.
            //
            // First we pop the number of remaining elements and the list subtype. If
            // there are no more elements to collect we pop the index of the original list
            // and we update the number of nested children. Otherwise we push the tag id
            // corresponding to the list subtype on top of another NBTLIB_OP_EXTEND_LIST
            // operation to keep going after scanning the child tag.

            uint32_t remaining = ops[--ops_count];
            uint32_t subtype = ops[--ops_count];

            if (remaining == 0)
            {
                uint32_t parent = ops[--ops_count];
                tags[parent].children = tags_count - parent - 1;
            }
            else
            {
                if (ops_count + 4 > ops_capacity)
                {
                    status = NBTLIB_ERROR_DEPTH;
                    break;
                }

                // Tags inside lists don't have a name so we set the name length to 0.
                current.name_length = 0;

                ops[ops_count++] = subtype;
                ops[ops_count++] = remaining - 1;
                ops[ops_count++] = NBTLIB_OP_EXTEND_LIST;
                ops[ops_count++] = subtype;
            }

            continue;
        }

        else if (op == NBTLIB_TAG_COMPOUND)
        {
            // Compound tags are handled a bit like list tags but we also have to take
            // into account the name of each child tag. Since the payload for compound
            // tags is formed by other tags we immediately push NBTLIB_OP_EXTEND_COMPOUND
            // to the stack.

            if (ops_count + 2 > ops_capacity)
            {
                status = NBTLIB_ERROR_DEPTH;
                break;
            }

            current.payload = buffer + i;
            current.children = 0;

            ops[ops_count++] = tags_count;
            ops[ops_count++] = NBTLIB_OP_EXTEND_COMPOUND;
        }

        else if (op == NBTLIB_OP_EXTEND_COMPOUND)
        {
            // Each time we need to add a new tag to a compound we first need to check if
            // we encountered the TAG_END marker (\x00). If there are no more nested tags
            // we pop the index of the original compound and update the number of nested
            // children.
            //
            // If the current tag should be part of the compound we push
            // NBTLIB_OP_SET_NAME onto the stack on top of another
            // NBTLIB_OP_EXTEND_COMPOUND operation to keep going when we're done scanning
            // the nested tag.

            if (i + 1 > buffer_size)
            {
                status = NBTLIB_ERROR_EOF;
                break;
            }

            if (buffer[i] == NBTLIB_TAG_END)
            {
                uint32_t parent = ops[--ops_count];
                tags[parent].children = tags_count - parent - 1;

                i += 1;
            }
            else
            {
                if (ops_count + 2 > ops_capacity)
                {
                    status = NBTLIB_ERROR_DEPTH;
                    break;
                }

                ops[ops_count++] = NBTLIB_OP_EXTEND_COMPOUND;
                ops[ops_count++] = NBTLIB_OP_SET_NAME;
            }

            continue;
        }

        else if (op == NBTLIB_OP_SET_NAME)
        {
            // For handling tags with names we first extract the tag id and the length of
            // the name, and then we skip all the characters of the name. We push the tag
            // id onto the stack to dispatch to the appropriate tag handler.

            if (i + 3 > buffer_size)
            {
                status = NBTLIB_ERROR_EOF;
                break;
            }

            if (ops_count + 1 > ops_capacity)
            {
                status = NBTLIB_ERROR_DEPTH;
                break;
            }

            char tag_type = buffer[i];
            uint16_t name_length = native ? *(uint16_t *)&buffer[i + 1]
                                          : bswap_16(*(uint16_t *)&buffer[i + 1]);

            current.name_length = name_length;

            i += 3 + name_length;

            ops[ops_count++] = tag_type;

            continue;
        }

        else
        {
            // If we didn't take any of the previous branches this means that the input
            // buffer contained an invalid tag id that was pushed onto the stack.

            status = NBTLIB_ERROR_TYPE;
            break;
        }

        // Now that all the cases are handled we should push the current tag into the tags
        // vector. All the NBTLIB_OP_* operations use a continue statement to skip this
        // part as we only want to push the tag when we pop a tag id from the stack.
        //
        // We also make sure that we didn't skip past the end of the input buffer before
        // pushing the tag.

        if (i > buffer_size)
        {
            status = NBTLIB_ERROR_EOF;
            break;
        }

        current.type = op;

        if (tags_count >= tags_capacity)
        {
            if (tags_capacity == 0)
            {
                tags_capacity = 32;
            }
            else
            {
                tags_capacity *= 2;
            }

            nbtlib_tag_t *tmp_tags;

#ifndef NBTLIB_USE_LIBC_MALLOC
            tmp_tags =
                (nbtlib_tag_t *)PyMem_Realloc(tags, tags_capacity * sizeof(nbtlib_tag_t));
#else
            tmp_tags =
                (nbtlib_tag_t *)realloc(tags, tags_capacity * sizeof(nbtlib_tag_t));
#endif

            if (tmp_tags == NULL)
            {
                status = NBTLIB_ERROR_MEMORY;
                break;
            }

            tags = tmp_tags;
        }

        tags[tags_count++] = current;
    }

    // We can exit the loop normally or by breaking with a status code. If the status is 0
    // this means that there were no errors and we can populate the tag index. Otherwise
    // we need to free the tags pointer.

    if (status == 0)
    {
        index->tags = tags;
        index->tags_count = tags_count;
        index->native = native;
    }
    else
    {
#ifndef NBTLIB_USE_LIBC_MALLOC
        PyMem_Free(tags);
#else
        free(tags);
#endif
    }

    return status;
}

#endif
