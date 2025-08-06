%% 1. 参数配置
pcmFile  = 'test_audio_20250804_200927.pcm';   % 你的 PCM 文件
fs       = 8000;           % 采样率 Hz
nBits    = 16;             % 位深
nCh      = 1;              % 声道数
precision = 'int16';       % 16-bit 小端

%% 2. 读取 PCM
fid = fopen(pcmFile, 'rb');
y   = fread(fid, Inf, [precision '=>' precision]);   % 读为 int16
fclose(fid);

% 若多声道，需 reshape
if nCh > 1
    y = reshape(y, nCh, [])';   % 每行一个声道，取第 1 个声道做分析
end
y = double(y);                  % 转成 double 方便运算

%% 3. 绘制时频图（spectrogram）
% 参数可调：window / noverlap / nfft
win   = hamming(1024);          % 窗长
nfft  = 1024;
novlp = round(0.75*nfft);       % 75% 重叠

figure;
spectrogram(y, win, novlp, nfft, fs, 'yaxis');
title('PCM 时频图');
xlabel('时间 [s]');
ylabel('频率 [Hz]');
colorbar;

%% 4. （可选）播放验证
% soundsc(y, fs);