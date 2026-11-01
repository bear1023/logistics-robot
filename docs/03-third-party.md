# 第三方与自研代码划分

这个仓库里哪些是自己写的、哪些是站在别人肩膀上，写清楚，既是对原作者的尊重，也方便以后维护。

## 1. 第三方（随仓库保留，版权归原作者）

| 路径 | 来源 | 用途 | 许可 |
| --- | --- | --- | --- |
| `firmware/can_ZDT/Emm_V5.c/.h` | 张大头（ZDT）闭环步进官方例程 | Emm_V5 步进 CAN 协议、参数读写 | 厂商例程，按其发布条款 |
| `firmware/can_ZDT/board.c/.h`、`can.c/.h`、`fifo.c/.h`、`delay.c/.h` | 同上（ZDT_X57 例程工程结构） | CAN 底层、FIFO、基础延时 | 同上 |
| `firmware/imu/wit_c_sdk.c/.h`、`REG.h` | 维特智能（WIT）官方 SDK | IMU 串口协议与寄存器表 | 厂商 SDK |
| `firmware/SYSTEM/delay/*`、`sys/*`、`usart/*`、`Serial.c/.h` | 正点原子 STM32F407 工程模板 | 延时、位带 IO、串口重定向与解析 | 模板代码 |
| `firmware/OLED/OLED.c`、`OLED_Font.h` | 江协科技风格 OLED 驱动 + 字库 | SSD1306 显示 | 开源教程代码 |
| `firmware/USER/stm32f4xx_it.c`、`stm32f4xx_conf.h`、`system_stm32f4xx.h` | ST 标准外设库模板 | 中断向量与工程配置 | ST 许可 |
| `vision/*` 里的 `cv2`、`numpy`、`pyzbar`、`serial` | 开源库 | 图像处理、二维码、串口 | 各自开源许可 |

**未随仓库提供**（体积大/标准库）：
- `FWLIB/`：ST STM32F4xx 标准外设库 V1.3.0
- `CORE/`：CMSIS 内核文件 + 启动汇编
- `OBJ/`：构建产物

## 2. 自研 / 大幅改写（本仓库 MIT 覆盖的部分）

| 文件 | 行数 | 内容 |
| --- | --- | --- |
| `firmware/USER/main.c` | 987 | **整车流程**：视觉交互、坐标换算、抓放顺序、舵机角度表、云台时间拟合 |
| `firmware/can_ZDT/yyb_move.c/.h` | 314 | 四轮混控、位置模式封装、脉冲换算、梯形延时 |
| `firmware/Hardware/pid.c/.h` | 254 | 航向 PID（±180° 环绕、5 组场景增益） |
| `firmware/Hardware/PWM.c/.h` | 268 | 舵机 PWM 初始化与插值 |
| `firmware/Hardware/servo.c`、`swith.c` | 40 / 19 | 舵机与开关封装 |
| `firmware/imu/imu.c/.h`、`timer.c` | 303 / 43 | 姿态数据解析（Yaw 提取）与定时采样 |
| `firmware/ckp/uart6_ckp.c` | 93 | 串口屏指令发送 |
| `firmware/lanya/usart5.c` | 205 | 蓝牙 AT 配置与数据通道 |
| `firmware/LED/LED.c`、`light.c` | 48 / 6 | 状态灯与补光 |
| `firmware/OLED/time_OLED.c` | 32 | OLED 周期刷 Yaw |
| `firmware/USER/exti.c` | 51 | 按键中断（重启树莓派） |
| `firmware/can_ZDT/circle_pid.c` | 176 | 圆形轨迹 PID（**未加入工程**） |
| `vision/finals/zongchengxu20250801chusai.py` | 1 910 | 国赛视觉：二维码/物块/色环/码垛/纠偏 |
| `vision/provincial/zongchengxu20250419.py` | 2 794 | 省赛视觉：含任意形状识别与决赛分支 |

## 3. 死代码 / 未加入工程

| 文件 | 状态 |
| --- | --- |
| `can_ZDT/circle_pid.c` | 未加入 Keil 工程 |
| `can_ZDT/delay.c` | 与 `SYSTEM/delay` 重名，`yyb_move.c` 的 include 顺序会先命中它（原型不一致隐患） |
| `lanya/hmi.c` | 与 `uart6_ckp.c` 的 `HMISends` 重名，已被排除 |
| `can_ZDT/fifo.c` | 无人调用，且 `fifo.h` 声明 `fifo_initQueue`、实现是 `initQueue` |
| `Emm_V5_Read_Sys_Params()`、`can_GetRxFlag()` | 有定义，从未调用（想加里程计的话从这两个函数入手） |

整理时保留它们（而不是删掉），是为了让"当时试过什么"有迹可循；如果要精简，可以整块删掉，不影响主流程编译。

## 4. 如果要把这个仓库当模板复用

1. 补 `FWLIB/` + `CORE/`（ST 标准库与 CMSIS），工程里的相对路径已经写好了；
2. Emm_V5 的电机地址（1–6）与波特率（500 kbps）按自己的硬件改 `yyb_move.c` 与 `can.c`；
3. 视觉端的像素→毫米系数、中心点必须重新标定（见 README 第 9 节）；
4. 命令码表在 `docs/02-protocol.md`，改协议时固件与 Python 两边同步改。
