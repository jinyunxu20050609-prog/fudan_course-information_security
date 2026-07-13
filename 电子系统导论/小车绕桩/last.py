# 导入所需库
import RPi.GPIO as GPIO  # 用于与树莓派的GPIO引脚通信
import time  # 提供延时功能
import cv2  # 用于处理图像
import numpy as np  # 提供对数组和矩阵的支持

# 定义一个函数，用于返回参数的符号
def sign(x):
    if x > 0:
        return 1.0
    else:
        return -1.0

# 定义引脚
EA, I2, I1, EB, I4, I3 = (13, 19, 26, 16, 20, 21)
FREQUENCY = 50  # PWM频率

# 设置GPIO模式
GPIO.setmode(GPIO.BCM)

# 设置GPIO引脚为输出
GPIO.setup([EA, I2, I1, EB, I4, I3], GPIO.OUT)
GPIO.output([EA, I2, EB, I3], GPIO.LOW)
GPIO.output([I1, I4], GPIO.HIGH)

# 初始化PWM波
pwma = GPIO.PWM(EA, FREQUENCY)
pwmb = GPIO.PWM(EB, FREQUENCY)
pwma.start(0)
pwmb.start(0)

# 定义目标中心
center_now = 320

# 打开摄像头，设置图像尺寸和格式
cap = cv2.VideoCapture(0)

# 初始化PID参数和误差
error = [0.0] * 3
adjust = [0.0] * 3
kp = 1.85
ki = 0.0
kd = 0.38
target = 320

# 读取一帧图像，因为我们砸了车，
#摄像头突然少读一帧，这是为了避免误判和确认起步位置合适
ret, frame = cap.read()

# 转换图像颜色空间为HSV
hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

# 提取橙色部分
lower_orange = np.array([0, 50, 50])
upper_orange = np.array([25, 255, 255])
mask = cv2.inRange(hsv, lower_orange, upper_orange)

# 形态学操作去除噪声
kernel = np.ones((3, 3), np.uint8)
opening = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
closing = cv2.morphologyEx(opening, cv2.MORPH_CLOSE, kernel)

# 将橙色部分转换为黑色
dst = cv2.bitwise_not(closing)
dst = cv2.dilate(dst, None, iterations=2)

# 在屏幕上显示图像
cv2.imshow("镜头画面", dst)

# 初始化黑色像素计数器
black_count = np.sum(dst[380] == 0)

# 打印黑色像素数量
print(black_count)

# 准备完毕，等待用户按下Enter键开始运行
print("准备完毕！按下Enter启动！")
input()

# 循环运行直到满足条件退出
n = 0
try:
    while n < 15:
        #这里是防止车头起步翘起，因此先给一个合适的加速度
        ret, frame = cap.read()
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        lower_orange = np.array([0, 50, 50])
        upper_orange = np.array([25, 255, 255])
        mask = cv2.inRange(hsv, lower_orange, upper_orange)
        kernel = np.ones((3, 3), np.uint8)
        opening = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        closing = cv2.morphologyEx(opening, cv2.MORPH_CLOSE, kernel)
        dst = cv2.bitwise_not(closing)
        dst = cv2.dilate(dst, None, iterations=2)
        black_count = np.sum(dst[380] == 0)
        cv2.imshow("镜头画面", dst)
        #相当于加速到原来的值
        pwma.ChangeDutyCycle(rspeed * (0.5 + n / 30))
        pwmb.ChangeDutyCycle(rspeed * (0.5 + n / 30))
        n += 1

    while True:
        #呈现图像，灰度图，同时将橙色线路变成黑色，别的都变成白色
        ret, frame = cap.read()
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        #只呈现橙色的部分，别的一律不在范围内，以排除干扰，同时又加入高斯降噪去除过多噪点
        lower_orange = np.array([0, 50, 50])
        upper_orange = np.array([25, 255, 255])
        mask = cv2.inRange(hsv, lower_orange, upper_orange)
        kernel = np.ones((3, 3), np.uint8)
        opening = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        closing = cv2.morphologyEx(opening, cv2.MORPH_CLOSE, kernel)
        dst = cv2.bitwise_not(closing)
        dst = cv2.dilate(dst, None, iterations=2)
        black_count = np.sum(dst[380] == 0)
        cv2.imshow("镜头画面", dst)
        
        if black_count == 0:
            continue

        #展示偏差
        center_now = (np.where(dst[380] == 0)[0][0] + np.where(dst[380] == 0)[0][-1]) / 2
        direction = center_now - 320
        print("偏差:", direction)

        #计算偏差
        error[0] = error[1]
        error[1] = error[2]
        error[2] = center_now - target

        #计算调整量
        adjust[0] = adjust[1]
        adjust[1] = adjust[2]
        adjust[2] = adjust[1] + kp * (error[2] - error[1]) + ki * error[2] + kd * (error[2] - 2 * error[1] + error[0])
        print(adjust[2])


        #本想在此处加入判断交叉点直行的逻辑，但因小车速度本来就较大，完全可以凭借惯性冲过去，就没有加
        #如果要加，逻辑就是当视野中像素点陡然增加，就认定其到达交叉点，这主要和adjust[1]和adjust[2]有关
        #大致代码如下,没有调参数，此部分代码不完善，测试时未使用：
        #if abs(adjust[2]) > control and abs(adjust[1]) < 20:
        #   pwma.ChangeDutyCycle(rspeed)
        #   pwmb.ChangeDutyCycle(lspeed)
        # 饱和输出限制在control绝对值之内
        if abs(adjust[2]) > control:
            adjust[2] = sign(adjust[2]) * control
            print(adjust[2])

        # 执行PID

        # 右转
        if adjust[2] > 30:
            pwma.ChangeDutyCycle(rspeed - 1.17*adjust[2])
            pwmb.ChangeDutyCycle(lspeed)

        # 左转
        elif adjust[2] < -30:
            pwma.ChangeDutyCycle(rspeed)
            pwmb.ChangeDutyCycle(lspeed + 1.17*adjust[2])

        #直行
        else:
            pwma.ChangeDutyCycle(rspeed)
            pwmb.ChangeDutyCycle(lspeed)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
except KeyboardInterrupt:
    print("结束！")
    pass

# 释放清理
cap.release()
cv2.destroyAllWindows()
pwma.stop()
pwma.stop()
GPIO.cleanup()























