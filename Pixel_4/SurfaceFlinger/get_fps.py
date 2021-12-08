import time
import subprocess


nanoseconds_per_second = 1e9


def get_multi_dnn_profiler_fps(ip):
    out = subprocess.check_output(
        ['adb', '-s', ip, 'shell', 'cat', '/storage/emulated/0/Android/data/com.multi_dnn_profiler/files/frame_rate'])
    out = out.decode('utf-8')
    return float(out[1:-1].split('=')[1])


class SurfaceFlingerFPS():
    
    def __init__(self, view, ip):
        self.view = view
        self.ip = ip
        self.refresh_period, self.base_timestamp, self.timestamps = self.__init_frame_data__(self.view)
        self.recent_timestamps = self.timestamps[-2]
        self.fps = 0
        
    def __init_frame_data__(self, view):
        out = subprocess.check_output(['adb', '-s', self.ip, 'shell', 'dumpsys', 'SurfaceFlinger', '--latency-clear', view])
        out = out.decode('utf-8')
        if out.strip() != '':
            raise RuntimeError("Not supported.")
        (refresh_period, timestamps) = self.__frame_data__(view)
        base_timestamp = 0
        base_index = 0
        for timestamp in timestamps:
            if timestamp != 0:
                base_timestamp = timestamp
                break
            base_index += 1
        if base_timestamp == 0:
            raise RuntimeError("Initial frame collect failed")
        return (refresh_period, base_timestamp, timestamps[base_index:])


    def __frame_data__(self, view):
        out = subprocess.check_output(['adb', '-s', self.ip, 'shell', 'dumpsys', 'SurfaceFlinger', '--latency', view])
        out = out.decode('utf-8')
        results = out.splitlines()
        refresh_period = int(results[0]) / nanoseconds_per_second
        timestamps = []
        for line in results[1:]:
            fields = line.split()
            if len(fields) != 3:
                continue
            (start, submitting, submitted) = map(int, fields)
            if submitting == 0:
                continue

            timestamp = submitting / nanoseconds_per_second
            timestamps.append(timestamp)
        return (refresh_period, timestamps)

    def collect_frame_data(self,view):
        if view is None:
            raise RuntimeError("Fail to get current SurfaceFlinger view")

        self.refresh_period, self.timestamps = self.__frame_data__(view)
        time.sleep(1)
        self.refresh_period, tss = self.__frame_data__(view)
        self.last_index = 0
        if self.timestamps:
                self.recent_timestamp = self.timestamps[-2]
                self.last_index = tss.index(self.recent_timestamp)
        self.timestamps = self.timestamps[:-2] + tss[self.last_index:]
        
        ajusted_timestamps = []
        for seconds in self.timestamps[:]:
                seconds -= self.base_timestamp
                if seconds > 1e6: # too large, just ignore
                    continue
                ajusted_timestamps.append(seconds)

        from_time = ajusted_timestamps[-1] - 1.0
        fps_count = 0
        for seconds in ajusted_timestamps:
                if seconds > from_time:
                    fps_count += 1
        self.fps = fps_count
    
    def getFPS(self):
        self.collect_frame_data(self.view)
        return self.fps


if __name__ == '__main__':
    print(get_multi_dnn_profiler_fps('192.168.0.102:5555'))
