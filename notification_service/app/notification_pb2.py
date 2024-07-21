# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: notification.proto
"""Generated protocol buffer code."""
from google.protobuf.internal import builder as _builder
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import symbol_database as _symbol_database
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x12notification.proto\"\xd3\x01\n\x04User\x12\n\n\x02id\x18\x01 \x01(\x05\x12\x0f\n\x07user_id\x18\x02 \x01(\t\x12\x10\n\x08username\x18\x03 \x01(\t\x12\r\n\x05\x65mail\x18\x04 \x01(\t\x12\x10\n\x08password\x18\x05 \x01(\t\x12\x14\n\x0c\x61\x63\x63\x65ss_token\x18\x06 \x01(\t\x12\x15\n\rrefresh_token\x18\x07 \x01(\t\x12\x15\n\rerror_message\x18\x08 \x01(\t\x12\x1d\n\x06option\x18\t \x01(\x0e\x32\r.SelectOption\x12\x18\n\x10http_status_code\x18\n \x01(\x03\"\xbb\x02\n\tInventory\x12\n\n\x02id\x18\x01 \x01(\x05\x12\x12\n\nproduct_id\x18\x02 \x01(\t\x12\x14\n\x0cinventory_id\x18\x03 \x01(\t\x12\x13\n\x0bstock_level\x18\x04 \x01(\x03\x12\x17\n\x0f\x61\x64\x64_stock_level\x18\x05 \x01(\x03\x12\x1a\n\x12reduce_stock_level\x18\x06 \x01(\x03\x12\x16\n\x0ereserved_stock\x18\x07 \x01(\x03\x12\x0c\n\x04name\x18\x08 \x01(\t\x12\x13\n\x0b\x64\x65scription\x18\t \x01(\t\x12\r\n\x05price\x18\n \x01(\x02\x12\x14\n\x0cis_available\x18\x0b \x01(\x08\x12\x15\n\rerror_message\x18\x0c \x01(\t\x12\x1d\n\x06option\x18\r \x01(\x0e\x32\r.SelectOption\x12\x18\n\x10http_status_code\x18\x0e \x01(\x03\"\xd2\x01\n\x07Product\x12\n\n\x02id\x18\x01 \x01(\x05\x12\x12\n\nproduct_id\x18\x02 \x01(\t\x12\x0c\n\x04name\x18\x03 \x01(\t\x12\x13\n\x0b\x64\x65scription\x18\x04 \x01(\t\x12\r\n\x05price\x18\x05 \x01(\x02\x12\x14\n\x0cis_available\x18\x06 \x01(\x08\x12\x0f\n\x07message\x18\x07 \x01(\t\x12\x15\n\rerror_message\x18\x08 \x01(\t\x12\x1d\n\x06option\x18\t \x01(\x0e\x32\r.SelectOption\x12\x18\n\x10http_status_code\x18\n \x01(\x03\" \n\x08UserList\x12\x14\n\x05users\x18\x01 \x03(\x0b\x32\x05.User*\x9b\x01\n\x0cSelectOption\x12\x07\n\x03GET\x10\x00\x12\x0b\n\x07GET_ALL\x10\x01\x12\x07\n\x03\x41\x44\x44\x10\x02\x12\x0c\n\x08REGISTER\x10\x03\x12\t\n\x05LOGIN\x10\x04\x12\x10\n\x0c\x43URRENT_USER\x10\x05\x12\x11\n\rREFRESH_TOKEN\x10\x06\x12\n\n\x06\x43REATE\x10\x07\x12\n\n\x06UPDATE\x10\x08\x12\n\n\x06REDUCE\x10\t\x12\n\n\x06\x44\x45LETE\x10\nb\x06proto3')

_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, globals())
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'notification_pb2', globals())
if _descriptor._USE_C_DESCRIPTORS == False:

  DESCRIPTOR._options = None
  _SELECTOPTION._serialized_start=802
  _SELECTOPTION._serialized_end=957
  _USER._serialized_start=23
  _USER._serialized_end=234
  _INVENTORY._serialized_start=237
  _INVENTORY._serialized_end=552
  _PRODUCT._serialized_start=555
  _PRODUCT._serialized_end=765
  _USERLIST._serialized_start=767
  _USERLIST._serialized_end=799
# @@protoc_insertion_point(module_scope)