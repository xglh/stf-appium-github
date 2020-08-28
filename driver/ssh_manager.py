#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2020/8/19 15:10
# @Author  : liuhui
# @Detail  : ssh终端管理
import re
import paramiko
import traceback
from driver.base import DeviceAcquireError
from driver.config import stf_providers
from driver.base import DeviceStatusEnum


class SSHClient:

    def __init__(self, ssh_type, hostname, port, username, password, app_dir, adb_path=''):
        self.ssh_type = ssh_type
        self.hostname = hostname
        self.port = port
        self.username = username
        self.password = password
        self.app_dir = app_dir
        self.adb_path = adb_path
        self.ssh = None
        self.ssh_connect()

    def ssh_connect(self):
        '''
        ssh连接
        :return: ssh连接对象
        '''
        try:
            # print('ssh连接')
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(hostname=self.hostname, port=self.port, username=self.username,
                        password=self.password)
        except Exception:
            msg = '{} {} ssh连接失败,traceback:{}'.format(self.ssh_type, self.hostname, traceback.format_exc())
            raise DeviceAcquireError(msg)
        self.ssh = ssh

    def ssh_close(self):
        '''
        关闭ssh连接
        :return:
        '''
        self.ssh.close()

    def shell(self, cmd):
        '''
        执行shell命令
        :param cmd: shell命令行
        :return:
        '''
        print('【执行命令】:{}'.format(cmd))
        stdin, stdout, stderr = self.ssh.exec_command(cmd)
        # 获取命令结果
        result = stdout.read()
        result = str(result, encoding='utf-8')
        return result

    def adb_shell(self, cmd):
        '''
        执行adb命令，将adb路径替换为appium路径
        :param cmd: adb命令行
        :return:
        '''
        # adb路径替换为appium adb路径
        cmd = cmd.replace('adb', self.adb_path)
        return self.shell(cmd)

    def get_android_device_info(self, serial_no):
        '''
        获取device信息
        :param serial_no: 设备号
        :return:
        '''
        device_info = {}
        cmd_1 = "adb -s {} shell getprop | grep -E 'ro.build.version.sdk|ro.build.version.release|ro.product.manufacturer|ro.product.vendor.model'".format(
            serial_no)
        cmd_2 = 'adb -s {} shell wm size'.format(serial_no)

        p_1 = re.compile(r'\[([^\[\]]*)\]:\s*\[([^\[\]]*)\]')
        f_1 = p_1.findall(self.adb_shell(cmd_1))
        for info in f_1:
            origin_key, value = info[0], info[1]
            key = origin_key.split('.')[-1]
            device_info[key] = value

        p_2 = re.compile(r':\s*(\S*)')
        f_2 = p_2.findall(self.adb_shell(cmd_2))
        if len(f_2) > 0:
            device_info['wm_size'] = f_2[0]
        return device_info

    def get_appium_hubs(self):
        '''
        获取设备:appium_hub信息
        :return: { 'serial_no': 'appium_port' }
        '''
        appium_ports = {}
        cmd = "ps -ef|grep appium|awk '{print $13,$11}'"
        shell_result = self.shell(cmd)
        lines = shell_result.split('\n')
        p = re.compile(r'^(\S*)\s+(\d+)$')
        for line in lines:
            f = p.findall(line)
            if len(f) > 0:
                uid, port = f[0][0], f[0][1]
                appium_ports[uid] = 'http://{}:{}/wd/hub'.format(self.hostname, port)
        if len(appium_ports) == 0:
            raise DeviceAcquireError(u'获取appium端口失败,请检查appium是否启动')
        return appium_ports

    def get_adb_devices(self):
        '''
        获取adb连接设备
        :return:
        '''
        adb_devices = {}
        appium_hubs = self.get_appium_hubs()
        shell_result = self.adb_shell('adb devices')
        lines = shell_result.split('\n')
        p = re.compile('^(\S+)\s+device$')
        for line in lines:
            f = p.findall(line)
            if len(f) > 0:
                serial_no = f[0]
                device_info = self.get_android_device_info(serial_no)
                # appium连接正常
                if serial_no in appium_hubs:
                    adb_devices[serial_no] = {
                        'device_status': DeviceStatusEnum.APPIUM_READY.value,
                        'appium_hub': appium_hubs[serial_no],
                        'ssh_client': self,
                        **device_info
                    }
                # adb连接
                else:
                    adb_devices[serial_no] = {
                        'device_status': DeviceStatusEnum.ADB_READY.value,
                        'appium_hub': None,
                        'ssh_client': self,
                        **device_info
                    }
                    print('【警告】：{}无对应appium进程'.format(serial_no))
        return adb_devices

    def get_remote_app_path(self, local_app_path):
        '''
        通过local_app_path获取远程app路径
        :param local_app_path: 本地local_app_path
        :return:
        '''
        local_app_path = local_app_path.replace('\\', '/')
        app_name = local_app_path.split('/')[-1]
        remote_app_path = '{}/{}'.format(self.app_dir.rstrip('/'), app_name)
        return remote_app_path


class SSHManager:

    def __init__(self, platform):
        self.platform = platform
        self.ssh_clients = {}
        self.devices = {}

    def ssh_connect(self):
        '''
        ssh连接
        :return:
        '''
        platform_providers = stf_providers.get(self.platform, [])
        if len(platform_providers) == 0:
            raise DeviceAcquireError('{}无provider配置')
        for provider_info in platform_providers:
            hostname, port, username, password = provider_info['hostname'], provider_info['port'], provider_info[
                'username'], provider_info['password']

            app_dir, adb_path = provider_info.get('app_dir', ''), provider_info.get('adb_path', '')
            try:
                ssh_client = SSHClient(self.platform, hostname, port, username, password, app_dir, adb_path)
                self.ssh_clients[hostname] = ssh_client
                adb_devices = ssh_client.get_adb_devices()
                self.devices.update(adb_devices)
            except DeviceAcquireError as e:
                print(e)

    def ssh_close(self):
        '''
        关闭ssh连接
        :return:
        '''
        for ssh_client in self.ssh_clients:
            try:
                ssh_client.close()
            except Exception:
                pass

        self.ssh_clients = {}
        self.devices = {}
