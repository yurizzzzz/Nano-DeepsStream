# AI-Cam

本产品的核心处理板使用NVIDIA的Jetson-Nano-4G，主要实现了使用Nano作为边缘处理板来做安防监控摄像头，并且使用Gstreamer和Deepstream作为主框架，使用MQTT协议作为核心板和云端通信的基础方式，使用RTMP协议作为实时视频传输的方式

<img src="https://s4.ax1x.com/2021/12/21/TMOBcT.jpg" style="zoom:60%;" />

# 整体框架

<img src="https://s4.ax1x.com/2021/12/21/TMxiUH.png" style="zoom:60%;" />

# 相机ISP调色

- 下载camera-override.isp文件，解压到特定文件夹

```
wget http://www.waveshare.net/w/upload/e/eb/Camera_overrides.tar.gz
```

- 解压并且移动

```
tar zxvf Camera_overrides.tar.gz 
sudo cp camera_overrides.isp /var/nvidia/nvcam/settings/
```

- 安装文件

```
sudo chmod 664 /var/nvidia/nvcam/settings/camera_overrides.isp
sudo chown root:root /var/nvidia/nvcam/settings/camera_overrides.isp
```

- 重新启动测试

# 开机自启动设置

- 打开设置点击用户账户，然后点击右上角解锁，再打开自动登录
- 创建shell文件

```
sudo gedit start.sh
```

- 添加以下内容

```
#!/bin/bash
cd /home/nvidia/Nano/Main/
python3 main.py
```

- 添加shell到开机自启动目录里，终端输入

```
gnome-session-properties
```

- 点击添加，在命令栏输入

```
gnome-terminal -x /home/nvidia/Nano/Main/start.sh
```

- 给文件赋予权限

```
sudo chmod a+x start.sh
```

- 重启测试

# 如何部署整个项目

- 安装好DeepStream6.0[官方安装文档](https://docs.nvidia.com/metropolis/deepstream/dev-guide/text/DS_Quickstart.html#jetson-setup)
- 安装好Gst-Python(Jetson系列板子已经自带了所以没必要再安装)

```
如果没装
sudo apt update
sudo apt install python3-gi python3-dev python3-gst-1.0 -y
```

- 安装好Python3.6(Jetson系列板子已经自带)
- 安装好Ubuntu18.04(Jetson系列板子已经自带)

- DeepStream Python bindings[官方参考](https://github.com/NVIDIA-AI-IOT/deepstream_python_apps/blob/master/bindings/README.md)

```
git clone https://github.com/NVIDIA-AI-IOT/deepstream_python_apps.git
cd deepstream_python_apps/bindings
mkdir build
cd build
cmake ..  -DPYTHON_MAJOR_VERSION=3 -DPYTHON_MINOR_VERSION=6 \
    -DPIP_PLATFORM=linux_aarch64 -DDS_PATH=/opt/nvidia/deepstream/deepstream-6.0/
make

pip3 install ./pyds-1.1.0-py3-none*.whl
```

- 将该项目全部搬到jetson的home目录下然后运行main.py即可
