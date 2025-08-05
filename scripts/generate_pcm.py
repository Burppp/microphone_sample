#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成PCM测试数据
采样率: 8kHz
时长: 10秒
格式: 16位有符号整数
"""

import numpy as np
import struct
import time
from datetime import datetime

def generate_pcm_data():
    """生成PCM测试数据"""
    
    # 参数设置
    sample_rate = 8000  # 8kHz采样率
    duration = 10       # 10秒时长
    num_samples = sample_rate * duration  # 总采样点数
    
    print(f"生成PCM数据:")
    print(f"  采样率: {sample_rate} Hz")
    print(f"  时长: {duration} 秒")
    print(f"  总采样点数: {num_samples}")
    
    # 生成时间轴
    t = np.linspace(0, duration, num_samples, False)
    
    # 生成复合信号（包含多个频率成分）
    # 1. 440Hz基频（A音）
    signal_440 = 0.3 * np.sin(2 * np.pi * 440 * t)
    
    # 2. 880Hz二次谐波
    signal_880 = 0.2 * np.sin(2 * np.pi * 880 * t)
    
    # 3. 1320Hz三次谐波
    signal_1320 = 0.15 * np.sin(2 * np.pi * 1320 * t)
    
    # 4. 200Hz低频成分
    signal_200 = 0.1 * np.sin(2 * np.pi * 200 * t)
    
    # 5. 添加一些噪声
    noise = 0.05 * np.random.normal(0, 1, num_samples)
    
    # 6. 添加一些瞬态事件（模拟敲击声）
    transient_times = [2.0, 4.5, 7.0, 9.0]  # 在2秒、4.5秒、7秒、9秒添加瞬态
    transient_signal = np.zeros(num_samples)
    for trans_time in transient_times:
        trans_idx = int(trans_time * sample_rate)
        if trans_idx < num_samples:
            # 生成一个短促的瞬态信号
            transient_duration = int(0.1 * sample_rate)  # 100ms
            end_idx = min(trans_idx + transient_duration, num_samples)
            transient_signal[trans_idx:end_idx] = 0.5 * np.exp(-np.arange(end_idx - trans_idx) / (0.05 * sample_rate))
    
    # 组合所有信号
    combined_signal = signal_440 + signal_880 + signal_1320 + signal_200 + noise + transient_signal
    
    # 归一化到int16范围 (-32768 到 32767)
    max_amplitude = np.max(np.abs(combined_signal))
    normalized_signal = combined_signal / max_amplitude * 0.8 * 32767  # 留一些余量
    
    # 转换为int16
    pcm_data = np.int16(normalized_signal)
    
    print(f"  信号范围: {pcm_data.min()} 到 {pcm_data.max()}")
    print(f"  信号标准差: {np.std(pcm_data):.2f}")
    
    return pcm_data, sample_rate

def save_pcm_file(pcm_data, filename):
    """保存PCM数据到文件"""
    with open(filename, 'wb') as f:
        for sample in pcm_data:
            f.write(struct.pack('<h', sample))  # 小端序16位整数
    print(f"PCM数据已保存到: {filename}")

def save_csv_with_timestamps(pcm_data, sample_rate, filename):
    """保存带时间戳的CSV文件"""
    timestamps = []
    current_time = time.time()
    
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        f.write("时间戳,数值\n")
        
        for i, sample in enumerate(pcm_data):
            # 计算时间戳（每个采样点间隔1/sample_rate秒）
            timestamp = current_time + i / sample_rate
            f.write(f"{timestamp},{sample}\n")
            timestamps.append(timestamp)
    
    print(f"CSV数据已保存到: {filename}")
    print(f"  时间范围: {timestamps[0]:.3f} 到 {timestamps[-1]:.3f}")
    return timestamps

def create_audio_info_file(pcm_data, sample_rate, filename):
    """创建音频信息文件"""
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("PCM音频文件信息\n")
        f.write("=" * 30 + "\n")
        f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"采样率: {sample_rate} Hz\n")
        f.write(f"时长: {len(pcm_data) / sample_rate:.2f} 秒\n")
        f.write(f"采样点数: {len(pcm_data)}\n")
        f.write(f"数据格式: 16位有符号整数 (int16)\n")
        f.write(f"字节序: 小端序 (Little Endian)\n")
        f.write(f"数据范围: {pcm_data.min()} 到 {pcm_data.max()}\n")
        f.write(f"数据标准差: {np.std(pcm_data):.2f}\n")
        f.write(f"文件大小: {len(pcm_data) * 2} 字节\n")
        f.write("\n信号成分:\n")
        f.write("- 440Hz 基频 (A音)\n")
        f.write("- 880Hz 二次谐波\n")
        f.write("- 1320Hz 三次谐波\n")
        f.write("- 200Hz 低频成分\n")
        f.write("- 随机噪声\n")
        f.write("- 瞬态事件 (2s, 4.5s, 7s, 9s)\n")
    
    print(f"音频信息已保存到: {filename}")

def main():
    """主函数"""
    print("=== PCM数据生成器 ===")
    
    # 生成PCM数据
    pcm_data, sample_rate = generate_pcm_data()
    
    # 保存文件
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 1. 保存原始PCM文件
    pcm_filename = f"test_audio_{timestamp}.pcm"
    save_pcm_file(pcm_data, pcm_filename)
    
    # 2. 保存CSV文件（带时间戳）
    csv_filename = f"test_audio_{timestamp}.csv"
    timestamps = save_csv_with_timestamps(pcm_data, sample_rate, csv_filename)
    
    # 3. 保存音频信息文件
    info_filename = f"test_audio_{timestamp}_info.txt"
    create_audio_info_file(pcm_data, sample_rate, info_filename)
    
    print("\n=== 生成完成 ===")
    print(f"生成的文件:")
    print(f"  PCM文件: {pcm_filename}")
    print(f"  CSV文件: {csv_filename}")
    print(f"  信息文件: {info_filename}")
    
    # 显示一些统计信息
    print(f"\n数据统计:")
    print(f"  最小值: {pcm_data.min()}")
    print(f"  最大值: {pcm_data.max()}")
    print(f"  均值: {np.mean(pcm_data):.2f}")
    print(f"  标准差: {np.std(pcm_data):.2f}")
    print(f"  有效位数: {np.log2(np.max(np.abs(pcm_data)) + 1):.1f} bits")

if __name__ == "__main__":
    main() 