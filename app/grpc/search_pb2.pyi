from google.protobuf import struct_pb2 as _struct_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class Empty(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class SearchRequest(_message.Message):
    __slots__ = ("query",)
    QUERY_FIELD_NUMBER: _ClassVar[int]
    query: str
    def __init__(self, query: _Optional[str] = ...) -> None: ...

class SearchResponse(_message.Message):
    __slots__ = ("top", "artists", "labels", "releases", "tracks", "playlists")
    TOP_FIELD_NUMBER: _ClassVar[int]
    ARTISTS_FIELD_NUMBER: _ClassVar[int]
    LABELS_FIELD_NUMBER: _ClassVar[int]
    RELEASES_FIELD_NUMBER: _ClassVar[int]
    TRACKS_FIELD_NUMBER: _ClassVar[int]
    PLAYLISTS_FIELD_NUMBER: _ClassVar[int]
    top: _containers.RepeatedCompositeFieldContainer[_struct_pb2.Struct]
    artists: _containers.RepeatedCompositeFieldContainer[_struct_pb2.Struct]
    labels: _containers.RepeatedCompositeFieldContainer[_struct_pb2.Struct]
    releases: _containers.RepeatedCompositeFieldContainer[_struct_pb2.Struct]
    tracks: _containers.RepeatedCompositeFieldContainer[_struct_pb2.Struct]
    playlists: _containers.RepeatedCompositeFieldContainer[_struct_pb2.Struct]
    def __init__(self, top: _Optional[_Iterable[_Union[_struct_pb2.Struct, _Mapping]]] = ..., artists: _Optional[_Iterable[_Union[_struct_pb2.Struct, _Mapping]]] = ..., labels: _Optional[_Iterable[_Union[_struct_pb2.Struct, _Mapping]]] = ..., releases: _Optional[_Iterable[_Union[_struct_pb2.Struct, _Mapping]]] = ..., tracks: _Optional[_Iterable[_Union[_struct_pb2.Struct, _Mapping]]] = ..., playlists: _Optional[_Iterable[_Union[_struct_pb2.Struct, _Mapping]]] = ...) -> None: ...

class ItemListResponse(_message.Message):
    __slots__ = ("results",)
    RESULTS_FIELD_NUMBER: _ClassVar[int]
    results: _containers.RepeatedCompositeFieldContainer[_struct_pb2.Struct]
    def __init__(self, results: _Optional[_Iterable[_Union[_struct_pb2.Struct, _Mapping]]] = ...) -> None: ...

class StatusResponse(_message.Message):
    __slots__ = ("success",)
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    success: bool
    def __init__(self, success: _Optional[bool] = ...) -> None: ...
