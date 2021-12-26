# Coding: UTF-8
# Author: Yuri_Fanzhiwei
# Function: Main execution code

import sys
sys.path.append('../')

import gi
gi.require_version('Gst', '1.0')

from gi.repository import GObject, Gst, GLib
from datetime import datetime, timedelta
from nvinfer_mask import mask_infer
from mqtt_module import mqtt_client
from filesave import filesaving
import multiprocessing as mp
import struct
import socket
import pyds
import sys
import os


active_filesave_processes = []
flag = [0]

def handle_statistics(client, stats_queue, send_msg):
    while not stats_queue.empty():
        statistics = stats_queue.get_nowait()

        person_nums = int(statistics["People_nums"])
        alert = False
        if person_nums % 30==0 and person_nums != 0:
            alert = True
            flag[0] = 1

        if alert:
            alert = False
            print(person_nums)
            if client is not None:
                print('ALERT')
                mqtt_client.mqtt_publish(client, '/pub', send_msg)


def saveFile_process(saveFile_name, udp_port):

    interrupt_process = mp.Event()
    filesave_process = mp.Process(target=filesaving.main, args=(saveFile_name, udp_port, interrupt_process))
    filesave_process.start()

    return filesave_process, interrupt_process


def finish_filesave_process(active_process):
    active_process["interrupt"].set()
    active_process["process_handler"].join(timeout=10)
    active_process["process_handler"].terminate()

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(('101.43.152.188', 8888))
    except socket.error as msg:
        print(msg)
        sys.exit(1)
    print(s.recv(1024))

    filepath = './output.mp4'

    if os.path.isfile(filepath):
        filein_size = struct.calcsize('128sl')
        ahead = struct.pack('128sq', os.path.basename(filepath).encode('utf-8'), os.stat(filepath).st_size)
        s.send(ahead)
        fp = open(filepath, 'rb')
        while 1:
            data = fp.read(1024)
            if not data:
                print('{0} file send over...'.format(os.path.basename(filepath)))
                break
            s.send(data)
        s.close()
    flag[0] = 0


def filesaving_process(period, duration):
    if flag[0] == 0:
        return

    period = timedelta(seconds=period)
    duration = timedelta(seconds=duration)
    latest_start = None

    for idx, active_process in enumerate(active_filesave_processes):
        if datetime.now() - active_process["start_time"] >= duration:
            finish_filesave_process(active_process)
            del active_filesave_processes[idx]
            return 
        if latest_start == None or active_process["start_time"] > latest_start:
            latest_start = active_process["start_time"]

    if latest_start is None or (datetime.now() - latest_start >= period):
        output_name = "/home/nvidia/Nano/codes/Main/output.mp4"
        port = 8001
        file_process, file_interrupt = saveFile_process(output_name, port)
        # file_process = mp.Process(target=filesaving.main, args=(output_name, port))
        # file_process.start()

        latest_start = datetime.now()
        active_filesave_processes.append(dict(start_time=latest_start, process_handler=file_process, interrupt=file_interrupt))


if __name__ == '__main__':
    send_msg = {'Warning': 'NoMask', 'Path': '/home/2021'}
    ip = "101.43.152.188"
    port = 1883
    client = mqtt_client.mqtt_init(ip, port)
    client = mqtt_client.mqtt_subscribe(client, '/sub')
    client.on_message = mqtt_client.mqtt_get_message

    stats_queue = mp.Queue(maxsize=5)
    main_process = mp.Process(target=mask_infer.infer_main, args=(sys.argv, stats_queue))
    main_process.start()
    # main(sys.argv, stats_queue)
    while True:
        handle_statistics(client, stats_queue, send_msg)
        filesaving_process(60, 35)
