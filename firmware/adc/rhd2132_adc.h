/*
 * rhd2132_adc.h
 *
 *  Created on: Mar 16, 2021
 *      Author: Dmitriy
 */

#ifndef RHD2132_ADC_H_
#define RHD2132_ADC_H_

#define SPI_SS_PIN 18
#define ANALOG_ENABLE_PIN 20

#pragma pack(1)
struct up_band_struct {
	uint32_t up_band;
	uint8_t rh1_dac1;
	uint8_t rh1_dac2;
	uint8_t rh2_dac1;
	uint8_t rh2_dac2;
};

#pragma pack(1)
struct low_band_struct {
	uint32_t low_band;
	uint8_t rl_dac1;
	uint8_t rl_dac2;
	uint8_t rl_dac3;
};

#pragma pack(1)
struct adc_config_struct {
	uint32_t samplrate_hz;
	uint32_t low_band;
	uint32_t high_band;
	uint32_t dsp_enable;
	uint32_t dsp_code_value;
	uint32_t channel_count;
};

uint16_t convert(uint8_t channel);
int rhd2132_write_register(uint8_t reg_addr, uint8_t reg_value);
int rhd2132_read_register(uint8_t reg_addr, uint8_t *reg_value);
void init_rhd2132(struct adc_config_struct *adc);
void reinit_rhd2132(struct adc_config_struct *adc);

#endif /* RHD2132_ADC_H_ */
