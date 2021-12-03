import sys

sys.path.append('../')
import gi

gi.require_version('Gst', '1.0')
from gi.repository import GObject, Gst
from common.is_aarch_64 import is_aarch64
from common.bus_call import bus_call

import pyds

PGIE_CLASS_ID_VEHICLE = 0
PGIE_CLASS_ID_BICYCLE = 1
PGIE_CLASS_ID_PERSON = 2
PGIE_CLASS_ID_ROADSIGN = 3


def osd_sink_pad_buffer_probe(pad, info, u_data):
    frame_number = 0
    # 初始化检测目标的计数
    obj_counter = {
        PGIE_CLASS_ID_VEHICLE: 0,
        PGIE_CLASS_ID_PERSON: 0,
        PGIE_CLASS_ID_BICYCLE: 0,
        PGIE_CLASS_ID_ROADSIGN: 0
    }
    num_rects = 0

    gst_buffer = info.get_buffer()
    if not gst_buffer:
        print("Unable to get GstBuffer ")
        return

    # 从gst-buffer中接收一批次的数据包
    # 其中由于gst-buffer当时是C语言编写所以，在这里用python的时候需要获取gst-buffer中的数据的hash值
    batch_meta = pyds.gst_buffer_get_nvds_batch_meta(hash(gst_buffer))
    l_frame = batch_meta.frame_meta_list
    while l_frame is not None:
        try:
            # Note that l_frame.data needs a cast to pyds.NvDsFrameMeta
            # The casting is done by pyds.NvDsFrameMeta.cast()
            # The casting also keeps ownership of the underlying memory
            # in the C code, so the Python garbage collector will leave
            # it alone.
            frame_meta = pyds.NvDsFrameMeta.cast(l_frame.data)
        except StopIteration:
            break

        frame_number = frame_meta.frame_num
        num_rects = frame_meta.num_obj_meta
        l_obj = frame_meta.obj_meta_list
        while l_obj is not None:
            try:
                # 将l_obj.data数据嵌入到pyds.NvDsObjectMeta类中
                obj_meta = pyds.NvDsObjectMeta.cast(l_obj.data)
            except StopIteration:
                break
            obj_counter[obj_meta.class_id] += 1
            try:
                l_obj = l_obj.next
            except StopIteration:
                break

        # 获取显示数据
        display_meta = pyds.nvds_acquire_display_meta_from_pool(batch_meta)
        display_meta.num_labels = 1
        py_nvosd_text_params = display_meta.text_params[0]
        py_nvosd_text_params.display_text = "Frame Number={} Number of Objects={} Vehicle_count={} Person_count={}".format(
            frame_number, num_rects, obj_counter[PGIE_CLASS_ID_VEHICLE],
            obj_counter[PGIE_CLASS_ID_PERSON])

        # 设置显示信息出现的位置坐标，左上角是坐标轴原点，设置offset偏移
        py_nvosd_text_params.x_offset = 10
        py_nvosd_text_params.y_offset = 12

        # 设置字体大小，颜色
        py_nvosd_text_params.font_params.font_name = "Serif"
        py_nvosd_text_params.font_params.font_size = 10
        # 设置显示字体颜色为白色
        py_nvosd_text_params.font_params.font_color.set(1.0, 1.0, 1.0, 1.0)

        py_nvosd_text_params.set_bg_clr = 1
        py_nvosd_text_params.text_bg_clr.set(0.0, 0.0, 0.0, 1.0)
        # 使用pyds.get_string()获取显示信息
        print(pyds.get_string(py_nvosd_text_params.display_text))
        # pyds.nvds_add_display_meta_to_frame(frame_meta, display_meta)
        try:
            l_frame = l_frame.next
        except StopIteration:
            break

    return Gst.PadProbeReturn.OK


