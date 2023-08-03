
# RX Characteristic (UUID: 6E400002-B5A3-F393-E0A9-E50E24DCCA9E) 
# The peer can send data to the device by writing to the RX Characteristic of the service. ATT Write Request or ATT Write Command can be used. The received data is sent on the UART interface. 
# TX Characteristic (UUID: 6E400003-B5A3-F393-E0A9-E50E24DCCA9E) 
# If the peer has enabled notifications for the TX Characteristic, the application can send data to the peer as notifications. The application will transmit all data received over UART as notifications.
# С ПК (или телефона) вычитываем характеристику TX Characteristic в ней будет массив из значений АЦП сложенных друг за другом. То есть первые два байта это канал 1, вторые два байта канал 2 и тд до 32 канала. Возможно для ускорения обмена - буду присылать сразу по 2-3 отсчета. То есть массив будет кратен 64 байтам (32 канала по 2 байта), но не более 192 байт в одной посылке.
# Принимать данные буду из RX Characteristic в нем надо будет присылать данные для конфигурирования АЦП. В идеале это структура вида
# #pragma pack(1)
#  struct adc_config_struct {
#  uint32_t samplrate_hz;
#  uint32_t low_band;
#  uint32_t high_band;
#  uint32_t dsp_enable;
#  uint32_t dsp_code_value;
#  uint32_t channel_count;
# };
# Где 
# samplrate_hz - частота семплирования в герцах
# dsp_enable - 1 либо 0
# high_band номер строки настройки из таблицы с 25 страницы даташита
# low_band номер строки настройки из таблицы с 26 страницы даташита
# channel_count - количество активных каналов (пока всегда 32)
#
# первые два байта это frame_counter и количество активных каналов. 
# Если frame_counter приходит первым байтом - значит все принимаемые и передаваемые данные надо разворачивать (младший и старший байт менять местами)
# Можно попробовать попередавать данные в плату. 
# На вашей прошивке должно принимать samplrate_hz
# Возможные значения: 1000, 500, 250, 125, 62
# При этом если значение применилось - данные будут прилетать с разными интервалами и будет возвращаться разное количество активных каналов
# При 
# 1000 Гц - 2 канала
# 500 Гц - 4 канала
# 250 Гц - 8 каналов
# 125 Гц - 16 каналов
# 62 Гц - 32 канала
# Принимать данные буду из RX Characteristic в нем надо будет присылать данные для конфигурирования АЦП. В идеале это структура вида
# #pragma pack(1)
#  struct adc_config_struct {
#  uint32_t samplrate_hz;
#  uint32_t low_band;
#  uint32_t high_band;
#  uint32_t dsp_enable;
#  uint32_t dsp_code_value;
#  uint32_t channel_count;
# };
# не забывайте переворачивать байты на приеме и отправке, на x86 и arm они по разному должны быть
#
#
#
# 6 * 4
# массив - 4 байта,
#
# 00, 00, 00, 00, ... 00, 00, 00, 00
# --------------      --------------
#  sample rate         channel_count
#
# 1000 - 0x3E8
# 500
#
#
# 1000 - 0x03E8
# E8, 03, 00, 00, ... 00, 00, 00, 00
#
# 500 - 0x1F4
# F4, 01, 00, 00, ... 00, 00, 00, 00
#
#


import asyncio
from bleak import BleakClient
import csv
from array import *
from datetime import datetime
import sys
import keyboard 
import time


#address = "E2:7A:CF:B5:80:96"
address = "D5:57:15:07:1D:A6"
tx_char = "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"
rx_char = "6E400002-B5A3-F393-E0A9-E50E24DCCA9E"

freq_values = [1000, 500, 250, 125, 62]  # допустимые частоты дискретизации
freq_ch_num = [   2,   4,   8,  16, 32]  # количество каналов на каждой частоте


res_file_name = ""
res_file_name_base = "mouse_ble"
res_file_ext = "csv"

proc_active = 0
frame_cnt = 0

data_cnt = 0


#32 канала
frame_list = []
ch_data = [[],[],[],[],[],[],[],[],[],[], [],[],[],[],[],[],[],[],[],[], [],[],[],[],[],[],[],[],[],[], [],[]]  

