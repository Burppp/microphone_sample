#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
串口数据接收和频率分析脚本
功能：
1. 接收串口数据（uint16格式）
2. 实时频率分析
3. 保存为CSV文件
4. 生成频谱图
"""

import sys
import os
import csv
import time
import threading
from datetime import datetime
from collections import deque

import numpy as np
import serial
import serial.tools.list_ports
from scipy import signal
from scipy.fft import fft, fftfreq
import tkinter as tk
from tkinter import ttk, messagebox

class SerialDataReceiver:
    """串口数据接收器"""
    
    def __init__(self, port, baudrate=115200, data_format='uint16_t', byteorder='little'):
        self.port = port
        self.baudrate = baudrate
        self.data_format = data_format
        self.byteorder = byteorder
        self.serial = None
        self.running = False
        self.data_buffer = deque(maxlen=10000)  # 数据缓冲区
        self.timestamps = deque(maxlen=10000)   # 时间戳缓冲区
        
        # 频率分析参数
        self.sample_rate = 8000  # 默认采样率
        self.fft_size = 1024     # FFT大小
        self.window_length = 256  # 窗口长度
        
        # 统计信息
        self.total_samples = 0
        self.start_time = None
        self.calculated_sample_rate = 0  # 计算得出的采样率
        
    def connect(self):
        """连接串口"""
        try:
            self.serial = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=1
            )
            self.running = True
            self.start_time = time.time()
            print(f"已连接到串口 {self.port}")
            return True
        except Exception as e:
            print(f"连接串口失败: {e}")
            return False
    
    def disconnect(self):
        """断开串口连接"""
        self.running = False
        if self.serial and self.serial.is_open:
            try:
                self.serial.close()
            except Exception as e:
                print(f"关闭串口时出错: {e}")
    
    def receive_data(self):
        """接收数据线程"""
        while self.running:
            try:
                if self.serial and self.serial.in_waiting:
                    if self.data_format == 'uint16_t':
                        # uint16_t模式：每两个字节解析为一个uint16_t
                        if self.serial.in_waiting >= 2:
                            # 读取两个字节
                            byte1 = self.serial.read(1)
                            byte2 = self.serial.read(1)
                            
                            if len(byte1) == 1 and len(byte2) == 1:
                                # 组合为16位无符号整数
                                uint16_value = int.from_bytes(byte1 + byte2, 
                                                            byteorder=self.byteorder, 
                                                            signed=False)
                                
                                # 记录时间戳和数据
                                timestamp = time.time()
                                self.data_buffer.append(uint16_value)
                                self.timestamps.append(timestamp)
                                self.total_samples += 1
                                
                                # 每1000个样本打印一次统计信息
                                if self.total_samples % 1000 == 0:
                                    elapsed_time = timestamp - self.start_time
                                    sample_rate = self.total_samples / elapsed_time
                                    calculated_rate = self.calculate_sample_rate()
                                    print(f"已接收 {self.total_samples} 个样本, "
                                          f"平均采样率: {sample_rate:.1f} Hz, "
                                          f"计算采样率: {calculated_rate:.1f} Hz")
                    
            except Exception as e:
                print(f"接收数据时出错: {e}")
                break
    
    def get_recent_data(self, num_samples=1000):
        """获取最近的数据"""
        if len(self.data_buffer) < num_samples:
            return list(self.data_buffer), list(self.timestamps)
        else:
            return list(self.data_buffer)[-num_samples:], list(self.timestamps)[-num_samples:]
    
    def analyze_frequency(self, data):
        """频率分析"""
        if len(data) < self.fft_size:
            return None, None, None
        
        # 去除均值
        data = np.array(data) - np.mean(data)
        
        # 应用窗函数
        window = np.hanning(len(data))
        data_windowed = data * window
        
        # 计算FFT
        fft_result = fft(data_windowed, self.fft_size)
        frequencies = fftfreq(self.fft_size, 1/self.sample_rate)
        
        # 计算功率谱密度
        power_spectrum = np.abs(fft_result)**2
        
        # 只取正频率部分
        positive_freq_mask = frequencies >= 0
        frequencies = frequencies[positive_freq_mask]
        power_spectrum = power_spectrum[positive_freq_mask]
        
        return frequencies, power_spectrum, data
    
    def save_to_csv(self, filename):
        """保存数据到CSV文件"""
        try:
            # 创建数据副本，避免deque迭代错误
            data_list = list(self.data_buffer)
            timestamps_list = list(self.timestamps)
            
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                
                # 写入表头
                writer.writerow(['时间戳', '数值'])
                
                # 写入数据
                for timestamp, value in zip(timestamps_list, data_list):
                    writer.writerow([timestamp, value])
            
            print(f"数据已保存到: {filename}")
            return True
        except Exception as e:
            print(f"保存CSV文件时出错: {e}")
            return False

    def calculate_sample_rate(self):
        """计算实际采样率"""
        if len(self.timestamps) < 2:
            return 0
        
        # 计算时间间隔
        time_diffs = []
        for i in range(1, len(self.timestamps)):
            time_diff = self.timestamps[i] - self.timestamps[i-1]
            if time_diff > 0:  # 避免零间隔
                time_diffs.append(time_diff)
        
        if not time_diffs:
            return 0
        
        # 计算平均时间间隔
        avg_time_diff = np.mean(time_diffs)
        
        # 计算采样率
        if avg_time_diff > 0:
            sample_rate = 1.0 / avg_time_diff
            self.calculated_sample_rate = sample_rate
            return sample_rate
        
        return 0
    
    def get_statistics(self):
        """获取统计信息"""
        stats = {
            'total_samples': self.total_samples,
            'buffer_size': len(self.data_buffer),
            'calculated_sample_rate': self.calculate_sample_rate(),
            'elapsed_time': 0,
            'data_range': (0, 0)
        }
        
        if self.start_time:
            stats['elapsed_time'] = time.time() - self.start_time
        
        if self.data_buffer:
            stats['data_range'] = (min(self.data_buffer), max(self.data_buffer))
        
        return stats

class FrequencyAnalyzerGUI:
    """频率分析GUI界面"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("串口数据接收")
        self.root.geometry("1000x600")
        
        # 串口接收器
        self.receiver = None
        self.receive_thread = None
        
        # 数据缓冲区
        self.data_buffer = deque(maxlen=10000)
        self.timestamps = deque(maxlen=10000)
        
        # 创建界面
        self.create_widgets()
        
        # 启动数据更新定时器
        self.update_timer()
    
    def create_widgets(self):
        """创建界面组件"""
        # 主框架
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 左侧控制面板
        control_frame = ttk.LabelFrame(main_frame, text="控制面板")
        control_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        
        # 串口设置
        ttk.Label(control_frame, text="串口设置", font=('Arial', 12, 'bold')).pack(anchor=tk.W, pady=(0, 5))
        
        # 端口选择
        ttk.Label(control_frame, text="端口:").pack(anchor=tk.W)
        self.port_var = tk.StringVar()
        self.port_combo = ttk.Combobox(control_frame, textvariable=self.port_var, width=15)
        self.port_combo.pack(fill=tk.X, pady=(0, 5))
        self.refresh_ports()
        
        # 刷新端口按钮
        ttk.Button(control_frame, text="刷新端口", command=self.refresh_ports).pack(fill=tk.X, pady=(0, 10))
        
        # 波特率
        ttk.Label(control_frame, text="波特率:").pack(anchor=tk.W)
        self.baudrate_var = tk.StringVar(value="115200")
        baudrate_combo = ttk.Combobox(control_frame, textvariable=self.baudrate_var, 
                                     values=["9600", "19200", "38400", "57600", "115200", "230400", "256000", "460800", "921600"])
        baudrate_combo.pack(fill=tk.X, pady=(0, 10))
        
        # 连接按钮
        self.connect_btn = ttk.Button(control_frame, text="连接", command=self.toggle_connection)
        self.connect_btn.pack(fill=tk.X, pady=(0, 10))
        
        # 数据记录
        ttk.Label(control_frame, text="数据记录", font=('Arial', 12, 'bold')).pack(anchor=tk.W, pady=(10, 5))
        
        self.record_btn = ttk.Button(control_frame, text="开始记录", command=self.toggle_recording)
        self.record_btn.pack(fill=tk.X, pady=(0, 5))
        
        self.save_btn = ttk.Button(control_frame, text="保存CSV", command=self.save_csv)
        self.save_btn.pack(fill=tk.X, pady=(0, 10))
        
        # 统计信息
        ttk.Label(control_frame, text="统计信息", font=('Arial', 12, 'bold')).pack(anchor=tk.W, pady=(10, 5))
        
        self.stats_text = tk.Text(control_frame, height=8, width=30)
        self.stats_text.pack(fill=tk.X, pady=(0, 10))
        
        # 右侧数据显示区域
        data_frame = ttk.LabelFrame(main_frame, text="接收数据")
        data_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # 创建数据显示文本框
        self.data_text = tk.Text(data_frame, font=('Consolas', 10))
        self.data_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(data_frame, orient="vertical", command=self.data_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.data_text.configure(yscrollcommand=scrollbar.set)
    
    def refresh_ports(self):
        """刷新可用串口列表"""
        try:
            ports = [port.device for port in serial.tools.list_ports.comports()]
            self.port_combo['values'] = ports
            if ports:
                self.port_combo.set(ports[0])
        except Exception as e:
            print(f"刷新串口列表时出错: {e}")
    
    def toggle_connection(self):
        """切换连接状态"""
        if self.receiver is None or not self.receiver.running:
            self.connect_serial()
        else:
            self.disconnect_serial()
    
    def connect_serial(self):
        """连接串口"""
        port = self.port_var.get()
        baudrate = int(self.baudrate_var.get())
        
        if not port:
            messagebox.showerror("错误", "请选择串口")
            return
        
        try:
            self.receiver = SerialDataReceiver(port, baudrate)
            if self.receiver.connect():
                self.receive_thread = threading.Thread(target=self.receiver.receive_data)
                self.receive_thread.daemon = True
                self.receive_thread.start()
                
                self.connect_btn.config(text="断开")
                self.update_stats("已连接到串口")
            else:
                messagebox.showerror("错误", "连接串口失败")
        except Exception as e:
            messagebox.showerror("错误", f"连接失败: {e}")
    
    def disconnect_serial(self):
        """断开串口连接"""
        if self.receiver:
            self.receiver.disconnect()
            self.receiver = None
            self.connect_btn.config(text="连接")
            self.update_stats("已断开连接")
    
    def toggle_recording(self):
        """切换记录状态"""
        if not hasattr(self, 'is_recording'):
            self.is_recording = False
        
        if not self.is_recording:
            self.is_recording = True
            self.record_btn.config(text="停止记录")
            self.update_stats("开始记录数据...")
        else:
            self.is_recording = False
            self.record_btn.config(text="开始记录")
            self.update_stats("停止记录数据")
    
    def save_csv(self):
        """保存CSV文件"""
        if not self.receiver:
            messagebox.showwarning("警告", "没有连接串口")
            return
        
        if not self.receiver.data_buffer:
            messagebox.showwarning("警告", "没有数据可保存")
            return
        
        filename = f"uart_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        try:
            # 创建数据副本，避免deque迭代错误
            data_list = list(self.receiver.data_buffer)
            timestamps_list = list(self.receiver.timestamps)
            
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                
                # 写入表头
                writer.writerow(['时间戳', '数值'])
                
                # 写入数据
                for timestamp, value in zip(timestamps_list, data_list):
                    writer.writerow([timestamp, value])
            
            print(f"数据已保存到: {filename}")
            messagebox.showinfo("成功", f"数据已保存到 {filename}")
            
            # 显示保存统计信息
            print(f"保存了 {len(data_list)} 个数据点")
            if timestamps_list:
                print(f"数据时间范围: {min(timestamps_list):.3f}s - {max(timestamps_list):.3f}s")
            
        except Exception as e:
            print(f"保存CSV文件时出错: {e}")
            messagebox.showerror("错误", f"保存失败: {e}")
    
    def update_stats(self, message):
        """更新统计信息"""
        if not hasattr(self, 'stats_text'):
            return
        
        current_time = datetime.now().strftime("%H:%M:%S")
        stats_info = f"[{current_time}] {message}\n"
        
        if self.receiver:
            # 获取详细统计信息
            stats = self.receiver.get_statistics()
            
            stats_info += f"总样本数: {stats['total_samples']}\n"
            stats_info += f"缓冲区大小: {stats['buffer_size']}\n"
            stats_info += f"计算采样率: {stats['calculated_sample_rate']:.1f} Hz\n"
            stats_info += f"运行时间: {stats['elapsed_time']:.1f} 秒\n"
            
            if stats['data_range'][0] != stats['data_range'][1]:
                stats_info += f"数据范围: {stats['data_range'][0]} 到 {stats['data_range'][1]}\n"
            
            # 计算平均采样率（基于总样本数和运行时间）
            if stats['elapsed_time'] > 0:
                avg_sample_rate = stats['total_samples'] / stats['elapsed_time']
                stats_info += f"平均采样率: {avg_sample_rate:.1f} Hz\n"
        
        # 限制显示行数
        current_text = self.stats_text.get("1.0", tk.END)
        lines = current_text.split('\n')
        if len(lines) > 20:
            lines = lines[-20:]
            self.stats_text.delete("1.0", tk.END)
            self.stats_text.insert("1.0", '\n'.join(lines))
        
        self.stats_text.insert(tk.END, stats_info)
        self.stats_text.see(tk.END)
    
    def update_timer(self):
        """数据更新定时器"""
        if self.receiver and self.receiver.data_buffer:
            # 获取最新的数据
            recent_data, recent_timestamps = self.receiver.get_recent_data(100)
            
            # 更新数据显示
            self.update_data_display(recent_data, recent_timestamps)
        
        # 每100ms更新一次
        self.root.after(100, self.update_timer)
    
    def update_data_display(self, data, timestamps):
        """更新数据显示"""
        if not data or not timestamps:
            return
        
        # 清空文本框
        self.data_text.delete("1.0", tk.END)
        
        # 显示最新的数据
        for i, (timestamp, value) in enumerate(zip(timestamps, data)):
            time_str = datetime.fromtimestamp(timestamp).strftime("%H:%M:%S.%f")[:-3]
            line = f"[{time_str}] {value}\n"
            self.data_text.insert(tk.END, line)
        
        # 滚动到底部
        self.data_text.see(tk.END)
    
    def run(self):
        """运行GUI"""
        self.root.mainloop()
    
    def on_closing(self):
        """关闭事件"""
        if self.receiver:
            self.receiver.disconnect()
        self.root.destroy()

def main():
    """主函数"""
    # 创建并运行GUI
    app = FrequencyAnalyzerGUI()
    app.root.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.run()

if __name__ == "__main__":
    main()
