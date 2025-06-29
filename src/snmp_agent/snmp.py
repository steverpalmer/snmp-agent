from __future__ import annotations
import enum
from typing import Any, overload
import ipaddress


import asn1


class CodeMixin(int):
    @property
    def class_(self) -> int:
        return self & 0xC0

    @property
    def pc(self) -> int:
        return self & 0x20

    @property
    def tag_number(self) -> int:
        return self & 0x1F


# SNMP Version
@enum.unique
class VERSION(enum.IntEnum, CodeMixin):
    V1 = 0x00
    V2C = 0x01


# ASN.1 TAG
@enum.unique
class ASN1(enum.IntEnum, CodeMixin):
    BOOLEAN = 0x01
    INTEGER = 0x02
    OCTET_STRING = 0x04
    NULL = 0x05
    OBJECT_IDENTIFIER = 0x06
    SEQUENCE = 0x30
    IPADDRESS = 0x40
    COUNTER32 = 0x41
    GAUGE32 = 0x42
    TIME_TICKS = 0x43
    COUNTER64 = 0x46
    NO_SUCH_OBJECT = 0x80
    NO_SUCH_INSTANCE = 0x81
    END_OF_MIB_VIEW = 0x82

    GET_REQUEST = 0xA0
    GET_NEXT_REQUEST = 0xA1
    GET_RESPONSE = 0xA2
    SET_REQUEST = 0xA3
    GET_BULK_REQUEST = 0xA5


class SNMPValue:
    def __init__(self, tag: ASN1) -> None:
        self.tag = tag

    @property
    def class_(self) -> int:
        return self.tag.class_

    @property
    def pc(self) -> int:
        return self.tag.pc

    @property
    def tag_number(self) -> int:
        return self.tag.tag_number


class SNMPLeafValue(SNMPValue):
    def __init__(self, value: Any, tag: ASN1) -> None:
        super().__init__(tag)
        self.value = value

    def encode(self) -> bytes:
        raise NotImplementedError


class Integer(SNMPLeafValue):
    def __init__(self, value: int) -> None:
        super().__init__(value, ASN1.INTEGER)

    def encode(self) -> bytes:
        return asn1.Encoder._encode_integer(self.value)


class Boolean(SNMPLeafValue):
    def __init__(self, value: bool) -> None:
        super().__init__(value, ASN1.INTEGER)

    def encode(self) -> bytes:
        return asn1.Encoder._encode_boolean(self.value)


class OctetString(SNMPLeafValue):
    def __init__(self, value: str) -> None:
        super().__init__(value, ASN1.OCTET_STRING)

    def encode(self) -> bytes:
        return asn1.Encoder._encode_octet_string(self.value)


class Null(SNMPLeafValue):
    def __init__(self) -> None:
        super().__init__(None, ASN1.NULL)

    def encode(self) -> bytes:
        return asn1.Encoder._encode_null()


class ObjectIdentifier(SNMPLeafValue):
    def __init__(self, value: str) -> None:
        super().__init__(value, ASN1.OBJECT_IDENTIFIER)

    def encode(self) -> bytes:
        return asn1.Encoder()._encode_object_identifier(self.value)


class IPAddress(SNMPLeafValue):
    def __init__(self, value: str) -> None:
        super().__init__(value, ASN1.IPADDRESS)

    def encode(self) -> bytes:
        return ipaddress.IPv4Address(self.value).packed


class Counter32(SNMPLeafValue):
    def __init__(self, value: int) -> None:
        super().__init__(value, ASN1.COUNTER32)

    def encode(self) -> bytes:
        return asn1.Encoder._encode_integer(self.value)


class Gauge32(SNMPLeafValue):
    def __init__(self, value: int) -> None:
        super().__init__(value, ASN1.GAUGE32)

    def encode(self) -> bytes:
        return asn1.Encoder._encode_integer(self.value)


class TimeTicks(SNMPLeafValue):
    def __init__(self, value: int) -> None:
        super().__init__(value, ASN1.TIME_TICKS)

    def encode(self) -> bytes:
        return asn1.Encoder._encode_integer(self.value)


class Counter64(SNMPLeafValue):
    def __init__(self, value: int) -> None:
        super().__init__(value, ASN1.COUNTER64)

    def encode(self) -> bytes:
        return asn1.Encoder._encode_integer(self.value)