def update_ch_data(data, ch_num, frame_num):
  global ch_data
  global frame_list
  # global data_cnt
  
  ch_rpt = int(((len(data) - 2) / 2) / ch_num)
  
  for i in range(ch_num): # для каждого канала из набора данных
    b_pos = i * 2 + 2
    
    for j in range(ch_rpt):
      int_val = ((data[b_pos + 1] << 8) | data[b_pos])
      ch_data[i].append(int_val) 
      b_pos += ch_num * 2 # по 2 байта на канал

      if i == 0: # для каждого значения канала пишем номер кадра, в котором значение пришло, пишем только для канала 0
        frame_list.append(frame_num)
        # data_cnt += 1



def save_data():
  global ch_data
  global frame_list
  global data_cnt
  
  f = open(res_file_name, 'a', newline = '') # open the file in the append mode
  writer = csv.writer(f, delimiter = ';')    # create the csv writer
  
  for i in range(len(ch_data[0])):  # количество значений для каждого канала
    
    data_row = []
    data_row.append(frame_list[i]) # 
    
    for j in range(32): # проходим по всем каналам
      if i < len(ch_data[j]):
        data_row.append(ch_data[j][i])
      else:
        data_row.append(0)      

    writer.writerow(data_row)      # write a row to the csv file
    
    data_cnt += 1
  
  f.close() # close the file

  #print(".", end = "")  

  frame_list.clear()
  for i in range(32):
    ch_data[i].clear()
    
    

def tx_callback(handle, data):
  global frame_cnt
  global proc_active
  
  #первые 2 байта - номер кадра и количество каналов
  channels_num = data[1];
  frame_num = data[0];
  
  update_ch_data(data, channels_num, frame_num)
  
  #print("FN ", frame_num, ", CN ", channels_num, ", DL ", len(data), ", ", end = "")  
  
  frame_cnt += 1
  if (frame_cnt > 100):
    frame_cnt = 0
    save_data()


def get_cur_date():
  date_str = ""
  # текущие дата и время для именования файла данных, формат имени: ble_mouse_YYYY_mm_dd_HH-MM-ss.csv
  cdt = datetime.now()
  c_date = str(cdt.year) + "_" + str(cdt.month).zfill(2) + "_" + str(cdt.day).zfill(2)
  c_time = str(cdt.hour).zfill(2) + "-" + str(cdt.minute).zfill(2) + "-" + str(cdt.second).zfill(2)
  date_str = c_date + "_" + c_time
  return date_str


def check_params(argv):
  result = {}
  u_freq = 0
  adc_freq = 0
  ch_list = []
  params_error = 0
  error_text = ""
  
  if len(argv) > 1: # есть параметры в командной строке
    
    u_freq = int(argv[1]) # превым параметром ожидаем частоту дискретизации
    
    if (u_freq in freq_values): # частота должна быть в списке допустимых значений
      adc_freq = u_freq
      fi = freq_values.index(adc_freq) 
      
      if adc_freq == freq_values[len(freq_values) - 1]: # если выбрана минимальная частота, включаем все каналы, номера указывать не надо
        
        ch_list.clear()     
        for i in range(freq_ch_num[fi]):
          ch_list.append(i)
        
      else:

        u_ch_cnt = freq_ch_num[fi]  # ожидаемое количество каналов
      
        if len(argv) > u_ch_cnt + 1:
          ch_list.clear()
          max_ch_num = freq_ch_num[len(freq_ch_num) - 1] - 1   # максимальный номер канала
        
          for i in range(u_ch_cnt):
            if int(argv[2 + i]) > max_ch_num: # номер канала больше допустимого
              params_error = 1
            
              error_text = "Wrong chnnel number - " + argv[2 + i] + ", max number - " + str(max_ch_num)
            
              break
            else:
              ch_list.append(int(argv[2 + i])) # номер канала в норме, добавляем в список
            
        else:
          params_error = 2      
          error_text = "Wrong number of channels!\r\nFor a sample rate of " + str(adc_freq) + "Hz, the number of channels sould be " + str(u_ch_cnt)
      
    else:
      params_error = 3
      
      error_text = "The sample rate is incorrect (" + str(u_freq) + ")! Valid values are: "
      
      for i in range(len(freq_values)):
        error_text += str(freq_values[i])
        if (i < len(freq_values) - 1):
          error_text += ", "
        else:
          error_text += "\r\n"
          
  ch_list_str = ""
  if params_error == 0:        
    for i in range(len(ch_list)):
      ch_list_str += str(ch_list[i])
      if (i < len(ch_list) - 1):
        ch_list_str += ", "
      else:
        ch_list_str += "\r\n"
          
  result['freq'] = adc_freq
  result['channels'] = ch_list
  result['channels_str'] = ch_list_str
  result['error'] = params_error
  result['error_text'] = error_text
  
  return result
     

