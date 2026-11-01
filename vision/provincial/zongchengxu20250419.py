import os
import sys
import serial
import cv2
import numpy as np
import time 
import threading

#A = ['1','2','3','+','3','1','2']   # 用于存储二维码数据
A=[]
# 配置串口连接
ser = serial.Serial(
    port='/dev/ttyUSB0',      # 根据你的STM32实际端口进行修改
    baudrate=9600,            # 设置波特率为9600
    bytesize=serial.EIGHTBITS, # 数据位为8
    stopbits=serial.STOPBITS_ONE,  # 停止位为1
    parity=serial.PARITY_NONE,     # 校验位为None 
    timeout=1
)

def restart_program():
    """
    退出当前程序并在3秒后重新启动
    """
    print("接收到数字0，程序将在3秒后重新启动...")
    time.sleep(20)
    python = sys.executable
    os.execl(python, python, *sys.argv)

def send_data(data):
    """
    发送数据到 STM32，数据格式为固定的8字节。
    """
    array = [ord(char) for char in data]
    while len(array) < 9: 
        array.append(0)
    data_packet = bytes([0xFF] + array[:9] + [0xFE]) 
    ser.write(data_packet)
    print(f"发送: {data_packet}") 

# 串口数据接收
def receive_data():
    data = ser.readline().decode('utf-8').strip()  # 读取一行数据并解码
    return data

import time

def wait_and_receive_data():
    """
    该函数进入等待状态，持续等待1秒钟，在1秒钟内接收7位数据并存储到全局数组A中。
    如果1秒内没有接收到数据，则重新开始等待。
    """
    global A

    start_time = time.time()  # 获取当前时间戳，用于计算等待时间
    while True:
        # 计算当前时间与开始时间的差值
        elapsed_time = time.time() - start_time

        # 如果等待时间超过1秒，则退出循环重新开始
        if elapsed_time >= 1:
            print("等待1秒钟未接收到数据，重新开始...")
            start_time = time.time()  # 重置开始时间
            continue  # 重新进入等待状态

        # 尝试从串口接收数据
        data = ser.readline().decode('utf-8').strip()  # 从串口读取数据并解码

        # 确保接收到的数据长度是7个字符
        if len(data) == 7:
            A = list(data)  # 将接收到的数据存储到数组A中
            print(f"接收到的数据: {data}")
            print(f"已存储到数组A: {A}")
            break  # 退出函数
        else:
            print("接收到的数据长度不为7，继续等待...")

# 获取颜色名称（共享函数）
def get_color_name(bgr_val):
    """
    根据BGR值判断颜色，仅支持红、绿、蓝三种颜色。
    """
    blue, green, red = bgr_val
    if red > blue and red > green:
        return "Red", "1"
    elif green > red and green > blue:
        return "Green", "2"
    elif blue > red and blue > green:
        return "Blue", "3"
    else:
        return "Unknown", "0"
    
# 二维码检测任务并存储到数组 A
def run_erweima():
    global A
    if not ser.is_open:
        ser.open()
    print(f"串口 {ser.port} 已打开，执行二维码检测任务...")
    cap0 = cv2.VideoCapture("/dev/video_xia0")
    if not cap0.isOpened():
        print("无法打开摄像头")
        return

    consistent_count = 0
    last_data = None

    while True:
        ret, frame = cap0.read()
        if not ret:
            print("无法接收帧，退出...")
            send_data("帧读取错误")
            break

        qrcode_detector = cv2.QRCodeDetector()
        data, _, _ = qrcode_detector.detectAndDecode(frame)

        if data:
            print(f"检测到二维码数据: {data}")

            # 如果当前数据与上次扫描的相同，则增加计数
            if data == last_data:
                consistent_count += 1
            else:
                consistent_count = 1
                last_data = data

            # 如果连续3次识别到相同结果，解析数据并存储到数组 A
            if consistent_count >= 3:
                if len(data) == 7:
                    A = list(data)  # 将字符串分解为 7 个字符存储到数组 A
                    print(f"解析二维码数据到数组 A: {A}")
                    formatted_data = data[:7].ljust(7, '0') + '0'
                    send_data(formatted_data)
                else:
                    print("二维码数据长度不符合要求（必须为7个字符）")
                    send_data("二维码数据错误")
                break

        cv2.imshow('QR Code Scanner', frame)
        if cv2.waitKey(1) == ord('q'):
            break

    cap0.release()
    cv2.destroyAllWindows()

