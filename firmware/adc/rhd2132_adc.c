/*
 * rhd2132_adc.c
 *
 *  Created on: Mar 16, 2021
 *      Author: Dmitriy
 */
#include "stdint.h"
#include "nrf_drv_spi.h"
#include "rhd2132_adc.h"
#include "nrf_gpio.h"
#include "nrf_delay.h"

extern const nrf_drv_spi_t spi;
extern volatile bool spi_xfer_done;

ret_code_t code = 0;
uint8_t reg;

uint8_t spi2_tx_data_8[2];
uint8_t spi2_rx_data_8[2];

uint16_t spi2_tx_data;
uint16_t spi2_rx_data;

struct up_band_struct up_band[17] = {
		{20000, 8, 0, 4, 0},
		{15000, 11, 0, 8, 0},
		{10000, 17, 0, 16, 0},
		{7500, 22, 0, 23, 0},
		{5000, 33, 0, 37, 0},
		{3000, 3, 1, 13, 1},
		{2500, 13, 1, 25, 1},
		{2000, 27, 1, 44, 1},
		{1500, 1, 2, 23, 2},
		{1000, 46, 2, 30, 3},
		{750, 41, 3, 36, 4},
		{500, 30, 5, 43, 6},
		{300, 6, 9, 2, 11},
		{250, 42, 10, 5, 13},
		{200, 24, 13, 7, 16},
		{150, 44, 17, 8, 21},
		{100, 38, 26, 5, 31}
};

struct low_band_struct low_band[25] = {
		{500000, 13, 0, 0},
		{300000, 15, 0, 0},
		{250000, 17, 0, 0},
		{200000, 18, 0, 0},
		{150000, 21, 0, 0},
		{100000, 25, 0, 0},
		{75000, 28, 0, 0},
		{50000, 34, 0, 0},
		{30000, 44, 0, 0},
		{25000, 48, 0, 0},
		{20000, 54, 0, 0},
		{15000, 62, 0, 0},
		{10000, 5, 1, 0},
		{7500, 18, 1, 0},
		{5000, 40, 1, 0},
		{3000, 20, 2, 0},
		{2500, 42, 2, 0},
		{2000, 8, 3, 0},
		{1500, 9, 4, 0},
		{1000, 44, 6, 0},
		{750, 49, 9, 0},
		{500, 35, 17, 0},
		{300, 1, 40, 0},
		{250, 56, 54, 0},
		{100, 16, 60, 1}
};

/* Возвращает значение конвертации канала, запущенное 2 запроса назад
 * иными словами:
 * отправляем запрос на конвертацию канала 1 - получаем ничего
 * отправляем запрос на конвертацию канала 2 - получаем ничего
 * отправляем запрос на конвертацию канала 3 - получаем данные канала 1
 * отправляем запрос на конвертацию канала 4 - получаем данные канала 2
 * и так далее
 *  */
uint16_t convert(uint8_t channel)
{
	uint16_t retval = 0;
	spi2_tx_data = 0x0000;
	spi2_tx_data |= ((uint16_t)channel << 8) & 0xff00;
	
	spi2_tx_data_8[0] = 0x00;
	spi2_tx_data_8[0] |= channel;
	nrf_gpio_pin_clear(SPI_SS_PIN);
	nrf_drv_spi_transfer(&spi, spi2_tx_data_8, 2, spi2_rx_data_8, 2);
	nrf_gpio_pin_set(SPI_SS_PIN);
	retval = spi2_rx_data_8[0] << 8 | spi2_rx_data_8[1];
	return retval;
}

int rhd2132_write_register(uint8_t reg_addr, uint8_t reg_value)
{
	int retval = -1;
	spi2_tx_data_8[0] = 0x80;
	spi2_tx_data_8[0] |= reg_addr;
	spi2_tx_data_8[1] = reg_value;
	nrf_gpio_pin_clear(SPI_SS_PIN);
	code = nrf_drv_spi_transfer(&spi, spi2_tx_data_8, 2, spi2_rx_data_8, 2);
	nrf_gpio_pin_set(SPI_SS_PIN);
	retval = 1;
	return retval;
}

