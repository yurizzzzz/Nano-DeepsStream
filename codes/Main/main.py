# Coding: UTF-8
# Author: Yuri_Fanzhiwei
# Action: 主程序

import sys
sys.path.append('../')

import gi
gi.require_version('Gst', '1.0')

from gi.repository import GObject, Gst, GLib
from datetime import datetime, timedelta
from nvinfer_mask import mask_infer
from mqtt_module import mqtt_client
from file_module import filesaving, file_process
import multiprocessing as mp
import threading
import argparse
import struct
import socket
import signal
import time
import pyds
import sys
import os


external_interrupt = threading.Event()

def signal_handler(sig, frame):
    """
    该函数是signal处理信号发生时候调用的处理函数，当按下CTRL+C
    的时候接收到中断信号并设置中断标志为True

    @Param sig: signal处理的信号编号
    @Param frame: signal处理的程序帧

    """

    print("\nCTRL-C Stop the Code!")
    external_interrupt.set()


def process_info(client, stats_queue, active_filesave_processes, pub_topic):
    """
    该函数通过队列获取到主进程中检测的信息，并且判断是否发生异常，若发现异常则
    令MQTT对象发送异常信息报警到云端，同时也令视频保存流保存相对应异常的视频。

    @Param client: 传入的初始化好的MQTT对象
    @Param stats_queue: 存放主进程中的检测信息的队列
    @Param active_filesave_processes: 目前正在运行的视频保存流进程
    @Param pub_topic: MQTT发布的主题

    """

    while not stats_queue.empty():
        statistics = stats_queue.get_nowait()

        person_nums = int(statistics["People_nums"])
        path = statistics["warning_images_dir"]
        alert = False
        if person_nums % 30==0 and person_nums != 0:
            alert = True
            file_process.saveFile_flag(active_filesave_processes)

        if alert:
            alert = False
            print(person_nums)
            if client is not None:
                print('ALERT')
                
                time_now = time.strftime("%Y,%m-%d,%H-%M", time.localtime())
                time_now = time_now.split(',')
                file_path = '/home/ubuntu/' + time_now[0] + '/' + time_now[1] + '/' + time_now[2]
                send_msg = {'Warning': 'NoMask', 'ImagePath': path}
                mqtt_client.mqtt_publish(client, pub_topic, send_msg)


def input_args():
    """
    该函数为主程序传入需要的参数
    
    @Param cam_device: 选择摄像头类型
    @Param usb_id: USB摄像头的设备号
    @Param sensor_id: CSI摄像头的设备号
    @Param port: 传入云服务器端的EMQX开放端口
    @Param sub_topic: MQTT对象订阅的主题
    @Param pub_topic: MQTT对象发布的主题关于异常告警
    @Param ip: 云服务器端的公网IP
    @Param file_period: 视频文件保存的周期(秒)
    @Param file_duration: 一个视频文件的保存的时长(秒)

    """
    parser = argparse.ArgumentParser()

    parser.add_argument("--cam_device", type=str, default="csi",
                        help="CSI or USB")
    parser.add_argument("--usb_id", type=str, default="/dev/video0",
                        help="Set the cloud server's port")                    
    parser.add_argument("--sensor_id", type=int, default=0,
                        help="Set the cloud server's port")
    parser.add_argument("--port", type=int, default=1883,
                        help="Set the cloud server's port")
    parser.add_argument("--sub_topic", type=str, default="/sub",
                        help="The MQTT object's subscribe topic")
    parser.add_argument("--pub_topic", type=str, default="/pub",
                        help="The MQTT object's published topic")
    parser.add_argument("--ip", type=str, default="101.43.152.188",
                        help="Set the cloud server's IP")
    parser.add_argument("--file_period", type=int, default=60,
                        help="Set the the filesaving period")
    parser.add_argument("--file_duration", type=int, default=35,
                        help="Set the the filesaving duration")

    return parser.parse_args()

if __name__ == '__main__':
    """
    整个项目的主运行程序,主运行代码的实现基本流程是:
    MQTT对象初始化-->初始化消息队列-->启动主进程-->
    进入循环处理检测信息-->发送消息和视频文件保存

    """
    
    # port = 1883
    # sub_topic = "/sub"
    # pub_topic = "/pub"
    # ip = "101.43.152.188"
    # file_period = 60
    # file_duration = 35 

    args = input_args()

    active_filesave_processes = []
    signal.signal(signal.SIGINT, signal_handler)

    client = mqtt_client.mqtt_init(args.ip, args.port)
    client = mqtt_client.mqtt_subscribe(client, args.sub_topic)
    client.on_message = mqtt_client.mqtt_get_message

    stats_queue = mp.Queue(maxsize=5)
    main_process = mp.Process(target=mask_infer.infer_main, args=(args, stats_queue))
    main_process.start()

    while not external_interrupt.is_set():
        process_info(client, stats_queue, active_filesave_processes, args.pub_topic)
        file_process.saveFile_start(args.file_period, args.file_duration, active_filesave_processes, client, args.pub_topic)

    for process in active_filesave_processes:
        file_process.saveFile_end(process, client, args.pub_topic)
    