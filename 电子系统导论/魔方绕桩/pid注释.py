class PID:
    #PID控制器 方便调用与PID控制有关函数
    
    def __init__(self, P=0.5, I=0, D=0, target=320, init_output=0):
        # 初始化 PID 控制器的参数
        self.Kp = P  # 比例增益
        self.Ki = I  # 积分增益
        self.Kd = D  # 微分增益
        self.err_pre = 0  # 上一次误差
        self.err_last = 0  # 上一次的误差
        self.u = 0  # 控制器的输出
        self.integral = 0  # 积分项
        self.ideal = target  # 设定的目标
        self.last_output = init_output  # 上一次的输出
        self.pre_output = init_output  # 当前的输出
        
    def update(self, feedback_value):
        self.err_pre = self.ideal - feedback_value  # 计算当前误差
        self.integral *= 0.86  # 对积分项进行衰减
        self.integral += self.err_pre  # 更新积分项
        self.u = self.Kp * self.err_pre + self.Ki * self.integral + \
                 self.Kd * (self.err_pre - self.err_last)  # 计算控制器输出
        self.err_last = self.err_pre  # 更新上一次误差
        self.pre_output = self.u  # 更新当前输出
        self.last_output = self.pre_output  # 更新上一次输出
        return self.pre_output  # 返回当前输出
    
    def setKp(self, proportional_gain):
        #确定PID控制器在设置比例增益时对当前误差作出的响应程度
        self.Kp = proportional_gain

    def setKi(self, integral_gain):
        #确定PID控制器在设置积分增益时对当前误差作出的响应程度
        self.Ki = integral_gain

    def setKd(self, derivative_gain):
        #确定PID控制器在设置微分增益时对当前误差作出的响应程度
        self.Kd = derivative_gain
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    