def get_manual_msg():
  man_str = "\r\n"
  
  man_str += "Parameter input error!\r\n\r\n"
  man_str += "Call syntax:\r\n"
  man_str += "ble_mouse.py SR Channel1 Channel2 ... ChannelN\r\n"
  man_str += "where\r\n"
  man_str += "SR - sample rate, valid values: 1000, 500, 250, 125, 62\r\n"
  man_str += "Channel1-ChannelN - list of channels\r\n"
  man_str += "Depending on the selected sample rate, the following number of channels are expected:\r\n"
  man_str += "1000Hz - 2 channels\r\n"
  man_str += "500Hz - 4 channels\r\n"
  man_str += "250Hz - 8 channels\r\n"
  man_str += "125Hz - 16 channels\r\n"
  man_str += "62Hz - no channel numbers, read all 32 channels\r\n"
  
  return man_str  
 

async def main():
  global proc_active
  global frame_list
  global res_file_name

  res_file_name = res_file_name_base + "_" + get_cur_date() + "." + res_file_ext
  
  def_freq_ind = 0                         # индекс частоты по умолчанию
  
  adc_freq = freq_values[def_freq_ind]  # частота дискретизации, по умолчанию 1000Гц
  ch_list = [] # список каналов
  
  for i in range(freq_ch_num[def_freq_ind]):
    ch_list.append(i)        # кналы по умолчанию с 0
  
  params_error = 0
  
  params_res = check_params(sys.argv)
  if int(params_res.get('error')) != 0:
    print("\r\n" + params_res.get('error_text'))
    print(get_manual_msg())
    return  
  else:
    adc_freq = params_res.get('freq')
    ch_list = params_res.get('channels')
    print("\r\nSample rate " + str(adc_freq) + ", channels: " + params_res.get('channels_str'))
    print("Data save file: ", res_file_name, "\r\n")

  connect_try_cnt = 0
  exit_state = 0   
  old_d_c = 0
  
  while True:
    try:
      connect_try_cnt += 1
      
      async with BleakClient(address) as client:
          print("Searching device...")

          if (not client.is_connected):
            raise "Failed to connect to device"

          print("Device connected")

          services = await client.get_services()

          params_data = bytearray(32)

          p_dtb = adc_freq.to_bytes(4, "little") 
          for i in range(4):
            params_data[i] = p_dtb[i]

          print("Writing parameters...", end = "")
          await client.write_gatt_char(rx_char, params_data, response = True) 
          print("...")
          await client.write_gatt_char(rx_char, params_data, response = True) 

          print("Enabling notification...")
          await client.start_notify(tx_char, tx_callback)

          print("Receiving data...\r\nPress and hold space to exit")

          proc_active = 1
          while proc_active > 0:
           
            if keyboard.is_pressed("Space"):  
              print("Exit")
              proc_active = 0
  
            await asyncio.sleep(0.1)
            
            if (proc_active < 1):
            
              exit_state = 1
              print("Disabling notification...")
              await client.stop_notify(tx_char)
            
              print("\r\nProgram ended\r\nValues saved:", data_cnt)
              
              for i in range(5):
                keyboard.press_and_release('backspace')

              return # завершение программы
              
            else:
              if data_cnt > old_d_c:
                old_d_c = data_cnt
                print(".", end = "")
      
    except:
      if exit_state > 0:
        return
      else:  
        print("Connection error")
        if connect_try_cnt > 4:
          print("Error! Failed to connect to the device.")
          return
        else:
          #asyncio.sleep(3)
          time.sleep(3)
  

if __name__ == '__main__':
  asyncio.run(main())