def run_wukuaiyuanxin():  ##第一圈物块定标（普通圆形）
    # 新增颜色阈值定义（来自ceshi022001.py）
    lower_red = np.array([0, 50, 50])
    upper_red = np.array([10, 255, 255])
    lower_green = np.array([30, 40, 40])
    upper_green = np.array([90, 255, 255])
    lower_blue = np.array([80, 50, 50])
    upper_blue = np.array([140, 255, 255])
    kernel = np.ones((3, 3), np.uint8)

    def detect_stacking_and_color(frame, loop_radius=(40, 50), roi=(0, 50, 640, 480)):
        """修改后的颜色识别逻辑"""
        roi_img = frame[roi[1]:roi[1] + roi[3], roi[0]:roi[0] + roi[2]]
        gray = cv2.cvtColor(roi_img, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (9, 9), 2, 2)
        circles = cv2.HoughCircles(
            gray, 
            cv2.HOUGH_GRADIENT, 
            1, 
            20, 
            param1=25, 
            param2=25, 
            minRadius=loop_radius[0], 
            maxRadius=loop_radius[1]
        )

        if circles is not None:
            circles = np.uint16(np.around(circles))
            for i in circles[0, :]:
                center = (i[0] + roi[0], i[1] + roi[1])
                radius = i[2]

                # 使用HSV颜色空间进行颜色识别（新增逻辑）
                mask = np.zeros_like(gray)
                cv2.circle(mask, (i[0], i[1]), radius, 255, -1)
                hsv_img = cv2.cvtColor(roi_img, cv2.COLOR_BGR2HSV)
                
                # 创建颜色掩膜
                red_mask = cv2.inRange(hsv_img, lower_red, upper_red)
                green_mask = cv2.inRange(hsv_img, lower_green, upper_green)
                blue_mask = cv2.inRange(hsv_img, lower_blue, upper_blue)

                # 形态学操作（与ceshi022001.py一致）
                red_mask = cv2.erode(red_mask, kernel, iterations=1)
                red_mask = cv2.dilate(red_mask, kernel, iterations=2)
                green_mask = cv2.erode(green_mask, kernel, iterations=2)
                green_mask = cv2.dilate(green_mask, kernel, iterations=6)
                blue_mask = cv2.erode(blue_mask, kernel, iterations=1)
                blue_mask = cv2.dilate(blue_mask, kernel, iterations=3)

                # 计算颜色区域面积
                red_area = cv2.countNonZero(cv2.bitwise_and(red_mask, mask))
                green_area = cv2.countNonZero(cv2.bitwise_and(green_mask, mask))
                blue_area = cv2.countNonZero(cv2.bitwise_and(blue_mask, mask))
                
                # 确定主颜色
                max_area = max(red_area, green_area, blue_area)
                if max_area == red_area:
                    color_code = "1"
                elif max_area == green_area:
                    color_code = "2"
                else:
                    color_code = "3"

                formatted_data = f"{center[0]:04}{center[1]:04}{color_code}{radius:01}"
                return formatted_data, center
        return None, None

    # 显式初始化摄像头
    cap = cv2.VideoCapture("/dev/video_shang0")
    if not cap.isOpened():
        print("摄像头初始化失败")
        return
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    stability_threshold = 20
    stable_count = 0
    last_center = None

    while True:
        ret, frame = cap.read()
        if not ret:
            print("无法读取摄像头帧")
            break

        data, current_center = detect_stacking_and_color(frame)

        if data:
            if last_center is not None:
                distance = np.sqrt((current_center[0] - last_center[0])**2 + (current_center[1] - last_center[1])**2)
                if distance < 5:
                    stable_count += 1
                else:
                    stable_count = 1
            else:
                stable_count = 1
            last_center = current_center
            if stable_count >= stability_threshold:
                send_data(data)
                print(f"发送的物块数据: {data}")
                break
        else:
            stable_count = 0
        cv2.imshow("物块检测", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # 释放摄像头资源
    cap.release()
    cv2.destroyAllWindows()

def wukuaiyuanxin_logic1():  ##第一圈物块颜色识别（普通圆形）
    # 新增颜色阈值定义（来自ceshi022001.py）
    lower_red = np.array([0, 50, 50])
    upper_red = np.array([10, 255, 255])
    lower_green = np.array([30, 40, 40])
    upper_green = np.array([90, 255, 255])
    lower_blue = np.array([80, 50, 50])
    upper_blue = np.array([140, 255, 255])
    kernel = np.ones((3, 3), np.uint8)

    def detect_stacking_and_color(frame, loop_radius=(40, 50), roi=(220, 200, 200, 120)):
        """修改后的颜色识别逻辑，限定识别区域"""
        roi_img = frame[roi[1]:roi[1] + roi[3], roi[0]:roi[0] + roi[2]]  # 提取ROI区域
        gray = cv2.cvtColor(roi_img, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (9, 9), 2, 2)
        circles = cv2.HoughCircles(
            gray, 
            cv2.HOUGH_GRADIENT, 
            1, 
            20, 
            param1=25, 
            param2=25, 
            minRadius=loop_radius[0], 
            maxRadius=loop_radius[1]
        )

        if circles is not None:
            circles = np.uint16(np.around(circles))
            for i in circles[0, :]:
                center = (i[0] + roi[0], i[1] + roi[1])  # 将圆心坐标转换回原图坐标系
                radius = i[2]

                # 使用HSV颜色空间进行颜色识别（新增逻辑）
                mask = np.zeros_like(gray)
                cv2.circle(mask, (i[0], i[1]), radius, 255, -1)
                hsv_img = cv2.cvtColor(roi_img, cv2.COLOR_BGR2HSV)
                
                # 创建颜色掩膜
                red_mask = cv2.inRange(hsv_img, lower_red, upper_red)
                green_mask = cv2.inRange(hsv_img, lower_green, upper_green)
                blue_mask = cv2.inRange(hsv_img, lower_blue, upper_blue)

                # 形态学操作（与ceshi022001.py一致）
                red_mask = cv2.erode(red_mask, kernel, iterations=1)
                red_mask = cv2.dilate(red_mask, kernel, iterations=2)
                green_mask = cv2.erode(green_mask, kernel, iterations=2)
                green_mask = cv2.dilate(green_mask, kernel, iterations=6)
                blue_mask = cv2.erode(blue_mask, kernel, iterations=1)
                blue_mask = cv2.dilate(blue_mask, kernel, iterations=3)

                # 计算颜色区域面积
                red_area = cv2.countNonZero(cv2.bitwise_and(red_mask, mask))
                green_area = cv2.countNonZero(cv2.bitwise_and(green_mask, mask))
                blue_area = cv2.countNonZero(cv2.bitwise_and(blue_mask, mask))
                
                # 确定主颜色
                max_area = max(red_area, green_area, blue_area)
                if max_area == red_area:
                    color_code = "1"
                elif max_area == green_area:
                    color_code = "2"
                else:
                    color_code = "3"

                formatted_data = f"{center[0]:04}{center[1]:04}{color_code}{radius:01}"
                return formatted_data, center
        return None, None

    # 显式初始化摄像头
    cap = cv2.VideoCapture("/dev/video_shang0")
    if not cap.isOpened():
        print("摄像头初始化失败")
        return
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    # 稳定性检测参数
    stability_threshold = 10  # 允许的坐标波动范围（像素）
    stable_count_threshold = 12  # 连续稳定次数
    last_center = None
    stable_count = 0

    count = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            print("无法读取摄像头帧")
            break

        data, current_center = detect_stacking_and_color(frame)

        if data and current_center:
            if last_center is not None:
                # 计算当前中心与上一次中心的距离
                distance = np.sqrt((current_center[0] - last_center[0])**2 + (current_center[1] - last_center[1])**2)
                if distance < stability_threshold:
                    stable_count += 1
                else:
                    stable_count = 0  # 超出波动范围，重置稳定计数
            else:
                stable_count = 1  # 第一次检测到中心

            last_center = current_center

            # 如果稳定次数达到阈值，则输出结果
            if stable_count >= stable_count_threshold:
                if count == 0 and data[8] == str(A[0]):
                    count = 1
                    send_data(data)
                    print(f"匹配到A[0]: {data}")
                    time.sleep(3.0)
                elif count == 1 and data[8] == str(A[1]):
                    count = 2
                    send_data(data)
                    print(f"匹配到A[1]: {data}")
                    time.sleep(3.0)
                elif count == 2 and data[8] == str(A[2]):
                    send_data(data)
                    print(f"匹配到A[2]: {data}")
                    time.sleep(3.0)
                    break

        # 绘制识别区域（调试用）
        cv2.rectangle(frame, (220, 200), (420, 320), (0, 255, 0), 2)  # 绘制ROI区域
        cv2.imshow("Logic1 Detection", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # 释放摄像头资源
    cap.release()
    cv2.destroyAllWindows()

def wukuaiyuanxin_logic2():  ##第二圈物块定标（普通圆形）
    # 新增颜色阈值定义（来自ceshi022001.py）
    lower_red = np.array([0, 50, 50])
    upper_red = np.array([10, 255, 255])
    lower_green = np.array([30, 40, 40])
    upper_green = np.array([90, 255, 255])
    lower_blue = np.array([80, 50, 50])
    upper_blue = np.array([140, 255, 255])
    kernel = np.ones((3, 3), np.uint8)

    def detect_stacking_and_color(frame, loop_radius=(40, 50), roi=(220, 200, 200, 120)):
        """修改后的颜色识别逻辑，限定识别区域"""
        roi_img = frame[roi[1]:roi[1] + roi[3], roi[0]:roi[0] + roi[2]]  # 提取ROI区域
        gray = cv2.cvtColor(roi_img, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (9, 9), 2, 2)
        circles = cv2.HoughCircles(
            gray, 
            cv2.HOUGH_GRADIENT, 
            1, 
            20, 
            param1=25, 
            param2=25, 
            minRadius=loop_radius[0], 
            maxRadius=loop_radius[1]
        )

        if circles is not None:
            circles = np.uint16(np.around(circles))
            for i in circles[0, :]:
                center = (i[0] + roi[0], i[1] + roi[1])  # 将圆心坐标转换回原图坐标系
                radius = i[2]

                # 使用HSV颜色空间进行颜色识别（新增逻辑）
                mask = np.zeros_like(gray)
                cv2.circle(mask, (i[0], i[1]), radius, 255, -1)
                hsv_img = cv2.cvtColor(roi_img, cv2.COLOR_BGR2HSV)
                
                # 创建颜色掩膜
                red_mask = cv2.inRange(hsv_img, lower_red, upper_red)
                green_mask = cv2.inRange(hsv_img, lower_green, upper_green)
                blue_mask = cv2.inRange(hsv_img, lower_blue, upper_blue)

                # 形态学操作（与ceshi022001.py一致）
                red_mask = cv2.erode(red_mask, kernel, iterations=1)
                red_mask = cv2.dilate(red_mask, kernel, iterations=2)
                green_mask = cv2.erode(green_mask, kernel, iterations=2)
                green_mask = cv2.dilate(green_mask, kernel, iterations=6)
                blue_mask = cv2.erode(blue_mask, kernel, iterations=1)
                blue_mask = cv2.dilate(blue_mask, kernel, iterations=3)

                # 计算颜色区域面积
                red_area = cv2.countNonZero(cv2.bitwise_and(red_mask, mask))
                green_area = cv2.countNonZero(cv2.bitwise_and(green_mask, mask))
                blue_area = cv2.countNonZero(cv2.bitwise_and(blue_mask, mask))
                
                # 确定主颜色
                max_area = max(red_area, green_area, blue_area)
                if max_area == red_area:
                    color_code = "1"
                elif max_area == green_area:
                    color_code = "2"
                else:
                    color_code = "3"

                formatted_data = f"{center[0]:04}{center[1]:04}{color_code}{radius:01}"
                return formatted_data, center
        return None, None

    # 显式初始化摄像头
    cap = cv2.VideoCapture("/dev/video_shang0")
    if not cap.isOpened():
        print("摄像头初始化失败")
        return
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    # 稳定性检测参数
    stability_threshold = 10  # 允许的坐标波动范围（像素）
    stable_count_threshold = 12  # 连续稳定次数
    last_center = None
    stable_count = 0

    count = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            print("无法读取摄像头帧")
            break

        data, current_center = detect_stacking_and_color(frame)

        if data and current_center:
            if last_center is not None:
                # 计算当前中心与上一次中心的距离
                distance = np.sqrt((current_center[0] - last_center[0])**2 + (current_center[1] - last_center[1])**2)
                if distance < stability_threshold:
                    stable_count += 1
                else:
                    stable_count = 0  # 超出波动范围，重置稳定计数
            else:
                stable_count = 1  # 第一次检测到中心

            last_center = current_center

            # 如果稳定次数达到阈值，则输出结果
            if stable_count >= stable_count_threshold:
                if count == 0 and data[8] == str(A[4]):
                    count = 1
                    send_data(data)
                    print(f"匹配到A[4]: {data}")
                    time.sleep(3.0)
                elif count == 1 and data[8] == str(A[5]):
                    count = 2
                    send_data(data)
                    print(f"匹配到A[5]: {data}")
                    time.sleep(3.0)
                elif count == 2 and data[8] == str(A[6]):
                    send_data(data)
                    print(f"匹配到A[6]: {data}")
                    time.sleep(3.0)
                    break

        # 绘制识别区域（调试用）
        cv2.rectangle(frame, (220, 200), (420, 320), (0, 255, 0), 2)  # 绘制ROI区域
        cv2.imshow("Logic2 Detection", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # 释放摄像头资源
    cap.release()
    cv2.destroyAllWindows()

def run_wukuaiyuanxin_1():  ##把物块放到转盘的时候，检测转盘上的物块贴纸(普通圆心)
    # 颜色阈值定义
    lower_red = np.array([0, 50, 50])
    upper_red = np.array([10, 255, 255])
    lower_green = np.array([30, 40, 40])
    upper_green = np.array([90, 255, 255])
    lower_blue = np.array([80, 50, 50])
    upper_blue = np.array([140, 255, 255])
    kernel = np.ones((3, 3), np.uint8)
    
    # 可配置的ROI区域 (x, y, width, height)
    ROI_CONFIG = {
        'x': 120,       # ROI左上角x坐标
        'y': 200,       # ROI左上角y坐标
        'width': 400,   # ROI宽度
        'height': 200   # ROI高度
    }

    def detect_stacking_and_color(frame, loop_radius=(28, 33)):
        """修改后的颜色识别逻辑"""
        # 从配置获取ROI参数
        x, y, w, h = ROI_CONFIG['x'], ROI_CONFIG['y'], ROI_CONFIG['width'], ROI_CONFIG['height']
        roi_img = frame[y:y + h, x:x + w]
        gray = cv2.cvtColor(roi_img, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (9, 9), 2, 2)
        circles = cv2.HoughCircles(
            gray, 
            cv2.HOUGH_GRADIENT, 
            1, 
            20, 
            param1=25, 
            param2=25, 
            minRadius=loop_radius[0], 
            maxRadius=loop_radius[1]
        )

        if circles is not None:
            circles = np.uint16(np.around(circles))
            for i in circles[0, :]:
                center = (i[0] + x, i[1] + y)  # 转换为全局坐标
                radius = i[2]

                # 使用HSV颜色空间进行颜色识别
                mask = np.zeros_like(gray)
                cv2.circle(mask, (i[0], i[1]), radius, 255, -1)
                hsv_img = cv2.cvtColor(roi_img, cv2.COLOR_BGR2HSV)
                
                # 创建颜色掩膜
                red_mask = cv2.inRange(hsv_img, lower_red, upper_red)
                green_mask = cv2.inRange(hsv_img, lower_green, upper_green)
                blue_mask = cv2.inRange(hsv_img, lower_blue, upper_blue)

                # 形态学操作
                red_mask = cv2.erode(red_mask, kernel, iterations=1)
                red_mask = cv2.dilate(red_mask, kernel, iterations=2)
                green_mask = cv2.erode(green_mask, kernel, iterations=2)
                green_mask = cv2.dilate(green_mask, kernel, iterations=6)
                blue_mask = cv2.erode(blue_mask, kernel, iterations=1)
                blue_mask = cv2.dilate(blue_mask, kernel, iterations=3)

                # 计算颜色区域面积
                red_area = cv2.countNonZero(cv2.bitwise_and(red_mask, mask))
                green_area = cv2.countNonZero(cv2.bitwise_and(green_mask, mask))
                blue_area = cv2.countNonZero(cv2.bitwise_and(blue_mask, mask))
                
                # 确定主颜色
                max_area = max(red_area, green_area, blue_area)
                if max_area == red_area:
                    color_code = "1"
                elif max_area == green_area:
                    color_code = "2"
                else:
                    color_code = "3"

                formatted_data = f"{center[0]:04}{center[1]:04}{color_code}{radius:01}"
                return formatted_data, center
        return None, None

    # 显式初始化摄像头
    cap = cv2.VideoCapture("/dev/video_shang0")
    if not cap.isOpened():
        print("摄像头初始化失败")
        return
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    stability_threshold = 25
    stable_count = 0
    last_center = None

    while True:
        ret, frame = cap.read()
        if not ret:
            print("无法读取摄像头帧")
            break

        # 绘制ROI区域
        x, y, w, h = ROI_CONFIG['x'], ROI_CONFIG['y'], ROI_CONFIG['width'], ROI_CONFIG['height']
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

        data, current_center = detect_stacking_and_color(frame)

        if data:
            if last_center is not None:
                distance = np.sqrt((current_center[0] - last_center[0])**2 + (current_center[1] - last_center[1])**2)
                if distance < 3:
                    stable_count += 1
                else:
                    stable_count = 1
            else:
                stable_count = 1
            last_center = current_center
            
            # 绘制圆心
            if current_center:
                cv2.circle(frame, current_center, 5, (0, 0, 255), -1)
            
            if stable_count >= stability_threshold:
                send_data(data)
                print(f"发送的物块数据: {data}")
                break
        else:
            stable_count = 0
        
        cv2.imshow("物块检测", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # 释放摄像头资源
    cap.release()
    cv2.destroyAllWindows()

def wukuaiyuanxin_logic1_1():  ##第一次把物块放到转盘的时候，物块的放置顺序（普通圆形）
    # 新增颜色阈值定义（来自ceshi022001.py）
    lower_red = np.array([0, 50, 50])
    upper_red = np.array([10, 255, 255])
    lower_green = np.array([30, 40, 40])
    upper_green = np.array([90, 255, 255])
    lower_blue = np.array([80, 50, 50])
    upper_blue = np.array([140, 255, 255])
    kernel = np.ones((3, 3), np.uint8)

    def detect_stacking_and_color(frame, loop_radius=(28, 33), roi=(220, 200, 200, 120)):
        """修改后的颜色识别逻辑，限定识别区域"""
        roi_img = frame[roi[1]:roi[1] + roi[3], roi[0]:roi[0] + roi[2]]  # 提取ROI区域
        gray = cv2.cvtColor(roi_img, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (9, 9), 2, 2)
        circles = cv2.HoughCircles(
            gray, 
            cv2.HOUGH_GRADIENT, 
            1, 
            20, 
            param1=25, 
            param2=25, 
            minRadius=loop_radius[0], 
            maxRadius=loop_radius[1]
        )

        if circles is not None:
            circles = np.uint16(np.around(circles))
            for i in circles[0, :]:
                center = (i[0] + roi[0], i[1] + roi[1])  # 将圆心坐标转换回原图坐标系
                radius = i[2]

                # 使用HSV颜色空间进行颜色识别（新增逻辑）
                mask = np.zeros_like(gray)
                cv2.circle(mask, (i[0], i[1]), radius, 255, -1)
                hsv_img = cv2.cvtColor(roi_img, cv2.COLOR_BGR2HSV)
                
                # 创建颜色掩膜
                red_mask = cv2.inRange(hsv_img, lower_red, upper_red)
                green_mask = cv2.inRange(hsv_img, lower_green, upper_green)
                blue_mask = cv2.inRange(hsv_img, lower_blue, upper_blue)

                # 形态学操作（与ceshi022001.py一致）
                red_mask = cv2.erode(red_mask, kernel, iterations=1)
                red_mask = cv2.dilate(red_mask, kernel, iterations=2)
                green_mask = cv2.erode(green_mask, kernel, iterations=2)
                green_mask = cv2.dilate(green_mask, kernel, iterations=6)
                blue_mask = cv2.erode(blue_mask, kernel, iterations=1)

                blue_mask = cv2.dilate(blue_mask, kernel, iterations=3)

                # 计算颜色区域面积
                red_area = cv2.countNonZero(cv2.bitwise_and(red_mask, mask))
                green_area = cv2.countNonZero(cv2.bitwise_and(green_mask, mask))
                blue_area = cv2.countNonZero(cv2.bitwise_and(blue_mask, mask))
                
                # 确定主颜色
                max_area = max(red_area, green_area, blue_area)
                if max_area == red_area:
                    color_code = "1"
                elif max_area == green_area:
                    color_code = "2"
                else:
                    color_code = "3"

                formatted_data = f"{center[0]:04}{center[1]:04}{color_code}{radius:01}"
                return formatted_data, center
        return None, None

    # 显式初始化摄像头
    cap = cv2.VideoCapture("/dev/video_shang0")
    if not cap.isOpened():
        print("摄像头初始化失败")
        return
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    # 稳定性检测参数
    stability_threshold = 10  # 允许的坐标波动范围（像素）
    stable_count_threshold = 25  # 连续稳定次数
    last_center = None
    stable_count = 0

    count = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            print("无法读取摄像头帧")
            break

        data, current_center = detect_stacking_and_color(frame)

        if data and current_center:
            if last_center is not None:
                # 计算当前中心与上一次中心的距离
                distance = np.sqrt((current_center[0] - last_center[0])**2 + (current_center[1] - last_center[1])**2)
                if distance < stability_threshold:
                    stable_count += 1
                else:
                    stable_count = 0  # 超出波动范围，重置稳定计数
            else:
                stable_count = 1  # 第一次检测到中心

            last_center = current_center

            # 如果稳定次数达到阈值，则输出结果
            if stable_count >= stable_count_threshold:
                if count == 0 and data[8] == str(A[0]):
                    count = 1
                    send_data(data)
                    print(f"匹配到A[0]: {data}")
                    time.sleep(2.5)
                elif count == 1 and data[8] == str(A[1]):
                    count = 2
                    send_data(data)
                    print(f"匹配到A[1]: {data}")
                    time.sleep(2.5)
                elif count == 2 and data[8] == str(A[2]):
                    send_data(data)
                    print(f"匹配到A[2]: {data}")
                    time.sleep(2.5)
                    break

        # 绘制识别区域（调试用）
        cv2.rectangle(frame, (220, 200), (420, 320), (0, 255, 0), 2)  # 绘制ROI区域
        cv2.imshow("Logic1 Detection", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # 释放摄像头资源
    cap.release()
    cv2.destroyAllWindows()

def wukuaiyuanxin_logic2_1():  ##第二次把物块放到转盘的时候，物块的放置顺序（普通圆形）
    # 新增颜色阈值定义（来自ceshi022001.py）
    lower_red = np.array([0, 50, 50])
    upper_red = np.array([10, 255, 255])
    lower_green = np.array([30, 40, 40])
    upper_green = np.array([90, 255, 255])
    lower_blue = np.array([80, 50, 50])
    upper_blue = np.array([140, 255, 255])
    kernel = np.ones((3, 3), np.uint8)

    def detect_stacking_and_color(frame, loop_radius=(28, 33), roi=(220, 200, 200, 120)):
        """修改后的颜色识别逻辑，限定识别区域"""
        roi_img = frame[roi[1]:roi[1] + roi[3], roi[0]:roi[0] + roi[2]]  # 提取ROI区域
        gray = cv2.cvtColor(roi_img, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (9, 9), 2, 2)
        circles = cv2.HoughCircles(
            gray, 
            cv2.HOUGH_GRADIENT, 
            1, 
            20, 
            param1=25, 
            param2=25, 
            minRadius=loop_radius[0], 
            maxRadius=loop_radius[1]
        )

        if circles is not None:
            circles = np.uint16(np.around(circles))
            for i in circles[0, :]:
                center = (i[0] + roi[0], i[1] + roi[1])  # 将圆心坐标转换回原图坐标系
                radius = i[2]

                # 使用HSV颜色空间进行颜色识别（新增逻辑）
                mask = np.zeros_like(gray)
                cv2.circle(mask, (i[0], i[1]), radius, 255, -1)
                hsv_img = cv2.cvtColor(roi_img, cv2.COLOR_BGR2HSV)
                
                # 创建颜色掩膜
                red_mask = cv2.inRange(hsv_img, lower_red, upper_red)
                green_mask = cv2.inRange(hsv_img, lower_green, upper_green)
                blue_mask = cv2.inRange(hsv_img, lower_blue, upper_blue)

                # 形态学操作（与ceshi022001.py一致）
                red_mask = cv2.erode(red_mask, kernel, iterations=1)
                red_mask = cv2.dilate(red_mask, kernel, iterations=2)
                green_mask = cv2.erode(green_mask, kernel, iterations=2)
                green_mask = cv2.dilate(green_mask, kernel, iterations=6)
                blue_mask = cv2.erode(blue_mask, kernel, iterations=1)
                blue_mask = cv2.dilate(blue_mask, kernel, iterations=3)

                # 计算颜色区域面积
                red_area = cv2.countNonZero(cv2.bitwise_and(red_mask, mask))
                green_area = cv2.countNonZero(cv2.bitwise_and(green_mask, mask))
                blue_area = cv2.countNonZero(cv2.bitwise_and(blue_mask, mask))
                
                # 确定主颜色
                max_area = max(red_area, green_area, blue_area)
                if max_area == red_area:
                    color_code = "1"
                elif max_area == green_area:
                    color_code = "2"
                else:
                    color_code = "3"

                formatted_data = f"{center[0]:04}{center[1]:04}{color_code}{radius:01}"
                return formatted_data, center
        return None, None

    # 显式初始化摄像头
    cap = cv2.VideoCapture("/dev/video_shang0")
    if not cap.isOpened():
        print("摄像头初始化失败")
        return
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    # 稳定性检测参数
    stability_threshold = 10  # 允许的坐标波动范围（像素）
    stable_count_threshold = 16  # 连续稳定次数
    last_center = None
    stable_count = 0

    count = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            print("无法读取摄像头帧")
            break

        data, current_center = detect_stacking_and_color(frame)

        if data and current_center:
            if last_center is not None:
                # 计算当前中心与上一次中心的距离
                distance = np.sqrt((current_center[0] - last_center[0])**2 + (current_center[1] - last_center[1])**2)
                if distance < stability_threshold:
                    stable_count += 1
                else:
                    stable_count = 0  # 超出波动范围，重置稳定计数
            else:
                stable_count = 1  # 第一次检测到中心

            last_center = current_center

            # 如果稳定次数达到阈值，则输出结果
            if stable_count >= stable_count_threshold:
                if count == 0 and data[8] == str(A[4]):
                    count = 1
                    send_data(data)
                    print(f"匹配到A[4]: {data}")
                    time.sleep(2.5)
                elif count == 1 and data[8] == str(A[5]):
                    count = 2
                    send_data(data)
                    print(f"匹配到A[5]: {data}")
                    time.sleep(2.5)
                elif count == 2 and data[8] == str(A[6]):
                    send_data(data)
                    print(f"匹配到A[6]: {data}")
                    time.sleep(2.5)
                    break

        # 绘制识别区域（调试用）
        cv2.rectangle(frame, (220, 200), (420, 320), (0, 255, 0), 2)  # 绘制ROI区域
        cv2.imshow("Logic2 Detection", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # 释放摄像头资源
    cap.release()
    cv2.destroyAllWindows()

def run_sehuanyuanxin2():  #初赛放物块的时候，色环第一次定标的程序（地上的圆形）
    # 红色双阈值范围
    lower_red1 = np.array([0, 50, 50])
    upper_red1 = np.array([10, 255, 255])
    lower_red2 = np.array([160, 50, 50])
    upper_red2 = np.array([180, 255, 255])
    lower_green = np.array([30, 40, 40])
    upper_green = np.array([90, 255, 255])
    lower_blue = np.array([90, 50, 90])
    upper_blue = np.array([140, 255, 255])
    kernel = np.ones((3, 3), np.uint8)

    cap2 = cv2.VideoCapture("/dev/video_shang0")
    if not cap2.isOpened():
        print("无法读取摄像头帧")
        return

    cap2.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
    cap2.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

    start_time = time.time()
    while True:
        ret, frame = cap2.read()
        if not ret:
            print("无法读取摄像头帧")
            break

        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        # 合并两个红色范围
        red_mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
        red_mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
        red_mask = cv2.bitwise_or(red_mask1, red_mask2)
        green_mask = cv2.inRange(hsv, lower_green, upper_green)
        blue_mask = cv2.inRange(hsv, lower_blue, upper_blue)

        # 形态学处理
        red_mask = cv2.erode(red_mask, kernel, iterations=2)
        red_mask = cv2.dilate(red_mask, kernel, iterations=4)
        green_mask = cv2.erode(green_mask, kernel, iterations=2)
        green_mask = cv2.dilate(green_mask, kernel, iterations=6)
        blue_mask = cv2.erode(blue_mask, kernel, iterations=1)
        blue_mask = cv2.dilate(blue_mask, kernel, iterations=3)

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        filtered_img = cv2.GaussianBlur(gray, (3, 3), 0)
        circles = cv2.HoughCircles(filtered_img,
                                cv2.HOUGH_GRADIENT, dp=1, minDist=30,
                                param1=50, param2=30,
                                minRadius=170, maxRadius=180)

        if circles is not None:
            circles = np.round(circles[0, :]).astype("int")
            for (x, y, r) in circles:
                x = np.clip(x, 0, frame.shape[1] - 1)
                y = np.clip(y, 0, frame.shape[0] - 1)

                mask = np.zeros_like(gray)
                cv2.circle(mask, (x, y), int(0.9 * r), 255, -1)

                red_area = cv2.countNonZero(cv2.bitwise_and(red_mask, mask))
                green_area = cv2.countNonZero(cv2.bitwise_and(green_mask, mask))
                blue_area = cv2.countNonZero(cv2.bitwise_and(blue_mask, mask))

                max_area = max(red_area, green_area, blue_area)
                if max_area == 0:
                    print("检测到无效颜色区域（HSV全为0），跳过...")
                    continue

                if max_area == red_area:
                    color = "1"
                    masked = cv2.bitwise_and(hsv, hsv, mask=cv2.bitwise_and(red_mask, mask))
                    avg_hsv = cv2.mean(masked, mask=cv2.bitwise_and(red_mask, mask))[:3]
                    if avg_hsv[0] == 0 and avg_hsv[1] == 0 and avg_hsv[2] == 0:
                        print("检测到无效红色区域（HSV全为0），跳过...")
                        continue
                elif max_area == green_area:
                    color = "2"
                    masked = cv2.bitwise_and(hsv, hsv, mask=cv2.bitwise_and(green_mask, mask))
                    avg_hsv = cv2.mean(masked, mask=cv2.bitwise_and(green_mask, mask))[:3]
                    if avg_hsv[0] == 0 and avg_hsv[1] == 0 and avg_hsv[2] == 0:
                        print("检测到无效绿色区域（HSV全为0），跳过...")
                        continue
                else:
                    color = "3"
                    masked = cv2.bitwise_and(hsv, hsv, mask=cv2.bitwise_and(blue_mask, mask))
                    avg_hsv = cv2.mean(masked, mask=cv2.bitwise_and(blue_mask, mask))[:3]
                    if avg_hsv[0] == 0 and avg_hsv[1] == 0 and avg_hsv[2] == 0:
                        print("检测到无效蓝色区域（HSV全为0），跳过...")
                        continue

                print(f"检测到颜色 {color}，HSV值: H={avg_hsv[0]:.1f}, S={avg_hsv[1]:.1f}, V={avg_hsv[2]:.1f}")
                formatted_data = f"{x:04}{y:04}{color[0]}"
                send_data(formatted_data)
                print(f"检测到颜色，发送数据：{formatted_data}")
                cap2.release()
                return

        if time.time() - start_time > 5.0:
            send_data("000000004")
            print("2秒内未检测到颜色，发送超时信号")
            break

        time.sleep(0.05)

    cap2.release()

def run_sehuanyuanxin2_centered():  #初赛放物块的时候，色环第二次定标的程序（地上的圆形）
    # 红色双阈值范围
    lower_red1 = np.array([0, 50, 50])
    upper_red1 = np.array([10, 255, 255])
    lower_red2 = np.array([160, 50, 50])
    upper_red2 = np.array([180, 255, 255])
    lower_green = np.array([30, 40, 40])
    upper_green = np.array([90, 255, 255])
    lower_blue = np.array([90, 50, 90])
    upper_blue = np.array([140, 255, 255])
    kernel = np.ones((3, 3), np.uint8)

    center_x, center_y = 960, 540
    square_side = 600
    square_side1 = 400
    square_side2 = 800
    half_side = square_side // 2
    half_side1 = square_side1 // 2
    half_side2 = square_side2 // 2

    cap2 = cv2.VideoCapture("/dev/video_shang0")
    if not cap2.isOpened():
        print("无法读取摄像头帧")
        return

    cap2.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
    cap2.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

    start_time = time.time()
    while True:
        ret, frame = cap2.read()
        if not ret:
            print("无法读取摄像头帧")
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        filtered_img = cv2.GaussianBlur(gray, (3, 3), 0)
        circles = cv2.HoughCircles(filtered_img,
                                cv2.HOUGH_GRADIENT, dp=1, minDist=30,
                                param1=50, param2=30,
                                minRadius=85, maxRadius=89)

        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        red_mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
        red_mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
        red_mask = cv2.bitwise_or(red_mask1, red_mask2)
        green_mask = cv2.inRange(hsv, lower_green, upper_green)
        blue_mask = cv2.inRange(hsv, lower_blue, upper_blue)

        red_mask = cv2.erode(red_mask, kernel, iterations=1)
        red_mask = cv2.dilate(red_mask, kernel, iterations=2)
        green_mask = cv2.erode(green_mask, kernel, iterations=2)
        green_mask = cv2.dilate(green_mask, kernel, iterations=6)
        blue_mask = cv2.erode(blue_mask, kernel, iterations=1)
        blue_mask = cv2.dilate(blue_mask, kernel, iterations=3)

        if circles is not None:
            circles = np.round(circles[0, :]).astype("int")
            for (x, y, r) in circles:
                if not (center_x - half_side <= x <= center_x + half_side and
                        center_y - half_side1 <= y <= center_y + half_side2):
                    continue

                x = np.clip(x, 0, frame.shape[1] - 1)
                y = np.clip(y, 0, frame.shape[0] - 1)

                mask = np.zeros_like(gray)
                cv2.circle(mask, (x, y), int(1.4 * r), 255, -1)

                red_area = cv2.countNonZero(cv2.bitwise_and(red_mask, mask))
                green_area = cv2.countNonZero(cv2.bitwise_and(green_mask, mask))
                blue_area = cv2.countNonZero(cv2.bitwise_and(blue_mask, mask))

                max_area = max(red_area, green_area, blue_area)
                if max_area == 0:
                    print("检测到无效颜色区域（HSV全为0），跳过...")
                    continue
                    
                if max_area == red_area:
                    color_code = "1"
                    masked = cv2.bitwise_and(hsv, hsv, mask=cv2.bitwise_and(red_mask, mask))
                    avg_hsv = cv2.mean(masked, mask=cv2.bitwise_and(red_mask, mask))[:3]
                    if avg_hsv[0] == 0 and avg_hsv[1] == 0 and avg_hsv[2] == 0:
                        print("检测到无效红色区域（HSV全为0），跳过...")
                        continue
                elif max_area == green_area:
                    color_code = "2"
                    masked = cv2.bitwise_and(hsv, hsv, mask=cv2.bitwise_and(green_mask, mask))
                    avg_hsv = cv2.mean(masked, mask=cv2.bitwise_and(green_mask, mask))[:3]
                    if avg_hsv[0] == 0 and avg_hsv[1] == 0 and avg_hsv[2] == 0:
                        print("检测到无效绿色区域（HSV全为0），跳过...")
                        continue
                else:
                    color_code = "3"
                    masked = cv2.bitwise_and(hsv, hsv, mask=cv2.bitwise_and(blue_mask, mask))
                    avg_hsv = cv2.mean(masked, mask=cv2.bitwise_and(blue_mask, mask))[:3]
                    if avg_hsv[0] == 0 and avg_hsv[1] == 0 and avg_hsv[2] == 0:
                        print("检测到无效蓝色区域（HSV全为0），跳过...")
                        continue

                print(f"检测到颜色 {color_code}，HSV值: H={avg_hsv[0]:.1f}, S={avg_hsv[1]:.1f}, V={avg_hsv[2]:.1f}")
                formatted_data = f"{x:04}{y:04}{color_code}"
                send_data(formatted_data)
                print(f"稳定坐标发送: {formatted_data}")
                cap2.release()
                return

        if time.time() - start_time > 5.0:
            send_data("000000004")
            print("检测超时，发送默认信号")
            break

        time.sleep(0.05)
    cap2.release()


def run_sehuanyuanxin2_1():  #初赛第二圈最后放物块的时候，色环第一次定标的程序（码垛普通圆形物块）
    # 红色双阈值范围
    lower_red1 = np.array([0, 50, 50])
    upper_red1 = np.array([10, 255, 255])
    lower_red2 = np.array([160, 50, 50])
    upper_red2 = np.array([180, 255, 255])
    lower_green = np.array([30, 40, 40])
    upper_green = np.array([90, 255, 255])
    lower_blue = np.array([90, 50, 90])
    upper_blue = np.array([140, 255, 255])
    kernel = np.ones((3, 3), np.uint8)

    cap2 = cv2.VideoCapture("/dev/video_shang0")
    if not cap2.isOpened():
        print("无法读取摄像头帧")
        return

    cap2.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
    cap2.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

    start_time = time.time()
    while True:
        ret, frame = cap2.read()
        if not ret:
            print("无法读取摄像头帧")
            break

        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        red_mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
        red_mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
        red_mask = cv2.bitwise_or(red_mask1, red_mask2)
        green_mask = cv2.inRange(hsv, lower_green, upper_green)
        blue_mask = cv2.inRange(hsv, lower_blue, upper_blue)

        red_mask = cv2.erode(red_mask, kernel, iterations=2)
        red_mask = cv2.dilate(red_mask, kernel, iterations=4)
        green_mask = cv2.erode(green_mask, kernel, iterations=2)
        green_mask = cv2.dilate(green_mask, kernel, iterations=6)
        blue_mask = cv2.erode(blue_mask, kernel, iterations=1)
        blue_mask = cv2.dilate(blue_mask, kernel, iterations=3)

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        filtered_img = cv2.GaussianBlur(gray, (3, 3), 0)
        circles = cv2.HoughCircles(filtered_img,
                                cv2.HOUGH_GRADIENT, dp=1, minDist=30,
                                param1=50, param2=30,
                                minRadius=110, maxRadius=115)

        if circles is not None:
            circles = np.round(circles[0, :]).astype("int")
            for (x, y, r) in circles:
                x = np.clip(x, 0, frame.shape[1] - 1)
                y = np.clip(y, 0, frame.shape[0] - 1)

                mask = np.zeros_like(gray)
                cv2.circle(mask, (x, y), int(1.4 * r), 255, -1)

                red_area = cv2.countNonZero(cv2.bitwise_and(red_mask, mask))
                green_area = cv2.countNonZero(cv2.bitwise_and(green_mask, mask))
                blue_area = cv2.countNonZero(cv2.bitwise_and(blue_mask, mask))

                max_area = max(red_area, green_area, blue_area)
                if max_area == 0:
                    print("检测到无效颜色区域（HSV全为0），跳过...")
                    continue

                if max_area == red_area:
                    color = "1"
                    masked = cv2.bitwise_and(hsv, hsv, mask=cv2.bitwise_and(red_mask, mask))
                    avg_hsv = cv2.mean(masked, mask=cv2.bitwise_and(red_mask, mask))[:3]
                    if avg_hsv[0] == 0 and avg_hsv[1] == 0 and avg_hsv[2] == 0:
                        print("检测到无效红色区域（HSV全为0），跳过...")
                        continue
                elif max_area == green_area:
                    color = "2"
                    masked = cv2.bitwise_and(hsv, hsv, mask=cv2.bitwise_and(green_mask, mask))
                    avg_hsv = cv2.mean(masked, mask=cv2.bitwise_and(green_mask, mask))[:3]
                    if avg_hsv[0] == 0 and avg_hsv[1] == 0 and avg_hsv[2] == 0:
                        print("检测到无效绿色区域（HSV全为0），跳过...")
                        continue
                else:
                    color = "3"
                    masked = cv2.bitwise_and(hsv, hsv, mask=cv2.bitwise_and(blue_mask, mask))
                    avg_hsv = cv2.mean(masked, mask=cv2.bitwise_and(blue_mask, mask))[:3]
                    if avg_hsv[0] == 0 and avg_hsv[1] == 0 and avg_hsv[2] == 0:
                        print("检测到无效蓝色区域（HSV全为0），跳过...")
                        continue

                print(f"检测到颜色 {color}，HSV值: H={avg_hsv[0]:.1f}, S={avg_hsv[1]:.1f}, V={avg_hsv[2]:.1f}")
                formatted_data = f"{x:04}{y:04}{color[0]}"
                send_data(formatted_data)
                print(f"检测到颜色，发送数据：{formatted_data}")
                cap2.release()
                return

        if time.time() - start_time > 5.0:
            send_data("000000004")
            print("未检测到颜色，发送超时信号")
            break

        time.sleep(0.05)
    cap2.release()


def run_sehuanyuanxin2_centered1():  #初赛第二圈最后放物块的时候，色环第二次定标的程序（码垛普通圆形物块）
    # 红色双阈值范围
    lower_red1 = np.array([0, 50, 50])
    upper_red1 = np.array([10, 255, 255])
    lower_red2 = np.array([160, 50, 50])
    upper_red2 = np.array([180, 255, 255])
    lower_green = np.array([30, 40, 40])
    upper_green = np.array([90, 255, 255])
    lower_blue = np.array([90, 50, 90])
    upper_blue = np.array([140, 255, 255])
    kernel = np.ones((3, 3), np.uint8)

    center_x, center_y = 960, 540
    square_side = 600
    square_side1 = 400
    square_side2 = 800
    half_side = square_side // 2
    half_side1 = square_side1 // 2
    half_side2 = square_side2 // 2

    cap2 = cv2.VideoCapture("/dev/video_shang0")
    if not cap2.isOpened():
        print("无法读取摄像头帧")
        return

    cap2.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
    cap2.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

    start_time = time.time()
    while True:
        ret, frame = cap2.read()
        if not ret:
            print("无法读取摄像头帧")
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        filtered_img = cv2.GaussianBlur(gray, (3, 3), 0)
        circles = cv2.HoughCircles(filtered_img,
                                cv2.HOUGH_GRADIENT, dp=1, minDist=30,
                                param1=50, param2=30,
                                minRadius=110, maxRadius=115)

        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        red_mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
        red_mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
        red_mask = cv2.bitwise_or(red_mask1, red_mask2)
        green_mask = cv2.inRange(hsv, lower_green, upper_green)
        blue_mask = cv2.inRange(hsv, lower_blue, upper_blue)

        red_mask = cv2.erode(red_mask, kernel, iterations=1)
        red_mask = cv2.dilate(red_mask, kernel, iterations=2)
        green_mask = cv2.erode(green_mask, kernel, iterations=2)
        green_mask = cv2.dilate(green_mask, kernel, iterations=6)
        blue_mask = cv2.erode(blue_mask, kernel, iterations=1)
        blue_mask = cv2.dilate(blue_mask, kernel, iterations=3)

        if circles is not None:
            circles = np.round(circles[0, :]).astype("int")
            for (x, y, r) in circles:
                if not (center_x - half_side <= x <= center_x + half_side and
                        center_y - half_side1 <= y <= center_y + half_side2):
                    continue

                x = np.clip(x, 0, frame.shape[1] - 1)
                y = np.clip(y, 0, frame.shape[0] - 1)

                mask = np.zeros_like(gray)
                cv2.circle(mask, (x, y), int(1.4 * r), 255, -1)

                red_area = cv2.countNonZero(cv2.bitwise_and(red_mask, mask))
                green_area = cv2.countNonZero(cv2.bitwise_and(green_mask, mask))
                blue_area = cv2.countNonZero(cv2.bitwise_and(blue_mask, mask))

                max_area = max(red_area, green_area, blue_area)
                if max_area == 0:
                    print("检测到无效颜色区域（HSV全为0），跳过...")
                    continue
                    
                if max_area == red_area:
                    color_code = "1"
                    masked = cv2.bitwise_and(hsv, hsv, mask=cv2.bitwise_and(red_mask, mask))
                    avg_hsv = cv2.mean(masked, mask=cv2.bitwise_and(red_mask, mask))[:3]
                    if avg_hsv[0] == 0 and avg_hsv[1] == 0 and avg_hsv[2] == 0:
                        print("检测到无效红色区域（HSV全为0），跳过...")
                        continue
                elif max_area == green_area:
                    color_code = "2"
                    masked = cv2.bitwise_and(hsv, hsv, mask=cv2.bitwise_and(green_mask, mask))
                    avg_hsv = cv2.mean(masked, mask=cv2.bitwise_and(green_mask, mask))[:3]
                    if avg_hsv[0] == 0 and avg_hsv[1] == 0 and avg_hsv[2] == 0:
                        print("检测到无效绿色区域（HSV全为0），跳过...")
                        continue
                else:
                    color_code = "3"
                    masked = cv2.bitwise_and(hsv, hsv, mask=cv2.bitwise_and(blue_mask, mask))
                    avg_hsv = cv2.mean(masked, mask=cv2.bitwise_and(blue_mask, mask))[:3]
                    if avg_hsv[0] == 0 and avg_hsv[1] == 0 and avg_hsv[2] == 0:
                        print("检测到无效蓝色区域（HSV全为0），跳过...")
                        continue

                print(f"检测到颜色 {color_code}，HSV值: H={avg_hsv[0]:.1f}, S={avg_hsv[1]:.1f}, V={avg_hsv[2]:.1f}")
                formatted_data = f"{x:04}{y:04}{color_code}"
                send_data(formatted_data)
                print(f"稳定坐标发送: {formatted_data}")
                cap2.release()
                return

        if time.time() - start_time > 5.0:
            send_data("000000004")
            print("检测超时，发送默认信号")
            break

        time.sleep(0.05)

    cap2.release()

def run_sehuanyuanxin_ordered():   ##三个物块按顺序输出颜色（普通圆形物块）
    # 双红色阈值定义（整合ceshi0316.py和原程序）
    lower_red1 = np.array([0, 50, 50])    # 红色阈值下界1
    upper_red1 = np.array([10, 255, 255]) # 红色阈值上界1
    lower_red2 = np.array([160, 50, 50])  # 红色阈值下界2（新增双阈值）
    upper_red2 = np.array([180, 255, 255])# 红色阈值上界2
    lower_green = np.array([30, 40, 40])  # 绿色阈值
    upper_green = np.array([90, 255, 255])
    lower_blue = np.array([80, 50, 50])   # 蓝色阈值
    upper_blue = np.array([140, 255, 255])
    kernel = np.ones((3, 3), np.uint8)

    # 配置参数
    ROI = (20, 190, 600, 200)  # 识别区域 (x,y,w,h)
    MIN_RADIUS = 30             # 最小半径
    MAX_RADIUS = 60             # 最大半径

    # 初始化摄像头
    cap = cv2.VideoCapture("/dev/video_shang0")
    if not cap.isOpened():
        print("无法读取摄像头帧")
        return
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    # 存储检测结果
    detected_colors = []  # 格式: [(x, y, color_code), ...]
    output_sequence = ""
    middle_x = "000"
    middle_y = "000"

    while True:
        ret, frame = cap.read()
        if not ret:
            print("无法读取摄像头帧")
            break

        # ROI预处理
        x_roi, y_roi, w_roi, h_roi = ROI
        roi_frame = frame[y_roi:y_roi+h_roi, x_roi:x_roi+w_roi]
        hsv = cv2.cvtColor(roi_frame, cv2.COLOR_BGR2HSV)
        
        # 创建双红色掩膜（关键修改）
        red_mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
        red_mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
        red_mask = cv2.bitwise_or(red_mask1, red_mask2)  # 合并红色区域
        green_mask = cv2.inRange(hsv, lower_green, upper_green)
        blue_mask = cv2.inRange(hsv, lower_blue, upper_blue)

        # 形态学操作（保持ceshi0316.py参数）
        red_mask = cv2.erode(red_mask, kernel, iterations=1)
        red_mask = cv2.dilate(red_mask, kernel, iterations=2)
        green_mask = cv2.erode(green_mask, kernel, iterations=2)
        green_mask = cv2.dilate(green_mask, kernel, iterations=6)
        blue_mask = cv2.erode(blue_mask, kernel, iterations=1)
        blue_mask = cv2.dilate(blue_mask, kernel, iterations=3)

        # 霍夫圆检测
        gray = cv2.cvtColor(roi_frame, cv2.COLOR_BGR2GRAY)
        filtered_img = cv2.GaussianBlur(gray, (3, 3), 0)
        circles = cv2.HoughCircles(
            filtered_img,
            cv2.HOUGH_GRADIENT,
            dp=1,
            minDist=30,
            param1=50,
            param2=30,
            minRadius=MIN_RADIUS,
            maxRadius=MAX_RADIUS
        )

        # 清空临时检测结果
        temp_detected = []
        if circles is not None:
            circles = np.uint16(np.around(circles))
            for i in circles[0, :]:
                # 转换为全局坐标
                global_x = x_roi + i[0]
                global_y = y_roi + i[1]
                radius = i[2]

                # 创建圆形掩膜
                mask = np.zeros_like(gray)
                cv2.circle(mask, (i[0], i[1]), radius, 255, -1)

                # 计算颜色区域面积
                red_area = cv2.countNonZero(cv2.bitwise_and(red_mask, mask))
                green_area = cv2.countNonZero(cv2.bitwise_and(green_mask, mask))
                blue_area = cv2.countNonZero(cv2.bitwise_and(blue_mask, mask))

                # 确定主颜色
                max_area = max(red_area, green_area, blue_area)
                if max_area == red_area:
                    color_code = "1"
                elif max_area == green_area:
                    color_code = "2"
                else:
                    color_code = "3"

                # 存储坐标和颜色（新增坐标记录）
                temp_detected.append( (global_x, global_y, color_code) )

        # 按X坐标排序并去重
        if temp_detected:
            # 按X坐标升序排序
            sorted_detected = sorted(temp_detected, key=lambda x: x[0],reverse=True)
            
            # 去重逻辑：保留每个颜色的第一个检测结果
            seen_colors = set()
            unique_detected = []
            for item in sorted_detected:
                if item[2] not in seen_colors:
                    seen_colors.add(item[2])
                    unique_detected.append(item)
            
            # 更新最终结果（最多3个）
            detected_colors = unique_detected[:3]
            
            # 提取中间颜色坐标（当有至少3个时）
            if len(detected_colors) >= 3:
                middle_x = f"{detected_colors[1][0]:03d}"  # 第二位X坐标
                middle_y = f"{detected_colors[1][1]:03d}"  # 第二位Y坐标
            else:
                middle_x = "000"
                middle_y = "000"

            # 构建输出数据
            color_order = "".join([item[2] for item in detected_colors[:3]]).ljust(3, "0")
            formatted_data = f"{color_order}{middle_x}{middle_y}"

            # 检查有效性条件
            color_valid = all(c in "123" for c in color_order[:3])  # 前三位无0
            coord_valid = not (middle_x == "000" and middle_y == "000")  # 坐标不全为0

            if color_valid and coord_valid:
                send_data(formatted_data)
                print(f"有效数据已发送: {formatted_data}")
                break  # 退出循环

        # 实时显示（调试用）
        debug_frame = frame.copy()
        cv2.rectangle(debug_frame, (x_roi, y_roi), (x_roi+w_roi, y_roi+h_roi), (0,255,0), 2)
        if circles is not None:
            for i in circles[0, :]:
                center = (x_roi + i[0], y_roi + i[1])
                cv2.circle(debug_frame, center, i[2], (0,255,0), 2)
        cv2.imshow("Detection", debug_frame)
        if cv2.waitKey(1) == ord('q'):
            break

    # 释放资源
    cap.release()
    cv2.destroyAllWindows()

def run_shape_detection():  ##决赛物块转盘第一次定心程序(什么形状的物块都能识别)
    # 颜色阈值定义
    lower_red1 = np.array([0, 50, 50])
    upper_red1 = np.array([10, 255, 255])
    lower_red2 = np.array([160, 50, 50])
    upper_red2 = np.array([180, 255, 255])
    lower_green = np.array([35, 40, 40])
    upper_green = np.array([85, 255, 255])
    lower_blue = np.array([90, 50, 50])
    upper_blue = np.array([130, 255, 255])
    
    # 配置参数
    roi = (220, 200, 200, 200)  # 识别区域
    stability_threshold = 5     # 坐标波动阈值（像素）
    stable_count_threshold = 30 # 连续稳定次数
    last_center = None
    stable_count = 0

    # 初始化摄像头
    cap = cv2.VideoCapture("/dev/video_shang0")
    if not cap.isOpened():
        print("无法打开摄像头")
        return
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    while True:
        ret, frame = cap.read()
        if not ret:
            print("无法读取帧")
            break

        # ROI处理
        roi_img = frame[roi[1]:roi[1]+roi[3], roi[0]:roi[0]+roi[2]]
        
        # 转换为灰度图并进行二值化
        gray = cv2.cvtColor(roi_img, cv2.COLOR_BGR2GRAY)
        ret, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)
        
        # 查找轮廓
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        current_center = None
        color_code = "0"
        
        for cnt in contours:
            # 计算轮廓矩
            mm = cv2.moments(cnt)
            if mm['m00'] == 0:
                continue
            
            # 计算质心
            cx = int(mm['m10']/mm['m00']) + roi[0]
            cy = int(mm['m01']/mm['m00']) + roi[1]
            current_center = (cx, cy)
            
            # 颜色检测
            hsv = cv2.cvtColor(roi_img, cv2.COLOR_BGR2HSV)
            mask_red = cv2.bitwise_or(
                cv2.inRange(hsv, lower_red1, upper_red1),
                cv2.inRange(hsv, lower_red2, upper_red2)
            )
            mask_green = cv2.inRange(hsv, lower_green, upper_green)
            mask_blue = cv2.inRange(hsv, lower_blue, upper_blue)
            
            # 计算颜色区域面积
            red_area = cv2.countNonZero(mask_red)
            green_area = cv2.countNonZero(mask_green)
            blue_area = cv2.countNonZero(mask_blue)
            
            # 确定主颜色
            if max(red_area, green_area, blue_area) == red_area:
                color_code = "1"
            elif max(red_area, green_area, blue_area) == green_area:
                color_code = "2"
            else:
                color_code = "3"
            break  # 只处理第一个检测到的轮廓

        # 稳定性检测
        if current_center:
            if last_center:
                distance = np.sqrt((current_center[0]-last_center[0])**2 + 
                                 (current_center[1]-last_center[1])**2)
                if distance < stability_threshold:
                    stable_count += 1
                else:
                    stable_count = 0
            else:
                stable_count = 1
            
            last_center = current_center
            
            if stable_count >= stable_count_threshold:
                # 格式化数据并发送
                x = f"{current_center[0]:04}"
                y = f"{current_center[1]:04}"
                formatted_data = f"{x}{y}{color_code}"
                send_data(formatted_data)
                print(f"发送形状数据: {formatted_data}")
                break

    cap.release()

def wukuaiyuanxin_logic1_renhexingzhuang():
    # 颜色范围设定（保留原有逻辑）
    lower_red1 = np.array([0, 50, 50])
    upper_red1 = np.array([10, 255, 255])
    lower_red2 = np.array([160, 50, 50])
    upper_red2 = np.array([180, 255, 255])
    lower_green = np.array([30, 40, 40])
    upper_green = np.array([90, 255, 255])
    lower_blue = np.array([80, 50, 50])
    upper_blue = np.array([140, 255, 255])
    kernel = np.ones((3, 3), np.uint8)

    # 启动摄像头
    cap = cv2.VideoCapture("/dev/video_shang0")
    if not cap.isOpened():
        print("无法打开摄像头")
        return

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    count = 0  # 用于跟踪已经识别的颜色数量
    stability_threshold = 10  # 稳定性阈值（像素）
    stable_count = 0  # 连续稳定帧数
    stable_count1 = 50  # 连续稳定帧数
    last_center = None  # 上一帧的质心坐标

    while True:
        ret, frame = cap.read()
        if not ret:
            print("无法读取帧")
            break

        # 提取ROI区域并转换到HSV空间
        roi = (220, 200, 200, 120)  # ROI区域（原有逻辑）
        roi_img = frame[roi[1]:roi[1] + roi[3], roi[0]:roi[0] + roi[2]]
        hsv_img = cv2.cvtColor(roi_img, cv2.COLOR_BGR2HSV)

        # 创建颜色掩膜
        red_mask = cv2.bitwise_or(
                cv2.inRange(hsv_img, lower_red1, upper_red1),
                cv2.inRange(hsv_img, lower_red2, upper_red2)
            )
        green_mask = cv2.inRange(hsv_img, lower_green, upper_green)
        blue_mask = cv2.inRange(hsv_img, lower_blue, upper_blue)

        # 形态学操作（原有逻辑）
        red_mask = cv2.erode(red_mask, kernel, iterations=1)
        red_mask = cv2.dilate(red_mask, kernel, iterations=2)
        green_mask = cv2.erode(green_mask, kernel, iterations=2)
        green_mask = cv2.dilate(green_mask, kernel, iterations=6)
        blue_mask = cv2.erode(blue_mask, kernel, iterations=1)
        blue_mask = cv2.dilate(blue_mask, kernel, iterations=3)

        # 计算颜色区域面积
        red_area = cv2.countNonZero(red_mask)
        green_area = cv2.countNonZero(green_mask)
        blue_area = cv2.countNonZero(blue_mask)

        # 找到面积最大的颜色
        areas = {'1': red_area, '2': green_area, '3': blue_area}
        max_color = max(areas, key=areas.get)  # 选择面积最大的颜色

        if max_color == '1':
            mask = red_mask
        elif max_color == '2':
            mask = green_mask
        else:
            mask = blue_mask

        # 计算最大颜色掩膜的质心
        M = cv2.moments(mask)
        if M["m00"] != 0:
            cx = int(M["m10"] / M["m00"]) + roi[0]
            cy = int(M["m01"] / M["m00"]) + roi[1]

            # 在图像上绘制质心坐标点
            cv2.circle(frame, (cx, cy), 5, (0, 0, 255), -1)
            cv2.putText(frame, f"({cx}, {cy})", (cx + 10, cy + 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

            # 检查质心坐标的稳定性
            if last_center is not None:
                distance = np.sqrt((cx - last_center[0])**2 + (cy - last_center[1])**2)
                if distance < stability_threshold:
                    stable_count += 1
                else:
                    stable_count = 0  # 重置稳定计数
            else:
                stable_count = 1  # 第一次检测到质心

            last_center = (cx, cy)

            # 当连续稳定帧数达到阈值时，发送数据
            if stable_count >= stable_count1:  # 设定连续稳定的帧数
                if count == 0 and max_color == str(A[0]):
                    send_data(f"{cx:04}{cy:04}{str(A[0])}")
                    print(f"匹配到A[0]，发送数据：({cx}, {cy}) 颜色：{str(A[0])}")
                    count += 1
                    time.sleep(3.0)
                elif count == 1 and max_color == str(A[1]):
                    send_data(f"{cx:04}{cy:04}{str(A[1])}")
                    print(f"匹配到A[1]，发送数据：({cx}, {cy}) 颜色：{str(A[1])}")
                    count += 1
                    time.sleep(3.0)
                elif count == 2 and max_color == str(A[2]):
                    send_data(f"{cx:04}{cy:04}{str(A[2])}")
                    print(f"匹配到A[2]，发送数据：({cx}, {cy}) 颜色：{str(A[2])}")
                    time.sleep(3.0)
                    break
        cv2.rectangle(frame, (220, 200), (420, 320), (0, 255, 0), 2)  # 绘制ROI区域
        cv2.imshow("Logic1 Detection", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

def wukuaiyuanxin_logic2_renhexingzhuang():
    # 颜色范围设定（保留原有逻辑）
    lower_red1 = np.array([0, 50, 50])
    upper_red1 = np.array([10, 255, 255])
    lower_red2 = np.array([160, 50, 50])
    upper_red2 = np.array([180, 255, 255])
    lower_green = np.array([30, 40, 40])
    upper_green = np.array([90, 255, 255])
    lower_blue = np.array([80, 50, 50])
    upper_blue = np.array([140, 255, 255])
    kernel = np.ones((3, 3), np.uint8)

    # 启动摄像头
    cap = cv2.VideoCapture("/dev/video_shang0")
    if not cap.isOpened():
        print("无法打开摄像头")
        return

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    count = 0  # 用于跟踪已经识别的颜色数量
    stability_threshold = 10  # 稳定性阈值（像素）
    stable_count = 0  # 连续稳定帧数
    stable_count1 = 50
    last_center = None  # 上一帧的质心坐标

    while True:
        ret, frame = cap.read()
        if not ret:
            print("无法读取帧")
            break

        # 提取ROI区域并转换到HSV空间
        roi = (220, 200, 200, 120)  # ROI区域（原有逻辑）
        roi_img = frame[roi[1]:roi[1] + roi[3], roi[0]:roi[0] + roi[2]]
        hsv_img = cv2.cvtColor(roi_img, cv2.COLOR_BGR2HSV)

        # 创建颜色掩膜
        red_mask = cv2.bitwise_or(
                cv2.inRange(hsv_img, lower_red1, upper_red1),
                cv2.inRange(hsv_img, lower_red2, upper_red2)
            )
        green_mask = cv2.inRange(hsv_img, lower_green, upper_green)
        blue_mask = cv2.inRange(hsv_img, lower_blue, upper_blue)

        # 形态学操作（原有逻辑）
        red_mask = cv2.erode(red_mask, kernel, iterations=1)
        red_mask = cv2.dilate(red_mask, kernel, iterations=2)
        green_mask = cv2.erode(green_mask, kernel, iterations=2)
        green_mask = cv2.dilate(green_mask, kernel, iterations=6)
        blue_mask = cv2.erode(blue_mask, kernel, iterations=1)
        blue_mask = cv2.dilate(blue_mask, kernel, iterations=3)

        # 计算颜色区域面积
        red_area = cv2.countNonZero(red_mask)
        green_area = cv2.countNonZero(green_mask)
        blue_area = cv2.countNonZero(blue_mask)

        # 找到面积最大的颜色
        areas = {'1': red_area, '2': green_area, '3': blue_area}
        max_color = max(areas, key=areas.get)  # 选择面积最大的颜色

        if max_color == '1':
            mask = red_mask
        elif max_color == '2':
            mask = green_mask
        else:
            mask = blue_mask

        # 计算最大颜色掩膜的质心
        M = cv2.moments(mask)
        if M["m00"] != 0:
            cx = int(M["m10"] / M["m00"]) + roi[0]
            cy = int(M["m01"] / M["m00"]) + roi[1]

            # 在图像上绘制质心坐标点
            cv2.circle(frame, (cx, cy), 5, (0, 0, 255), -1)
            cv2.putText(frame, f"({cx}, {cy})", (cx + 10, cy + 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

            # 检查质心坐标的稳定性
            if last_center is not None:
                distance = np.sqrt((cx - last_center[0])**2 + (cy - last_center[1])**2)
                if distance < stability_threshold:
                    stable_count += 1
                else:
                    stable_count = 0  # 重置稳定计数
            else:
                stable_count = 1  # 第一次检测到质心

            last_center = (cx, cy)

            # 当连续稳定帧数达到阈值时，发送数据
            if stable_count >= stable_count1:  # 设定连续稳定的帧数
                if count == 0 and max_color == str(A[4]):
                    send_data(f"{cx:04}{cy:04}{str(A[4])}")
                    print(f"匹配到A[4]，发送数据：({cx}, {cy}) 颜色：{str(A[4])}")
                    count += 1
                    time.sleep(3.0)
                elif count == 1 and max_color == str(A[5]):
                    send_data(f"{cx:04}{cy:04}{str(A[5])}")
                    print(f"匹配到A[5]，发送数据：({cx}, {cy}) 颜色：{str(A[5])}")
                    count += 1
                    time.sleep(3.0)
                elif count == 2 and max_color == str(A[6]):
                    send_data(f"{cx:04}{cy:04}{str(A[6])}")

                    print(f"匹配到A[6]，发送数据：({cx}, {cy}) 颜色：{str(A[6])}")
                    time.sleep(3.0)
                    break
        cv2.rectangle(frame, (220, 200), (420, 320), (0, 255, 0), 2)  # 绘制ROI区域
        cv2.imshow("Logic2 Detection", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    
def run_shape_detection1():  ##决赛物块转盘第二圈第一次定心程序(什么形状的物块都能识别)
    # 颜色阈值定义
    lower_red1 = np.array([0, 50, 50])
    upper_red1 = np.array([10, 255, 255])
    lower_red2 = np.array([160, 50, 50])
    upper_red2 = np.array([180, 255, 255])
    lower_green = np.array([35, 40, 40])
    upper_green = np.array([85, 255, 255])
    lower_blue = np.array([90, 50, 50])
    upper_blue = np.array([130, 255, 255])
    
    # 配置参数
    roi = (120,200,400,250)   # 识别区域
    stability_threshold = 5     # 坐标波动阈值（像素）
    stable_count_threshold = 30 # 连续稳定次数
    last_center = None
    stable_count = 0

    # 初始化摄像头
    cap = cv2.VideoCapture("/dev/video_shang0")
    if not cap.isOpened():
        print("无法打开摄像头")
        return
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    while True:
        ret, frame = cap.read()
        if not ret:
            print("无法读取帧")
            break

        # ROI处理
        roi_img = frame[roi[1]:roi[1]+roi[3], roi[0]:roi[0]+roi[2]]
        
        # 转换为灰度图并进行二值化
        gray = cv2.cvtColor(roi_img, cv2.COLOR_BGR2GRAY)
        ret, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)
        
        # 查找轮廓
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        current_center = None
        color_code = "0"
        
        for cnt in contours:
            # 计算轮廓矩
            mm = cv2.moments(cnt)
            if mm['m00'] == 0:
                continue
            
            # 计算质心
            cx = int(mm['m10']/mm['m00']) + roi[0]
            cy = int(mm['m01']/mm['m00']) + roi[1]
            current_center = (cx, cy)
            
            # 颜色检测
            hsv = cv2.cvtColor(roi_img, cv2.COLOR_BGR2HSV)
            mask_red = cv2.bitwise_or(
                cv2.inRange(hsv, lower_red1, upper_red1),
                cv2.inRange(hsv, lower_red2, upper_red2)
            )
            mask_green = cv2.inRange(hsv, lower_green, upper_green)
            mask_blue = cv2.inRange(hsv, lower_blue, upper_blue)
            
            # 计算颜色区域面积
            red_area = cv2.countNonZero(mask_red)
            green_area = cv2.countNonZero(mask_green)
            blue_area = cv2.countNonZero(mask_blue)
            
            # 确定主颜色
            if max(red_area, green_area, blue_area) == red_area:
                color_code = "1"
            elif max(red_area, green_area, blue_area) == green_area:
                color_code = "2"
            else:
                color_code = "3"
            break  # 只处理第一个检测到的轮廓

        # 稳定性检测
        if current_center:
            if last_center:
                distance = np.sqrt((current_center[0]-last_center[0])**2 + 
                                 (current_center[1]-last_center[1])**2)
                if distance < stability_threshold:
                    stable_count += 1
                else:
                    stable_count = 0
            else:
                stable_count = 1
            
            last_center = current_center
            
            if stable_count >= stable_count_threshold:
                # 格式化数据并发送
                x = f"{current_center[0]:04}"
                y = f"{current_center[1]:04}"
                formatted_data = f"{x}{y}{color_code}"
                send_data(formatted_data)
                print(f"发送形状数据: {formatted_data}")
                break

    cap.release()

def run_shape_ordered():   ##三个物块按顺序输出颜色（普通圆形物块）
    # 颜色阈值定义（增强颜色区分度）
    lower_red1 = np.array([0, 120, 70])    
    upper_red1 = np.array([10, 255, 255])
    lower_red2 = np.array([170, 120, 70])  
    upper_red2 = np.array([180, 255, 255])
    lower_green = np.array([35, 80, 50])  
    upper_green = np.array([85, 255, 255])
    lower_blue = np.array([90, 120, 70])   
    upper_blue = np.array([130, 255, 255])
    kernel = np.ones((5, 5), np.uint8)

    # 配置参数
    ROI = (20, 190, 600, 200)  # 识别区域 (x,y,w,h)
    MIN_AREA = 1000             # 最小有效区域面积（过滤噪声）
    STABILITY_THRESHOLD = 5     # 坐标波动阈值（像素）
    last_valid_data = None

    # 初始化摄像头
    cap = cv2.VideoCapture("/dev/video_shang0")
    if not cap.isOpened():
        print("无法读取摄像头帧")
        return
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    # 形态学操作增强颜色分离
    def process_mask(mask, operation="open", iterations=2):
        if operation == "open":
            return cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=iterations)
        else:
            return cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=iterations)

    # 颜色质心检测（保证唯一性）
    def detect_unique_color(hsv_frame):
        color_centroids = {}
        
        # 红色检测（双阈值）
        red_mask = cv2.bitwise_or(
            cv2.inRange(hsv_frame, lower_red1, upper_red1),
            cv2.inRange(hsv_frame, lower_red2, upper_red2)
        )
        red_mask = process_mask(red_mask, "open", 2)
        red_contours, _ = cv2.findContours(red_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if red_contours:
            largest_red = max(red_contours, key=cv2.contourArea)
            if cv2.contourArea(largest_red) > MIN_AREA:
                M = cv2.moments(largest_red)
                color_centroids["1"] = (int(M["m10"]/M["m00"]), int(M["m01"]/M["m00"]))

        # 绿色检测
        green_mask = cv2.inRange(hsv_frame, lower_green, upper_green)
        green_mask = process_mask(green_mask, "close", 3)
        green_contours, _ = cv2.findContours(green_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if green_contours:
            largest_green = max(green_contours, key=cv2.contourArea)
            if cv2.contourArea(largest_green) > MIN_AREA:
                M = cv2.moments(largest_green)
                color_centroids["2"] = (int(M["m10"]/M["m00"]), int(M["m01"]/M["m00"]))

        # 蓝色检测
        blue_mask = cv2.inRange(hsv_frame, lower_blue, upper_blue)
        blue_mask = process_mask(blue_mask, "open", 1)
        blue_contours, _ = cv2.findContours(blue_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if blue_contours:
            largest_blue = max(blue_contours, key=cv2.contourArea)
            if cv2.contourArea(largest_blue) > MIN_AREA:
                M = cv2.moments(largest_blue)
                color_centroids["3"] = (int(M["m10"]/M["m00"]), int(M["m01"]/M["m00"]))
        
        return color_centroids

    # 主循环
    while True:
        ret, frame = cap.read()
        if not ret: break

        # ROI处理
        x_roi, y_roi, w_roi, h_roi = ROI
        roi_frame = frame[y_roi:y_roi+h_roi, x_roi:x_roi+w_roi]
        hsv_roi = cv2.cvtColor(roi_frame, cv2.COLOR_BGR2HSV)

        # 检测颜色质心
        color_data = detect_unique_color(hsv_roi)
        if len(color_data) != 3: 
            continue  # 必须检测到三种不同颜色

        # 转换为全局坐标
        global_coords = []
        for color, (rx, ry) in color_data.items():
            gx = x_roi + int(rx)
            gy = y_roi + int(ry)
            global_coords.append( (gx, gy, color) )

        # 按X坐标排序
        sorted_colors = sorted(global_coords, key=lambda x: x[0])
        color_order = "".join([c[2] for c in sorted_colors])
        mid_x, mid_y = sorted_colors[1][0], sorted_colors[1][1]  # 中间颜色坐标

        # 稳定性验证
        current_data = f"{color_order}{mid_x:04}{mid_y:04}"
        if last_valid_data:
            if abs(int(current_data[3:7]) - int(last_valid_data[3:7])) > STABILITY_THRESHOLD or \
               abs(int(current_data[7:11]) - int(last_valid_data[7:11])) > STABILITY_THRESHOLD:
                continue  # 坐标波动过大则忽略
        
        last_valid_data = current_data
        print(f"稳定数据发送: {current_data}")
        break

        cv2.imshow("Detection", frame)
        if cv2.waitKey(1) == ord('q'):
            break

    # 释放资源
    cap.release()
    cv2.destroyAllWindows()
  
def test_triangle_detection0():
    # 设置HSV范围（红、绿、蓝）
    lower_red1 = np.array([0, 50, 50])
    upper_red1 = np.array([10, 255, 255])
    lower_red2 = np.array([160, 50, 50])
    upper_red2 = np.array([180, 255, 255])
    lower_green = np.array([30, 40, 40])
    upper_green = np.array([90, 255, 255])
    lower_blue = np.array([90, 50, 50])
    upper_blue = np.array([130, 255, 255])

    kernel = np.ones((5, 5), np.uint8)  # 用于形态学操作

    # 稳定性检测参数
    stability_threshold = 5    # 坐标波动阈值（像素）
    stable_frames_threshold = 5  # 需要连续稳定的帧数
    last_cx = None
    last_cy = None
    stable_count = 0

    # 摄像头设置
    cap = cv2.VideoCapture("/dev/video_shang0")
    if not cap.isOpened():
        print("无法打开摄像头")
        return
    
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    while True:
        ret, frame = cap.read()
        if not ret:
            print("无法读取帧")
            break

        # 提取ROI区域并转换到HSV空间
        roi = (120,200,400,250)   # 设置ROI区域
        roi_img = frame[roi[1]:roi[1] + roi[3], roi[0]:roi[0] + roi[2]]
        hsv_img = cv2.cvtColor(roi_img, cv2.COLOR_BGR2HSV)
        
        # 创建颜色掩膜
        red_mask1 = cv2.inRange(hsv_img, lower_red1, upper_red1)
        red_mask2 = cv2.inRange(hsv_img, lower_red2, upper_red2)
        red_mask = cv2.bitwise_or(red_mask1, red_mask2)
        green_mask = cv2.inRange(hsv_img, lower_green, upper_green)
        blue_mask = cv2.inRange(hsv_img, lower_blue, upper_blue)

        # 增强形态学操作以消除噪声
        red_mask = cv2.erode(red_mask, kernel, iterations=2)
        red_mask = cv2.dilate(red_mask, kernel, iterations=4)
        green_mask = cv2.erode(green_mask, kernel, iterations=3)
        green_mask = cv2.dilate(green_mask, kernel, iterations=5)
        blue_mask = cv2.erode(blue_mask, kernel, iterations=2)
        blue_mask = cv2.dilate(blue_mask, kernel, iterations=5)

        # 计算每个颜色区域的面积
        red_area = cv2.countNonZero(red_mask)
        green_area = cv2.countNonZero(green_mask)
        blue_area = cv2.countNonZero(blue_mask)

        # 找到面积最大的颜色
        areas = {'1': red_area, '2': green_area, '3': blue_area}
        max_color = max(areas, key=areas.get)

        # 根据最大的颜色掩膜计算质心坐标
        current_cx = current_cy = None
        if max_color == '1':
            mask = red_mask
        elif max_color == '2':
            mask = green_mask
        else:
            mask = blue_mask

        # 计算质心
        M = cv2.moments(mask)
        if M["m00"] != 0:
            current_cx = int(M["m10"] / M["m00"]) + roi[0]
            current_cy = int(M["m01"] / M["m00"]) + roi[1]

            # 稳定性检测逻辑
            if last_cx is not None and last_cy is not None:
                distance = np.sqrt((current_cx - last_cx)**2 + (current_cy - last_cy)**2)
                if distance < stability_threshold:
                    stable_count += 1
                else:
                    stable_count = 0  # 坐标波动过大，重置计数
            else:
                stable_count = 1  # 首次检测

            last_cx, last_cy = current_cx, current_cy

            # 当稳定帧数达到阈值时发送数据
            if stable_count >= stable_frames_threshold:
                x = f"{current_cx:04}"
                y = f"{current_cy:04}"
                formatted_data = f"{x}{y}{max_color}"
                #send_data(formatted_data)
                print(f"稳定坐标发送: {formatted_data}")
                break  # 发送后退出循环

        # 调试显示（可选）
        #debug_frame = frame.copy()
        #cv2.rectangle(debug_frame, (roi[0], roi[1]), 
                     #(roi[0]+roi[2], roi[1]+roi[3]), (255,0,0), 2)
        #if current_cx and current_cy:
            #cv2.circle(debug_frame, (current_cx, current_cy), 5, (0,0,255), -1)
        #cv2.imshow("Detection", debug_frame)
        #if cv2.waitKey(1) & 0xFF == ord('q'):
            #break

    cap.release()
    cv2.destroyAllWindows()
def test_triangle_detection1():
    # 设置HSV范围（红、绿、蓝）
    lower_red1 = np.array([0, 50, 50])
    upper_red1 = np.array([10, 255, 255])
    lower_red2 = np.array([160, 50, 50])
    upper_red2 = np.array([180, 255, 255])
    lower_green = np.array([30, 40, 40])
    upper_green = np.array([90, 255, 255])
    lower_blue = np.array([90, 50, 50])
    upper_blue = np.array([130, 255, 255])

    kernel = np.ones((5, 5), np.uint8)  # 用于形态学操作

    # 稳定性检测参数
    stability_threshold = 5    # 坐标波动阈值（像素）
    stable_frames_threshold = 40  # 需要连续稳定的帧数
    last_cx = None
    last_cy = None
    stable_count = 0

    # 摄像头设置
    cap = cv2.VideoCapture("/dev/video_shang0")
    if not cap.isOpened():
        print("无法打开摄像头")
        return
    
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    while True:
        ret, frame = cap.read()
        if not ret:
            print("无法读取帧")
            break

        # 提取ROI区域并转换到HSV空间
        roi = (120,200,400,250)   # 设置ROI区域
        roi_img = frame[roi[1]:roi[1] + roi[3], roi[0]:roi[0] + roi[2]]
        hsv_img = cv2.cvtColor(roi_img, cv2.COLOR_BGR2HSV)
        
        # 创建颜色掩膜
        red_mask1 = cv2.inRange(hsv_img, lower_red1, upper_red1)
        red_mask2 = cv2.inRange(hsv_img, lower_red2, upper_red2)
        red_mask = cv2.bitwise_or(red_mask1, red_mask2)
        green_mask = cv2.inRange(hsv_img, lower_green, upper_green)
        blue_mask = cv2.inRange(hsv_img, lower_blue, upper_blue)

        # 增强形态学操作以消除噪声
        red_mask = cv2.erode(red_mask, kernel, iterations=2)
        red_mask = cv2.dilate(red_mask, kernel, iterations=4)
        green_mask = cv2.erode(green_mask, kernel, iterations=3)
        green_mask = cv2.dilate(green_mask, kernel, iterations=5)
        blue_mask = cv2.erode(blue_mask, kernel, iterations=2)
        blue_mask = cv2.dilate(blue_mask, kernel, iterations=5)

        # 计算每个颜色区域的面积
        red_area = cv2.countNonZero(red_mask)
        green_area = cv2.countNonZero(green_mask)
        blue_area = cv2.countNonZero(blue_mask)

        # 找到面积最大的颜色
        areas = {'1': red_area, '2': green_area, '3': blue_area}
        max_color = max(areas, key=areas.get)

        # 根据最大的颜色掩膜计算质心坐标
        current_cx = current_cy = None
        if max_color == '1':
            mask = red_mask
        elif max_color == '2':
            mask = green_mask
        else:
            mask = blue_mask

        # 计算质心
        M = cv2.moments(mask)
        if M["m00"] != 0:
            current_cx = int(M["m10"] / M["m00"]) + roi[0]
            current_cy = int(M["m01"] / M["m00"]) + roi[1]

            # 稳定性检测逻辑
            if last_cx is not None and last_cy is not None:
                distance = np.sqrt((current_cx - last_cx)**2 + (current_cy - last_cy)**2)
                if distance < stability_threshold:
                    stable_count += 1
                else:
                    stable_count = 0  # 坐标波动过大，重置计数
            else:
                stable_count = 1  # 首次检测

            last_cx, last_cy = current_cx, current_cy

            # 当稳定帧数达到阈值时发送数据
            if stable_count >= stable_frames_threshold:
                x = f"{current_cx:04}"
                y = f"{current_cy:04}"
                formatted_data = f"{x}{y}{max_color}"
                send_data(formatted_data)
                print(f"稳定坐标发送: {formatted_data}")
                break  # 发送后退出循环

        # 调试显示（可选）
        debug_frame = frame.copy()
        cv2.rectangle(debug_frame, (roi[0], roi[1]), 
                     (roi[0]+roi[2], roi[1]+roi[3]), (255,0,0), 2)
        if current_cx and current_cy:
            cv2.circle(debug_frame, (current_cx, current_cy), 5, (0,0,255), -1)
        cv2.imshow("Detection", debug_frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
def run_test_for_5_seconds():
    # 运行 test_triangle_detection 函数 5 秒钟
    test_thread = threading.Thread(target=test_triangle_detection0)
    test_thread.start()
    time.sleep(3.0)
    # 5 秒钟后停止测试并继续执行形状检测
    print("5秒已过，开始执行形状检测...")
    # 你可能需要添加一些逻辑来安全地终止测试线程（如果有必要）
    # 然后调用 run_shape_detection 函数
    test_triangle_detection1()

def run_combined_ordered_detection_v6():
    # 定义颜色范围（红、绿、蓝）
    lower_red1 = np.array([0, 50, 50])
    upper_red1 = np.array([10, 255, 255])
    lower_red2 = np.array([160, 50, 50])
    upper_red2 = np.array([180, 255, 255])
    lower_green = np.array([30, 40, 40])
    upper_green = np.array([90, 255, 255])
    lower_blue = np.array([90, 50, 50])
    upper_blue = np.array([130, 255, 255])
    kernel = np.ones((3, 3), np.uint8)

    # 摄像头初始化
    cap = cv2.VideoCapture("/dev/video_shang0")
    if not cap.isOpened():
        print("无法读取摄像头帧")
        return
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    # 设置ROI区域
    roi = (120, 150, 400, 200)  # x, y, width, height
    min_area = 1000  # 最小区域面积

    max_area = 100000  # 最大区域面积

    # 存储检测到的颜色和质心
    detected_colors = []

    # 设置质心合并阈值（单位：像素）
    merge_threshold = 10  # 如果两个质心之间的距离小于这个值，认为它们是同一个色块

    # 定义识别次数计数器
    detection_counter = 0

    def distance(p1, p2):
        return np.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)

    while True:
        ret, frame = cap.read()
        if not ret:
            print("无法读取摄像头帧")
            break

        # 提取ROI区域
        x_roi, y_roi, w_roi, h_roi = roi
        roi_frame = frame[y_roi:y_roi + h_roi, x_roi:x_roi + w_roi]
        hsv = cv2.cvtColor(roi_frame, cv2.COLOR_BGR2HSV)

        # 创建颜色掩膜
        red_mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
        red_mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
        red_mask = cv2.bitwise_or(red_mask1, red_mask2)  # 合并两个红色阈值

        green_mask = cv2.inRange(hsv, lower_green, upper_green)
        blue_mask = cv2.inRange(hsv, lower_blue, upper_blue)

        # 形态学操作
        red_mask = cv2.erode(red_mask, kernel, iterations=1)
        red_mask = cv2.dilate(red_mask, kernel, iterations=2)
        green_mask = cv2.erode(green_mask, kernel, iterations=2)
        green_mask = cv2.dilate(green_mask, kernel, iterations=6)
        blue_mask = cv2.erode(blue_mask, kernel, iterations=1)
        blue_mask = cv2.dilate(blue_mask, kernel, iterations=3)

        # 轮廓检测
        contours_red, _ = cv2.findContours(red_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        contours_green, _ = cv2.findContours(green_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        contours_blue, _ = cv2.findContours(blue_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # 存储临时检测到的颜色和质心
        temp_detected = []

        def detect_color_centroid(contours, color_code):
            for contour in contours:
                area = cv2.contourArea(contour)
                if area > min_area and area < max_area:  # 过滤掉面积过小或过大的轮廓
                    M = cv2.moments(contour)
                    if M["m00"] != 0:  # 防止除零错误
                        cX = int(M["m10"] / M["m00"])
                        cY = int(M["m01"] / M["m00"])
                        temp_detected.append((cX, cY, color_code))

        # 检测红、绿、蓝色块的质心
        detect_color_centroid(contours_red, "1")
        detect_color_centroid(contours_green, "2")
        detect_color_centroid(contours_blue, "3")

        # 按X坐标排序
        temp_detected = sorted(temp_detected, key=lambda x: x[0])

        # 合并相近的质心坐标
        unique_detected = []
        seen_colors = set()

        for item in temp_detected:
            color_code = item[2]
            centroid = item[:2]

            # 检查是否已经存在该颜色，如果存在，检查质心是否接近
            if color_code not in seen_colors:
                seen_colors.add(color_code)
                unique_detected.append(item)
            else:
                # 检查已存在的质心是否与当前质心接近
                for i, existing_item in enumerate(unique_detected):
                    if existing_item[2] == color_code and distance(existing_item[:2], centroid) < merge_threshold:
                        unique_detected[i] = (int((existing_item[0] + centroid[0]) / 2),
                                              int((existing_item[1] + centroid[1]) / 2),
                                              color_code)
                        break

        detected_colors = unique_detected[:3]  # 取前3个色块

        # 如果检测到了三个色块，进行数据处理
        if len(detected_colors) == 3:
            # 获取色块颜色顺序
            color_order = "".join([item[2] for item in detected_colors])  # 顺序：红，绿，蓝

            # 获取中间色块的质心坐标
            middle_x = f"{detected_colors[1][0]:03d}"
            middle_y = f"{detected_colors[1][1]:03d}"

            # 拼接格式数据
            formatted_data = f"{color_order}{middle_x}{middle_y}"

            # 控制发送数据的时机，只有在第四次识别后才发送数据
            detection_counter += 1
            if detection_counter >= 4:
                # 发送数据并打印
                print(f"发送给32板的数据: {formatted_data}")
                send_data(formatted_data)
                break
            else:
                # 打印前三次的识别结果，但不发送数据
                print(f"识别结果：{formatted_data}")

        # 实时显示（调试用）
        debug_frame = frame.copy()
        cv2.rectangle(debug_frame, (x_roi, y_roi), (x_roi + w_roi, y_roi + h_roi), (0, 255, 0), 2)
        for (x, y, color) in detected_colors:
            cv2.circle(debug_frame, (x_roi + x, y_roi + y), 5, (0, 0, 255), -1)  # 画出质心
        cv2.imshow("Combined Detection", debug_frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    cap.release()
    cv2.destroyAllWindows()
 

def test_triangle_detection0_1():
    # 设置HSV范围（红、绿、蓝）
    lower_red1 = np.array([0, 50, 50])
    upper_red1 = np.array([10, 255, 255])
    lower_red2 = np.array([160, 50, 50])
    upper_red2 = np.array([180, 255, 255])
    lower_green = np.array([30, 40, 40])
    upper_green = np.array([90, 255, 255])
    lower_blue = np.array([90, 50, 50])
    upper_blue = np.array([130, 255, 255])

    kernel = np.ones((5, 5), np.uint8)  # 用于形态学操作

    # 稳定性检测参数
    stability_threshold = 5    # 坐标波动阈值（像素）
    stable_frames_threshold = 5  # 需要连续稳定的帧数
    last_cx = None
    last_cy = None
    stable_count = 0

    # 摄像头设置
    cap = cv2.VideoCapture("/dev/video_shang0")
    if not cap.isOpened():
        print("无法打开摄像头")
        return
    
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

    while True:
        ret, frame = cap.read()
        if not ret:
            print("无法读取帧")
            break

        # 提取ROI区域并转换到HSV空间
        roi = (660,340,600,600)   # 设置ROI区域
        roi_img = frame[roi[1]:roi[1] + roi[3], roi[0]:roi[0] + roi[2]]
        hsv_img = cv2.cvtColor(roi_img, cv2.COLOR_BGR2HSV)
        
        # 创建颜色掩膜
        red_mask1 = cv2.inRange(hsv_img, lower_red1, upper_red1)
        red_mask2 = cv2.inRange(hsv_img, lower_red2, upper_red2)
        red_mask = cv2.bitwise_or(red_mask1, red_mask2)
        green_mask = cv2.inRange(hsv_img, lower_green, upper_green)
        blue_mask = cv2.inRange(hsv_img, lower_blue, upper_blue)

        # 增强形态学操作以消除噪声
        red_mask = cv2.erode(red_mask, kernel, iterations=2)
        red_mask = cv2.dilate(red_mask, kernel, iterations=4)
        green_mask = cv2.erode(green_mask, kernel, iterations=3)
        green_mask = cv2.dilate(green_mask, kernel, iterations=5)
        blue_mask = cv2.erode(blue_mask, kernel, iterations=2)
        blue_mask = cv2.dilate(blue_mask, kernel, iterations=5)

        # 计算每个颜色区域的面积
        red_area = cv2.countNonZero(red_mask)
        green_area = cv2.countNonZero(green_mask)
        blue_area = cv2.countNonZero(blue_mask)

        # 找到面积最大的颜色
        areas = {'1': red_area, '2': green_area, '3': blue_area}
        max_color = max(areas, key=areas.get)

        # 根据最大的颜色掩膜计算质心坐标
        current_cx = current_cy = None
        if max_color == '1':
            mask = red_mask
        elif max_color == '2':
            mask = green_mask
        else:
            mask = blue_mask

        # 计算质心
        M = cv2.moments(mask)
        if M["m00"] != 0:
            current_cx = int(M["m10"] / M["m00"]) + roi[0]
            current_cy = int(M["m01"] / M["m00"]) + roi[1]

            # 稳定性检测逻辑
            if last_cx is not None and last_cy is not None:
                distance = np.sqrt((current_cx - last_cx)**2 + (current_cy - last_cy)**2)
                if distance < stability_threshold:
                    stable_count += 1
                else:
                    stable_count = 0  # 坐标波动过大，重置计数
            else:
                stable_count = 1  # 首次检测

            last_cx, last_cy = current_cx, current_cy

            # 当稳定帧数达到阈值时发送数据
            if stable_count >= stable_frames_threshold:
                x = f"{current_cx:04}"
                y = f"{current_cy:04}"
                formatted_data = f"{x}{y}{max_color}"
                #send_data(formatted_data)
                print(f"稳定坐标发送: {formatted_data}")
                break  # 发送后退出循环

        # 调试显示（可选）
        #debug_frame = frame.copy()
        #cv2.rectangle(debug_frame, (roi[0], roi[1]), 
                     #(roi[0]+roi[2], roi[1]+roi[3]), (255,0,0), 2)
        #if current_cx and current_cy:
            #cv2.circle(debug_frame, (current_cx, current_cy), 5, (0,0,255), -1)
        #cv2.imshow("Detection", debug_frame)
        #if cv2.waitKey(1) & 0xFF == ord('q'):
            #break

    cap.release()
    cv2.destroyAllWindows()
def test_triangle_detection1_1():
    # 设置HSV范围（红、绿、蓝）
    lower_red1 = np.array([0, 50, 50])
    upper_red1 = np.array([10, 255, 255])
    lower_red2 = np.array([160, 50, 50])
    upper_red2 = np.array([180, 255, 255])
    lower_green = np.array([30, 40, 40])
    upper_green = np.array([90, 255, 255])
    lower_blue = np.array([90, 50, 50])
    upper_blue = np.array([130, 255, 255])

    kernel = np.ones((5, 5), np.uint8)  # 用于形态学操作

    # 稳定性检测参数
    stability_threshold = 10    # 坐标波动阈值（像素）
    stable_frames_threshold = 20  # 需要连续稳定的帧数
    last_cx = None
    last_cy = None
    stable_count = 0

    # 摄像头设置
    cap = cv2.VideoCapture("/dev/video_shang0")
    if not cap.isOpened():
        print("无法打开摄像头")
        return
    
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

    while True:
        ret, frame = cap.read()
        if not ret:
            print("无法读取帧")
            break

        # 提取ROI区域并转换到HSV空间
        roi = (660,340,600,600)   # 设置ROI区域
        roi_img = frame[roi[1]:roi[1] + roi[3], roi[0]:roi[0] + roi[2]]
        hsv_img = cv2.cvtColor(roi_img, cv2.COLOR_BGR2HSV)
        
        # 创建颜色掩膜
        red_mask1 = cv2.inRange(hsv_img, lower_red1, upper_red1)
        red_mask2 = cv2.inRange(hsv_img, lower_red2, upper_red2)
        red_mask = cv2.bitwise_or(red_mask1, red_mask2)
        green_mask = cv2.inRange(hsv_img, lower_green, upper_green)
        blue_mask = cv2.inRange(hsv_img, lower_blue, upper_blue)

        # 增强形态学操作以消除噪声
        red_mask = cv2.erode(red_mask, kernel, iterations=2)
        red_mask = cv2.dilate(red_mask, kernel, iterations=4)
        green_mask = cv2.erode(green_mask, kernel, iterations=3)
        green_mask = cv2.dilate(green_mask, kernel, iterations=5)
        blue_mask = cv2.erode(blue_mask, kernel, iterations=2)
        blue_mask = cv2.dilate(blue_mask, kernel, iterations=5)

        # 计算每个颜色区域的面积
        red_area = cv2.countNonZero(red_mask)
        green_area = cv2.countNonZero(green_mask)
        blue_area = cv2.countNonZero(blue_mask)

        # 找到面积最大的颜色
        areas = {'1': red_area, '2': green_area, '3': blue_area}
        max_color = max(areas, key=areas.get)

        # 根据最大的颜色掩膜计算质心坐标
        current_cx = current_cy = None
        if max_color == '1':
            mask = red_mask
        elif max_color == '2':
            mask = green_mask
        else:
            mask = blue_mask

        # 计算质心
        M = cv2.moments(mask)
        if M["m00"] != 0:
            current_cx = int(M["m10"] / M["m00"]) + roi[0]
            current_cy = int(M["m01"] / M["m00"]) + roi[1]

            # 稳定性检测逻辑
            if last_cx is not None and last_cy is not None:
                distance = np.sqrt((current_cx - last_cx)**2 + (current_cy - last_cy)**2)
                if distance < stability_threshold:
                    stable_count += 1
                else:
                    stable_count = 0  # 坐标波动过大，重置计数
            else:
                stable_count = 1  # 首次检测

            last_cx, last_cy = current_cx, current_cy

            # 当稳定帧数达到阈值时发送数据
            if stable_count >= stable_frames_threshold:
                x = f"{current_cx:04}"
                y = f"{current_cy:04}"
                formatted_data = f"{x}{y}{max_color}"
                send_data(formatted_data)
                print(f"稳定坐标发送: {formatted_data}")
                break  # 发送后退出循环

        # 调试显示（可选）
        debug_frame = frame.copy()
        cv2.rectangle(debug_frame, (roi[0], roi[1]), 
                     (roi[0]+roi[2], roi[1]+roi[3]), (255,0,0), 2)
        if current_cx and current_cy:
            cv2.circle(debug_frame, (current_cx, current_cy), 5, (0,0,255), -1)
        cv2.imshow("Detection", debug_frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
def run_test_for_5_seconds_1():
    # 运行 test_triangle_detection 函数 5 秒钟
    test_thread = threading.Thread(target=test_triangle_detection0_1)
    test_thread.start()
    time.sleep(3.0)
    # 5 秒钟后停止测试并继续执行形状检测
    print("5秒已过，开始执行形状检测...")
    # 你可能需要添加一些逻辑来安全地终止测试线程（如果有必要）
    # 然后调用 run_shape_detection 函数
    test_triangle_detection1_1()

def main():
    if not ser.is_open:
        ser.open()
    ser.timeout = 0.1  # 设置更短的超时时间
    print(f"串口 {ser.port} 已打开")
    send_data("987654321")
    print("987654321")
    def serial_receiver():
        while True:
            print("0419等待STM32数据...")
            data = receive_data()
            if data:
                print(f"接收到: {data}")
                if "1" in data:
                    print("检测到任务1: 执行二维码检测")
                    run_erweima()
                elif "2" in data:
                    print("检测到任务2: 执行物块检测")
                    run_wukuaiyuanxin()
                elif "a" in data:
                    run_wukuaiyuanxin_1()#圆盘出识别底部贴纸，识别定心坐标
                elif "3" in data:
                    print("检测到任务2: 执行物块检测")
                    send_data("123456789")
                    wukuaiyuanxin_logic1()
                elif "4" in data:
                    print("检测到任务2: 执行物块检测")
                    send_data("123456789")
                    wukuaiyuanxin_logic2()
                elif "b" in data:#圆盘识别底部贴纸颜色，按任务码顺序输出（第一圈）
                    send_data("123456789")
                    wukuaiyuanxin_logic1_1()
                elif "c" in data:#圆盘识别底部贴纸颜色，按任务码顺序输出（第二圈）
                    send_data("123456789")
                    wukuaiyuanxin_logic2_1()
                elif "d" in data:
                    run_sehuanyuanxin_ordered()#返回放在固定色环上的随机顺序物块的顺序
                elif "5" in data:
                    print("检测到任务3: 执行色环检测")
                    run_sehuanyuanxin2()
                    #run_sehuanyuanxin_jiandanlvbo()
                elif "6" in data:
                    print("检测到任务3: 执行色环检测")
                    run_sehuanyuanxin2_centered()
                    #etect_green_circle_only()
                elif "7" in data:
                    run_sehuanyuanxin2_1()     
                elif "8" in data:
                    run_sehuanyuanxin2_centered1()  
                elif "e" in data:
                    print("检测到任务3: 执行色环检测")
                    #run_shape_detection() ##决赛物块转盘第一次定心程序(什么形状的物块都能识别)
                    #test_triangle_detection()
                    run_test_for_5_seconds()#返回决赛放在转盘上的随机形状物块的坐标和颜色
                elif "f" in data:
                    print("检测到任务3: 执行色环检测")
                    send_data("123456789")
                    wukuaiyuanxin_logic1_renhexingzhuang()  ##决赛转盘第一圈任意形状物块颜色识别（普通圆形）
                elif "g" in data:
                    print("检测到任务3: 执行色环检测")
                    send_data("123456789")
                    wukuaiyuanxin_logic2_renhexingzhuang()  ##决赛转盘第二圈任意形状物块颜色识别（普通圆形）
                elif "h" in data:
                    print("检测到任务3: 执行色环检测")
                    run_shape_detection1()##决赛物块转盘第二圈码垛区的第一次定心程序(什么形状的物块都能识别)
                elif "i" in data:
                    print("检测到任务3: 执行色环检测")
                    run_test_for_5_seconds_1()
                elif "j" in data:
                    print("检测到任务3: 执行色环检测")
                    run_combined_ordered_detection_v6() #识别放置成一排的随机形状物块的颜色顺序
                elif "0" in data:
                    ser.close()
                    restart_program()
                elif "r" in data:
                    wait_and_receive_data()#接受32板发送信息，32板先发这个r字母，后发任务码（7位数）
                elif "end" in data:
                    print("任务序列完成。")
                    break

    # 启动串口接收线程
    serial_thread = threading.Thread(target=serial_receiver, daemon=True)
    serial_thread.start()

    try:
        while True:
            # 主线程可以执行其他任务
            time.sleep(0.01)
    except KeyboardInterrupt:
        print("程序被用户终止")
    finally:
        ser.close()
        print(f"串口 {ser.port} 已关闭")

if __name__ == "__main__":
    main()
    #run_sehuanyuanxin()
