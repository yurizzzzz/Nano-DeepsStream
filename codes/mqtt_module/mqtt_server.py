# coding:UTF-8
# Author:Yuri
# 服务端（其实也算是另一个客户端）实现：既能订阅特定的主题的消息，也能发布特定的主题的消息

import paho.mqtt.client as mqtt
from threading import Thread
import argparse
import json


def input_args():
    parser = argparse.ArgumentParser()
    # 设定公网服务器的公网IP
    parser.add_argument("--host", type=str, default='59.110.7.232',
                        help="Set the cloud server's IP address")
    # 设定公网服务器进行MQTT协议传输的端口号
    parser.add_argument("--port", type=int, default=1883,
                        help="Set the cloud server's opened port")
    # 设定该客户端发布的主题
    parser.add_argument("--publish_topic", type=str, default='/sub',
                        help="Set the publish topic")
    # 设定该客户端订阅的主题
    parser.add_argument("--subscribe_topic", type=str, default='/pub',
                        help="Set the subscribe topic")

    return parser.parse_args()


# 该客户端的发布数据模块
def publish_data(arg, publish_msg):
    # 创建mqtt的客户端
    publish_client = mqtt.Client()
    # 如有需要可设置客户端连接服务器的账号密码
    # publish_client.username_pw_set(username='tdyjy', password='tdyjy321')
    # 连接公网服务器
    publish_client.connect(arg.host, arg.port, 60)
    # 对传入的数据进行json格式化
    publish_msg = json.dumps(publish_msg)
    print('Sending: ', publish_msg)
    # 发布数据，消息质量设置为1，Qos一共三个级别：0、1、2
    publish_client.publish(arg.publish_topic, publish_msg, qos=1)


# 该客户端的订阅数据模块
def subscribe_data(arg):
    # 创建mqtt客户端
    subscribe_client = mqtt.Client()
    # 设置连接成功时输出
    subscribe_client.on_connect = lambda client, userdata, flags, rc: print(
        "Connected with result code: " + str(rc))
    # 接收消息并解码输出
    subscribe_client.on_message = lambda client, userdata, message: print(
        message.payload.decode())
    # 如有需要设置账号密码
    # subscribe_client.username_pw_set(username='tdyjy', password='tdyjyEmq2021#')
    # 连接公网服务器
    subscribe_client.connect(arg.host, arg.port, 60)
    # 订阅对应主题
    subscribe_client.subscribe(arg.subscribe_topic)
    # 进行阻塞方式运行不然会中断
    subscribe_client.loop_start()


if __name__ == '__main__':
    args = input_args()
    # 设置发送数据
    # msg = {'path': '/202107'}
    # 设置多线程并行使得发送和订阅同时进行
    # publish_thread = Thread(target=publish_data(args, msg))
    subscribe_thread = Thread(target=subscribe_data(args))
    # publish_thread.start()
    while True:
        subscribe_data(args)