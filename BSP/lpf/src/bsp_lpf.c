#include "bsp_lpf.h"

simple_lowpass_filter_t lowpass_filter;

/**
 * @brief 初始化低通滤波器
 */
void init_lowpass_filter(void)
{
    lowpass_filter.prev_output = 0;
    lowpass_filter.alpha = ALPHA;
    lowpass_filter.min_val = -32768;
    lowpass_filter.max_val = 32767;
}

/**
 * @brief 单点低通滤波
 * @param input 输入样本
 * @return 滤波后的输出样本
 */
int16_t filter_sample(int16_t input)
{
    // 转换为浮点数进行计算
    float32_t input_float = (float32_t)input;
    float32_t prev_output_float = (float32_t)lowpass_filter.prev_output;
    
    // 低通滤波公式: y[n] = α * x[n] + (1-α) * y[n-1]
    float32_t output_float = lowpass_filter.alpha * input_float + 
                             (1.0f - lowpass_filter.alpha) * prev_output_float;
    
    // 限制范围并转换回int16_t
    if (output_float > lowpass_filter.max_val) output_float = lowpass_filter.max_val;
    if (output_float < lowpass_filter.min_val) output_float = lowpass_filter.min_val;
    
    int16_t output = (int16_t)output_float;
    
    // 更新状态
    lowpass_filter.prev_output = output;
    
    return output;
}

/**
 * @brief 批量处理低通滤波
 * @param input 输入数据数组
 * @param output 输出数据数组
 * @param size 数据大小
 */
void filter_block(int16_t* input, int16_t* output, uint32_t size)
{
    for (uint32_t i = 0; i < size; i++)
    {
        output[i] = filter_sample(input[i]);
    }
}