class NoSuchObject(SNMPLeafValue):
    def __init__(self) -> None:
        super().__init__(None, ASN1.NO_SUCH_OBJECT)

    def encode(self) -> bytes:
        return b""


class NoSuchInstance(SNMPLeafValue):
    def __init__(self) -> None:
        super().__init__(None, ASN1.NO_SUCH_INSTANCE)

    def encode(self) -> bytes:
        return b""


class EndOfMibView(SNMPLeafValue):
    def __init__(self) -> None:
        super().__init__(None, ASN1.END_OF_MIB_VIEW)

    def encode(self) -> bytes:
        return b""


class SNMPConstructedValue(SNMPValue):
    pass


class Sequence(SNMPConstructedValue):
    def __init__(self) -> None:
        super().__init__(ASN1.SEQUENCE)


class SnmpContext(SNMPConstructedValue):
    pass


class SnmpGetContext(SnmpContext):
    def __init__(self) -> None:
        super().__init__(ASN1.GET_REQUEST)


class SnmpGetNextContext(SnmpContext):
    def __init__(self) -> None:
        super().__init__(ASN1.GET_NEXT_REQUEST)


class SnmpGetBulkContext(SnmpContext):
    def __init__(self) -> None:
        super().__init__(ASN1.GET_BULK_REQUEST)


class SnmpGetResponseContext(SnmpContext):
    def __init__(self) -> None:
        super().__init__(ASN1.GET_RESPONSE)


_TAG_2_CONEXT = {
    ASN1.GET_REQUEST: SnmpGetContext,
    ASN1.GET_NEXT_REQUEST: SnmpGetNextContext,
    ASN1.GET_BULK_REQUEST: SnmpGetBulkContext
}


class Encoder:
    _encode: asn1.Encoder

    def __init__(self) -> None:
        self._encoder = asn1.Encoder()
        self._encoder.start()

    def enter(self, value: SNMPConstructedValue):
        self._encoder.enter(cls=value.class_, nr=value.tag_number)

    def leave(self) -> None:
        self._encoder.leave()

    def write(self, value: SNMPLeafValue) -> None:
        self._encoder._emit_tag(
            cls=value.class_, typ=value.pc, nr=value.tag_number
        )
        value_bytes = value.encode()
        self._encoder._emit_length(len(value_bytes))
        self._encoder._emit(value_bytes)

    def output(self) -> bytes:
        return self._encoder.output()


def encode_response(response: SNMPResponse) -> bytes:
    encoder = Encoder()

    encoder.enter(Sequence())
    encoder.write(Integer(response.version))
    encoder.write(OctetString(response.community))

    encoder.enter(response.context)
    encoder.write(Integer(response.request_id))
    encoder.write(Integer(response.error_status))
    encoder.write(Integer(response.error_index))

    encoder.enter(Sequence())
    for variable_binding in response.variable_bindings:
        encoder.enter(Sequence())
        encoder.write(ObjectIdentifier(variable_binding.oid))
        encoder.write(variable_binding.value)
        encoder.leave()
    encoder.leave()
    encoder.leave()
    encoder.leave()

    return encoder.output()


class Decoder:
    def __init__(self, data: bytes) -> None:
        self._decoder = asn1.Decoder()
        self._decoder.start(data=data)

    def enter(self) -> None:
        self._decoder.enter()

    def read(self) -> tuple[Any, Any]:
        # TODO: Look into response type warning
        return self._decoder.read()  # (asn1.Tag, value)

    def peek(self) -> asn1.Tag:
        return self._decoder.peek()

    def eof(self) -> bool:
        return self._decoder.eof()

    def leave(self) -> None:
        self._decoder.leave()


