#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
串口接收上位机程序
功能：串口数据接收、实时波形显示、数据保存为CSV
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
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QGridLayout, QLabel, QComboBox, 
                             QPushButton, QSpinBox, QCheckBox, QFileDialog,
                             QMessageBox, QGroupBox, QTextEdit, QProgressBar)
from PyQt5.QtCore import QTimer, pyqtSignal, QThread
from PyQt5.QtGui import QFont
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.animation as animation
import matplotlib.font_manager as fm
from scipy import signal
from scipy.fft import fft, fftfreq

class SerialThread(QThread):
    """串口数据接收线程"""
    data_received = pyqtSignal(list)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, port, baudrate, data_format='int16_t', byteorder='little'):
        super().__init__()
        self.port = port
        self.baudrate = baudrate
        self.data_format = data_format
        self.byteorder = byteorder
        self.serial = None
        self.running = False
        
    def run(self):
        try:
            self.serial = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=1
            )
            self.running = True
            
            while self.running:
                if self.serial.in_waiting:
                    if self.data_format == 'int16_t':
                        # int16_t模式：每两个字节解析为一个int16_t
                        if self.serial.in_waiting >= 2:
                            # 读取两个字节
                            byte1 = self.serial.read(1)
                            byte2 = self.serial.read(1)
                            
                            if len(byte1) == 1 and len(byte2) == 1:
                                # 组合为16位整数
                                int16_value = int.from_bytes(byte1 + byte2, byteorder=self.byteorder, signed=True)
                                # int16_value = int16_value / 3277.0
                                self.data_received.emit([int16_value])
                    else:
                        # 文本模式：按行读取并解析
                        data = self.serial.readline()
                        try:
                            # 尝试解析数据为浮点数
                            values = [float(x.strip()) for x in data.decode().strip().split(',')]
                            self.data_received.emit(values)
                        except (ValueError, UnicodeDecodeError):
                            # 如果解析失败，发送原始字节数据
                            self.data_received.emit([float(x) for x in data])
                        
        except serial.SerialException as e:
            self.error_occurred.emit(f"串口错误: {str(e)}")
        except Exception as e:
            self.error_occurred.emit(f"未知错误: {str(e)}")
        finally:
            if self.serial and self.serial.is_open:
                try:
                    self.serial.close()
                except Exception as e:
                    print(f"关闭串口时出错: {e}")
    
    def stop(self):
        self.running = False
        if self.serial and self.serial.is_open:
            try:
                self.serial.close()
            except Exception as e:
                print(f"关闭串口时出错: {e}")

