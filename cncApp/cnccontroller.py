# -*- coding: utf-8 -*-

import serial, time, configparser, os, numpy
from cncparser import CncCodeParser

class CncControllerException(Exception):
    '''CNC Controller Exception'''
    def __init__(self, err):
        self.error_code = err
        
        self.error_message = ":不明な例外が発生しました"
        if err == 'e00':
            self.error_message = ":設定ファイルが読み込めません"
        elif err == 'e01':
            self.error_message = ":コントローラのステイタスが不正です"
        elif err == 'e02':
            self.error_message = ":コントローラに接続されていません"
        elif err == 's01':
            self.error_message = ":ポートにアクセスできません"
    
    def set_error(self, cnc):
        print(self.error_code, self.error_message)
        cnc.is_error = True
        cnc.error_code = self.error_code
        cnc.error_message = self.error_message        

class CncController:
    '''CNC Controller Class'''
    IS_READY = b'READY\n'
    ACTION_KEY = {'SET_PARAM':'@', 'INIT': 'S', 'FIN': 'E', 'MOVE': 'M', 'GO': 'G', 'ZERO': 'Z'}
    MAX_BUF = 30
    
    MOTOR_BASE_STEP = 200
    LEAD_DISTANCE = 1.496
    
    def __init__(self, ini_file):
        self.is_error = False
        self.is_connect = False
        
        try:
            #設定ファイルの読み込み
            if not os.path.exists(ini_file):
                raise CncControllerException('e00')
            
            self.ini_file = ini_file
            
            inifile = configparser.SafeConfigParser()
            inifile.read(self.ini_file, encoding='utf8')
                
            self.port = inifile.get('arduino', 'port')
            self.baud_rate = int(inifile.get('arduino', 'baud_rate'))
            
            l6470_default = inifile.items('l6470-default')
            l6470_change = inifile.items('l6470-change')
            self.__l6470_config(l6470_default, l6470_change)
            
            max_def = float(inifile.get('parser', 'max_def'))
            base_scale = float(inifile.get('parser', 'base_scale'))
            
            self.code_parser = CncCodeParser(max_def, base_scale)
            
            self.pos = numpy.array([0.0, 0.0, 0.0])
            self.pos_rotation = numpy.array([0.0, 0.0, 0.0])
            
        #エラー処理
        except CncControllerException as e:
            e.set_error(self) 
            
    def __del__(self):
        try:
            self.ser.close()
            print('COM' + str(self.port) + 'ポートを閉じました')
        except:
            pass
    
    def __l6470_config(self, default_val, change_val):
        self.l6470_setting = dict(default_val)
        self.l6470_setting.update(change_val)
        self.l6470_setting = {k:int(self.l6470_setting[k],0) for k in self.l6470_setting}
    
    def send_param(self):
        if self.check_connection():
            self.__write_buffer(CncController.ACTION_KEY['SET_PARAM'] + '00,0,0,0,0')
            for i, k in enumerate(self.l6470_setting):
                self.__write_buffer(CncController.ACTION_KEY['SET_PARAM'] + '{0:X}'.format(i + 1).zfill(2) + (',' + str(self.l6470_setting[k]))*3)
            
    def send_action(self, action, pos_rotation, top_z=0, is_wait=True):
        def pos_str():
            return str(int(pos_rotation[0])) + ',' + str(int(pos_rotation[1])) + ',' + str(int(pos_rotation[2])) + ',' + str(int(top_z))
        
        if self.check_connection():
            self.__write_buffer(action + ',' + pos_str(), is_wait)       
        
    def __write_buffer(self, buf, is_wait=True):
        b = (buf + '\n').encode('utf-8') 
        self.ser.write(b)
        print("アクション送信:", b)
        self.buf_cnt += 1
        
        if is_wait:
            self.__read_buffer()
        elif self.buf_cnt > CncController.MAX_BUF:
            self.__read_buffer(CncController.MAX_BUF//2)
                
    def __read_buffer(self, max_buf_cnt=0):
        while self.buf_cnt > max_buf_cnt:
            is_wait = True
            buf = ''
            while is_wait:
                if self.ser.in_waiting != 0:
                    buf = self.ser.readline()
                    print("状態受信:", buf, buf[0:2])
                    if buf[0:2] == b'OK':
                        self.buf_cnt -= 1
                        is_wait = False
           
            
    def __set_pos(self, pos_rotation, is_def=False):
        if is_def:
            self.pos_rotation += pos_rotation
        else:
            self.pos_rotation[:] = pos_rotation
                
        self.pos = self.conv_to_pos(self.pos_rotation)
            
    def init(self):
        self.is_error = False
        
        if not self.is_connect:
            try:
                #設定ファイルの読み込み
                inifile = configparser.SafeConfigParser()
                inifile.read(self.ini_file, encoding='utf8')
                                
                inifile.remove_section('l6470-change')
                inifile.add_section('l6470-change')
                for k in self.l6470_setting:
                    if self.l6470_setting[k] != int(inifile.get('l6470-default', k), 0):
                        inifile.set('l6470-change', k, hex(self.l6470_setting[k]))
            
                inifile.write(open(self.ini_file, 'w'))
                        
                #シリアルポート接続
                self.ser = serial.Serial('COM' + self.port, self.baud_rate)
                
                #バッファークリア
                self.ser.reset_input_buffer()
                self.ser.reset_output_buffer()
                self.buf_cnt = 0
                
                #Arduinoの準備を待つ
                while self.ser.in_waiting == 0:
                    time.sleep(0.001)
            
                #準備完了をチェック（'READY'の受信を確認）
                if self.ser.readline() == CncController.IS_READY:
                    self.is_connect = True
                    print('COM' + self.port + 'にボーレイト' + str(self.baud_rate) + 'で接続しました') 
                    
                    if self.port != inifile.get('arduino', 'port'):
                        inifile.set('arduino', 'port', self.port)
                    
                    if self.baud_rate != int(inifile.get('arduino', 'baud_rate')):
                        inifile.set('arduino', 'baud_rate', self.baud_rate)
                
                    inifile.write(open(self.ini_file, 'w'))
                    
                    self.top_z = self.conv_to_rotation(15)
                    
                    self.send_param()  
                    print('モーターの初期パラメータを設定しました')  
                    
                else:
                    raise CncControllerException('e01')
                
            #ポートにアクセスできない
            except serial.SerialException:
                e = CncControllerException('s01')
                e.set_error(self) 
            #上記以外のエラー処理
            except CncControllerException as e:
                e.set_error(self) 
            
        self.send_action(CncController.ACTION_KEY['INIT'], self.pos_rotation, 0, True)
        self.set_current_pos()
        
    def zero(self):
        self.send_action(CncController.ACTION_KEY['ZERO'], numpy.array([0, 0, 0]), 0, True)
        self.set_current_pos()   
        
    def fin(self):
        self.send_action(CncController.ACTION_KEY['FIN'], numpy.array([0, 0, 0]), self.top_z, True)
        self.set_current_pos()      
        
    def set_current_pos(self):
        self.__set_pos(numpy.array([0.0, 0.0, 0.0]))
        
    def goto(self, pos, is_def=False):
        self.__set_pos(pos, is_def)
        self.send_action(CncController.ACTION_KEY['GO'], self.pos_rotation, self.top_z)
        
    def moveto(self, pos, is_def=False):
        self.__set_pos(pos, is_def)
        self.send_action(CncController.ACTION_KEY['MOVE'], self.pos_rotation)
    
    def check_connection(self):
        try:
            if not self.is_connect:
                raise CncControllerException('e02')
            return True
        except CncControllerException as e:
            e.set_error(self)
            return False
    
    def conv_to_rotation(self, pos):
        base_step = CncController.MOTOR_BASE_STEP * 2**self.l6470_setting['step_mode']
        base_rate = base_step / CncController.LEAD_DISTANCE
        
        return numpy.trunc(pos * base_rate)
    
    def conv_to_pos(self, rot, round_num=3):
        base_step = CncController.MOTOR_BASE_STEP * 2**self.l6470_setting['step_mode']
        base_rate = CncController.LEAD_DISTANCE / base_step
        
        return numpy.round(rot * base_rate, round_num)
    
    @property
    def x(self):
        return self.pos[0] 
    
    @property
    def y(self):
        return self.pos[1]
     
    @property
    def z(self):
        return self.pos[2]

    @property
    def rot_x(self):
        return self.pos_rotation[0] 
    
    @property
    def rot_y(self):
        return self.pos_rotation[1]
     
    @property
    def rot_z(self):
        return self.pos_rotation[2]
