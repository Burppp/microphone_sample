from scipy.signal import spectrogram
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import os

def analyze_csv_data(csv_file_path):
    """分析CSV文件中的音频数据"""
    print(f"正在分析CSV文件: {csv_file_path}")
    
    # 读取CSV文件
    try:
        df = pd.read_csv(csv_file_path)
        print(f"成功读取CSV文件，共 {len(df)} 行数据")
        print(f"列名: {df.columns.tolist()}")
        
        # 显示前几行数据
        print("\n前5行数据:")
        print(df.head())
        
        # 显示数据统计信息
        print("\n数据统计信息:")
        print(df.describe())
        
    except Exception as e:
        print(f"读取CSV文件时出错: {e}")
        return
    
    # 提取时间戳和数值
    timestamps = df.iloc[:, 0].values  # 第一列是时间戳
    values = df.iloc[:, 1].values      # 第二列是数值
    
    # 数据预处理
    print(f"\n原始数据范围: {values.min()} 到 {values.max()}")
    
    # 将int16数据转换为浮点数（假设数据是int16格式）
    # int16范围是-32768到32767
    if values.max() > 32767 or values.min() < -32768:
        print("警告: 数据超出int16范围，可能不是int16格式")
    
    # 转换为浮点数并归一化
    float_values = values.astype(np.float64)
    
    # 去除直流分量（均值）
    float_values = float_values - np.mean(float_values)
    
    print(f"预处理后数据范围: {float_values.min():.2f} 到 {float_values.max():.2f}")
    print(f"数据标准差: {np.std(float_values):.2f}")
    
    # 计算采样率
    if len(timestamps) > 1:
        time_diffs = np.diff(timestamps)
        avg_sample_rate = 1.0 / np.mean(time_diffs)
        print(f"估算采样率: {avg_sample_rate:.2f} Hz")
        sample_rate = avg_sample_rate
    else:
        sample_rate = 12000  # 默认采样率
        print(f"使用默认采样率: {sample_rate} Hz")
    
    # 计算频谱图
    print("\n正在计算频谱图...")
    try:
        f, t, Sxx = spectrogram(float_values, sample_rate, 
                               nperseg=256, noverlap=128,
                               scaling='density')
        
        print(f"频谱图计算完成:")
        print(f"  频率范围: {f.min():.1f} - {f.max():.1f} Hz")
        print(f"  时间范围: {t.min():.3f} - {t.max():.3f} 秒")
        print(f"  频谱图尺寸: {Sxx.shape}")
        
        # 计算有效的频率范围（基于功率谱密度）
        Sxx_db = 10 * np.log10(Sxx + 1e-10)
        # 找到有意义的频率范围（功率谱密度大于最大值的1%）
        max_power = np.max(Sxx_db)
        threshold = max_power - 40  # 40dB动态范围
        significant_freq_mask = np.any(Sxx_db > threshold, axis=1)
        
        if np.any(significant_freq_mask):
            min_significant_freq = f[significant_freq_mask].min()
            max_significant_freq = f[significant_freq_mask].max()
            print(f"  有效频率范围: {min_significant_freq:.1f} - {max_significant_freq:.1f} Hz")
        else:
            min_significant_freq = f.min()
            max_significant_freq = f.max()
            print(f"  使用全频率范围: {min_significant_freq:.1f} - {max_significant_freq:.1f} Hz")
        
    except Exception as e:
        print(f"计算频谱图时出错: {e}")
        return
    
    # 创建可视化图表
    fig, axes = plt.subplots(1, 2, figsize=(15, 6))
    fig.suptitle(f'CSV数据分析: {os.path.basename(csv_file_path)}', fontsize=16)
    
    # 1. 时域波形
    ax1 = axes[0]
    time_axis = np.arange(len(float_values)) / sample_rate
    ax1.plot(time_axis, float_values, 'b-', linewidth=0.5, alpha=0.7)
    ax1.set_title('时域波形')
    ax1.set_xlabel('时间 (秒)')
    ax1.set_ylabel('幅度')
    ax1.grid(True, alpha=0.3)
    
    # 2. 频谱图
    ax2 = axes[1]
    im = ax2.pcolormesh(t, f, 10 * np.log10(Sxx + 1e-10), 
                        cmap='viridis', shading='gouraud')
    ax2.set_title('频谱图')
    ax2.set_xlabel('时间 (秒)')
    ax2.set_ylabel('频率 (Hz)')
    
    # 智能设置纵轴范围
    if 'max_significant_freq' in locals():
        # 使用计算出的有效频率范围
        if max_significant_freq > min_significant_freq:
            # 添加一些边距，确保显示完整
            margin = (max_significant_freq - min_significant_freq) * 0.1
            y_min = max(0, min_significant_freq - margin)
            y_max = min(20000, max_significant_freq + margin)
            ax2.set_ylim(y_min, y_max)
        else:
            # 如果有效范围很小，使用默认范围
            ax2.set_ylim(0, min(20000, f.max()))
    else:
        # 如果没有计算有效范围，使用传统方法
        if f.max() > 0:
            max_freq = min(20000, f.max())
            ax2.set_ylim(0, max_freq)
        else:
            ax2.set_ylim(0, 1000)  # 默认范围
    
    plt.colorbar(im, ax=ax2, label='功率谱密度 (dB/Hz)')
    
    # 3. 功率谱密度
    # ax3 = axes[1, 0]
    # 计算平均功率谱密度
    # psd = np.mean(Sxx, axis=1)
    # ax3.semilogy(f, psd, 'r-', linewidth=1)
    # ax3.set_title('平均功率谱密度')
    # ax3.set_xlabel('频率 (Hz)')
    # ax3.set_ylabel('功率谱密度')
    # ax3.grid(True, alpha=0.3)
    # ax3.set_xlim(0, min(4000, f.max()))
    
    # 4. 数据分布直方图
    # ax4 = axes[1, 1]
    # ax4.hist(float_values, bins=50, alpha=0.7, color='green', edgecolor='black')
    # ax4.set_title('数据分布直方图')
    # ax4.set_xlabel('幅度')
    # ax4.set_ylabel('频次')
    # ax4.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.show()
    
    # 打印分析结果
    print("\n=== 分析结果 ===")
    print(f"数据总时长: {time_axis[-1]:.3f} 秒")
    print(f"数据点数: {len(float_values)}")
    print(f"有效采样率: {sample_rate:.2f} Hz")
    
    # 计算平均功率谱密度
    psd = np.mean(Sxx, axis=1)
    
    # 计算主要频率成分
    if len(psd) > 0:
        # 找到功率谱密度的峰值
        peak_indices = np.argsort(psd)[-5:]  # 前5个峰值
        print("\n主要频率成分:")
        for i, idx in enumerate(reversed(peak_indices)):
            if psd[idx] > np.max(psd) * 0.1:  # 只显示相对较强的成分
                print(f"  峰值 {i+1}: {f[idx]:.1f} Hz (功率: {psd[idx]:.2e})")
    
    # 计算信噪比估计
    if len(psd) > 0:
        signal_power = np.max(psd)
        noise_power = np.mean(psd)
        snr_estimate = 10 * np.log10(signal_power / noise_power) if noise_power > 0 else 0
        print(f"\n估计信噪比: {snr_estimate:.1f} dB")

# 主程序
if __name__ == "__main__":
    # 设置中文字体
    plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
    plt.rcParams['axes.unicode_minus'] = False
    
    # 分析CSV文件
    csv_file = "sample_19_58.csv"
    
    if os.path.exists(csv_file):
        analyze_csv_data(csv_file)
    else:
        print(f"错误: 找不到文件 {csv_file}")
        print("请确保CSV文件在当前目录中")