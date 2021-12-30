# Coding : UTF-8
# Author : Yuri_FanZhiwei
# Action : 此文件是用来测试从Nano端发送文件到远程云服务器可行性
#          实现方式使用基于TCP连接的Socket传输数据文件

import os
import sys
import struct
import socket


def socket_client():
    try:
        # 连接云服务器端
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(('59.110.7.232', 8888))
    except socket.error as msg:
        print(msg)
        sys.exit(1)
    print(s.recv(1024))

    # 设置文件名
    filepath = './output.mp4'

    if os.path.isfile(filepath):
        # 获取文件名并用UTF-8编码
        filein_size = struct.calcsize('128sl')
        ahead = struct.pack('128sq', os.path.basename(filepath).encode('utf-8'), os.stat(filepath).st_size)
        s.send(ahead)
        fp = open(filepath, 'rb')
        # 文件会被隔断分批次发送
        # 进入循环发送文件直到文件发送完毕
        while 1:
            data = fp.read(1024)
            if not data:
                print('{0} file send over...'.format(os.path.basename(filepath)))
                break
            s.send(data)
        s.close()


if __name__ == '__main__':
    socket_client()