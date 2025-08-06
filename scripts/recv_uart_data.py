#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
串口数据接收和FFT分析脚本
功能：
1. 接收串口数据并解析为int格式
2. 保存数据到xlsx文件
3. 对数据进行FFT分析，输出频率成分
"""

import serial
import struct
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.fft import fft, fftfreq
import time
import os
from datetime import datetime
import argparse

# 设置matplotlib中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

class UartDataReceiver:
    def __init__(self, port='COM31', baudrate=921600, timeout=1):
        """
        初始化串口接收器
        
        Args:
            port: 串口号
            baudrate: 波特率
            timeout: 超时时间
        """
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial_conn = None
        self.data_buffer = []
        self.timestamps = []
        
    def connect(self):
        """连接串口"""
        try:
            self.serial_conn = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout
            )
            print(f"成功连接到串口 {self.port}")
            return True
        except serial.SerialException as e:
            print(f"连接串口失败: {e}")
            return False
    
    def disconnect(self):
        """断开串口连接"""
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()
            print("串口连接已断开")
    
    def receive_data(self, duration=10, sample_rate=1000):
        """
        接收数据
        
        Args:
            duration: 接收时长（秒）
            sample_rate: 采样率（Hz）
        """
        if not self.serial_conn or not self.serial_conn.is_open:
            print("串口未连接")
            return
        
        print(f"开始接收数据，时长: {duration}秒，采样率: {sample_rate}Hz")
        
        start_time = time.time()
        sample_interval = 1.0 / sample_rate
        
        while time.time() - start_time < duration:
            if self.serial_conn.in_waiting >= 4:  # 假设每个int是4字节
                try:
                    # 读取4字节数据并解析为int
                    raw_data = self.serial_conn.read(4)
                    if len(raw_data) == 4:
                        # 解析为32位有符号整数
                        value = struct.unpack('<i', raw_data)[0]
                        self.data_buffer.append(value)
                        self.timestamps.append(time.time() - start_time)
                        
                        # 控制采样率
                        time.sleep(sample_interval)
                        
                        # 显示进度
                        elapsed = time.time() - start_time
                        if int(elapsed) % 5 == 0 and elapsed > 0:
                            print(f"已接收 {len(self.data_buffer)} 个数据点，用时 {elapsed:.1f}秒")
                            
                except struct.error as e:
                    print(f"数据解析错误: {e}")
                    continue
                except Exception as e:
                    print(f"接收数据错误: {e}")
                    break
        
        print(f"数据接收完成，共接收 {len(self.data_buffer)} 个数据点")
    
    def save_to_xlsx(self, filename=None):
        """
        保存数据到xlsx文件
        
        Args:
            filename: 文件名，如果为None则自动生成
        """
        if not self.data_buffer:
            print("没有数据可保存")
            return
        
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"uart_data_{timestamp}.xlsx"
        
        # 创建DataFrame
        df = pd.DataFrame({
            'Timestamp': self.timestamps,
            'Value': self.data_buffer
        })
        
        # 保存到xlsx
        df.to_excel(filename, index=False)
        print(f"数据已保存到: {filename}")
        return filename
    
    def perform_fft(self, sample_rate=1000):
        """
        对数据进行FFT分析
        
        Args:
            sample_rate: 采样率（Hz）
        """
        if not self.data_buffer:
            print("没有数据可进行FFT分析")
            return
        
        # 转换为numpy数组
        data = np.array(self.data_buffer)
        
        # 执行FFT
        fft_result = fft(data)
        
        # 计算频率轴
        n = len(data)
        freq = fftfreq(n, 1/sample_rate)
        
        # 计算幅度谱
        magnitude = np.abs(fft_result)
        
        # 只取正频率部分
        positive_freq_mask = freq >= 0
        freq_positive = freq[positive_freq_mask]
        magnitude_positive = magnitude[positive_freq_mask]
        
        # 找到主要频率成分
        peak_indices = self._find_peaks(magnitude_positive)
        
        print("\n=== FFT分析结果 ===")
        print(f"数据点数: {n}")
        print(f"采样率: {sample_rate} Hz")
        print(f"频率分辨率: {sample_rate/n:.2f} Hz")
        print(f"最大频率: {sample_rate/2:.1f} Hz")
        
        print("\n主要频率成分:")
        for i, peak_idx in enumerate(peak_indices[:10]):  # 显示前10个峰值
            freq_val = freq_positive[peak_idx]
            magnitude_val = magnitude_positive[peak_idx]
            print(f"  {i+1}. 频率: {freq_val:.2f} Hz, 幅度: {magnitude_val:.2f}")
        
        # 绘制频谱图
        self._plot_spectrum(freq_positive, magnitude_positive, sample_rate)
        
        return freq_positive, magnitude_positive
    
    def _find_peaks(self, magnitude, threshold_ratio=0.1):
        """找到频谱中的峰值"""
        threshold = np.max(magnitude) * threshold_ratio
        peaks = []
        
        for i in range(1, len(magnitude) - 1):
            if (magnitude[i] > magnitude[i-1] and 
                magnitude[i] > magnitude[i+1] and 
                magnitude[i] > threshold):
                peaks.append(i)
        
        # 按幅度排序
        peaks.sort(key=lambda x: magnitude[x], reverse=True)
        return peaks
    
    def _plot_spectrum(self, freq, magnitude, sample_rate):
        """绘制频谱图"""
        # 设置中文字体
        plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
        plt.rcParams['axes.unicode_minus'] = False
        
        plt.figure(figsize=(12, 8))
        
        # 主频谱图
        plt.subplot(2, 1, 1)
        plt.plot(freq, magnitude)
        plt.xlabel('频率 (Hz)')
        plt.ylabel('幅度')
        plt.title('FFT频谱分析')
        plt.grid(True)
        
        # 自适应横轴范围
        if len(freq) > 0:
            freq_max = np.max(freq)
            if freq_max > 0:
                plt.xlim(0, freq_max)
        
        # 自适应纵轴范围
        if len(magnitude) > 0:
            max_mag = np.max(magnitude)
            min_mag = np.min(magnitude)
            if max_mag > min_mag:
                # 设置Y轴范围为数据范围的1.1倍，避免贴边
                margin = (max_mag - min_mag) * 0.1
                plt.ylim(max(0, min_mag - margin), max_mag + margin)
        
        # 对数坐标频谱图
        plt.subplot(2, 1, 2)
        plt.semilogy(freq, magnitude)
        plt.xlabel('频率 (Hz)')
        plt.ylabel('幅度 (对数)')
        plt.title('FFT频谱分析 (对数坐标)')
        plt.grid(True)
        
        # 自适应横轴范围
        if len(freq) > 0:
            freq_max = np.max(freq)
            if freq_max > 0:
                plt.xlim(0, freq_max)
        
        # 自适应对数坐标的Y轴范围
        if len(magnitude) > 0:
            positive_mag = magnitude[magnitude > 0]
            if len(positive_mag) > 0:
                min_mag = np.min(positive_mag)
                max_mag = np.max(magnitude)
                if max_mag > min_mag:
                    # 对数坐标的Y轴范围，确保数据在合适范围内显示
                    plt.ylim(min_mag * 0.1, max_mag * 10)
        
        plt.tight_layout()
        
        # 保存图片
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        plot_filename = f"fft_spectrum_{timestamp}.png"
        plt.savefig(plot_filename, dpi=300, bbox_inches='tight')
        print(f"频谱图已保存到: {plot_filename}")
        
        plt.show()

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='串口数据接收和FFT分析工具')
    parser.add_argument('--port', default='COM31', help='串口号 (默认: COM31)')
    parser.add_argument('--baudrate', type=int, default=921600, help='波特率 (默认: 921600)')
    parser.add_argument('--duration', type=int, default=10, help='接收时长(秒) (默认: 10)')
    parser.add_argument('--sample-rate', type=int, default=1000, help='采样率(Hz) (默认: 1000)')
    parser.add_argument('--output', help='输出文件名')
    
    args = parser.parse_args()
    
    # 创建接收器
    receiver = UartDataReceiver(
        port=args.port,
        baudrate=args.baudrate
    )
    
    try:
        # 连接串口
        if not receiver.connect():
            return
        
        # 接收数据
        receiver.receive_data(
            duration=args.duration,
            sample_rate=args.sample_rate
        )
        
        # 保存数据
        if receiver.data_buffer:
            receiver.save_to_xlsx(args.output)
            
            # 进行FFT分析
            receiver.perform_fft(args.sample_rate)
        
    except KeyboardInterrupt:
        print("\n用户中断程序")
    except Exception as e:
        print(f"程序错误: {e}")
    finally:
        receiver.disconnect()

if __name__ == "__main__":
    main()
