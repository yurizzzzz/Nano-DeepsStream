import paho.mqtt.client as mqtt
from threading import Thread
import json
import threading
import shutil
import socket
import struct
import sys
import time
import os


def publish_data(publish_msg):
    # 创建mqtt的客户端
    publish_client = mqtt.Client()
    # 如有需要可设置客户端连接服务器的账号密码
    # publish_client.username_pw_set(username='xxxx', password='xxxxxxxx')
    # 连接公网服务器
    publish_client.connect('xx.xxx.xxx.xxx', 1883, 60)
    # 对传入的数据进行json格式化
    publish_msg = json.dumps(publish_msg)
    print('Sending: ', publish_msg)
    # 发布数据，消息质量设置为1，Qos一共三个级别：0、1、2
    publish_client.publish('topic_wx/device0', publish_msg, qos=1)


def socket_service():
    try:
        # 连接本地监听特定端口号
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((' ', 8888))
        s.listen(10)
    except socket.error as msg:
        print(msg)
        sys.exit(1)
    print('Waiting connection...')

    while 1:
        conn, addr = s.accept()
        t = threading.Thread(target=deal_data, args=(conn, addr))
        t.start()

# 处理接收的数据
def deal_data(conn, addr):
    print('Accept new connection from {0}'.format(addr))
    conn.send('Hi, Welcome to the server!'.encode('utf-8'))

    # 按年月日时间来创建视频存储的文件夹
    time_now = time.strftime("%Y,%m-%d,%H-%M", time.localtime())
    time_now = time_now.split(',')
    root = os.getcwd()
    new_path = root + '/' + time_now[0] + '/' + time_now[1] + '/' + time_now[2]
    if not os.path.exists(new_path):
        os.makedirs(new_path)
    
    # 编辑约定好的信息并发送到topic上
    # msg = {'path': new_path, 'message': 'An exception occurred'}
    # publish_data(msg)

    # 进入循环接收传过来的文件
    while 1:
        fileinfo_size = struct.calcsize('128sl')
        buf = conn.recv(fileinfo_size)
        if buf:
            # 对文件名进行解码
            filename, filesize = struct.unpack('128sl', buf)
            fn = filename.strip(b'\00')
            fn = fn.decode()
            print('file new name is {0}, filesize if {1}'.format(str(fn), filesize))
            recvd_size = 0
            fp = open('./' + str(fn), 'wb')
            print('start receiving...')
            begin = time.time()

            while not recvd_size == filesize:
                if filesize - recvd_size > 1024:
                    data = conn.recv(1024)
                    recvd_size += len(data)
                else:
                    data = conn.recv(filesize - recvd_size)
                    recvd_size = filesize
                fp.write(data)
            fp.close()
            end = time.time()
            print('end receive and cost %f s' % (end - begin))
            # 将接收到的文件转移到之前创建好的文件夹中去
            shutil.move('./' + str(fn), new_path + '/' + str(fn))
        conn.close()
        break


if __name__ == "__main__":
    socket_service()