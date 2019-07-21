from uuid import UUID

from nbtlib import Long


def combine_uuid(uuid_most_tag, uuid_least_tag):
    uuid_most = uuid_most_tag.as_unsigned
    uuid_least = uuid_least_tag.as_unsigned
    return UUID(int=uuid_most << Long.bits | uuid_least)


def split_uuid(uuid):
    uuid_most = uuid.int >> Long.bits & Long.mask
    uuid_least = uuid.int & Long.mask
    return Long.from_unsigned(uuid_most), Long.from_unsigned(uuid_least)


if __name__ == "__main__":
    # f8de0ffd-21e9-4cf2-804e-ecf099a67e39 is represented by
    # UUIDMost: -513955727603577614L
    # UUIDLeast: -9201156470557213127L

    uuid_most_tag = Long(-513955727603577614)
    uuid_least_tag = Long(-9201156470557213127)

    uuid = combine_uuid(uuid_most_tag, uuid_least_tag)
    assert split_uuid(uuid) == (uuid_most_tag, uuid_least_tag)

    print(uuid)
