# Coding: UTF-8
# Author: Yuri_Fanzhiwei
# Action: 此代码文件的作用是保存的视频文件的各种处理函数比如文件保存进程
#         终止文件保存进程、开始文件保存进程

import sys
sys.path.append('../')

import gi
gi.require_version('Gst', '1.0')

from gi.repository import GObject, Gst, GLib
from datetime import datetime, timedelta
from file_module import filesaving
import multiprocessing as mp
import struct
import socket
import time
import pyds
import sys
import os


# active_filesave_processes = []

def saveFile_flag(active_filesave_processes):
    for process in active_filesave_processes:
        process["save_flag"] = True


def saveFile_process(saveFile_name, udp_port):

    interrupt_process = mp.Event()
    filesave_process = mp.Process(target=filesaving.main, args=(saveFile_name, udp_port, interrupt_process))
    filesave_process.start()

    return filesave_process, interrupt_process


def saveFile_end(active_process):
    active_process["interrupt"].set()
    active_process["process_handler"].join(timeout=10)
    active_process["process_handler"].terminate()

    filepath = active_process["save_path"]
    # filepath = '/home/nvidia/Nano/video/output.mp4'

    if active_process["save_flag"] == True:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect(('101.43.152.188', 8888))
        except socket.error as msg:
            print(msg)
            return
            # sys.exit(1)
        print(s.recv(1024))

        # filepath = '/home/nvidia/Nano/video/output.mp4'
        # filepath = './output.mp4'

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
    else:
        os.remove(filepath)


def saveFile_start(period, duration, active_filesave_processes):
    period = timedelta(seconds=period)
    duration = timedelta(seconds=duration)
    latest_start = None

    for idx, active_process in enumerate(active_filesave_processes):
        if datetime.now() - active_process["start_time"] >= duration:
            saveFile_end(active_process)
            del active_filesave_processes[idx]
            return 
        if latest_start == None or active_process["start_time"] > latest_start:
            latest_start = active_process["start_time"]

    if latest_start is None or (datetime.now() - latest_start >= period):
        local_time = time.strftime("%Y%m%d%H%M%S", time.localtime())
        output_name = "/home/nvidia/Nano/video/" + local_time + ".mp4"
        # output_name = "/home/nvidia/Nano/video/output.mp4"
        port = 8001
        file_process, file_interrupt = saveFile_process(output_name, port)
        # file_process = mp.Process(target=filesaving.main, args=(output_name, port))
        # file_process.start()

        latest_start = datetime.now()
        active_filesave_processes.append(
            dict(
                start_time=latest_start, 
                process_handler=file_process, 
                interrupt=file_interrupt, 
                save_path = output_name,
                save_flag=False
                )
            )