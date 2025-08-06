function workspace_fft()
% 工作空间FFT分析脚本
% 使用工作空间内的变量进行FFT分析
% 需要工作空间中有时间戳和数值数据

clc; clear; close all;

fprintf('=== 工作空间FFT分析工具 ===\n');

% 获取工作空间变量
vars = who;
fprintf('工作空间变量:\n');
for i = 1:length(vars)
    fprintf('  %d. %s\n', i, vars{i});
end

% 查找可能的数据变量
data_vars = {};
time_vars = {};

for i = 1:length(vars)
    var_name = vars{i};
    var_data = eval(var_name);
    
    if isnumeric(var_data) && isvector(var_data)
        if length(var_data) > 10  % 假设数据长度大于10
            data_vars{end+1} = var_name;
        end
    end
end

fprintf('\n找到的数值变量:\n');
for i = 1:length(data_vars)
    var_name = data_vars{i};
    var_data = eval(var_name);
    fprintf('  %d. %s (长度: %d)\n', i, var_name, length(var_data));
end

if isempty(data_vars)
    fprintf('未找到合适的数据变量\n');
    return;
end

% 选择数据变量
if length(data_vars) == 1
    data_var_name = data_vars{1};
    fprintf('自动选择变量: %s\n', data_var_name);
else
    data_idx = input('请选择数据变量编号: ');
    if data_idx < 1 || data_idx > length(data_vars)
        fprintf('无效的选择\n');
        return;
    end
    data_var_name = data_vars{data_idx};
end

% 获取数据
data = eval(data_var_name);
fprintf('选择的数据变量: %s (长度: %d)\n', data_var_name, length(data));

% 检查是否有时间变量
time_var_name = '';
for i = 1:length(vars)
    var_name = vars{i};
    if contains(lower(var_name), 'time') || contains(lower(var_name), 'timestamp')
        time_var_name = var_name;
        break;
    end
end

if ~isempty(time_var_name)
    time_data = eval(time_var_name);
    fprintf('找到时间变量: %s\n', time_var_name);
    
    % 检查时间数据长度是否匹配
    if length(time_data) == length(data)
        fprintf('时间数据长度匹配\n');
        use_time = true;
    else
        fprintf('时间数据长度不匹配，将使用索引作为时间\n');
        use_time = false;
    end
else
    fprintf('未找到时间变量，将使用索引作为时间\n');
    use_time = false;
end

% 获取采样率
if use_time
    % 从时间数据计算采样率
    dt = diff(time_data);
    if length(dt) > 0
        avg_dt = mean(dt);
        sample_rate = 1 / avg_dt;
        fprintf('从时间数据计算的采样率: %.2f Hz\n', sample_rate);
    else
        sample_rate = input('请输入采样率 (Hz): ');
    end
else
    sample_rate = input('请输入采样率 (Hz): ');
end

% 数据预处理
N = length(data);
if mod(N, 2) == 1
    % 如果是奇数，去掉最后一个点
    data = data(1:end-1);
    if use_time
        time_data = time_data(1:end-1);
    end
    N = N - 1;
    fprintf('调整为偶数个数据点: %d\n', N);
end

% 应用窗函数
window_type = input('选择窗函数 (1:矩形窗, 2:汉宁窗, 3:汉明窗) [默认: 1]: ');
if isempty(window_type)
    window_type = 1;
end

switch window_type
    case 1
        window_data = ones(N, 1);
        window_name = '矩形窗';
    case 2
        window_data = hann(N);
        window_name = '汉宁窗';
    case 3
        window_data = hamming(N);
        window_name = '汉明窗';
    otherwise
        window_data = ones(N, 1);
        window_name = '矩形窗';
end

% 应用窗函数
data_windowed = data .* window_data;

% 执行FFT
fft_result = fft(data_windowed, N);
fft_magnitude = abs(fft_result);

% 计算频率轴
freq = (0:N-1) * sample_rate / N;

% 只取正频率部分（前一半）
half_N = N/2;
freq_positive = freq(1:half_N);
magnitude_positive = fft_magnitude(1:half_N);

% 计算功率谱密度
psd = magnitude_positive.^2 / (sample_rate * N);

% 找到主要频率成分
peak_indices = find_peaks(magnitude_positive);

% 显示分析结果
fprintf('\n=== FFT分析结果 ===\n');
fprintf('数据变量: %s\n', data_var_name);
if use_time
    fprintf('时间变量: %s\n', time_var_name);
