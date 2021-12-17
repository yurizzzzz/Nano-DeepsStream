# coding: UTF-8
# Author: Yuri_Fanzhiwei
# 告警视频文件保存模块

# 将文件夹内的包加入到路径下
import sys
sys.path.append('../')

import gi
gi.require_version('Gst', '1.0')
gi.require_version("GstBase", "1.0")

from gi.repository import GObject, Gst, GLib,GstBase
from common.is_aarch_64 import is_aarch64
from common.bus_call import bus_call
import multiprocessing as mp
import threading
import signal
import pyds

e_interrupt = None

def sigint_handler(sig, frame):
    print("[red]Ctrl+C pressed. Interrupting file-save...[/red]")
    e_interrupt.set()

def main(ouput_name: str, udp_port: int, e_external_interrupt: mp.Event = None):

    global e_interrupt

    Gst.init(None)
    pipeline = Gst.Pipeline()
    if not pipeline:
        sys.stderr.write(" Unable to create Pipeline \n")

    udp_capabilities = f"application/x-rtp, encoding-name=(string)H264, payload=(int)96"
    # udp_capabilities = f"application/x-rtp,media=video,encoding-name=(string)H264,clock-rate=(int)90000, payload=(int)96"
    udpsrc = Gst.ElementFactory.make("udpsrc")
    udpsrc.set_property("address", "127.0.0.1")
    udpsrc.set_property("port", udp_port)
    # udpsrc.set_property("buffer-size", 524288)
    udpsrc.set_property("caps", Gst.Caps.from_string(udp_capabilities))
    # rtpjitterbuffer = Gst.ElementFactory.make("rtpjitterbuffer")
    # rtpjitterbuffer.set_property("mode", 4)


    rtpdepay = Gst.ElementFactory.make("rtph264depay")
    file_queue = Gst.ElementFactory.make("queue")
    codeparser = Gst.ElementFactory.make("h264parse")
    # GstBase.BaseParse.set_pts_interpolation(codeparser, True)
    container = Gst.ElementFactory.make("qtmux")
    filesink = Gst.ElementFactory.make("filesink")
    filesink.set_property("location", ouput_name)


    pipeline.add(udpsrc)
    # pipeline.add(rtpjitterbuffer)

    pipeline.add(rtpdepay)
    pipeline.add(file_queue)
    pipeline.add(codeparser)
    pipeline.add(container)
    pipeline.add(filesink)

    # udpsrc.link(rtpjitterbuffer)
    udpsrc.link(rtpdepay)
    # rtpjitterbuffer.link(rtpdepay)
    rtpdepay.link(file_queue)
    file_queue.link(codeparser)
    codeparser.link(container)
    container.link(filesink)

    loop = GObject.MainLoop()
    g_context = loop.get_context()

    bus = pipeline.get_bus()

    print("Starting pipeline \n")

    if e_external_interrupt is None:
        e_interrupt = threading.Event()
        signal.signal(signal.SIGINT, sigint_handler)
        print("[green bold]Press Ctrl+C to save video and exit[/green bold]")
    else:
        e_interrupt = e_external_interrupt
    pipeline.set_state(Gst.State.PLAYING)

    running = True
    
    while running:
        g_context.iteration(may_block=True)
        message = bus.pop()
        if message is not None:
            t = message.type

            if t == Gst.MessageType.EOS:
                print(f"File saved: [yellow]{output_filename}[/yellow]")
                running = False
            elif t == Gst.MessageType.WARNING:
                err, debug = message.parse_warning()
                print("%s: %s" % (err, debug), warning=True)
            elif t == Gst.MessageType.ERROR:
                err, debug = message.parse_error()
                print("%s: %s" % (err, debug), error=True)
                running = False
        if e_interrupt.is_set():
            print("Interruption received. Sending EOS to generate video file.")
                # This will allow the filesink to create a readable mp4 file
            container.send_event(Gst.Event.new_eos())
            e_interrupt.clear()

    pipeline.set_state(Gst.State.NULL)

if __name__ == "__main__":
    save_file = 'output.mp4'
    port = 8001
    main(save_file, port)
