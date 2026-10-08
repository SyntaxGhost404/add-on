"""Little-endian NBT writer used for Bedrock .mcstructure files.

Values are wrapped in small typed classes so the exact tag type is always
explicit (Bedrock is strict about byte vs int vs string state values).
"""
import struct

TAG_END, TAG_BYTE, TAG_SHORT, TAG_INT, TAG_LONG, TAG_FLOAT, TAG_DOUBLE = 0, 1, 2, 3, 4, 5, 6
TAG_BYTE_ARRAY, TAG_STRING, TAG_LIST, TAG_COMPOUND, TAG_INT_ARRAY, TAG_LONG_ARRAY = 7, 8, 9, 10, 11, 12


class Tag:
    tag_id = None

    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return f"{type(self).__name__}({self.value!r})"

    def __eq__(self, other):
        return type(self) is type(other) and self.value == other.value

    def __hash__(self):
        return hash((type(self).__name__, repr(self.value)))


class Byte(Tag):
    tag_id = TAG_BYTE


class Short(Tag):
    tag_id = TAG_SHORT


class Int(Tag):
    tag_id = TAG_INT


class Long(Tag):
    tag_id = TAG_LONG


class Float(Tag):
    tag_id = TAG_FLOAT


class Double(Tag):
    tag_id = TAG_DOUBLE


class String(Tag):
    tag_id = TAG_STRING


class List(Tag):
    """Homogeneous list. element_type is the tag class of the items (None for empty)."""
    tag_id = TAG_LIST

    def __init__(self, items, element_type=None):
        items = list(items)
        if element_type is None and items:
            element_type = type(items[0])
        for it in items:
            if element_type is not None and type(it) is not element_type:
                raise TypeError(f"heterogeneous NBT list: {type(it).__name__} vs {element_type.__name__}")
        super().__init__(items)
        self.element_type = element_type


class Compound(Tag):
    tag_id = TAG_COMPOUND

    def __init__(self, value=None):
        super().__init__(dict(value or {}))


class IntArray(Tag):
    tag_id = TAG_INT_ARRAY


def _w_string(out, s):
    b = s.encode('utf-8')
    if len(b) > 0xFFFF:
        raise ValueError('string too long for NBT')
    out += struct.pack('<H', len(b))
    out += b


def _w_payload(out, tag):
    t = type(tag)
    if t is Byte:
        out += struct.pack('<b', tag.value)
    elif t is Short:
        out += struct.pack('<h', tag.value)
    elif t is Int:
        out += struct.pack('<i', tag.value)
    elif t is Long:
        out += struct.pack('<q', tag.value)
    elif t is Float:
        out += struct.pack('<f', tag.value)
    elif t is Double:
        out += struct.pack('<d', tag.value)
    elif t is String:
        _w_string(out, tag.value)
    elif t is List:
        et = tag.element_type.tag_id if tag.element_type is not None else TAG_END
        out += struct.pack('<b', et)
        out += struct.pack('<i', len(tag.value))
        for it in tag.value:
            _w_payload(out, it)
    elif t is Compound:
        for name, child in tag.value.items():
            if not isinstance(child, Tag):
                raise TypeError(f"untyped NBT value for key {name!r}: {child!r}")
            out += struct.pack('<b', child.tag_id)
            _w_string(out, name)
            _w_payload(out, child)
        out += struct.pack('<b', TAG_END)
    elif t is IntArray:
        out += struct.pack('<i', len(tag.value))
        for v in tag.value:
            out += struct.pack('<i', v)
    else:
        raise TypeError(f"unsupported NBT tag {t}")


def dumps(root, name=''):
    """Serialize a root Compound to little-endian NBT bytes."""
    if type(root) is not Compound:
        raise TypeError('root must be a Compound')
    out = bytearray()
    out += struct.pack('<b', TAG_COMPOUND)
    _w_string(out, name)
    _w_payload(out, root)
    return bytes(out)


def to_plain(tag):
    """Convert typed tags into plain python values (for comparisons/tests)."""
    t = type(tag)
    if t is Compound:
        return {k: to_plain(v) for k, v in tag.value.items()}
    if t is List:
        return [to_plain(v) for v in tag.value]
    return tag.value