end
fprintf('窗函数: %s\n', window_name);
fprintf('采样率: %.2f Hz\n', sample_rate);
fprintf('数据点数: %d\n', N);
fprintf('频率分辨率: %.2f Hz\n', sample_rate/N);
fprintf('最大频率: %.1f Hz\n', sample_rate/2);

fprintf('\n主要频率成分:\n');
for i = 1:min(10, length(peak_indices))
    idx = peak_indices(i);
    freq_val = freq_positive(idx);
    magnitude_val = magnitude_positive(idx);
    fprintf('  %d. 频率: %.2f Hz, 幅度: %.2f\n', i, freq_val, magnitude_val);
end

% 绘制频谱图
plot_spectrum(freq_positive, magnitude_positive, psd, sample_rate, data_var_name);

% 保存结果到工作空间
assignin('base', 'fft_freq', freq_positive);
assignin('base', 'fft_magnitude', magnitude_positive);
assignin('base', 'fft_psd', psd);
assignin('base', 'fft_sample_rate', sample_rate);
assignin('base', 'fft_peaks', peak_indices);

fprintf('\n结果已保存到工作空间:\n');
fprintf('  fft_freq: 频率数组\n');
fprintf('  fft_magnitude: 幅度数组\n');
fprintf('  fft_psd: 功率谱密度\n');
fprintf('  fft_sample_rate: 采样率\n');
fprintf('  fft_peaks: 峰值索引\n');

end

function peak_indices = find_peaks(magnitude)
% 找到频谱中的峰值
threshold = max(magnitude) * 0.1; % 阈值设为最大值的10%
peaks = [];

for i = 2:length(magnitude)-1
    if magnitude(i) > magnitude(i-1) && ...
       magnitude(i) > magnitude(i+1) && ...
       magnitude(i) > threshold
        peaks = [peaks; i];
    end
end

% 按幅度排序
[~, sort_idx] = sort(magnitude(peaks), 'descend');
peak_indices = peaks(sort_idx);

end

function plot_spectrum(freq, magnitude, psd, sample_rate, data_var_name)
% 绘制频谱图

figure('Name', 'FFT频谱分析', 'Position', [100, 100, 1200, 800]);

% 线性坐标频谱图
subplot(2, 2, 1);
plot(freq, magnitude, 'b-', 'LineWidth', 1);
xlabel('频率 (Hz)');
ylabel('幅度');
title('FFT频谱分析 (线性坐标)');
grid on;
xlim([0, max(freq)]);

% 自适应Y轴范围
if ~isempty(magnitude)
    max_mag = max(magnitude);
    min_mag = min(magnitude);
    if max_mag > min_mag
        margin = (max_mag - min_mag) * 0.1;
        ylim([max(0, min_mag - margin), max_mag + margin]);
    end
end

% 对数坐标频谱图
subplot(2, 2, 2);
semilogy(freq, magnitude, 'r-', 'LineWidth', 1);
xlabel('频率 (Hz)');
ylabel('幅度 (对数)');
title('FFT频谱分析 (对数坐标)');
grid on;
xlim([0, max(freq)]);

% 功率谱密度
subplot(2, 2, 3);
plot(freq, psd, 'g-', 'LineWidth', 1);
xlabel('频率 (Hz)');
ylabel('功率谱密度');
title('功率谱密度');
grid on;
xlim([0, max(freq)]);

% 自适应Y轴范围
if ~isempty(psd)
    max_psd = max(psd);
    min_psd = min(psd);
    if max_psd > min_psd
        margin = (max_psd - min_psd) * 0.1;
        ylim([max(0, min_psd - margin), max_psd + margin]);
    end
end

% 对数坐标功率谱密度
subplot(2, 2, 4);
semilogy(freq, psd, 'm-', 'LineWidth', 1);
xlabel('频率 (Hz)');
ylabel('功率谱密度 (对数)');
title('功率谱密度 (对数坐标)');
grid on;
xlim([0, max(freq)]);

% 添加总标题
sgtitle(sprintf('FFT频谱分析 - %s', data_var_name), 'FontSize', 14);

% 保存图片
timestamp = datestr(now, 'yyyymmdd_HHMMSS');
plot_filename = sprintf('fft_spectrum_%s_%s.png', data_var_name, timestamp);
saveas(gcf, plot_filename);
fprintf('频谱图已保存到: %s\n', plot_filename);

end 