int rhd2132_read_register(uint8_t reg_addr, uint8_t *reg_value)
{
	int retval = -1;
	spi2_tx_data_8[0] = 0xc0;
	spi2_tx_data_8[0] |= reg_addr;
	spi2_tx_data_8[1] = 0x00;
	nrf_gpio_pin_clear(SPI_SS_PIN);
	code = nrf_drv_spi_transfer(&spi, spi2_tx_data_8, 2, spi2_rx_data_8, 2);
	nrf_gpio_pin_set(SPI_SS_PIN);
	spi2_tx_data_8[0] = 0x00;
	spi2_tx_data = 0;
	nrf_gpio_pin_clear(SPI_SS_PIN);
	nrf_drv_spi_transfer(&spi, spi2_tx_data_8, 2, spi2_rx_data_8, 2);
	nrf_gpio_pin_set(SPI_SS_PIN);
	spi2_tx_data = 0;
	nrf_gpio_pin_clear(SPI_SS_PIN);
	nrf_drv_spi_transfer(&spi, spi2_tx_data_8, 2, spi2_rx_data_8, 2);
	nrf_gpio_pin_set(SPI_SS_PIN);
	*reg_value = spi2_rx_data_8[1] >> 8;
	retval = 1;
	return retval;
}

void reinit_rhd2132(struct adc_config_struct *adc)
{
	uint8_t regval;
	uint8_t value_numb;
		regval = adc->dsp_code_value;
	regval |= 0x80;
	if (adc->dsp_enable == 1) {
		regval |= 0x10;
	}
	rhd2132_write_register(4, regval);
		for (value_numb = 0; value_numb < 17; value_numb++)
	{
		if (up_band[value_numb].up_band == adc->high_band) {
			rhd2132_write_register(8, up_band[value_numb].rh1_dac1);
			rhd2132_write_register(9, up_band[value_numb].rh1_dac2);
			rhd2132_write_register(10, up_band[value_numb].rh2_dac1);
			rhd2132_write_register(11, up_band[value_numb].rh2_dac2);
		} else {
			rhd2132_write_register(8, 38);
			rhd2132_write_register(9, 26);
			rhd2132_write_register(10, 5);
			rhd2132_write_register(11, 31);
		}
	}
	for (value_numb = 0; value_numb < 25; value_numb++)
	{
		if (low_band[value_numb].low_band == adc->low_band) {
			rhd2132_write_register(12, low_band[value_numb].rl_dac1);
			rhd2132_write_register(13, (low_band[value_numb].rl_dac3 << 6) | low_band[value_numb].rl_dac2);
		} else {
			rhd2132_write_register(12, 16);
			rhd2132_write_register(13, 60);
		}
	}
	convert(0);
	convert(1);
}

void init_rhd2132(struct adc_config_struct *adc)
{
	uint8_t regval;
	uint8_t value_numb;
	
	nrf_gpio_cfg_output(SPI_SS_PIN);
	nrf_gpio_cfg_output(ANALOG_ENABLE_PIN);
	nrf_gpio_pin_set(SPI_SS_PIN);
	nrf_gpio_pin_set(ANALOG_ENABLE_PIN);
	//nrf_delay_ms(100);
	
	//40 - 44 регистры - надпись INTAN
	//code = rhd2132_read_register(40, &reg);

	/* ADC config */
	rhd2132_write_register(0, 0xDE);
	rhd2132_write_register(1, 0x20);
	rhd2132_write_register(2, 0x28);
	rhd2132_write_register(3, 0);
	regval = adc->dsp_code_value;
	regval |= 0x80;
	if (adc->dsp_enable == 1) {
		regval |= 0x10;
	}
	rhd2132_write_register(4, regval);
	rhd2132_write_register(5, 0);
	rhd2132_write_register(6, 0);
	rhd2132_write_register(7, 0);
	for (value_numb = 0; value_numb < 17; value_numb++)
	{
		if (up_band[value_numb].up_band == adc->high_band) {
			rhd2132_write_register(8, up_band[value_numb].rh1_dac1);
			rhd2132_write_register(9, up_band[value_numb].rh1_dac2);
			rhd2132_write_register(10, up_band[value_numb].rh2_dac1);
			rhd2132_write_register(11, up_band[value_numb].rh2_dac2);
		} else {
			rhd2132_write_register(8, 38);
			rhd2132_write_register(9, 26);
			rhd2132_write_register(10, 5);
			rhd2132_write_register(11, 31);
		}
	}

	for (value_numb = 0; value_numb < 25; value_numb++)
	{
		if (low_band[value_numb].low_band == adc->low_band) {
			rhd2132_write_register(12, low_band[value_numb].rl_dac1);
			rhd2132_write_register(13, (low_band[value_numb].rl_dac3 << 6) | low_band[value_numb].rl_dac2);
		} else {
			rhd2132_write_register(12, 16);
			rhd2132_write_register(13, 60);
		}
	}

	rhd2132_write_register(14, 0xff);
	rhd2132_write_register(15, 0xff);
	rhd2132_write_register(16, 0xff);
	rhd2132_write_register(17, 0xff);
	convert(0);
	convert(1);
}
