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
BACKGROUND_COLOR = (0, 0, 0)  # 背景颜色
DIGIT_COLOR = (200, 200, 200)  # 数字颜色
FRAME_COLOR = (50, 50, 50)  # 框架颜色
FRAME_PADDING = 10  # 框架填充
DIGIT_WIDTH, DIGIT_HEIGHT = 150, 200  # 数字宽度和高度
MARGIN = 20  # 间距
IP_INTERFACE = 'wlan0'  # 网络接口
HITOKOTO_API = 'https://v1.hitokoto.cn/'  # 一言API
WEATHER_API = 'https://api.vvhan.com/api/weather'  # 天气API
IMAGE_PATH = 'tkr.jpg'  # 图片路径
GOLD_PRICE_API = 'https://api.jinjia.com.cn/index.php?m=app&mi=0&cache=1'  # 金价API
GOLD_PRICE_STORE_API = 'https://api.jinjia.com.cn/index.php?m=app&a=brand&mi=0&cache=1'

# 初始化Pygame
pygame.init()
pygame.freetype.init()
FONT_PATH = 'SimHei.ttf'  # 字体路径
TIMES_NEW_ROMAN_PATH = 'times.ttf'  # Times New Roman字体路径


class FlipClock:
    def __init__(self):
        # 初始化Pygame显示窗口
        self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        self.width, self.height = self.screen.get_width(), self.screen.get_height()
        self.x_start = (self.width - 8 * DIGIT_WIDTH - 7 * MARGIN) // 2
        self.y_start = (self.height - DIGIT_HEIGHT) // 2 + 50

        # 加载字体
        self.fonts = self.load_fonts()

        # 用于缓存渲染的文本
        self.rendered_text_cache = {}
        pygame.display.set_caption('Flip Clock')

        # 隐藏鼠标指针
        pygame.mouse.set_visible(False)

        # 初始化变量
        self.old_data = self.init_old_data()

        # 记录上次绘制内容的矩形区域
        self.rects = self.init_rects()

        # 加载静态图片
        self.image = pygame.image.load(IMAGE_PATH)
        self.image = pygame.transform.scale(self.image, (250, 230))
        self.image_rect = self.image.get_rect()
        self.draw_image()

    def load_fonts(self):
        # 加载所有需要的字体
        return {
            'date': pygame.freetype.Font(FONT_PATH, 50),
            'time': pygame.freetype.Font(TIMES_NEW_ROMAN_PATH, 180),
            'lunar': pygame.freetype.Font(FONT_PATH, 30),
            'digit': pygame.freetype.Font(TIMES_NEW_ROMAN_PATH, 180),
            'ip': pygame.freetype.Font(TIMES_NEW_ROMAN_PATH, 30),
            'hitokoto': pygame.freetype.Font(FONT_PATH, 30),
            'usage': pygame.freetype.Font(TIMES_NEW_ROMAN_PATH, 30),
            'label': pygame.freetype.Font(TIMES_NEW_ROMAN_PATH, 20),
            'gold': pygame.freetype.Font(FONT_PATH, 30),
            'weather': pygame.freetype.Font(FONT_PATH, 30)
        }

    def init_old_data(self):
        # 初始化旧数据变量
        return {
            'time': "",
            'date': "",
            'lunar_date': "",
            'ip': "",
            'hitokoto': "",
            'cpu_usage': 0,
            'memory_usage': 0,
            'disk_usage': 0,
            'upload_speed': 0,
            'download_speed': 0,
            'cpu_temp': 0,
            'gold_price': "",
            'weather': ""
        }

    def init_rects(self):
        # 初始化矩形区域
        return {
            "date": None,
            "lunar_date": None,
            "hitokoto": None,
            "time": None,
            "usage": None,
            "network": None,
            "gold_price": None,
            "weather": None
        }

    def draw_flip_clock(self, data):
        dirty_rects = []
        self.update_text(data, 'date', dirty_rects, self.fonts['date'], (self.width // 2, self.height // 4 - 150))
        self.update_text(data, 'lunar_date', dirty_rects, self.fonts['lunar'], (self.width // 2, self.height // 4 - 100))
        self.update_text(data, 'hitokoto', dirty_rects, self.fonts['hitokoto'], (self.width // 2, self.height // 4))
        self.update_flip_time(data, dirty_rects)
        self.update_usage_circles(data, dirty_rects)
        self.update_network_info(data, dirty_rects)
        self.update_text(data, 'gold_price', dirty_rects, self.fonts['gold'], (30, self.height - 200), alignment='left')
        self.update_text(data, 'weather', dirty_rects, self.fonts['weather'], (self.width-250, 80), wrapped=True, max_width=200)
        return dirty_rects


    def update_text(self, data, key, dirty_rects, font, position, wrapped=False, max_width=None, alignment='center'):
        # 更新文本信息
        if data[key] != self.old_data[key]:
            if self.rects[key]:
                self.clear_rect(self.rects[key])
            if wrapped:
                self.rects[key] = self.render_wrapped_text(font, data[key], position, max_width, alignment)
            else:
                self.rects[key] = self.render_text(font, data[key], position, alignment)
            dirty_rects.append(self.rects[key])
            self.old_data[key] = data[key]

    def update_flip_time(self, data, dirty_rects):
        # 更新翻页时钟
        if data['time'] and (data['time'] != self.old_data['time']):
            if self.rects['time']:
                self.clear_rect(self.rects['time'])
            self.rects['time'] = self.render_flip_numbers(data['time'])
            dirty_rects.append(self.rects['time'])
            self.old_data['time'] = data['time']

    def update_usage_circles(self, data, dirty_rects):
        # 更新系统使用率的圆环
        if any(data[key] != self.old_data[key] for key in ['cpu_usage', 'memory_usage', 'disk_usage', 'cpu_temp']):
            if self.rects['usage']:
                self.clear_rect(self.rects['usage'])
            self.rects['usage'] = self.draw_usage_circles(data['cpu_usage'], data['memory_usage'], data['disk_usage'], data['cpu_temp'])
            dirty_rects.append(self.rects['usage'])
            for key in ['cpu_usage', 'memory_usage', 'disk_usage', 'cpu_temp']:
                self.old_data[key] = data[key]

    def update_network_info(self, data, dirty_rects):
        # 更新网络信息
        if any(data[key] != self.old_data[key] for key in ['ip', 'upload_speed', 'download_speed']):
            if self.rects['network']:
                self.clear_rect(self.rects['network'])
            self.rects['network'] = self.draw_network_info(data['ip'], data['upload_speed'], data['download_speed'], (self.width // 2, self.height - 50))
            dirty_rects.append(self.rects['network'])
            for key in ['ip', 'upload_speed', 'download_speed']:
                self.old_data[key] = data[key]

    def clear_rect(self, rect):
        # 清除矩形区域
        pygame.draw.rect(self.screen, BACKGROUND_COLOR, rect.inflate(10, 10))

    def render_text(self, font, text, position, alignment='center'):
        lines = text.split('\n')
        y_offset = 0
        max_width = 0
        rects = []
        for line in lines:
            surface, rect = self.get_rendered_text(font, line, (255, 255, 255))
            
            if alignment == 'left':
                rect.topleft = (position[0], position[1] + y_offset)
            elif alignment == 'center':
                rect.midtop = (position[0], position[1] + y_offset)
            elif alignment == 'right':
                rect.topright = (position[0], position[1] + y_offset)
            self.screen.blit(surface, rect)
            y_offset += rect.height
            max_width = max(max_width, rect.width)
            rects.append(rect)
        
        # Calculate the bounding rect for all lines
        bounding_rect = pygame.Rect(position[0] - max_width // 2, position[1], max_width, y_offset)

        return bounding_rect

    def render_wrapped_text(self, font, text, position, max_width, alignment='left'):
        # 渲染自动换行的文本
        lines = self.wrap_text(font, text, max_width)
        x, y = position
        total_height = sum([font.get_sized_height() for line in lines])
        y = total_height
        rects = []

        for line in lines:
            surface, rect = font.render(line, (255, 255, 255))
            if alignment == 'center':
                rect.centerx = x
            elif alignment == 'right':
                rect.right = x + max_width // 2
            elif alignment == 'left':
                rect.left = x - max_width // 2
            rect.top = y
            self.screen.blit(surface, rect)
            rects.append(rect)
            y += font.get_sized_height()

        return pygame.Rect(x - max_width // 2, y - total_height, max_width, total_height)

    def wrap_text(self, font, text, max_width):
        # 自动换行处理
        words = text.split()
        lines = []
        current_line = []

        for word in words:
            current_line.append(word)
            line_width, _ = font.get_rect(' '.join(current_line)).size
            if line_width > max_width:
                current_line.pop()
                lines.append(' '.join(current_line))
                current_line = [word]

        if current_line:
            lines.append(' '.join(current_line))

        return lines

    def render_flip_numbers(self, current_time):
        # 渲染翻页时钟数字
        flip_rect = pygame.Rect(self.x_start - 10, self.y_start - FRAME_PADDING - 10, 8 * DIGIT_WIDTH + 7 * MARGIN + 20, DIGIT_HEIGHT + 2 * FRAME_PADDING + 20)
        for i, char in enumerate(current_time):
            rect_x = self.x_start + i * (DIGIT_WIDTH + MARGIN)
            if char.isdigit():
                # 绘制背景框
                pygame.draw.rect(self.screen, FRAME_COLOR, (rect_x, self.y_start - FRAME_PADDING, DIGIT_WIDTH, DIGIT_HEIGHT + 2 * FRAME_PADDING), border_radius=10)
                # 绘制数字
                digit_surface, digit_rect = self.get_rendered_text(self.fonts['digit'], char, DIGIT_COLOR)
                digit_rect.center = (rect_x + DIGIT_WIDTH // 2, self.y_start + DIGIT_HEIGHT // 2)
            else:
                # 绘制冒号，不加背景框
                digit_surface, digit_rect = self.get_rendered_text(self.fonts['digit'], char, DIGIT_COLOR)
                digit_rect.center = (rect_x + DIGIT_WIDTH // 2, self.y_start + DIGIT_HEIGHT // 2)
            self.screen.blit(digit_surface, digit_rect)
        return flip_rect

    def get_rendered_text(self, font, text, color):
        # 如果文本未缓存，则渲染并缓存
        if text not in self.rendered_text_cache:
            self.rendered_text_cache[text] = font.render(text, color)
        return self.rendered_text_cache[text]

    def draw_usage_circles(self, cpu_usage, memory_usage, disk_usage, cpu_temp):
        # 绘制系统使用率的圆环
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
        self.render_text(self.fonts['label'], label, (x, y - 20))

        # 绘制使用率文本
        usage_text = f"{int(usage)}%"
        self.render_text(self.fonts['usage'], usage_text, (x, y + 10))

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
        self.render_text(self.fonts['label'], label, (x, y - 20))

        # 绘制温度文本
        temp_text = f"{int(temp)}°C"
        self.render_text(self.fonts['usage'], temp_text, (x, y + 10))

    def draw_network_info(self, ip_address, upload_speed, download_speed, position):
        # 绘制网络信息
        x, y = position
        ip_surface, ip_rect = self.get_rendered_text(self.fonts['ip'], f"IP: {ip_address}", (255, 255, 255))
        
        up_arrow = "↑"
        down_arrow = "↓"

        up_surface, up_rect = self.get_rendered_text(self.fonts['ip'], f"{up_arrow} {upload_speed:.2f} Mbps", (0, 255, 0))
        down_surface, down_rect = self.get_rendered_text(self.fonts['ip'], f"{down_arrow} {download_speed:.2f} Mbps", (255, 0, 0))

        total_width = ip_rect.width + up_rect.width + down_rect.width + 40

        ip_x = x - total_width // 2
        up_x = ip_x + ip_rect.width + 20
        down_x = up_x + up_rect.width + 20

        self.screen.blit(ip_surface, (ip_x, y - ip_rect.height // 2))
        self.screen.blit(up_surface, (up_x, y - up_rect.height // 2))
        self.screen.blit(down_surface, (down_x, y - down_rect.height // 2))
        return pygame.Rect(ip_x, y - ip_rect.height // 2, total_width, max(ip_rect.height, up_rect.height, down_rect.height))

    def draw_image(self):
        # 绘制静态图片在右下角
        self.image_rect.bottomright = (self.width - 10, self.height - 10)
        self.screen.blit(self.image, self.image_rect)


class Utils:
    @staticmethod
    def gold_price_zh():
        # 实时金价
        msg = ''
        try:
            resp = requests.get(GOLD_PRICE_API).json()
            gn = resp['gn'][0]
            price = gn['price']
            changepercent = gn['changepercent']
            msg = f">> 国内金价: {price}元/g({changepercent})"
        except Exception:
            pass
        return msg

    
    @staticmethod
    def gold_price_store(num=1):
        # 实时金价
        msg = ''
        try:
            resp = requests.get(GOLD_PRICE_STORE_API).json()
            for i in range(num):
                brand = resp['brand'][i]
                title = brand['title']
                gold = brand['gold']
                msg += f">> {title}: {gold}元/g\n"
        except Exception:
            pass
        return msg.strip()
    
    
    @staticmethod
    def get_time_strings():
        # 获取当前时间
        now = time.localtime()
        return time.strftime('%H:%M:%S', now)

    @staticmethod
    def get_date_strings():
        # 获取当前日期和农历日期
        now = time.localtime()
        current_date = time.strftime('%Y-%m-%d %A', now)

        # 转换为农历日期
        solar = Solar(now.tm_year, now.tm_mon, now.tm_mday)
        lunar = Converter.Solar2Lunar(solar)
        lunar_date = f"农历 {lunar.year}年{lunar.month}月{lunar.day}日"
        return current_date, lunar_date

    @staticmethod
    def get_ip_address(interface):
        # 获取指定网络接口的IP地址
        try:
            addrs = psutil.net_if_addrs()
            return [addr.address for addr in addrs[interface] if addr.family == 2][0]
        except Exception:
            return "IP获取失败"

    @staticmethod
    def get_hitokoto():
        # 从API获取一言
        try:
            response = requests.get(HITOKOTO_API)
            if response.status_code == 200:
                data = response.json()
                return f"{data.get('hitokoto', '')} —— {data.get('from', '')}"
            else:
                return "无法获取一言"
        except Exception:
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

    @staticmethod
    def get_gold_price():
        # 获取实时金价
        try:
            price_zh = Utils.gold_price_zh()
            price_store = Utils.gold_price_store(num=4)
            return price_zh+'\n'+price_store
        except Exception as e:
            print(e)
            return "<金价获取失败>"

    @staticmethod
    def get_weather():
        # 获取天气信息
        try:
            response = requests.get(WEATHER_API)
            if response.status_code == 200:
                data = response.json()
                if data['success']:
                    weather = data['data']
                    return f"{weather['type']} {weather['low']}~{weather['high']}\n{data['tip']}"
                else:
                    return "无法获取天气"
            else:
                return "无法获取天气"
        except Exception:
            return "天气获取失败"


def fetch_data(data_queue):
    # 初始化数据
    data = {
        'hitokoto': Utils.get_hitokoto(),
        'date': Utils.get_date_strings()[0],
        'lunar_date': Utils.get_date_strings()[1],
        'ip': Utils.get_ip_address(IP_INTERFACE),
        'gold_price': Utils.get_gold_price(),
        'weather': Utils.get_weather()
    }

    for key, value in data.items():
        data_queue.put((key, value))

    timers = {
        'hitokoto': time.time(),
        'date': time.time(),
        'ip': time.time(),
        'gold_price': time.time(),
        'weather': time.time()
    }

    while True:
        # 更新一言
        if time.time() - timers['hitokoto'] >= 10:
            data_queue.put(('hitokoto', Utils.get_hitokoto()))
            timers['hitokoto'] = time.time()

        # 更新日期和农历日期
        if time.time() - timers['date'] >= 60:
            current_date, lunar_date = Utils.get_date_strings()
            data_queue.put(('date', current_date))
            data_queue.put(('lunar_date', lunar_date))
            timers['date'] = time.time()

        # 更新IP地址
        if time.time() - timers['ip'] >= 5:
            data_queue.put(('ip', Utils.get_ip_address(IP_INTERFACE)))
            timers['ip'] = time.time()

        # 更新金价
        if time.time() - timers['gold_price'] >= 60:
            data_queue.put(('gold_price', Utils.get_gold_price()))
            timers['gold_price'] = time.time()

        # 更新天气信息
        if time.time() - timers['weather'] >= 1800:  # 更新天气信息的时间间隔为30分钟
            data_queue.put(('weather', Utils.get_weather()))
            timers['weather'] = time.time()

        # 获取网络速度
        upload_speed, download_speed = Utils.get_network_speed(IP_INTERFACE)
        data_queue.put(('upload_speed', upload_speed))
        data_queue.put(('download_speed', download_speed))

        # 获取系统使用率
        cpu_usage, memory_usage, disk_usage = Utils.get_system_usage()
        data_queue.put(('cpu_usage', cpu_usage))
        data_queue.put(('memory_usage', memory_usage))
        data_queue.put(('disk_usage', disk_usage))

        # 获取CPU温度
        data_queue.put(('cpu_temp', Utils.get_cpu_temp()))

        time.sleep(1)


def main():
    clock = pygame.time.Clock()
    flip_clock = FlipClock()
    running = True

    # 创建数据队列和线程
    data_queue = queue.Queue()
    data_thread = threading.Thread(target=fetch_data, args=(data_queue,), daemon=True)
    data_thread.start()

    # 初始化数据
    data = {
        'ip': " ",
        'hitokoto': " ",
        'upload_speed': 0.0,
        'download_speed': 0.0,
        'cpu_temp': 0.0,
        'cpu_usage': 0.0,
        'memory_usage': 0.0,
        'disk_usage': 0.0,
        'date': " ",
        'lunar_date': " ",
        'gold_price': " ",
        'weather': " "
    }

    while running:
        # 事件处理
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                running = False

        # 更新数据队列中的数据
        while not data_queue.empty():
            key, value = data_queue.get()
            data[key] = value

        # 获取当前时间
        data['time'] = Utils.get_time_strings()
        dirty_rects = flip_clock.draw_flip_clock(data)
        pygame.display.update(dirty_rects)
        clock.tick(30)

    pygame.quit()


if __name__ == '__main__':
    main()
