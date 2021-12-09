#!/usr/bin/env python3

import os
import time
import socket
import argparse
import csv
from collections import namedtuple

import numpy as np
import matplotlib.pyplot as plt

from SurfaceFlinger.get_fps import SurfaceFlingerFPS, get_multi_dnn_profiler_fps
from PowerLogger.powerlogger import PowerLogger
from CPU.cpu import CPU, big_cpu_clock_list
from GPU.gpu import GPU, gpu_clock_list


FILEPATH_STATES = 'states.csv'
SURFACE_FLINGER_TARGETS = {
    'showroom': '"SurfaceView - com.android.chrome/com.google.android.apps.chrome.Main#0"',
    'skype': '"com.skype.raider/com.skype4life.MainActivity#0"',
    'call': '"SurfaceView - com.tencent.tmgp.kr.codm/com.tencent.tmgp.cod.CODMainActivity#0"',
    'multi_dnn_profiler': '"com.multi_dnn_profiler/com.multi_dnn_profiler.MainActivity#0"',
    #"\"SurfaceView - com.tencent.tmgp.kr.codm/com.tencent.tmgp.cod.CODMainActivity#0\""
    #"\"com.skype.raider/com.skype4life.MainActivity#0\""
    #"\"SurfaceView - com.android.chrome/org.chromium.chrome.browser.ChromeTabbedActivity#0\""
}

# (CPU clock, GPU clock, power, CPU temperature, GPU temperature)
State = namedtuple('State', ['c_c', 'g_c', 'c_p', 'c_t', 'g_t', 'fps'])


