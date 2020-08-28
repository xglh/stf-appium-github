#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2019/11/4 11:23
# @Author  : liuhui
# @Detail  : ftp模块

import ftplib
import os
import socket
from driver.config import stf_providers


class FtpClient:

    def __init__(self, hostname, username, password):
        self.hostname = hostname
        self.username = username
        self.password = password

        # 获取ftp连接
        self.ftp = self._ftpConnect()

    def _ftpConnect(self):
        try:
            ftp = ftplib.FTP(self.hostname)
        except (socket.error, socket.gaierror) as e:
            print('Error, cannot reach ' + self.hostname)
            return
        else:
            pass
            # print('Connect To Host Success...')

        try:
            ftp.login(self.username, self.password)
        except ftplib.error_perm:
            print('Username or Passwd Error')
            ftp.quit()
            return
        else:
            pass
            #print('Login Success...')
        ftp.set_pasv(False)
        return ftp

    def ftp_download(self, remote_path, local_path):
        try:
            self.ftp.retrbinary('RETR %s' % remote_path, open(local_path, 'wb').write)
        except ftplib.error_perm:
            print('File Error')
            os.unlink(local_path)
        else:
            pass
            # print('Download Success...')

    def ftp_upload(self, remote_dir, local_path):
        local_path = local_path.replace('\\', '/')
        file_name = local_path.split('/')[-1]
        remote_path = '{}/{}'.format(remote_dir.rstrip('/'), file_name)
        with open(local_path, 'rb') as file:
            self.ftp.storbinary('STOR %s' % remote_path, file)
            print('【ftp上传】：hostname={},local_path={},remote_path={}'.format(self.hostname, local_path, remote_path))

    def ftp_close(self):
        try:
            self.ftp.close()
        except Exception:
            pass


class FtpManager:

    def __init__(self, platform):
        assert platform in stf_providers, u'无{} provider配置'
        self.platform = platform
        self.providers = stf_providers[platform]
        self.ftp_clients = []

    def ftp_upload(self, local_path):
        for provider in self.providers:
            hostname, username, password, remote_dir = provider['hostname'], provider['username'], provider['password'], \
                                                    provider['app_dir']
            mFtpClient = FtpClient(hostname, username, password)
            self.ftp_clients.append(mFtpClient)

            mFtpClient.ftp_upload(remote_dir, local_path)

    def ftp_close(self):
        for ftp_client in self.ftp_clients:
            ftp_client.ftp_close()