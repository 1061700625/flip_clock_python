import pygame
import pygame.freetype
import time
import locale
import psutil
import requests
from lunarcalendar import Converter, Solar
import os
import math
import threading
import queue

# 设置中国时间和语言环境
locale.setlocale(locale.LC_TIME, 'zh_CN.utf8')

# 常量定义
BACKGROUND_COLOR = (0, 0, 0)
DIGIT_COLOR = (200, 200, 200)
FRAME_COLOR = (50, 50, 50)
FRAME_PADDING = 10
DIGIT_WIDTH, DIGIT_HEIGHT = 150, 200
MARGIN = 20
IP_INTERFACE = 'wlan0'
HITOKOTO_API = 'https://v1.hitokoto.cn/'

# 初始化Pygame
pygame.init()
pygame.freetype.init()
FONT_PATH = 'SimHei.ttf'
TIMES_NEW_ROMAN_PATH = 'times.ttf'  # 需要确保系统中存在Times New Roman字体文件

class FlipClock:
    def __init__(self):
        # 初始化Pygame显示窗口
        self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        self.width, self.height = self.screen.get_width(), self.screen.get_height()
        self.x_start = (self.width - 8 * DIGIT_WIDTH - 7 * MARGIN) // 2
        self.y_start = (self.height - DIGIT_HEIGHT) // 2 + 50

        # 加载字体
        self.date_font = pygame.freetype.Font(FONT_PATH, 50)
        self.time_font = pygame.freetype.Font(TIMES_NEW_ROMAN_PATH, 180)
        self.lunar_font = pygame.freetype.Font(FONT_PATH, 30)
        self.digit_font = pygame.freetype.Font(TIMES_NEW_ROMAN_PATH, 180)
        self.ip_font = pygame.freetype.Font(TIMES_NEW_ROMAN_PATH, 30)
        self.hitokoto_font = pygame.freetype.Font(FONT_PATH, 30)
        self.usage_font = pygame.freetype.Font(TIMES_NEW_ROMAN_PATH, 30)
        self.label_font = pygame.freetype.Font(TIMES_NEW_ROMAN_PATH, 20)

        # 用于缓存渲染的文本
        self.rendered_text_cache = {}
        pygame.display.set_caption('Flip Clock with Date, Day, Lunar Calendar, and IP')

        # 隐藏鼠标指针
        pygame.mouse.set_visible(False)

        # 初始变量
        self.old_time = ""
        self.old_date = ""
        self.old_lunar_date = ""
        self.old_ip = ""
        self.old_hitokoto = ""
        self.old_cpu_usage = 0
        self.old_memory_usage = 0
        self.old_disk_usage = 0
        self.old_upload_speed = 0
        self.old_download_speed = 0
        self.old_cpu_temp = 0

        # 记录上次绘制内容的矩形区域
        self.rects = {
            "date": None,
            "lunar_date": None,
            "hitokoto": None,
            "time": None,
            "usage": None,
            "network": None
        }

    def draw_flip_clock(self, current_time, current_date, lunar_date, ip_address, hitokoto, cpu_usage, memory_usage, disk_usage, upload_speed, download_speed, cpu_temp):
        dirty_rects = []

        # 比较并更新公历日期和星期几
        if current_date != self.old_date:
            if self.rects["date"]:
                self.clear_rect(self.rects["date"])
            self.rects["date"] = self.render_text(self.date_font, current_date, (self.width // 2, self.height // 4 - 150))
            dirty_rects.append(self.rects["date"])
            self.old_date = current_date

        # 比较并更新农历日期
        if lunar_date != self.old_lunar_date:
            if self.rects["lunar_date"]:
                self.clear_rect(self.rects["lunar_date"])
            self.rects["lunar_date"] = self.render_text(self.lunar_font, lunar_date, (self.width // 2, self.height // 4 - 100))
            dirty_rects.append(self.rects["lunar_date"])
            self.old_lunar_date = lunar_date

        # 比较并更新一言
        if hitokoto != self.old_hitokoto:
            if self.rects["hitokoto"]:
                self.clear_rect(self.rects["hitokoto"])
            self.rects["hitokoto"] = self.render_text(self.hitokoto_font, hitokoto, (self.width // 2, self.height // 4))
            dirty_rects.append(self.rects["hitokoto"])
            self.old_hitokoto = hitokoto

        # 比较并更新翻页时钟
        if current_time != self.old_time:
            if self.rects["time"]:
                self.clear_rect(self.rects["time"])
            self.rects["time"] = self.render_flip_numbers(current_time)
            dirty_rects.append(self.rects["time"])
            self.old_time = current_time

        # 比较并更新CPU、内存和磁盘使用率的圆环
        if (cpu_usage != self.old_cpu_usage or
            memory_usage != self.old_memory_usage or
            disk_usage != self.old_disk_usage or
            cpu_temp != self.old_cpu_temp):
            if self.rects["usage"]:
                self.clear_rect(self.rects["usage"])
            self.rects["usage"] = self.draw_usage_circles(cpu_usage, memory_usage, disk_usage, cpu_temp)
            dirty_rects.append(self.rects["usage"])
            self.old_cpu_usage = cpu_usage
            self.old_memory_usage = memory_usage
            self.old_disk_usage = disk_usage
            self.old_cpu_temp = cpu_temp

        # 比较并更新IP地址和网络速度
        if (ip_address != self.old_ip or
            upload_speed != self.old_upload_speed or
            download_speed != self.old_download_speed):
            if self.rects["network"]:
                self.clear_rect(self.rects["network"])
            self.rects["network"] = self.draw_network_info(ip_address, upload_speed, download_speed, (self.width // 2, self.height - 50))
            dirty_rects.append(self.rects["network"])
            self.old_ip = ip_address
            self.old_upload_speed = upload_speed
            self.old_download_speed = download_speed

        return dirty_rects

    def clear_rect(self, rect):
        pygame.draw.rect(self.screen, BACKGROUND_COLOR, rect)

    def render_text(self, font, text, position):
        # 获取渲染的文本，如果不存在则创建并缓存
        surface, rect = self.get_rendered_text(font, text, (255, 255, 255))
        rect.center = position
        self.screen.blit(surface, rect)
        return rect

    def render_flip_numbers(self, current_time):
        flip_rect = pygame.Rect(self.x_start - 10, self.y_start - FRAME_PADDING - 10, 8 * DIGIT_WIDTH + 7 * MARGIN + 20, DIGIT_HEIGHT + 2 * FRAME_PADDING + 20)
        for i, char in enumerate(current_time):
            rect_x = self.x_start + i * (DIGIT_WIDTH + MARGIN)
            if char.isdigit():
                # 绘制背景框
                pygame.draw.rect(self.screen, FRAME_COLOR, (rect_x, self.y_start - FRAME_PADDING, DIGIT_WIDTH, DIGIT_HEIGHT + 2 * FRAME_PADDING), border_radius=10)
                # 绘制数字
                digit_surface, digit_rect = self.get_rendered_text(self.digit_font, char, DIGIT_COLOR)
                digit_rect.center = (rect_x + DIGIT_WIDTH // 2, self.y_start + DIGIT_HEIGHT // 2)
            else:
                # 绘制冒号，不加背景框
                digit_surface, digit_rect = self.get_rendered_text(self.digit_font, char, DIGIT_COLOR)
                digit_rect.center = (rect_x + DIGIT_WIDTH // 2, self.y_start + DIGIT_HEIGHT // 2)
            self.screen.blit(digit_surface, digit_rect)
        return flip_rect

    def get_rendered_text(self, font, text, color):
        # 如果文本未缓存，则渲染并缓存
        if text not in self.rendered_text_cache:
            self.rendered_text_cache[text] = font.render(text, color)
        return self.rendered_text_cache[text]

    def draw_usage_circles(self, cpu_usage, memory_usage, disk_usage, cpu_temp):
        usage_rect = pygame.Rect(self.width // 2 - 270, self.height - 200, 540, 120)
        total_width = 4 * 120  # 每个圆环和标签的总宽度，包括间距
        start_x = (self.width - total_width) // 2 + 60  # 向右移动半个圆环的距离
        y = self.height - 140
        
        self.draw_usage_circle(start_x, y, cpu_usage, "CPU", (0, 255, 0))
        self.draw_usage_circle(start_x + 120, y, memory_usage, "MEM", (0, 255, 0))
        self.draw_usage_circle(start_x + 240, y, disk_usage, "DISK", (0, 255, 0))
        self.draw_temp_circle(start_x + 360, y, cpu_temp, "TEMP", (255, 0, 0))
        return usage_rect

    def draw_usage_circle(self, x, y, usage, label, color):
        # 绘制使用率圆环
        radius = 50
        thickness = 10
        start_angle = 0
        end_angle = 360 * (usage / 100)

        # 绘制背景圆环
        pygame.draw.circle(self.screen, (100, 100, 100), (x, y), radius, thickness)

        # 绘制前景圆环
        pygame.draw.arc(self.screen, color, 
                        (x - radius, y - radius, 2 * radius, 2 * radius), 
                        math.radians(start_angle), math.radians(end_angle), thickness)

        # 绘制标签文本在圆环的上方
        self.render_text(self.label_font, label, (x, y - 20))

        # 绘制使用率文本
        usage_text = f"{int(usage)}%"
        self.render_text(self.usage_font, usage_text, (x, y + 10))

    def draw_temp_circle(self, x, y, temp, label, color):
        # 绘制温度圆环
        radius = 50
        thickness = 10
        start_angle = 0
        end_angle = 360 * (temp / 100)  # 假设最大温度为100°C

        # 绘制背景圆环
        pygame.draw.circle(self.screen, (100, 100, 100), (x, y), radius, thickness)

        # 绘制前景圆环
        pygame.draw.arc(self.screen, color, 
                        (x - radius, y - radius, 2 * radius, 2 * radius), 
                        math.radians(start_angle), math.radians(end_angle), thickness)

        # 绘制标签文本在圆环的上方
        self.render_text(self.label_font, label, (x, y - 20))

        # 绘制温度文本
        temp_text = f"{int(temp)}°C"
        self.render_text(self.usage_font, temp_text, (x, y + 10))

    def draw_network_info(self, ip_address, upload_speed, download_speed, position):
        x, y = position
        ip_surface, ip_rect = self.get_rendered_text(self.ip_font, f"IP: {ip_address}", (255, 255, 255))
        
        up_arrow = "↑"
        down_arrow = "↓"

        up_surface, up_rect = self.get_rendered_text(self.ip_font, f"{up_arrow} {upload_speed:.2f} Mbps", (0, 255, 0))
        down_surface, down_rect = self.get_rendered_text(self.ip_font, f"{down_arrow} {download_speed:.2f} Mbps", (255, 0, 0))

        total_width = ip_rect.width + up_rect.width + down_rect.width + 40

        ip_x = x - total_width // 2
        up_x = ip_x + ip_rect.width + 20
        down_x = up_x + up_rect.width + 20

        self.screen.blit(ip_surface, (ip_x, y - ip_rect.height // 2))
        self.screen.blit(up_surface, (up_x, y - up_rect.height // 2))
        self.screen.blit(down_surface, (down_x, y - down_rect.height // 2))
        return pygame.Rect(ip_x, y - ip_rect.height // 2, total_width, max(ip_rect.height, up_rect.height, down_rect.height))

class Utils:
    @staticmethod
    def get_time_strings():
        # 获取当前时间和日期
        now = time.localtime()
        current_time = time.strftime('%H:%M:%S', now)
        current_date = time.strftime('%Y-%m-%d %A', now)

        # 转换为农历日期
        solar = Solar(now.tm_year, now.tm_mon, now.tm_mday)
        lunar = Converter.Solar2Lunar(solar)
        lunar_date = f"农历 {lunar.year}年{lunar.month}月{lunar.day}日"
        return current_time, current_date, lunar_date

    @staticmethod
    def get_ip_address(interface):
        # 获取指定网络接口的IP地址
        try:
            addrs = psutil.net_if_addrs()
            ip_address = [addr.address for addr in addrs[interface] if addr.family == 2][0]
            return ip_address
        except Exception:
            return "IP获取失败"

    @staticmethod
    def get_hitokoto():
        # 从API获取一言
        try:
            response = requests.get(HITOKOTO_API)
            if response.status_code == 200:
                data = response.json()
                hitokoto = data.get('hitokoto', '')
                from_source = data.get('from', '')
                return f"{hitokoto} —— {from_source}"
            else:
                return "无法获取一言"
        except Exception as e:
            return "一言获取失败"

    @staticmethod
    def get_system_usage():
        # 获取系统CPU、内存和磁盘使用率
        cpu_usage = psutil.cpu_percent(interval=1)
        memory_info = psutil.virtual_memory()
        memory_usage = memory_info.percent
        disk_usage = psutil.disk_usage('/').percent
        return cpu_usage, memory_usage, disk_usage

    @staticmethod
    def get_network_speed(interface):
        # 获取网络接口的上行和下行速度
        net_io = psutil.net_io_counters(pernic=True)
        upload_speed = net_io[interface].bytes_sent
        download_speed = net_io[interface].bytes_recv
        time.sleep(0.1)
        net_io = psutil.net_io_counters(pernic=True)
        upload_speed = (net_io[interface].bytes_sent - upload_speed) * 8 / 1e6
        download_speed = (net_io[interface].bytes_recv - download_speed) * 8 / 1e6
        return upload_speed, download_speed

    @staticmethod
    def get_cpu_temp():
        # 获取CPU温度
        temp_file = '/sys/class/thermal/thermal_zone0/temp'
        try:
            with open(temp_file, 'r') as f:
                temp = f.read()
                return int(temp) / 1000  # 假设读取到的温度值是毫摄氏度，需要转换为摄氏度
        except:
            return 0

def fetch_data(data_queue):
    # 初始化一言
    hitokoto = Utils.get_hitokoto()
    data_queue.put(('hitokoto', hitokoto))
    hitokoto_timer = time.time()

    while True:
        # 每10秒更新一次一言
        if time.time() - hitokoto_timer >= 10:
            hitokoto = Utils.get_hitokoto()
            data_queue.put(('hitokoto', hitokoto))
            hitokoto_timer = time.time()

        # 获取IP地址
        ip_address = Utils.get_ip_address(IP_INTERFACE)
        data_queue.put(('ip', ip_address))

        # 每1秒更新一次网络速度
        upload_speed, download_speed = Utils.get_network_speed(IP_INTERFACE)
        data_queue.put(('network_speed', (upload_speed, download_speed)))

        # 获取CPU温度
        cpu_temp = Utils.get_cpu_temp()
        data_queue.put(('cpu_temp', cpu_temp))

        time.sleep(1)

def main():
    clock = pygame.time.Clock()
    flip_clock = FlipClock()
    running = True

    # 创建数据队列和线程
    data_queue = queue.Queue()
    data_thread = threading.Thread(target=fetch_data, args=(data_queue,))
    data_thread.daemon = True
    data_thread.start()

    # 初始化系统使用率
    cpu_usage, memory_usage, disk_usage = Utils.get_system_usage()
    system_usage_timer = time.time()

    while running:
        # 事件处理
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                running = False

        # 获取当前时间、日期和IP地址
        current_time, current_date, lunar_date = Utils.get_time_strings()

        # 更新数据队列中的数据
        while not data_queue.empty():
            key, value = data_queue.get()
            if key == 'hitokoto':
                hitokoto = value
            elif key == 'ip':
                ip_address = value
            elif key == 'network_speed':
                upload_speed, download_speed = value
            elif key == 'cpu_temp':
                cpu_temp = value

        # 每1秒更新一次系统使用率
        if time.time() - system_usage_timer >= 1:
            cpu_usage, memory_usage, disk_usage = Utils.get_system_usage()
            system_usage_timer = time.time()

        # 绘制翻页时钟
        dirty_rects = flip_clock.draw_flip_clock(current_time, current_date, lunar_date, ip_address, hitokoto, cpu_usage, memory_usage, disk_usage, upload_speed, download_speed, cpu_temp)

        # 更新显示，仅更新脏矩形区域
        pygame.display.update(dirty_rects)

        # 控制帧率
        clock.tick(30)

    pygame.quit()

if __name__ == '__main__':
    main()