def main(args):
    # 如果输入参数错误报错
    if len(args) != 2:
        sys.stderr.write("usage: %s <v4l2-device-path>\n" % args[0])
        sys.exit(1)

    # 初始化GStreamer
    GObject.threads_init()
    Gst.init(None)

    # 创建GStreamer元件
    print("Creating Pipeline \n ")
    pipeline = Gst.Pipeline()

    if not pipeline:
        sys.stderr.write(" Unable to create Pipeline \n")

    print("Creating Source \n ")
    # 添加CSI摄像头作为输入摄像头
    source = Gst.ElementFactory.make("nvarguscamerasrc", "usb-cam-source")
    if not source:
        sys.stderr.write(" Unable to create Source \n")

    # 选择输入摄像头的编号
    source.set_property("sensor-id", int(args[1]))
    source.set_property("bufapi-version", 1)

    caps_v4l2src = Gst.ElementFactory.make("capsfilter", "v4l2src_caps")
    if not caps_v4l2src:
        sys.stderr.write(" Unable to create v4l2src capsfilter \n")

    print("Creating Video Converter \n")

    # Adding videoconvert -> nvvideoconvert as not all
    # raw formats are supported by nvvideoconvert;
    # Say YUYV is unsupported - which is the common
    # raw format for many logi usb cams
    # In case we have a camera with raw format supported in
    # nvvideoconvert, GStreamer plugins' capability negotiation
    # shall be intelligent enough to reduce compute by
    # videoconvert doing passthrough (TODO we need to confirm this)

    # videoconvert to make sure a superset of raw formats are supported
    vidconvsrc = Gst.ElementFactory.make("videoconvert", "convertor_src1")
    if not vidconvsrc:
        sys.stderr.write(" Unable to create videoconvert \n")

    # 使用nvvidconv对输入的raw视频数据进行拷贝转换到NVMM上
    nvvidconvsrc = Gst.ElementFactory.make("nvvidconv", "convertor_src2")
    if not nvvidconvsrc:
        sys.stderr.write(" Unable to create Nvvideoconvert \n")

    caps_vidconvsrc = Gst.ElementFactory.make("capsfilter", "nvmm_caps")
    if not caps_vidconvsrc:
        sys.stderr.write(" Unable to create capsfilter \n")

    # 创建nv的视频流接收处理，可以从一个source或者多个source得到一批次的视频帧
    streammux = Gst.ElementFactory.make("nvstreammux", "Stream-muxer")
    if not streammux:
        sys.stderr.write(" Unable to create NvStreamMux \n")

    # 使用nvinfer来推理模型从而输出结果
    pgie = Gst.ElementFactory.make("nvinfer", "primary-inference")
    if not pgie:
        sys.stderr.write(" Unable to create pgie \n")

    # nvosd需要RGBA格式的数据，因此将数据格式从NV12转换到RGBA
    nvvidconv = Gst.ElementFactory.make("nvvideoconvert", "convertor")
    if not nvvidconv:
        sys.stderr.write(" Unable to create nvvidconv \n")

    # 创建nv的OSD插件来实现显示输出上的目标框取
    nvosd = Gst.ElementFactory.make("nvdsosd", "onscreendisplay")

    if not nvosd:
        sys.stderr.write(" Unable to create nvosd \n")

    # 进入rtmp的推流
    queue0 = Gst.ElementFactory.make("queue")
    nvvidconv_postosd = Gst.ElementFactory.make("nvvideoconvert",
                                                "convertor_postosd")
    caps = Gst.ElementFactory.make("capsfilter", "filter")
    caps.set_property(
        "caps", Gst.Caps.from_string("video/x-raw(memory:NVMM), format=I420"))
    encoder = Gst.ElementFactory.make("nvv4l2h264enc", "encoder")
    queue = Gst.ElementFactory.make("queue")
    h264parse = Gst.ElementFactory.make("h264parse")
    flvmux = Gst.ElementFactory.make("flvmux")
    flvmux.set_property("streamable", True)

    # 输出到osd
    if is_aarch64():
        transform = Gst.ElementFactory.make("nvegltransform",
                                            "nvegl-transform")

    print("Creating EGLSink \n")
    sink = Gst.ElementFactory.make("rtmpsink")
    sink.set_property("location", "rtmp://59.110.7.232:1935/rtmplive")
    if not sink:
        sys.stderr.write(" Unable to create egl sink \n")

    print("Playing cam %s " % args[1])
    caps_v4l2src.set_property(
        'caps',
        Gst.Caps.from_string("video/x-raw(memory:NVMM), framerate=30/1"))
    caps_vidconvsrc.set_property(
        'caps', Gst.Caps.from_string("video/x-raw(memory:NVMM)"))
    # source.set_property('device', args[1])
    streammux.set_property('width', 1920)
    streammux.set_property('height', 1080)
    streammux.set_property('batch-size', 1)
    streammux.set_property('batched-push-timeout', 4000000)

    # 设置检测算法配置文件的路径并载入
    pgie.set_property('config-file-path',
                      "config_infer_primary_yoloV3_tiny.txt")
    # Set sync = false to avoid late frame drops at the display-sink
    # sink.set_property('sync', False)

    print("Adding elements to Pipeline \n")
    pipeline.add(source)
    pipeline.add(caps_v4l2src)
    pipeline.add(vidconvsrc)
    pipeline.add(nvvidconvsrc)
    pipeline.add(caps_vidconvsrc)
    pipeline.add(streammux)
    pipeline.add(pgie)
    pipeline.add(nvvidconv)
    pipeline.add(nvosd)
    pipeline.add(queue0)
    pipeline.add(nvvidconv_postosd)
    pipeline.add(caps)
    pipeline.add(encoder)
    pipeline.add(queue)
    pipeline.add(h264parse)
    pipeline.add(flvmux)
    pipeline.add(sink)
    if is_aarch64():
        pass
        # pipeline.add(transform)

    # v4l2src -> nvvideoconvert -> mux -> nvinfer -> nvvideoconvert -> nvosd -> 
    # queue -> nvvideoconvert -> caps -> encoder -> queue -> h264parse -> flvmux -> rtmpsink
    print("Linking elements in the Pipeline \n")
    source.link(caps_v4l2src)
    caps_v4l2src.link(vidconvsrc)
    vidconvsrc.link(nvvidconvsrc)
    nvvidconvsrc.link(caps_vidconvsrc)

    sinkpad = streammux.get_request_pad("sink_0")
    if not sinkpad:
        sys.stderr.write(" Unable to get the sink pad of streammux \n")
    srcpad = caps_vidconvsrc.get_static_pad("src")
    if not srcpad:
        sys.stderr.write(" Unable to get source pad of caps_vidconvsrc \n")
    srcpad.link(sinkpad)
    streammux.link(pgie)
    pgie.link(nvvidconv)
    nvvidconv.link(nvosd)
    if is_aarch64():
        nvosd.link(queue0)
        queue0.link(nvvidconv_postosd)
        # transform.link(sink)
    else:
        nvosd.link(queue0)
        queue0.link(nvvidconv_postosd)

    nvvidconv_postosd.link(caps)
    caps.link(encoder)
    encoder.link(queue)
    queue.link(h264parse)
    h264parse.link(flvmux)
    flvmux.link(sink)

    # 创建GStreamer的事件循环从而不断的获取bus总线上的信息
    # create an event loop and feed gstreamer bus mesages to it
    loop = GObject.MainLoop()
    bus = pipeline.get_bus()
    bus.add_signal_watch()
    bus.connect("message", bus_call, loop)

    # 加入检测探针
    osdsinkpad = nvosd.get_static_pad("sink")
    if not osdsinkpad:
        sys.stderr.write(" Unable to get sink pad of nvosd \n")

    osdsinkpad.add_probe(Gst.PadProbeType.BUFFER, osd_sink_pad_buffer_probe, 0)

    # 开始整个管道运行
    print("Starting pipeline \n")
    pipeline.set_state(Gst.State.PLAYING)
    try:
        loop.run()
    except:
        pass
    pipeline.set_state(Gst.State.NULL)


if __name__ == '__main__':
    sys.exit(main(sys.argv))
