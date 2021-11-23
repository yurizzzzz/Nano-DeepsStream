import paho.mqtt.client as mqtt
from threading import Thread
import argparse
import json

def mqtt_init(server_ip:str, server_port:int):
    # 创建mqtt
    mqtt_client = mqtt.Client(client_id=" ")
    # 如有需要设置账号密码
    # mqtt_client.username_pw_set(username='', password='')
    # 设置连接成功时输出
    mqtt_client.on_connect = lambda client, userdata, flags, rc: print(
        "Connected with result code: " + str(rc))
    # 设置连接失败的时候的输出
    mqtt_client.on_disconnect = lambda client, userdata, flags, rc: print(
        "Disconnected with result code: " + str(rc))
    # 连接公网服务器
    mqtt_client.connect(server_ip, server_port, 60)
    return mqtt_client

def mqtt_subscribe(mqtt_client, sub_topic):
    # 订阅对应主题
    mqtt_client.subscribe(sub_topic, qos=0)
    # 放入后台的子线程中去运行不断循环接收信息
    mqtt_client.loop_start()
    return mqtt_client

def mqtt_publish(mqtt_client, pub_topic, pub_msg):
    # 对传入的数据进行json格式化即将字典格式转换为字符串
    publish_msg = json.dumps(pub_msg)
    print('Sending mmessage: ', pub_msg)
    # 发布数据，消息质量设置为1，Qos一共三个级别：0、1、2
    result = mqtt_client.publish(pub_topic, publish_msg, qos=1)
    # 其中publish方法会返回两个参数[rc, mid]rc指的是发送成功，mid指的是追踪发送请求
    if result[0] == 0:
        print('Send successfully')
    else:
        print('Sending failed')

def mqtt_get_message(mqtt_client, userdata, message):
    # 对接收的信息进行解码
    msg = message.payload.decode()
    # json格式对接收到信息从字符串转换为字典格式
    # payload = json.loads(msg)
    print("Recieved message: ", msg)
    



if __name__ == '__main__':
    send_msg = {'path': '/2021', 'device': 'nano'}
    # 创建mqtt对象
    ip = "59.110.7.232"
    port = 1883
    client = mqtt_init(ip, port)
    client = mqtt_subscribe(client, '/sub')
    client.on_message = mqtt_get_message

    while True:
        cmd_input = input("send or not send: \n")
        if cmd_input == "yes":
            mqtt_publish(client, '/pub', send_msg)
        if cmd_input == "no":
            break         


