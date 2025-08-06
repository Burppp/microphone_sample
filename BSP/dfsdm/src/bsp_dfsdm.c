#include "bsp_dfsdm.h"

extern UART_HandleTypeDef huart1;

int16_t Buf_Mic0[BUF_LENGTH];
int16_t Buf_Mic1[BUF_LENGTH];

void HAL_DFSDM_FilterRegConvHalfCpltCallback(DFSDM_Filter_HandleTypeDef *hdfsdm_filter)
{
	if(hdfsdm_filter == &hdfsdm1_filter0)
	{
		
	}
	else if(hdfsdm_filter == &hdfsdm1_filter1)
	{
		HAL_UART_Transmit_DMA(&huart1, (uint8_t *)Buf_Mic1, BUF_LENGTH);
	}
}

void HAL_DFSDM_FilterRegConvCpltCallback(DFSDM_Filter_HandleTypeDef *hdfsdm_filter)
{
	if(hdfsdm_filter == &hdfsdm1_filter0)
	{
		
	}
	else if(hdfsdm_filter == &hdfsdm1_filter1)
	{
		HAL_UART_Transmit_DMA(&huart1, (uint8_t *)(Buf_Mic1 + BUF_LENGTH / 2), BUF_LENGTH);
	}
}
