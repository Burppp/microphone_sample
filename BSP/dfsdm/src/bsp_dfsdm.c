#include "bsp_dfsdm.h"

extern UART_HandleTypeDef huart1;

int16_t dfsdm_buf[BUF_LENGTH] = {0x12};

void HAL_DFSDM_FilterRegConvHalfCpltCallback(DFSDM_Filter_HandleTypeDef *hdfsdm_filter)
{
    HAL_UART_Transmit_DMA(&huart1, (uint8_t *)dfsdm_buf, BUF_LENGTH);
}

void HAL_DFSDM_FilterRegConvCpltCallback(DFSDM_Filter_HandleTypeDef *hdfsdm_filter)
{
  HAL_UART_Transmit_DMA(&huart1, (uint8_t *)(dfsdm_buf + BUF_LENGTH / 2), BUF_LENGTH);
}
