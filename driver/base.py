#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2020/8/25 21:15
# @Author  : liuhui
# @Detail  : 基础类

from enum import unique, Enum


# 设备获取异常
class DeviceAcquireError(Exception):

    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return self.msg


# 设备连接状态
@unique
class DeviceStatusEnum(Enum):
    # adb连接正常
    ADB_READY = 'ADB_READY'
    # appium连接正常
    APPIUM_READY = 'APPIUM_READY'
    # stf连接正常
    STF_READY = 'STF_READY'
    # stf被占用
    STF_LOCKED = 'STF_LOCKED'


# 申请设备类型
@unique
class DeviceAcquireTypeEnum(Enum):
    # 单个
    SINGLE = 'SINGLE'
    # 单个指定设备
    SINGLE_SPECIFIED = 'SINGLE_SPECIFIED'
    # 所有
    ALL = 'ALL'
