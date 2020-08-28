#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2020/8/18 8:37
# @Author  : liuhui
# @Detail  : stf openapi

# 接口文档详细说明见 https://blog.csdn.net/u011608531/article/details/105283652
import re
import time
import requests
from driver.config import stf_host, stf_token
from driver.ssh_manager import SSHManager
from driver.base import DeviceStatusEnum, DeviceAcquireTypeEnum, DeviceAcquireError

# openapi鉴权

headers = {
    'Authorization': 'Bearer {}'.format(stf_token)
}


def api_stf_user():
    '''
    1、获取当前用户信息
    :return:
    '''
    url = 'http://{}/api/v1/user'.format(stf_host)
    response = requests.get(url, headers=headers)
    return response


def api_stf_devices_get():
    '''
    2、列出所有STF设备
    :return:
    '''
    url = 'http://{}/api/v1/devices'.format(stf_host)
    response = requests.get(url, headers=headers)
    return response


def api_stf_device_detail_get(serial_no):
    '''
    3、返回设备信息
    :param serial_no: 设备序列号
    :return:
    '''
    url = 'http://{}/api/v1/devices/{}'.format(stf_host, serial_no)
    response = requests.get(url, headers=headers)
    return response


def api_stf_devices_post(serial_no):
    '''
    4、控制设备
    :param serial_no: 设备序列号
    :return:
    '''
    url = 'http://{}/api/v1/user/devices'.format(stf_host)
    body = {
        'serial': serial_no
    }
    response = requests.post(url, headers=headers, json=body)
    return response


def api_stf_user_devices_get():
    '''
    5、获取当前用户控制的设备
    :return:
    '''
    url = 'http://{}/api/v1/user/devices'.format(stf_host)
    response = requests.get(url, headers=headers)
    return response


def api_stf_user_devices_delete(serial_no):
    '''
    6、释放设备
    :return:
    '''
    url = 'http://{}/api/v1/user/devices/{}'.format(stf_host, serial_no)
    body = {'serial': serial_no}
    response = requests.delete(url, headers=headers, json=body)
    return response


def api_stf_user_devices_remoteConnect_post(serial_no):
    '''
    7、获取设备远程连接url
    :return:
    '''
    url = 'http://{}/api/v1/user/devices/{}/remoteConnect'.format(stf_host, serial_no)
    response = requests.post(url, headers=headers)
    return response


def api_stf_user_devices_remoteConnect_delete(serial_no):
    '''
    8、释放连接url
    :return:
    '''
    url = 'http://{}/api/v1/user/devices/{}/remoteConnect'.format(stf_host, serial_no)
    response = requests.post(url, headers=headers)
    return response


# stf管理类
class StfManager(SSHManager):

    def __init__(self, platform):
        super().__init__(platform)
        self.devices_used = {}

    def _get_devices(self):
        '''
        获取所有可用设备
        :return:
        '''
        self.ssh_connect()

        response = api_stf_devices_get()
        rsp_json = response.json()
        stf_devices = rsp_json.get('devices', [])

        for device in stf_devices:
            platform = device.get('platform', '').lower()
            if platform == self.platform and device.get('serial'):
                owner, serial_no, device_ready = device.get('owner'), device.get('serial'), device.get('ready', False)
                if serial_no in self.devices:
                    device_info = self.devices[serial_no]
                    device_status = device_info['device_status']
                    # 有appium hub才进入下一步状态判断
                    if device_status == DeviceStatusEnum.APPIUM_READY.value:
                        if owner is not None:
                            device_info['device_status'] = DeviceStatusEnum.STF_LOCKED.value
                        elif owner is None and device_ready:
                            device_info['device_status'] = DeviceStatusEnum.STF_READY.value

        print('【{}设备连接状态】:{}'.format(self.platform, self.devices))
        return self.devices

    def acquire_devices(self, acquire_type: DeviceAcquireTypeEnum = DeviceAcquireTypeEnum.SINGLE.value,
                        serial_no=''):
        '''
        占用设备
        :param acquire_type: 设备申请类型
        :return:
        '''
        # 获取所有设备
        devices = self._get_devices()
        # 可用设备
        free_devices = {}

        free_devices_catalog_dict = {}
        for serial_no_inner in devices:
            device_info = devices[serial_no_inner]
            device_status = device_info['device_status']
            # APPIUM_READY和STF_READY才进入判断
            if device_status in [DeviceStatusEnum.APPIUM_READY.value, DeviceStatusEnum.STF_READY.value]:

                if device_status not in free_devices_catalog_dict:
                    free_devices_catalog_dict[device_status] = []

                free_devices_catalog_dict[device_status].append(serial_no_inner)
                free_devices[serial_no_inner] = device_info

        stf_ready_devices, appium_ready_devices = free_devices_catalog_dict.get(DeviceStatusEnum.STF_READY.value,
                                                                                []), free_devices_catalog_dict.get(
            DeviceStatusEnum.APPIUM_READY.value, [])

        if len(stf_ready_devices) == 0 and len(appium_ready_devices) == 0:
            raise DeviceAcquireError('无可用设备')

        target_serial_no_list = []
        # 单个设备优先返回stf空闲设备
        if acquire_type == DeviceAcquireTypeEnum.SINGLE.value:
            if len(stf_ready_devices) > 0:
                target_serial_no = stf_ready_devices[0]
            else:
                target_serial_no = appium_ready_devices[0]
            target_serial_no_list.append(target_serial_no)
        # 单个指定设备
        elif acquire_type == DeviceAcquireTypeEnum.SINGLE_SPECIFIED.value:
            if serial_no not in free_devices:
                raise DeviceAcquireError('指定{}设备不可用'.format(serial_no))
            else:
                target_serial_no_list.append(serial_no)

        # 所有设备
        elif acquire_type == DeviceAcquireTypeEnum.ALL.value:
            target_serial_no_list = list(free_devices.keys())

        for target_serial_no in target_serial_no_list:
            device_info = free_devices[target_serial_no]
            device_status = device_info['device_status']

            # STF_READY状态需要锁定
            if device_status == DeviceStatusEnum.STF_READY.value:
                lock_result = self._lock_device(target_serial_no, device_status)
                if lock_result:
                    device_info['device_status'] = DeviceStatusEnum.STF_LOCKED.value
                    self.devices_used[target_serial_no] = device_info
            else:
                self.devices_used[target_serial_no] = device_info
        target_serial_no_list = []
        return self.devices_used

    def _lock_device(self, serial_no, device_status: DeviceStatusEnum):
        '''
        锁定设备
        :param serial_no:设备序列号
        :return:
        '''
        result = True
        if device_status == DeviceStatusEnum.STF_READY.value:
            response = api_stf_devices_post(serial_no)
            rsp_json = response.json()
            success = rsp_json.get('success', False)

            if success:
                print('【锁定设备】:{}'.format(serial_no))
            else:
                result = False
                self._release_device(serial_no)
        return result

    def release_devices(self):
        for serial_no in self.devices_used:
            device_info = self.devices_used[serial_no]
            device_status = device_info['device_status']

            if device_status == DeviceStatusEnum.STF_LOCKED.value:
                self._release_device(serial_no)
        self.devices_used = {}

    def _release_device(self, serial_no):
        try:
            api_stf_user_devices_delete(serial_no)
            print('【释放设备】:{}'.format(serial_no))
        except Exception:
            print('【{}设备释放异常】'.format(serial_no))