def decode_request(data: bytes) -> SNMPRequest:
    decoder = Decoder(data=data)

    # Get version and community
    decoder.enter()
    _, _value = decoder.read()
    version_code: int = _value
    try:
        version = VERSION(version_code)
    except KeyError:
        raise NotImplementedError(
            f"SNMP Version code '{version_code}' is not implemented"
        ) from None

    _, _value = decoder.read()
    community = _value.decode()

    # Get pdu_type, request_id, non_repeaters and max_repetitions
    _tag = decoder.peek()
    _pdu_type_code = ASN1(_tag.cls | _tag.typ | _tag.nr)
    try:
        context = _TAG_2_CONEXT[_pdu_type_code]()
    except KeyError:
        raise NotImplementedError(
            f"PDU-TYPE code '{_pdu_type_code}' is not implemented"
        )

    decoder.enter()
    _, _value = decoder.read()
    request_id: int = _value

    non_repeaters: int
    max_repetitions: int
    if isinstance(context, SnmpGetBulkContext):
        _, _value = decoder.read()
        non_repeaters = _value
        _, _value = decoder.read()
        max_repetitions = _value
    else:
        _, _ = decoder.read()
        _, _ = decoder.read()
        non_repeaters = 0
        max_repetitions = 0

    # Get variable-bindings
    decoder.enter()
    variable_bindings = []
    while not decoder.eof():
        # Get oid, type and value
        decoder.enter()
        _, _value = decoder.read()
        oid: str = _value
        _, _ = decoder.read()
        variable_bindings.append(VariableBinding(oid=oid, value=Null()))
        decoder.leave()
    decoder.leave()
    decoder.leave()
    decoder.leave()

    return SNMPRequest(
        version=version,
        community=community,
        context=context,
        request_id=request_id,
        non_repeaters=non_repeaters,
        max_repetitions=max_repetitions,
        variable_bindings=variable_bindings,
    )


class SNMP:
    def __init__(self) -> None:
        pass

    def to_dict(self) -> dict[str, Any]:
        dict_ = SNMP._to_primitive(self)
        return dict_

    @overload
    @staticmethod
    def _to_primitive(value: dict) -> dict: ...

    @overload
    @staticmethod
    def _to_primitive(value: list) -> list: ...

    @overload
    @staticmethod
    def _to_primitive(value: bool) -> bool: ...

    @overload
    @staticmethod
    def _to_primitive(value: int) -> int: ...

    @overload
    @staticmethod
    def _to_primitive(value: str) -> str: ...

    @overload
    @staticmethod
    def _to_primitive(value: bytes) -> bytes: ...

    @overload
    @staticmethod
    def _to_primitive(value: None) -> None: ...

    @overload
    @staticmethod
    def _to_primitive(value) -> dict: ...

    @staticmethod
    def _to_primitive(value):
        match value:
            case dict():
                _dict = {}
                for k, v in value.items():
                    _dict[k] = SNMP._to_primitive(v)
                return _dict
            case list():
                items = []
                for item in value:
                    items.append(SNMP._to_primitive(item))
                return items
            case int() | str() | bool() | bytes() | None:
                return value
            case _:
                _dict = {}
                for k, v in vars(value).items():
                    _dict[k] = SNMP._to_primitive(v)
                return _dict


class SNMPRequest(SNMP):
    def __init__(
        self,
        version: VERSION,
        community: str,
        context: SnmpContext,
        request_id: int,
        variable_bindings: list[VariableBinding],
        non_repeaters: int = 0,
        max_repetitions: int = 0,
    ) -> None:
        self.version = version
        self.community = community
        self.context = context
        self.request_id = request_id
        self.non_repeaters = non_repeaters
        self.max_repetitions = max_repetitions
        self.variable_bindings = variable_bindings

    def create_response(
        self,
        variable_bindings: list[VariableBinding],
        error_status: int = 0,
        error_index: int = 0,
    ) -> SNMPResponse:
        return SNMPResponse(
            version=self.version,
            community=self.community,
            request_id=self.request_id,
            variable_bindings=variable_bindings,
            error_status=error_status,
            error_index=error_index,
        )


class SNMPResponse(SNMP):
    def __init__(
        self,
        version: VERSION,
        community: str,
        request_id: int,
        variable_bindings: list[VariableBinding],
        error_status: int = 0,
        error_index: int = 0,
    ) -> None:
        self.version = version
        self.community = community
        self.context = SnmpGetResponseContext()
        self.request_id = request_id
        self.error_status = error_status
        self.error_index = error_index
        self.variable_bindings = variable_bindings


class VariableBinding(SNMP):
    def __init__(self, oid: str, value: SNMPLeafValue) -> None:
        self.oid = oid.lstrip(".")
        self.value = value

    def encode(self) -> bytes:
        return self.value.encode()
