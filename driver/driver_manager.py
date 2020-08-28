#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2020/8/18 8:37
# @Author  : liuhui
# @Detail  : driver manager
import time
import traceback
import threadpool
from appium import webdriver
from threading import Thread
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from driver.config import driver_wait_timeout, driver_wait_poll_frequency, driver_get_thread_num
from driver.ssh_manager import SSHClient
from driver.stf_manager import StfManager
from driver.ftp_manager import FtpManager
from driver.base import DeviceAcquireError, DeviceAcquireTypeEnum


class DriverManager(StfManager):

    def __init__(self, platform, app_path):
        '''
        初始化
        :param platform:  平台 android/ios
        :param app_path:  app文件路径
        '''
        assert platform in ['ios', 'android'], u'platform只能为android或者ios'
        assert platform != 'ios', u'ios暂不支持，敬请期待。。。'
        super().__init__(platform)
        self.drivers_acquired = {}
        self.app_path = app_path
        self.package_name = ''

        # ftp上传
        mFtpManager = FtpManager(platform)
        mFtpManager.ftp_upload(app_path)
        mFtpManager.ftp_close()

    def get_driver(self, package_name, activity_name, serial_no='', acquire_all_device=False):
        '''
        获取drivers
        :param package_name: package_name
        :param activity_name: activity_name
        :param serial_no: 序列号，不为空时获取指定设备，不指定则随机获取一个
        :param acquire_all_device: 是否请求全部可用设备，为true时获取全部
        :return: driver信息
        返回示例：
                {
            'ca352a47': {
                'device_status': 'STF_LOCKED',
                'appium_hub': 'http://1.1.1.1:4727/wd/hub',
                'ssh_client':  < driver.ssh_manager.SSHClient object at 0x000001C1F50D2CC0 > ,
                'release': '9',
                'sdk': '28',
                'manufacturer': 'Xiaomi',
                'model': 'Redmi K20',
                'wm_size': '1080x2340'
            }
        }
        '''
        self.package_name = package_name
        # 遍历模式
        if acquire_all_device:
            self.drivers_acquired = self.acquire_devices(acquire_type=DeviceAcquireTypeEnum.ALL.value)
        # 指定设备模式
        elif serial_no != '':
            self.drivers_acquired = self.acquire_devices(acquire_type=DeviceAcquireTypeEnum.SINGLE_SPECIFIED.value,
                                                         serial_no=serial_no)
        # 默认模式
        else:
            self.drivers_acquired = self.acquire_devices(acquire_type=DeviceAcquireTypeEnum.SINGLE.value,
                                                         serial_no=serial_no)

        # 线程池处理
        thread_num = driver_get_thread_num
        tpool = threadpool.ThreadPool(thread_num)
        thread_args = []

        # 申请到的设备
        for acquired_serial_no in self.drivers_acquired:
            device_info = self.drivers_acquired[acquired_serial_no]
            appium_hub, ssh_client = device_info['appium_hub'], device_info['ssh_client']
            remote_app_path = ssh_client.get_remote_app_path(self.app_path)
            func_args = [ssh_client, appium_hub, package_name, activity_name, remote_app_path, acquired_serial_no]
            thread_args.append((func_args, None))

        thread_requests = threadpool.makeRequests(self._get_driver_thread, thread_args)
        [tpool.putRequest(req) for req in thread_requests]
        tpool.wait()  # 表示所有请求结束后，结束进程

        return self.drivers_acquired

    def _get_driver_thread(self, ssh_client: SSHClient, appium_hub, package_name, activity_name, remote_app_path,
                           serial_no):
        '''
        单线程获取driver，默认会在目标设备上安装并启动目标应用
        :param ssh_client: ssh终端对象
        :param appium_hub: appium_hub
        :param package_name: package_name
        :param activity_name: activity_name
        :param remote_app_path: 远程app路径
        :param serial_no: 设备序列号
        :return:
        '''
        try:

            desired_caps = {
                "platformName": self.platform,
                # appium setting不需要重复安装
                "skipServerInstallation": True,
                "skipDeviceInitialization": True,
                "deviceName": serial_no,
            }
            driver = webdriver.Remote(appium_hub, desired_caps)
            driver.unlock()

            # 检查app是否有安装，安装则卸载
            if driver.is_app_installed(package_name):
                driver.remove_app(package_name)
            Thread(target=self._install_app, args=(ssh_client, serial_no, remote_app_path)).start()
            # start_activity opts配置
            opts = {}
            try:
                opts = self._confirm_install_app(ssh_client, driver, serial_no)
            except:
                print('【确认安装apk异常】,serial_no={},traceback:{}'.format(serial_no, traceback.format_exc()))
            time.sleep(3)

            # 确认app是否安装
            count = 0
            while count > 10:
                if driver.is_app_installed(package_name): break
                count += 1
                time.sleep(1)

            # 启动app
            driver.start_activity(package_name, activity_name, appWaitDuration=10000, **opts)
            time.sleep(1)
            driver.switch_to.alert.accept()

        except Exception:
            print('【安装apk异常】:serial_no={},traceback={}'.format(serial_no, traceback.format_exc()))
            self.drivers_acquired[serial_no]['driver'] = None
        else:
            self.drivers_acquired[serial_no]['driver'] = driver

    def close(self):
        '''
        关闭driver
        :return:
        '''
        for serial_no in self.drivers_acquired:
            device_info = self.drivers_acquired[serial_no]
            driver = device_info.get('driver')
            try:
                if driver:
                    # 关闭app
                    driver.close_app()
                    # 卸载安装包
                    driver.remove_app(self.package_name)
                    driver.quit()
            except Exception:
                pass
        # 释放设备
        self.release_devices()
        # 关闭ssh连接
        self.ssh_close()
        self.drivers_acquired = {}

    def _install_app(self, ssh_client: SSHClient, serial_no, remote_app_path):
        '''
        安装apk到指定设备
        :param ssh_client:ssh对象
        :param serial_no:设备编号
        :param remote_app_path: stf服务器路径
        :return:
        '''
        try:
            # 执行命令
            adb_shell_str = 'adb -s {} install -r {}'.format(serial_no, remote_app_path)
            shell_result = ssh_client.adb_shell(adb_shell_str)
            # 获取命令结果
            print('【apk安装结果】:{}'.format(shell_result))
            # 关闭连接
        except Exception:
            pass

    def _confirm_install_app(self, ssh_client: SSHClient, driver, serial_no):
        '''
        确认安装apk，需要根据不同机型适配
        :param ssh_client:ssh对象
        :param driver: driver对象
        :param serial_no: 设备编号
        :return: start_activity的opts参数，解决启动的activity不是指定的activity场景
        {
            'app_wait_package': 'com.lbe.security.miui',
            'app_wait_activity': 'com.android.packageinstaller.permission.ui.GrantPermissionsActivity'
        }

        '''
        opts = {}
        # Redmi K20点击继续安装按钮
        if serial_no == 'ca352a47':
            # 启动后的activity与目标的不一样，需要设置start_activity方法的app_wait_package，app_wait_activity
            opts = {
                'app_wait_package': 'com.lbe.security.miui',
                'app_wait_activity': 'com.android.packageinstaller.permission.ui.GrantPermissionsActivity'
            }
            # 点击继续安装按钮
            WebDriverWait(driver, driver_wait_timeout, driver_wait_poll_frequency).until(
                EC.element_to_be_clickable((By.ID, "android:id/button2"))
            ).click()

        return opts

    def tap_screen(self, ssh_client: SSHClient, serial_no, pos_x, pos_y):
        '''
        模拟屏幕点击，oppo手机无法获取到确认安装按钮，采用模拟屏幕点击方法
        :param ssh_client:ssh对象
        :param serial_no: 设备序列号
        :param pos_x: x轴坐标
        :param pos_y: y轴坐标
        :return:
        '''
        ssh_client.adb_shell('adb -s {} shell input tap {} {}'.format(serial_no, pos_x, pos_y))