class Client:

    def __init__(self, app, exp_time, server_ip, server_port, target_fps, pixel_ip):
        self.app = app
        self.exp_time = exp_time
        self.server_ip = server_ip
        self.server_port = server_port
        self.target_fps = target_fps
        self.pixel_ip = pixel_ip
        self.pl = PowerLogger()
        self.t = 1
        self.ts = []
        self.fps_data = []
        self.state = State(c_c=0, g_c=0, c_p=0, c_t=0, g_t=0, fps=0)
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket.connect((self.server_ip, self.server_port))
        self.c0 = CPU(0, ip=self.pixel_ip, cpu_type='l')
        self.c6 = CPU(4, ip=self.pixel_ip, cpu_type='b')
        self.g = GPU(ip=self.pixel_ip)
        self.start_time = None
        self.initialize()

    def initialize(self):
        self.client_socket.send((str(self.target_fps) + ',' + str(self.exp_time)).encode())

        ''' Set CPU and GPU governor to userspace '''
        self.c0.setUserspace()
        self.c6.setUserspace()
        # self.g.setUserspace()

        ''' Set CPU and GPU clock to maximum before starting '''
        max_clock_index_cpu = len(big_cpu_clock_list) - 1
        max_clock_index_gpu = len(gpu_clock_list) - 1
        self.c0.setCPUclock(max_clock_index_cpu)
        self.c6.setCPUclock(max_clock_index_cpu)
        self.g.setGPUclock(2)
        
        if self.app != 'multi_dnn_profiler':
            view = SURFACE_FLINGER_TARGETS[self.app]
            self.sf_fps_driver = SurfaceFlingerFPS(view, ip=self.pixel_ip)

        c_c = max_clock_index_cpu
        g_c = max_clock_index_gpu
        c_t = float(self.c0.getCPUtemp())
        g_t = float(self.g.getGPUtemp())
        fps = self.get_fps()
        self.state = State(c_c=c_c, g_c=g_c, c_p=int(self.pl.getPower() / 100), c_t=c_t, g_t=g_t, fps=fps)
        time.sleep(4)

        if os.path.exists(FILEPATH_STATES):
            os.remove(FILEPATH_STATES)

    def run(self):
        self.start_time = time.time()
        while self.t <= self.exp_time:
            self.step()
            self.t += 1

    def step(self):
        send_msg = str(tuple(self.state))[1:-1]
        self.client_socket.send(send_msg.encode())
        is_received = False
        while not is_received:
            try:
                recv_msg = self.client_socket.recv(8702).decode()
                clk = recv_msg.split(',')
                c_c = int(clk[0])
                g_c = int(clk[1])
                is_received = True
            except:
                pass

        self.c0.setCPUclock(c_c)
        self.c6.setCPUclock(c_c)
        self.g.setGPUclock(g_c)

        fps = self.get_fps()
        self.fps_data.append(fps)

        self.ts.append(self.t)

        self.c0.collectdata()
        self.c6.collectdata()
        self.g.collectdata()

        c_p = int(self.pl.getPower() / 100)
        if c_p == 0:
            return

        c_t = float(self.c0.getCPUtemp())
        g_t = float(self.g.getGPUtemp())

        next_state = State(c_c, g_c, c_p, c_t, g_t, fps)
        print('[{}] state:{} next_state:{} fps:{}'.format(self.t, self.state, next_state, fps))
        self.state = next_state

        with open(FILEPATH_STATES, 'a') as fp:
            fp.write(','.join(map(str, [time.time() - self.start_time] + list(self.state))) + '\n')

    def get_fps(self):
        if self.app == 'multi_dnn_profiler':
            fps = get_multi_dnn_profiler_fps(self.pixel_ip)
        else:
            fps = float(self.sf_fps_driver.getFPS())
        if fps > 60:
            fps = 60.0
        return fps

    def log_results(self):
        # Logging results
        print('Average Total power={} mW'.format(sum(self.pl.power_data) / len(self.pl.power_data)))
        print('Average fps = {} fps'.format(sum(self.fps_data) / len(self.fps_data)))

        ts = range(0, len(self.fps_data))
        f = open('power_skype_zTT.csv', 'w', encoding='utf-8', newline='')
        wr = csv.writer(f)
        wr.writerow(self.pl.power_data[1:])
        f.close()

        f = open('temp_skype_zTT.csv', 'w', encoding='utf-8', newline='')
        wr = csv.writer(f)
        wr.writerow(self.c0.temp_data)
        wr.writerow(self.c6.temp_data)
        wr.writerow(self.g.temp_data)
        f.close()

        f = open('clock_skype_zTT.csv', 'w', encoding='utf-8', newline='')
        wr = csv.writer(f)
        wr.writerow(self.c0.clock_data)
        wr.writerow(self.c6.clock_data)
        wr.writerow(self.g.clock_data)
        f.close()

        f = open('fps_skype_zTT.csv', 'w', encoding='utf-8', newline='')
        wr = csv.writer(f)
        wr.writerow(self.fps_data)
        f.close()

        # Plot results
        fig = plt.figure(figsize=(12, 14))
        ax1 = fig.add_subplot(2, 2, 1)
        ax2 = fig.add_subplot(2, 2, 2)
        ax3 = fig.add_subplot(2, 2, 3)
        ax4 = fig.add_subplot(2, 2, 4)

        ax1.set_xlabel('time')
        ax1.set_ylabel('power(mw)')
        ax1.set_ylim(0, 1.1 * np.max(self.pl.power_data))
        ax1.grid(True)
        ax1.plot(ts, self.pl.power_data[1:], label='TOTAL')
        ax1.legend(loc='upper right')
        ax1.set_title('Power')

        ax2.set_xlabel('time')
        ax2.set_ylabel('temperature')
        ax2.grid(True)
        ax2.plot(ts, self.c0.temp_data, label='LITTLE')
        ax2.plot(ts, self.c6.temp_data, label='Big')
        ax2.plot(ts, self.g.temp_data, label='GPU')
        ax2.legend(loc='upper right')
        ax2.set_title('temperature')

        ax3.set_xlabel('time')
        ax3.set_ylabel('clock frequency(MHz)')
        ax3.set_ylim(0, 1.1 * np.max([np.max(self.c0.clock_data), np.max(self.c6.clock_data), np.max(self.g.clock_data)]))
        ax3.grid(True)
        ax3.plot(ts, self.c0.clock_data, label='LITTLE')
        ax3.plot(ts, self.c6.clock_data, label='Big')
        ax3.plot(ts, self.g.clock_data, label='GPU')
        ax3.legend(loc='upper right')
        ax3.set_title('clock')

        ax4.set_xlabel('time')
        ax4.set_ylabel('FPS')
        ax4.set_ylim(0, 1.1 * np.max([np.max(self.fps_data), self.target_fps]))
        ax4.grid(True)
        ax4.plot(ts, self.fps_data, label='Average FPS')
        ax4.axhline(y=self.target_fps, color='r', linewidth=1)
        ax4.legend(loc='upper right')
        ax4.set_title('fps')

        plt.tight_layout
        plt.show()


def parse_arguments():
    ''' 
    --app            Application name [showroom, skype, call]
    --exp_time         Time steps for learning
    --server_ip        Agent server IP
    --server_port    Agent server port
    --target_fps    Target FPS
    --pixel_ip        Pixel device IP for connecting device via adb
    '''
    parser = argparse.ArgumentParser()
    parser.add_argument('--app', type=str, required=True, choices=['showroom', 'skype', 'call', 'multi_dnn_profiler'],
		help="Application name for learning")
    parser.add_argument('--exp_time', type=int, default='300', help="Time steps for learning")
    parser.add_argument('--server_ip', type=str, required=True, help="Agent server IP")
    parser.add_argument('--server_port', type=int, default=8702, help="Agent server port number")
    parser.add_argument('--target_fps', type=int, required=True, help="Target FPS")
    parser.add_argument('--pixel_ip', type=str, required=True, help="Pixel device IP for connecting device via adb")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_arguments()
    client = Client(args.app, args.exp_time, args.server_ip, args.server_port, args.target_fps, args.pixel_ip)
    client.run()
    client.log_results()
