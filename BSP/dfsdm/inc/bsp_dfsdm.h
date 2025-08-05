#ifndef __BSP_DFSDM_H
#define __BSP_DFSDM_H

#include "stm32h7xx_hal.h"
#include "stdint.h"
#include "usart.h"

#define SAMPLE_FREQUENCY            8000
#define BYTE_PER_SAMPLE             2
#define MICROPHEN_NUMBER            1
#define FRAME_NUMBER                1

#define BUF_LENGTH                 (SAMPLE_FREQUENCY / 1000 * MICROPHEN_NUMBER * FRAME_NUMBER)

#endif
