# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: order.proto
"""Generated protocol buffer code."""
from google.protobuf.internal import builder as _builder
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import symbol_database as _symbol_database
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x0border.proto\"\xe6\x01\n\x05Order\x12\n\n\x02id\x18\x01 \x01(\x05\x12\x10\n\x08order_id\x18\x02 \x01(\t\x12\x12\n\nproduct_id\x18\x03 \x01(\t\x12\x10\n\x08quantity\x18\x04 \x01(\x03\x12\x18\n\x10shipping_address\x18\x05 \x01(\t\x12\x16\n\x0e\x63ustomer_notes\x18\x06 \x01(\t\x12\x17\n\x0fstock_available\x18\x07 \x01(\x08\x12\x15\n\rerror_message\x18\x08 \x01(\t\x12\x1d\n\x06option\x18\t \x01(\x0e\x32\r.SelectOption\x12\x18\n\x10http_status_code\x18\n \x01(\x03\"#\n\tOrderList\x12\x16\n\x06Orders\x18\x01 \x03(\x0b\x32\x06.Order*H\n\x0cSelectOption\x12\x07\n\x03GET\x10\x00\x12\x0b\n\x07GET_ALL\x10\x01\x12\n\n\x06\x43REATE\x10\x02\x12\n\n\x06UPDATE\x10\x03\x12\n\n\x06\x44\x45LETE\x10\x04\x62\x06proto3')

_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, globals())
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'order_pb2', globals())
if _descriptor._USE_C_DESCRIPTORS == False:

  DESCRIPTOR._options = None
  _SELECTOPTION._serialized_start=285
  _SELECTOPTION._serialized_end=357
  _ORDER._serialized_start=16
  _ORDER._serialized_end=246
  _ORDERLIST._serialized_start=248
  _ORDERLIST._serialized_end=283
# @@protoc_insertion_point(module_scope)
