import sys
sys.path.append('../')

import gi
gi.require_version('Gst', '1.0')
gi.require_version("GstBase", "1.0")

from gi.repository import GObject, Gst, GLib, GstBase
from common.bus_call import bus_call
import pyds

if __name__ == "__main__":
    GObject.threads_init()
    Gst.init(None)
    print("Creating Pipeline \n ")
    pipeline = Gst.Pipeline()

    source = Gst.ElementFactory.make("nvarguscamerasrc")
    source.set_property("sensor-id", 0)

    caps_src = Gst.ElementFactory.make("capsfilter")
    caps_src.set_property('caps', Gst.Caps.from_string("video/x-raw(memory:NVMM), width=1920, height=1080, framerate=30/1"))

    vidconv = Gst.ElementFactory.make("videoconvert")

    encoder = Gst.ElementFactory.make("nvv4l2h264enc")
    encoder.set_property("insert-sps-pps", True)
    encoder.set_property("maxperf-enable", 1)
    encoder.set_property("preset-level", 1)
    encoder.set_property("profile", 4)
    encoder.set_property("iframeinterval", 500)
    encoder.set_property("control-rate", 1)
    encoder.set_property("bitrate", 2000000)

    parse = Gst.ElementFactory.make("h264parse")

    rtppay = Gst.ElementFactory.make("rtph264pay")

    udp_sink = Gst.ElementFactory.make("udpsink")
    udp_sink.set_property("host", "127.0.0.1")
    udp_sink.set_property("port", 8001)
    udp_sink.set_property("sync", False)

    pipeline.add(source)
    pipeline.add(caps_src)
    pipeline.add(vidconv)
    pipeline.add(encoder)
    pipeline.add(parse)
    pipeline.add(rtppay)
    pipeline.add(udp_sink)

    source.link(caps_src)
    caps_src.link(vidconv)
    vidconv.link(encoder)
    encoder.link(parse)
    parse.link(rtppay)
    rtppay.link(udp_sink)

    loop = GObject.MainLoop()
    bus = pipeline.get_bus()
    bus.add_signal_watch()
    bus.connect ("message", bus_call, loop)
    print("Starting pipeline \n")
    pipeline.set_state(Gst.State.PLAYING)
    
    try:
        loop.run()
    except:
        pass
    pipeline.set_state(Gst.State.NULL)

