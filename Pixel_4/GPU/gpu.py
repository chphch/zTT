import subprocess


# gpu_clock_list = [180000000, 267000000, 355000000, 430000000]
gpu_clock_list = [257, 345, 427, 499, 585]
dir_thermal = '/sys/devices/virtual/thermal'


class GPU:
    def __init__(self, ip):
        self.clk = 2
        self.clock_data = []
        self.temp_data = []
        self.ip = ip
        self.setGPUclock(len(gpu_clock_list) - 1)
		
    def setGPUclock(self, i):
        self.clk = i
        # fname = '/sys/class/kgsl/kgsl-3d0/devfreq/userspace/set_freq'
        fname = '/sys/class/kgsl/kgsl-3d0/min_clock_mhz'
        subprocess.check_output(['adb', '-s', self.ip, 'shell', 'su -c', '\"echo', str(gpu_clock_list[i]) + " >", fname + "\""])
        fname = '/sys/class/kgsl/kgsl-3d0/max_clock_mhz'
        subprocess.check_output(['adb', '-s', self.ip, 'shell', 'su -c', '\"echo', str(gpu_clock_list[i]) + " >", fname + "\""])
		
    def getGPUtemp(self):
        fname='{}/thermal_zone10/temp'.format(dir_thermal)
        output = subprocess.check_output(['adb', '-s', self.ip, 'shell',  'su -c', '\"cat', fname+"\""])
        output = output.decode('utf-8')
        output = output.strip()
        return int(output) / 1000

    def getGPUclock(self):
        # fname = '/sys/class/kgsl/kgsl-3d0/devfreq/cur_freq'
        fname = '/sys/class/kgsl/kgsl-3d0/clock_mhz'
        output = subprocess.check_output(['adb', '-s', self.ip, 'shell',  'su -c', '\"cat', fname + "\""])
        output = output.decode('utf-8')
        output = output.strip()
        # return int(output) / 1000000
        return int(output)

    def collectdata(self):
        self.clock_data.append(self.getGPUclock())
        self.temp_data.append(self.getGPUtemp())

    # def setUserspace(self):
    #     fname = '/sys/class/kgsl/kgsl-3d0/devfreq/governor'
    #     subprocess.check_output(['adb', '-s', self.ip, 'shell',  'su -c', '\"echo userspace >', fname + "\""])
    #     print('[gpu]Set userspace')
    
    # def setdefault(self):
    #     fname = '/sys/class/kgsl/kgsl-3d0/devfreq/governor'
    #     subprocess.check_output(['adb', '-s', self.ip, 'shell',  'su -c', '\"echo msm-adreno-tz >', fname + "\""])
    #     print('[gpu]Set msm-adreno-tz')
    
    def getCurrentClock(self):
        # fname = '/sys/class/kgsl/kgsl-3d0/devfreq/cur_freq'
        fname = '/sys/class/kgsl/kgsl-3d0/clock_mhz'
        output = subprocess.check_output(['adb', '-s', self.ip, 'shell',  'su -c', '\"cat', fname + "\""])
        output = output.decode('utf-8')
        output = output.strip()
        print('[gpu]{}MHz'.format(output))