class SerialMonitor(QMainWindow):
    """主窗口类"""
    
    def __init__(self):
        super().__init__()
        self.serial_thread = None
        self.data_buffer = deque(maxlen=1000)  # 数据缓冲区
        self.acceleration_buffer = deque(maxlen=1000)  # 加速度数据缓冲区
        self.is_recording = False
        self.recorded_data = []
        self.animation = None
        self.bytes_received = 0
        self.data_points = 0
        
        # 时频图相关参数
        self.spectrogram_data = None
        self.spectrogram_times = None
        self.spectrogram_frequencies = None
        self.sample_rate = 1000  # 默认采样率
        self.window_length = 256  # FFT窗口长度
        self.overlap = 128  # 重叠长度
        
        # 性能优化：添加UI更新定时器
        self.ui_update_timer = QTimer()
        self.ui_update_timer.timeout.connect(self.update_ui)
        self.ui_update_timer.start(100)  # 100ms更新一次UI
        
        # 数据接收缓冲
        self.pending_data = []
        self.last_ui_update = time.time()
        self.last_perf_check = time.time()
        self.ui_update_count = 0
        
        self.init_ui()
        self.init_plot()
        
        # 初始化信息显示
        if hasattr(self, 'info_text'):
            self.info_text.append("系统初始化完成")
            self.info_text.append("等待串口连接...")
        
    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle("串口数据接收上位机 - 实时时频图分析")
        self.setGeometry(100, 100, 1200, 800)
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QHBoxLayout(central_widget)
        
        # 左侧控制面板
        control_panel = self.create_control_panel()
        main_layout.addWidget(control_panel, 1)
        
        # 右侧图表区域
        plot_panel = self.create_plot_panel()
        main_layout.addWidget(plot_panel, 4)
        
    def create_control_panel(self):
        """创建控制面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # 串口设置组
        serial_group = QGroupBox("串口设置")
        serial_layout = QGridLayout(serial_group)
        
        # 端口选择
        serial_layout.addWidget(QLabel("端口:"), 0, 0)
        self.port_combo = QComboBox()
        self.refresh_ports()
        serial_layout.addWidget(self.port_combo, 0, 1)
        
        # 刷新端口按钮
        refresh_btn = QPushButton("刷新")
        refresh_btn.clicked.connect(self.refresh_ports)
        serial_layout.addWidget(refresh_btn, 0, 2)
        
        # 波特率选择
        serial_layout.addWidget(QLabel("波特率:"), 1, 0)
        self.baudrate_combo = QComboBox()
        baudrates = ['9600', '19200', '38400', '57600', '115200', '230400', '460800', '921600']
        self.baudrate_combo.addItems(baudrates)
        self.baudrate_combo.setCurrentText('115200')
        serial_layout.addWidget(self.baudrate_combo, 1, 1)
        
        # 数据格式选择
        serial_layout.addWidget(QLabel("数据格式:"), 2, 0)
        self.data_format_combo = QComboBox()
        data_formats = ['int16_t (每2字节)', '文本格式']
        self.data_format_combo.addItems(data_formats)
        self.data_format_combo.setCurrentText('int16_t (每2字节)')
        serial_layout.addWidget(self.data_format_combo, 2, 1)
        
        # 字节序选择（仅int16_t模式有效）
        serial_layout.addWidget(QLabel("字节序:"), 3, 0)
        self.byteorder_combo = QComboBox()
        byteorders = ['小端序 (Little Endian)', '大端序 (Big Endian)']
        self.byteorder_combo.addItems(byteorders)
        self.byteorder_combo.setCurrentText('小端序 (Little Endian)')
        serial_layout.addWidget(self.byteorder_combo, 3, 1)
        
        # 连接/断开按钮
        self.connect_btn = QPushButton("连接")
        self.connect_btn.clicked.connect(self.toggle_connection)
        serial_layout.addWidget(self.connect_btn, 4, 0, 1, 2)
        
        layout.addWidget(serial_group)
        
        # 数据显示组
        data_group = QGroupBox("数据显示")
        data_layout = QVBoxLayout(data_group)
        
        self.data_display = QTextEdit()
        self.data_display.setMaximumHeight(150)
        self.data_display.setFont(QFont("Consolas", 9))
        data_layout.addWidget(self.data_display)
        
        layout.addWidget(data_group)
        
        # 信息显示组
        info_group = QGroupBox("分析信息")
        info_layout = QVBoxLayout(info_group)
        
        self.info_text = QTextEdit()
        self.info_text.setMaximumHeight(100)
        self.info_text.setFont(QFont("Consolas", 9))
        info_layout.addWidget(self.info_text)
        
        layout.addWidget(info_group)
        
        # 数据记录组
        record_group = QGroupBox("数据记录")
        record_layout = QVBoxLayout(record_group)
        
        # 记录控制
        record_control_layout = QHBoxLayout()
        self.record_btn = QPushButton("开始记录")
        self.record_btn.clicked.connect(self.toggle_recording)
        record_control_layout.addWidget(self.record_btn)
        
        self.save_btn = QPushButton("保存CSV")
        self.save_btn.clicked.connect(self.save_csv)
        self.save_btn.setEnabled(False)
        record_control_layout.addWidget(self.save_btn)
        
        record_layout.addLayout(record_control_layout)
        
        # 记录状态
        self.record_status = QLabel("未记录")
        record_layout.addWidget(self.record_status)
        
        # 记录进度
        self.record_progress = QProgressBar()
        self.record_progress.setVisible(False)
        record_layout.addWidget(self.record_progress)
        
        layout.addWidget(record_group)
        
        # 图表设置组
        plot_group = QGroupBox("图表设置")
        plot_layout = QGridLayout(plot_group)
        
        # 显示模式选择
        plot_layout.addWidget(QLabel("显示模式:"), 0, 0)
        self.display_mode_combo = QComboBox()
        display_modes = ['时频图', '波形图']
        self.display_mode_combo.addItems(display_modes)
        self.display_mode_combo.setCurrentText('时频图')
        self.display_mode_combo.currentTextChanged.connect(self.on_display_mode_changed)
        plot_layout.addWidget(self.display_mode_combo, 0, 1)
        
        # 采样率设置
        plot_layout.addWidget(QLabel("采样率(Hz):"), 1, 0)
        self.sample_rate_spin = QSpinBox()
        self.sample_rate_spin.setRange(100, 100000)
        self.sample_rate_spin.setValue(1000)
        self.sample_rate_spin.valueChanged.connect(self.on_sample_rate_changed)
        plot_layout.addWidget(self.sample_rate_spin, 1, 1)
        
        # FFT窗口长度
        plot_layout.addWidget(QLabel("FFT窗口长度:"), 2, 0)
        self.window_length_spin = QSpinBox()
        self.window_length_spin.setRange(64, 2048)
        self.window_length_spin.setValue(256)
        self.window_length_spin.valueChanged.connect(self.on_window_length_changed)
        plot_layout.addWidget(self.window_length_spin, 2, 1)
        
        # 最大频率
        plot_layout.addWidget(QLabel("最大频率(Hz):"), 3, 0)
        self.max_freq_spin = QSpinBox()
        self.max_freq_spin.setRange(10, 20000)
        self.max_freq_spin.setValue(15000)
        plot_layout.addWidget(self.max_freq_spin, 3, 1)
        
        # 清除图表按钮
        clear_btn = QPushButton("清除图表")
        clear_btn.clicked.connect(self.clear_plot)
        plot_layout.addWidget(clear_btn, 4, 0, 1, 2)
        
        layout.addWidget(plot_group)
        
        # 状态栏
        self.status_label = QLabel("就绪")
        layout.addWidget(self.status_label)
        
        # 统计信息
        self.stats_label = QLabel("接收字节: 0 | 数据点: 0")
        layout.addWidget(self.stats_label)
        
        # 性能信息
        self.perf_label = QLabel("性能: 正常")
        layout.addWidget(self.perf_label)
        
        layout.addStretch()
        return panel
    
    def create_plot_panel(self):
        """创建图表面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # 创建matplotlib图表
        self.figure = Figure(figsize=(8, 6), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)
        
        return panel
    
    def init_plot(self):
        """初始化图表"""
        # 设置中文字体
        plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
        plt.rcParams['axes.unicode_minus'] = False
        
        self.ax = self.figure.add_subplot(111)
        self.ax.set_title("实时时频图")
        self.ax.set_xlabel("时间 (秒)")
        self.ax.set_ylabel("频率 (Hz)")
        self.ax.grid(True, alpha=0.3)
        
        # 初始化数据线
        self.lines = []
        self.times = deque(maxlen=1000)
        self.values = deque(maxlen=1000)
        
        # 设置动画更新（降低更新频率以提高性能）
        self.animation = animation.FuncAnimation(
            self.figure, self.update_plot, interval=200, blit=False, cache_frame_data=False
        )
    
    def refresh_ports(self):
        """刷新可用串口列表"""
        self.port_combo.clear()
        try:
            ports = [port.device for port in serial.tools.list_ports.comports()]
            self.port_combo.addItems(ports)
            
            if not ports:
                self.port_combo.addItem("无可用串口")
        except Exception as e:
            print(f"刷新串口列表时出错: {e}")
            self.port_combo.addItem("无可用串口")
    
    def toggle_connection(self):
        """切换连接状态"""
        if self.serial_thread is None or not self.serial_thread.isRunning():
            self.connect_serial()
        else:
            self.disconnect_serial()
    
    def connect_serial(self):
        """连接串口"""
        port = self.port_combo.currentText()
        baudrate = int(self.baudrate_combo.currentText())
        data_format = 'int16_t' if 'int16_t' in self.data_format_combo.currentText() else 'text'
        byteorder = 'little' if '小端序' in self.byteorder_combo.currentText() else 'big'
        
        if port == "无可用串口":
            QMessageBox.warning(self, "警告", "没有可用的串口")
            return
        
        # 检查是否已经连接
        if self.serial_thread and self.serial_thread.isRunning():
            QMessageBox.warning(self, "警告", "请先断开当前连接")
            return
        
        try:
            self.serial_thread = SerialThread(port, baudrate, data_format, byteorder)
            self.serial_thread.data_received.connect(self.on_data_received)
            self.serial_thread.error_occurred.connect(self.on_serial_error)
            self.serial_thread.start()
            
            self.connect_btn.setText("断开")
            self.status_label.setText(f"已连接到 {port} ({data_format}模式, {byteorder}字节序)")
            
            # 显示连接信息
            if hasattr(self, 'info_text'):
                self.info_text.append(f"已连接到串口: {port}")
                self.info_text.append(f"数据格式: {data_format}")
                self.info_text.append(f"字节序: {byteorder}")
                self.info_text.append("开始接收数据...")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"连接失败: {str(e)}")
    
    def disconnect_serial(self):
        """断开串口连接"""
        if self.serial_thread:
            try:
                self.serial_thread.stop()
                self.serial_thread.wait()
            except Exception as e:
                print(f"断开串口连接时出错: {e}")
            finally:
                self.serial_thread = None
        
        self.connect_btn.setText("连接")
        self.status_label.setText("已断开连接")
    
    def on_data_received(self, data):
        """处理接收到的数据"""
        try:
            timestamp = time.time()
            
            # 更新统计信息
            self.data_points += 1
            if hasattr(self.serial_thread, 'data_format') and self.serial_thread.data_format == 'int16_t':
                self.bytes_received += 2  # int16_t模式每次接收2字节
            else:
                self.bytes_received += len(str(data).encode())
            
            # 添加到数据缓冲区
            self.data_buffer.append((timestamp, data))
            
            # 转换为加速度值并添加到加速度缓冲区
            if hasattr(self.serial_thread, 'data_format') and self.serial_thread.data_format == 'int16_t':
                if isinstance(data, list) and len(data) > 0:
                    int16_value = data[0]
                    # 除以3277得到加速度值
                    acceleration = int16_value / 3277.0
                    self.acceleration_buffer.append((timestamp, acceleration))
            
            # 添加到待处理数据列表（减少UI更新频率）
            self.pending_data.append((timestamp, data))
            
            # 如果正在记录，保存数据
            if self.is_recording:
                self.recorded_data.append((timestamp, data))
        except Exception as e:
            print(f"处理接收数据时出错: {e}")
    
    def update_data_display(self, data):
        """更新数据显示"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        display_text = f"[{timestamp}] {data}\n"
        
        # 限制显示行数
        current_text = self.data_display.toPlainText()
        lines = current_text.split('\n')
        if len(lines) > 100:
            lines = lines[-100:]
            self.data_display.setPlainText('\n'.join(lines))
        
        self.data_display.append(display_text)
        
        # 滚动到底部
        cursor = self.data_display.textCursor()
        cursor.movePosition(cursor.End)
        self.data_display.setTextCursor(cursor)
    
    def update_stats_display(self):
        """更新统计显示"""
        self.stats_label.setText(f"接收字节: {self.bytes_received} | 数据点: {self.data_points}")
    
    def change_ui_frequency(self):
        """改变UI更新频率"""
        frequency = self.ui_freq_spin.value()
        self.ui_update_timer.setInterval(frequency)
        print(f"UI更新频率已调整为: {frequency}ms")
    
    def on_display_mode_changed(self):
        """显示模式改变事件"""
        mode = self.display_mode_combo.currentText()
        if mode == '时频图':
            self.ax.set_title("实时时频图")
            self.ax.set_xlabel("时间 (秒)")
            self.ax.set_ylabel("频率 (Hz)")
        else:
            self.ax.set_title("实时数据波形")
            self.ax.set_xlabel("时间 (秒)")
            self.ax.set_ylabel("数值")
        
        # 安全地清除颜色条
        try:
            if hasattr(self, 'colorbar') and self.colorbar is not None:
                self.colorbar.remove()
                self.colorbar = None
        except Exception as e:
            print(f"清除颜色条时出错: {e}")
        
        self.canvas.draw()
    
    def on_sample_rate_changed(self):
        """采样率改变事件"""
        self.sample_rate = self.sample_rate_spin.value()
        print(f"采样率已调整为: {self.sample_rate} Hz")
    
    def on_window_length_changed(self):
        """窗口长度改变事件"""
        self.window_length = self.window_length_spin.value()
        self.overlap = self.window_length // 2  # 自动设置重叠长度
        print(f"FFT窗口长度已调整为: {self.window_length} 点")
    
    def update_ui(self):
        """批量更新UI（由定时器调用）"""
        try:
            # 批量更新数据显示
            if self.pending_data:
                # 只显示最新的几条数据
                recent_data = self.pending_data[-10:]  # 只显示最新10条
                display_text = ""
                
                for timestamp, data in recent_data:
                    time_str = datetime.fromtimestamp(timestamp).strftime("%H:%M:%S.%f")[:-3]
                    display_text += f"[{time_str}] {data}\n"
                
                # 更新显示
                current_text = self.data_display.toPlainText()
                lines = current_text.split('\n')
                if len(lines) > 90:  # 保留90行，为新数据留空间
                    lines = lines[-90:]
                    self.data_display.setPlainText('\n'.join(lines))
                
                self.data_display.append(display_text)
                
                # 滚动到底部
                cursor = self.data_display.textCursor()
                cursor.movePosition(cursor.End)
                self.data_display.setTextCursor(cursor)
                
                # 清空待处理数据
                self.pending_data.clear()
            
            # 更新统计显示
            self.update_stats_display()
            
            # 显示加速度信息
            if hasattr(self, 'info_text') and len(self.acceleration_buffer) > 0:
                accel_values = [item[1] for item in self.acceleration_buffer]
                if len(accel_values) > 0:
                    try:
                        mean_accel = np.mean(accel_values)
                        std_accel = np.std(accel_values)
                        self.info_text.append(f"加速度统计: 均值={mean_accel:.3f}, 标准差={std_accel:.3f}")
                    except Exception as e:
                        print(f"计算加速度统计时出错: {e}")
            
            # 更新记录进度
            if self.is_recording:
                self.update_record_progress()
            
            # 性能监控
            self.ui_update_count += 1
            current_time = time.time()
            if current_time - self.last_perf_check >= 1.0:  # 每秒检查一次
                fps = self.ui_update_count / (current_time - self.last_perf_check)
                if fps < 8:  # 如果UI更新频率低于8Hz，显示警告
                    self.perf_label.setText(f"性能: 较慢 ({fps:.1f} FPS)")
                else:
                    self.perf_label.setText(f"性能: 正常 ({fps:.1f} FPS)")
                
                self.ui_update_count = 0
                self.last_perf_check = current_time
                
        except Exception as e:
            print(f"更新UI时出错: {e}")
    
    def update_plot(self, frame):
        """更新图表"""
        display_mode = self.display_mode_combo.currentText()
        
        if display_mode == '时频图':
            self.update_spectrogram()
        else:
            self.update_waveform()
        
        return []
    
    def update_spectrogram(self):
        """更新时频图"""
        if len(self.acceleration_buffer) < self.window_length:
            return
        
        try:
            # 获取加速度数据并转换为numpy数组
            accel_data = np.array([item[1] for item in self.acceleration_buffer])
            
            # 去除均值
            accel_data = accel_data - np.mean(accel_data)
            
            # 计算短时FFT
            frequencies, times, Sxx = signal.spectrogram(
                accel_data,
                fs=self.sample_rate,
                window='hann',
                nperseg=self.window_length,
                noverlap=self.overlap,
                scaling='density'
            )
            
            # 转换为dB
            Sxx_db = 10 * np.log10(Sxx + 1e-10)
            
            # 限制频率范围
            max_freq = self.max_freq_spin.value()
            if max_freq > 0 and max_freq <= self.sample_rate // 2:  # 确保不超过奈奎斯特频率
                freq_mask = frequencies <= max_freq
                frequencies = frequencies[freq_mask]
                Sxx_db = Sxx_db[freq_mask, :]
            
            # 清除旧图表
            self.ax.clear()
            
            # 绘制时频图
            im = self.ax.pcolormesh(times, frequencies, Sxx_db,
                                  cmap='viridis', shading='gouraud')
            
            # 设置标签和标题
            self.ax.set_xlabel('时间 (秒)')
            self.ax.set_ylabel('频率 (Hz)')
            self.ax.set_title('实时时频图 (加速度频谱)')
            self.ax.grid(True, alpha=0.3)
            
            # 添加颜色条
            try:
                if not hasattr(self, 'colorbar') or self.colorbar is None:
                    self.colorbar = self.figure.colorbar(im, ax=self.ax)
                    self.colorbar.set_label('功率谱密度 (dB/Hz)')
                else:
                    self.colorbar.update_normal(im)
            except Exception as e:
                print(f"创建或更新颜色条时出错: {e}")
                # 如果颜色条创建失败，继续执行但不显示颜色条
                pass
            
            # 刷新画布
            self.canvas.draw()
            
        except Exception as e:
            print(f"更新时频图时出错: {e}")
            # 如果时频图更新失败，尝试显示波形图
            try:
                self.update_waveform()
            except Exception as e2:
                print(f"更新波形图也失败: {e2}")
    
    def update_waveform(self):
        """更新波形图"""
        if not self.data_buffer:
            return
        
        # 获取最新的数据点
        max_points = 500  # 固定显示点数
        recent_data = list(self.data_buffer)[-max_points:]
        
        # 如果数据没有变化，跳过更新
        if len(recent_data) < 2:
            return
        
        times = [item[0] for item in recent_data]
        values = [item[1][0] if isinstance(item[1], list) else item[1] for item in recent_data]
        
        # 清除旧图表
        self.ax.clear()
        
        # 绘制新数据
        if times and values:
            # 将时间转换为相对时间
            start_time = times[0]
            relative_times = [t - start_time for t in times]
            
            # 使用更高效的绘图方式
            self.ax.plot(relative_times, values, 'b-', linewidth=0.8, alpha=0.8)
            
            self.ax.set_title("实时数据波形")
            self.ax.set_xlabel("时间 (秒)")
            self.ax.set_ylabel("数值")
            self.ax.grid(True, alpha=0.3)
        
        # 刷新画布
        self.canvas.draw()
    
    def clear_plot(self):
        """清除图表"""
        self.data_buffer.clear()
        self.acceleration_buffer.clear()
        self.ax.clear()
        
        # 根据显示模式设置标题
        mode = self.display_mode_combo.currentText()
        if mode == '时频图':
            self.ax.set_title("实时时频图")
            self.ax.set_xlabel("时间 (秒)")
            self.ax.set_ylabel("频率 (Hz)")
        else:
            self.ax.set_title("实时数据波形")
            self.ax.set_xlabel("时间 (秒)")
            self.ax.set_ylabel("数值")
        
        self.ax.grid(True, alpha=0.3)
        
        # 安全地清除颜色条
        try:
            if hasattr(self, 'colorbar') and self.colorbar is not None:
                # 使用更安全的方法移除颜色条
                self.colorbar.remove()
                self.colorbar = None
        except Exception as e:
            print(f"清除颜色条时出错: {e}")
            # 如果移除失败，尝试重新创建图表
            try:
                self.ax.figure.clear()
                self.ax = self.figure.add_subplot(111)
                self.ax.set_title("实时时频图")
                self.ax.set_xlabel("时间 (秒)")
                self.ax.set_ylabel("频率 (Hz)")
                self.ax.grid(True, alpha=0.3)
            except Exception as e2:
                print(f"重新创建图表时出错: {e2}")
        
        self.canvas.draw()
        
        # 重置统计信息
        self.bytes_received = 0
        self.data_points = 0
        self.update_stats_display()
    
    def toggle_recording(self):
        """切换记录状态"""
        if not self.is_recording:
            self.start_recording()
        else:
            self.stop_recording()
    
    def start_recording(self):
        """开始记录"""
        self.is_recording = True
        self.recorded_data = []
        self.record_btn.setText("停止记录")
        self.record_status.setText("正在记录...")
        self.record_progress.setVisible(True)
        self.record_progress.setValue(0)
    
    def stop_recording(self):
        """停止记录"""
        self.is_recording = False
        self.record_btn.setText("开始记录")
        self.record_status.setText(f"已记录 {len(self.recorded_data)} 个数据点")
        self.record_progress.setVisible(False)
        
        if self.recorded_data:
            self.save_btn.setEnabled(True)
    
    def update_record_progress(self):
        """更新记录进度"""
        if self.recorded_data:
            progress = min(100, len(self.recorded_data) // 10)
            self.record_progress.setValue(progress)
    
    def save_csv(self):
        """保存数据为CSV文件"""
        if not self.recorded_data:
            QMessageBox.warning(self, "警告", "没有数据可保存")
            return
        
        filename, _ = QFileDialog.getSaveFileName(
            self, "保存CSV文件", "", "CSV文件 (*.csv)"
        )
        
        if filename:
            try:
                with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                    writer = csv.writer(csvfile)
                    
                    # 写入表头
                    writer.writerow(['时间戳', '数值'])
                    
                    # 写入数据
                    for timestamp, data in self.recorded_data:
                        if isinstance(data, list):
                            value = data[0] if data else 0
                        else:
                            value = data
                        writer.writerow([timestamp, value])
                
                QMessageBox.information(self, "成功", f"数据已保存到 {filename}")
                
            except Exception as e:
                QMessageBox.critical(self, "错误", f"保存失败: {str(e)}")
    
    def on_serial_error(self, error_msg):
        """处理串口错误"""
        QMessageBox.critical(self, "串口错误", error_msg)
        self.disconnect_serial()
    
    def closeEvent(self, event):
        """窗口关闭事件"""
        self.disconnect_serial()
        event.accept()

def main():
    """主函数"""
    app = QApplication(sys.argv)
    app.setApplicationName("串口数据接收上位机")
    
    window = SerialMonitor()
    window.show()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
