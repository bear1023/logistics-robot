# 视觉（树莓派 + OpenCV）

## 文件

| 文件 | 版本 | 行数 | 说明 |
| --- | --- | --- | --- |
| `finals/zongchengxu20250801chusai.py` | 国赛（8.6） | 1 910 | 11 个识别函数 + 单线程轮询串口 |
| `provincial/zongchengxu20250419.py` | 省赛（4.10） | 2 794 | 31 个函数，含"任意形状"识别与决赛分支 |

**两版必须配套对应版本的固件**：命令码在 `5/6`（省赛色环）与 `7/8`（国赛色环）上不同，混用会跑错流程。

## 依赖与运行

```bash
pip install opencv-python numpy pyserial pyzbar
sudo apt install libzbar0        # pyzbar 依赖的系统库

python3 zongchengxu20250801chusai.py
```

必须改的三处（脚本开头）：

```python
port = '/dev/ttyUSB0'          # 串口设备（STM32 的 USART1）
cap_shang = cv2.VideoCapture('/dev/video_shang0')   # 上视
cap_xia   = cv2.VideoCapture('/dev/video_xia0')     # 下视
```

- 波特率 **9600**，与固件一致；
- 所有 `imshow` 已注释，可无头运行；
- `r` 命令分支用 `os.execl` 自重启，因此必须 `python3 xxx.py` 启动（不能直接 `./xxx.py`）。

## 算法要点

| 任务 | 算法 | 关键参数 |
| --- | --- | --- |
| 二维码 | 灰度 → `pyzbar.decode()` | 长度必须 7；连续 3 帧一致才确认 |
| 物块 | `GaussianBlur(9,9,2)` → `HoughCircles` | `dp=1, minDist=20, param1=25, param2=25, r=35~45`，ROI `[120,80,400,217]` |
| 色环 | `HoughCircles` + 圆心约束 | `param1=50, param2=30, r=35~38`；`x∈[320±216]`、`y∈[240−111,240+120]` |
| 颜色 | HSV 双阈值 + 形态学 + `countNonZero` | 红两段、绿 `[35,40,40]~[89..]`、蓝 `[90,60,60]~[140..]` |
| 稳定判据 | 连续多帧一致 | 位移 <10 px × 3 次；颜色 ≥5 次且置信度 ≥0.5；窗口 15 帧；总超时 8 s |
| 直线纠偏（国赛） | `Canny(50,150)` → `HoughLinesP` → 长度加权均角 | `threshold=20, minLineLength=140, maxLineGap=10`；方差 ≤1.0；限幅 ±9.9° |
| 任意形状（省赛） | `THRESH_OTSU|BINARY_INV` → `findContours` → `moments` 质心 | 只求质心 + HSV 判色，不分类形状 |

## 与 STM32 的协议

| 方向 | 内容 |
| --- | --- |
| 收 | 单字节 ASCII 命令（`1`~`0`、`a`~`d`、`r`） |
| 发 | 11 字节：`0xFF` + 9 字节 ASCII + `0xFE` |

9 字节三种格式：

```
坐标  : "xxxx yyyy c"      例 "0316 0238 2"
角度  : "000000±nn.n"      例 "000000-12.3"
状态  : "987654321" 就绪 / "000000004" 未识别 / "123+312" 任务码
```

完整命令表见 [`../docs/02-protocol.md`](../docs/02-protocol.md)。

## 现场踩坑

1. **光照**：白天窗边和晚上日光灯下的 HSV 阈值完全不同，靠补光灯（`TIM3_CH1` PWM 三档）拉平；
2. **摄像头位置**：像素→毫米系数（`1.1805555` / `0.29239766` / `0.6756` / `0.96153846`）随高度/角度变化，重装摄像头必须重标；
3. **USB 带宽**：两路 640×480 同时开会丢帧，精定标那一步会切到 1920×1080 单路；
4. **8 s 总超时**：超时会回 `"000000004"` 触发重试，但不会重连摄像头——摄像头掉线只能重启脚本。
