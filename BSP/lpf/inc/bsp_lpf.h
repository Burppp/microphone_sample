#ifndef __BSP_LPF_H
#define __BSP_LPF_H

#include "arm_math.h"
#include "string.h"
#include "stdint.h"

/* 滤波器参数定义 */
#define SAMPLE_RATE       48000   // 采样频率
#define CUTOFF_FREQ       5000    // 截止频率 (Hz)
#define BLOCK_SIZE        128     // 处理块大小

/* 滤波器系数计算 */
#define ALPHA             (1.0f / (1.0f + 2.0f * PI * CUTOFF_FREQ / SAMPLE_RATE))

/* 滤波器状态 */
typedef struct 
{
    int16_t prev_output;  // 前一个输出值
    float32_t alpha;      // 滤波系数
    int16_t min_val;      // 最小值限制
    int16_t max_val;      // 最大值限制
} simple_lowpass_filter_t;

void init_lowpass_filter(void);
int16_t filter_sample(int16_t input);
void filter_block(int16_t* input, int16_t* output, uint32_t size);

#endif
