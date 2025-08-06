#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CSV到PCM文件转换工具
功能：将CSV格式的音频数据转换为PCM文件
支持格式：uint16_t, int16_t
"""

import sys
import os
import csv
import numpy as np
import argparse
from datetime import datetime

def csv_to_pcm(csv_file, pcm_file, data_format='uint16_t', sample_rate=8000, 
                normalize=True, remove_dc=True):
    """
    将CSV文件转换为PCM文件
    
    参数:
    csv_file: CSV文件路径
    pcm_file: 输出PCM文件路径
    data_format: 数据格式 ('uint16_t' 或 'int16_t')
    sample_rate: 采样率 (Hz)
    normalize: 是否归一化数据
    remove_dc: 是否去除直流分量
    """
    
    print(f"正在转换 {csv_file} 到 {pcm_file}")
    print(f"数据格式: {data_format}")
    print(f"采样率: {sample_rate} Hz")
    
    try:
        # 读取CSV文件
        print("正在读取CSV文件...")
        timestamps = []
        values = []
        
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            
            # 跳过表头（如果存在）
            first_line = next(reader)
            if not first_line[0].replace('.', '').replace('-', '').isdigit():
                print("跳过表头行")
            else:
                # 第一行是数据，重新开始读取
                timestamps.append(float(first_line[0]))
                values.append(int(first_line[1]))
            
            # 读取剩余数据
            for row in reader:
                if len(row) >= 2:
                    timestamps.append(float(row[0]))
                    values.append(int(row[1]))
        
        print(f"读取完成，共 {len(values)} 个数据点")
        
        # 数据预处理
        values = np.array(values, dtype=np.int32)
        timestamps = np.array(timestamps)
        
        print(f"原始数据范围: {values.min()} 到 {values.max()}")
        
        # 数据格式转换
        if data_format == 'uint16_t':
            # uint16_t: 0 到 65535
            if values.max() > 65535 or values.min() < 0:
                print("警告: 数据超出uint16_t范围，将进行裁剪")
                values = np.clip(values, 0, 65535)
            
            # 转换为int16_t格式（PCM通常使用有符号格式）
            if normalize:
                # 将uint16_t转换为int16_t
                # 先转换为int32避免溢出，然后再转换为int16
                values = (values.astype(np.int32) - 32768).astype(np.int16)
            else:
                # 保持uint16_t格式
                values = values.astype(np.uint16)
                
        elif data_format == 'int16_t':
            # int16_t: -32768 到 32767
            if values.max() > 32767 or values.min() < -32768:
                print("警告: 数据超出int16_t范围，将进行裁剪")
                values = np.clip(values, -32768, 32767)
            
            values = values.astype(np.int16)
        
        # 去除直流分量
        if remove_dc:
            values = values - np.mean(values)
            print("已去除直流分量")
        
        # 归一化（可选）
        if normalize and not remove_dc:
            max_val = np.max(np.abs(values))
            if max_val > 0:
                # 先转换为float进行计算，避免溢出
                values = (values.astype(np.float32) / max_val * 32767).astype(np.int16)
                print("已归一化数据")
        
        print(f"处理后数据范围: {values.min()} 到 {values.max()}")
        
        # 计算实际采样率
        if len(timestamps) > 1:
            time_diffs = np.diff(timestamps)
            actual_sample_rate = 1.0 / np.mean(time_diffs)
            print(f"实际采样率: {actual_sample_rate:.2f} Hz")
            
            # 如果实际采样率与指定采样率差异较大，给出警告
            if abs(actual_sample_rate - sample_rate) / sample_rate > 0.1:
                print(f"警告: 实际采样率 ({actual_sample_rate:.2f} Hz) 与指定采样率 ({sample_rate} Hz) 差异较大")
        
        # 写入PCM文件
        print("正在写入PCM文件...")
        with open(pcm_file, 'wb') as f:
            values.tofile(f)
        
        print(f"转换完成！")
        print(f"输出文件: {pcm_file}")
        print(f"数据点数: {len(values)}")
        print(f"文件大小: {os.path.getsize(pcm_file)} 字节")
        
        # 生成音频信息文件
        info_file = pcm_file.replace('.pcm', '_info.txt')
        with open(info_file, 'w', encoding='utf-8') as f:
            f.write(f"PCM文件信息\n")
            f.write(f"==========\n")
            f.write(f"源文件: {csv_file}\n")
            f.write(f"输出文件: {pcm_file}\n")
            f.write(f"数据格式: {data_format}\n")
            f.write(f"采样率: {sample_rate} Hz\n")
            f.write(f"数据点数: {len(values)}\n")
            f.write(f"时长: {len(values) / sample_rate:.3f} 秒\n")
            f.write(f"文件大小: {os.path.getsize(pcm_file)} 字节\n")
            f.write(f"数据范围: {values.min()} 到 {values.max()}\n")
            f.write(f"转换时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        print(f"音频信息已保存到: {info_file}")
        
        return True
        
    except Exception as e:
        print(f"转换过程中出错: {e}")
        return False

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='CSV到PCM文件转换工具')
    parser.add_argument('csv_file', help='输入的CSV文件路径')
    parser.add_argument('-o', '--output', help='输出的PCM文件路径（可选）')
    parser.add_argument('-f', '--format', choices=['uint16_t', 'int16_t'], 
                       default='uint16_t', help='数据格式 (默认: uint16_t)')
    parser.add_argument('-r', '--sample-rate', type=int, default=8000,
                       help='采样率 (默认: 8000 Hz)')
    parser.add_argument('--no-normalize', action='store_true',
                       help='不进行归一化处理')
    parser.add_argument('--no-remove-dc', action='store_true',
                       help='不去除直流分量')
    
    args = parser.parse_args()
    
    # 检查输入文件
    if not os.path.exists(args.csv_file):
        print(f"错误: 找不到文件 {args.csv_file}")
        return 1
    
    # 生成输出文件名
    if args.output:
        pcm_file = args.output
    else:
        base_name = os.path.splitext(args.csv_file)[0]
        pcm_file = f"{base_name}.pcm"
    
    # 执行转换
    success = csv_to_pcm(
        csv_file=args.csv_file,
        pcm_file=pcm_file,
        data_format=args.format,
        sample_rate=args.sample_rate,
        normalize=not args.no_normalize,
        remove_dc=not args.no_remove_dc
    )
    
    return 0 if success else 1

if __name__ == "__main__":
    # 如果没有命令行参数，使用默认参数处理sample_16_39.csv
    if len(sys.argv) == 1:
        csv_file = "sample_16_16.csv"
        pcm_file = "IVS_audio.pcm"
        
        if os.path.exists(csv_file):
            success = csv_to_pcm(
                csv_file=csv_file,
                pcm_file=pcm_file,
                data_format='uint16_t',
                sample_rate=8000,
                normalize=True,
                remove_dc=True
            )
            sys.exit(0 if success else 1)
        else:
            print(f"错误: 找不到文件 {csv_file}")
            sys.exit(1)
    else:
        sys.exit(main())
