import RPi.GPIO as GPIO  # 导入GPIO库
import cv2  # 导入OpenCV库
import cube_recognizer.libRecognize as lR  # 导入魔方识别库
import math  # 导入数学库
from collections import OrderedDict  # 导入有序字典
from pid import PID  # 导入PID控制器

EA, I2, I1, EB, I4, I3 = (13, 19, 26, 16, 20, 21)  # 定义引脚
FREQUENCY = 50  # PWM频率

# PID 参数
kp = 0.4  # 比例系数
ki = 0.001  # 积分系数
kd = 0.3  # 微分系数
target_x = 320  # 始终不变的量 指向最中央

#初始阶段速度和转向限制
speed_init = 70  # 初始速度
lim_init = 18  # 初始转向限制

stage_cutter = 9  # 第几次循环开始阶段2
# 因为小车起步重心不稳为防止抬头分为两个阶段

# 阶段2速度和转向限制
speed_st2 = 70  # 阶段2速度
lim_st2 = 27  # 阶段2转向限制

side_cutter = 70  # 边沿设定

# 与魔方目标距离系数
distant_factor = 2.2  # 与魔方目标距离系数，越大弯越大

# 目标坐标限制
x_lim_from_side = 67  # 目标坐标限制，越大越晚转

# 设置GPIO编号模式
GPIO.setmode(GPIO.BCM)

# 设置GPIO口为输出
GPIO.setup([EA, I2, I1, EB, I4, I3], GPIO.OUT)
GPIO.output([EA, I2, EB, I3], GPIO.LOW)
GPIO.output([I1, I4], GPIO.HIGH)

# 设置PWM引脚和频率
pwma = GPIO.PWM(EA, FREQUENCY)
pwmb = GPIO.PWM(EB, FREQUENCY)
pwma.start(0)
pwmb.start(0)

# 打开摄像头
cap = cv2.VideoCapture(0)

ret, frame = cap.read()  # 读取摄像头帧
ct = 0  # 初始化循环计数器

cur_x = target_x  # 当前X坐标初始化为图像中央
# 打开/新建视频文件用于写入,帧率=17,帧尺寸=640x480
out = cv2.VideoWriter("movie.avi", cv2.VideoWriter_fourcc(
    'X', 'V', 'I', 'D'), 17, (640, 480))  

def get_motor_value(adjustment, speed, lim):  
    # 定义函数 get_motor_value
    if abs(adjustment) > lim:  # 如果调整值adjustment的绝对值超过了限制 lim
        # 将调整值限制在 -lim 到 lim 之间
        adjustment = lim if adjustment > 0 else -lim  
    # 返回计算后的电机速度，包括增加调整值后的速度和减去调整值后的速度
    return speed + adjustment, speed - adjustment  

pid_line = PID(kp/100, ki/100, kd/100, target_x, 0)  # 初始化PID控制器

print("Ready")
input()  # 等待用户输入继续执行程序

adjust_prev = 0  # 上一次调整量
adjust = 0  # 调整量
prev_x = cur_x  # 上一次X坐标初始化为当前X坐标
tgt_x = 320  # 目标X坐标
rCN = lR.CubeRecognizer()  # 初始化魔方识别器
rCN.init()  # 初始化魔方识别器
count = 0  # 计数器

