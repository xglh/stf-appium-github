#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2020/8/18 8:39
# @Author  : liuhui
# @Detail  : 全局配置文件

# stf部署域名   自定义
stf_host = 'www.stf.com'
# stf access token  自定义
stf_token = 'xxxx'
# stf provider配置
stf_providers = {

    # android-provider配置  自定义
    'android': [
        {
            'hostname': '1.1.1.1',
            'port': 22,
            'username': 'root',
            'password': 'xxxx',
            # appium adb路径
            'adb_path': '/opt/android-sdk-linux/platform-tools/adb',
            # apk文件目录
            'app_dir': '/html/apk/'
        }
    ],
    # ios-provider配置  自定义
    'ios': [
        {
            'hostname': '1.1.1.2',
            'port': 22,
            'username': 'root',
            'password': 'xxxx'
        }
    ]
}

# WebDriverWait超时时间，秒
driver_wait_timeout = 30
# WebDriverWait等待时间间隔
driver_wait_poll_frequency = 1
# 获取driver时，前置处理线程数
driver_get_thread_num = 5
