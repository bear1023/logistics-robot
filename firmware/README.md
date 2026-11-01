# 固件说明（STM32F407，Keil）

## 目录

| 路径 | 内容 |
| --- | --- |
| `USER/` | `main.c`（987 行，整车流程）、`exti.c`、中断与工程配置、`Template.uvprojx` |
| `can_ZDT/` | `yyb_move.c`（自研运动封装）、`circle_pid.c`（未用）、Emm_V5/CAN/FIFO/延时（第三方） |
| `Hardware/` | `pid.c`（航向 PID）、`PWM.c`（舵机 PWM + 插值）、`servo.c`、`swith.c` |
| `imu/` | `imu.c`（解析 Yaw）、`timer.c` + WIT SDK（第三方） |
| `lanya/` | `usart5.c`（蓝牙 AT）、`hmi.c`（未用） |
| `ckp/` | `uart6_ckp.c`（串口屏指令） |
| `LED/` | `LED.c`、`light.c`（补光） |
| `OLED/` | `time_OLED.c`（刷 Yaw）+ `OLED.c`/字库（第三方） |
| `SYSTEM/` | 延时、位带 IO、串口（正点原子模板） |

**缺**：`FWLIB/`（ST 标准库 V1.3.0）、`CORE/`（CMSIS + 启动文件）、`OBJ/`（构建产物）。

## 主要接口

```c
// main.c 里的流程骨架（顺序阻塞）
void main(void)
{
    Init();                            // 时钟、CAN、UART、TIM、IMU、OLED、舵机
    while (1) {                        // 严格说只有一轮，跑完流程就停在最后
        if (!wait_pi_ready()) continue;      // 等树莓派 "98"
        task_code = get_task_code();          // '1' → 任务码 "123+312"
        for (round = 1; round <= 2; round++) {
            calibrate_disc(round);            // '2' / 'a'
            for (i = 0; i < 3; i++) {
                target = ask_pi_blocks(i);    // '3' / '4'
                move_to(target);              // car_move + PID + 延时
                pick();                       // 云台 + 升降 + 抓手
                ring = ask_pi_ring();         // '7' / '8'
                place(ring, color_order[i]);
            }
        }
        stack_three_layers();                 // '9' / '0'
        go_home();
    }
}
```

```c
// yyb_move.c
void car_move(float vx, float vy, float w);       // 四轮混控 + 逐轴下发
void move_all(...);                                // 7 参数版：一次走完 x/y/角度
void car_move_delay(float dx, float dy);           // 解析式延时（梯形速度规划）
```

```c
// Hardware/pid.c
void PID_Init(float kp, float ki, float kd, float maxInt, float maxOut);
float PID_Calc(PIDController *pid, float target, float actual);   // 内含 ±180° 环绕
void PID_move(PIDController *pid, float target, int pid_choose);   // 5 组场景增益
```

## 关键宏与常量

| 常量 | 值 | 位置 |
| --- | --- | --- |
| CAN 波特率 | 500 kbps | `can.c` |
| 轮子脉冲系数 | X ×10.5、Y ×10.3 | `yyb_move.c` / `main.c` |
| 升降 | 80 脉冲/mm | `main.c` |
| 平推 | 25.465 脉冲/mm | `main.c` |
| 舵机 CCR | `angle/270*2000+500`，云台 `/360` | `servo.c` / `main.c` |
| 航向 PID 周期 | 50 ms | `imu/timer.c` |

## 编译

1. Keil µVision 5.34 + ARMCC V5.06u7（AC5，不用 AC6）；
2. 装 `Keil.STM32F4xx_DFP 2.17.1`；
3. 把 ST 标准库 `FWLIB/` 与 `CORE/` 放到工程同级目录（include 路径是 `..\FWLIB\inc` 等相对路径）；
4. Target `Template`，宏 `STM32F40_41xxx, USE_STDPERIPH_DRIVER`；
5. 下载器 CMSIS-DAP / J-Link / ST-Link 均可（工程里都登记了）。

构建体积：Code 48 400 B + RO 2 762 B ≈ 50 KB Flash；RW 2 640 B + ZI 328 B ≈ 2.9 KB RAM。

## 调试经验（来自现场）

- **先看串口屏**：屏上会显示当前步骤与坐标，卡住时一眼能看出是"等视觉"还是"等电机"；
- **CAN 不通先查使能**：`0xF3` 没发出去，电机只会响不动；
- **视觉不回来先查波特率**：固件 9600，树莓派脚本里 `ser = serial.Serial(port, 9600)`；
- **树莓派没起来**：固件会永远停在 `wait_pi_ready()`，现象是屏不刷新。