try:  
    while True:  # 进入循环
        if ct < stage_cutter:  # 如果当前循环计数 ct 小于阶段切换值 stage_cutter
            speed = speed_init  # 设置速度为初始速度 
            lim = lim_init  # 设置限制为初始转向限制
        else:  # 否则，即当前循环计数 ct 大于等于阶段切换值 stage_cutter
            speed = speed_st2  # 设置速度为阶段2速度和转向限制
            lim = lim_st2  # 设置限制为阶段2转向限制
        ct = ct + 1  # 计数器ct加1
        
        ret, frame = cap.read()  # 读取摄像头，返回值存储在 ret 和 frame 中
        count += 1  # 计数器count加1
        
        # 调用 get_rec_cen() 获取魔方信息
        cur_x, color, size, height = rCN.get_rec_cen(frame)  
        # cur_x 是当前魔方中心位置，通过cur_x=(black_start+black_end)/2计算得出
        # color 是魔方颜色, size 是魔方的尺寸, height 是魔方的高度
        
        im = frame  # 将当前帧保存为 im
        
        font = cv2.FONT_HERSHEY_SIMPLEX  # 设置字体为 OpenCV 内置的简单字体
        
        # 如果当前识别到魔方且其尺寸在合理范围内
        if (cur_x != 0 and size < 80000 and size > 1400):  
            # 在图像上绘制垂直于魔方中心的绿色线条
            cv2.line(im, (cur_x, 0), (cur_x, 480), (0, 255, 0), 3)
            # 记录当前魔方中心位置为 prev_x，以便在未检测到魔方时保持转向
            prev_x = cur_x  
            # 在图像上添加文字显示当前魔方中心的 x 坐标
            cv2.putText(im, "cur_x:"+str(cur_x),  
                        (10, 30), font, 1, (0, 255, 0), 2)
            
            # 给tgt_x赋值，确定转向
            if cur_x > 640 - side_cutter: # 如果魔方中心靠近图像右侧边缘
                tgt_x = 320  # 设置目标转向位置为图像中心
            elif cur_x < side_cutter:  # 如果魔方中心靠近图像左侧边缘
                tgt_x = 320  # 设置目标转向位置为图像中心
                print("go straight")  # 打印信息表示直行
           # 上列代码为判断方块是否位于图像边缘，位于边缘则直行 
           
            elif color == "blue":  # 如果魔方颜色为蓝色
                # 根据魔方大小调整目标转向位置向左偏移
                tgt_x = cur_x - distant_factor * math.sqrt(size) 
            elif color == "red" or color == "yellow":  # 如果魔方颜色为红色或黄色
                # 根据魔方大小调整目标转向位置向右偏移
                tgt_x = cur_x + distant_factor * math.sqrt(size)  
    
            # 检测tgx是否越界
            # 越界参数可调整(即x_lim_from_side)
            if tgt_x > 640 - x_lim_from_side:
                tgt_x = 640 - x_lim_from_side
            elif tgt_x < x_lim_from_side:
                tgt_x = x_lim_from_side

            # 在图像上添加文字
            cv2.putText(im, "height:"+str(height),
                        (10, 120), font, 1, (0, 0, 255), 2) #显示魔方高度
            cv2.putText(im, "size:{:.1f}".format(size),
                        (10, 150), font, 1, (0, 0, 255), 2) #显示魔方尺寸

            adjust = pid_line.update(tgt_x)  # 使用 PID 控制器更新转向调整量
            adjust_prev = adjust  # 记录当前的转向调整量作为上一个调整量
             
        elif size >= 30000:  # 如果检测到的魔方尺寸过大（异常情况）
            adjust = 0  # 不进行转向调整
        else:  # 如果当前未识别到魔方
            if count >= 20: # 如果计数器大于等于 20
                tgt_x = 320  # 设置目标转向位置为图像中心
                speed = speed_init  # 恢复默认速度
                lim = lim_init  # 恢复默认限制
            # 根据之前记忆的魔方位置进行转向调整
            adjust = pid_line.update(0.9 * prev_x)  
            if prev_x < 320:  # 如果之前的魔方位置在图像左侧
                tgt_x = 80  # 设置目标转向位置为较左侧位置
            else:  # 如果之前的魔方位置在图像右侧
                tgt_x = 535  # 设置目标转向位置为较右侧位置
            # 根据目标转向位置进行转向调整
            adjust = pid_line.update(1.12 * tgt_x)  
            
            # 在图像im中tgt_x位置上画一条垂直线
            cv2.line(im, (int(tgt_x), 0), (int(tgt_x), 480), (255, 0, 0), 3)

            # 添加文字，标注tgt_x值
            cv2.putText(im, "tgt_x:"+str(tgt_x), (10, 60), 
                        font, 1, (255, 0, 0), 2)
            cv2.putText(im, "adj:{:.3f}".format(adjust),
                        (10, 90), font, 1, (0, 0, 255), 2)

            # 根据adjust乘以lim的结果和指定的速度计算两个电机的速度值
            motor_a, motor_b = get_motor_value(adjust*lim, speed, lim)

            # 设置PWM信号，改变电机的占空比
            pwma.ChangeDutyCycle(motor_a) #电机a占空比为motor_a
            pwmb.ChangeDutyCycle(motor_b) #电机b占空比为motor_b

            # 将带有注释和文字的图像im写入视频输出
            out.write(im)
except KeyboardInterrupt:
    print("End")
    
#释放清理
cap.release() 
out.release()  # 关闭视频文件
cv2.destroyAllWindows()
pwma.stop()
pwmb.stop()
GPIO.cleanup()
rCN.terminate()
            




















