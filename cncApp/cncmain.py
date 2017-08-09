#!/usr/bin/env python
# -*- coding: utf-8 -*-

import numpy
from cnccontroller import CncController
from flask import Flask, render_template, request
from IPython.external.decorators import _numpy_testing_utils

app = Flask(__name__)
app.config['DEBUG'] = True
cnc = CncController('setting.ini')

@app.route("/")
def electron_start():
    if cnc.is_error:
        return '<type>error</type><code>' + cnc.error_code + '</code><message>'+ cnc.error_message + '</message>'
    else:
        x = str(cnc.l6470_setting['abs_pos']) + '.000'
        y = x
        z = x
        
        for k in cnc.l6470_setting:
            globals()['__' + k] = hex(cnc.l6470_setting[k])
        
        return render_template('./index.html',
                               x=x, y=y, z=z, 
                               abs_pos=__abs_pos, el_pos=__el_pos, mark=__mark, speed=__speed, acc=__acc, dec=__dec, max_speed=__max_speed, min_speed=__min_speed,
                               kval_hold=__kval_hold, kval_run=__kval_run, kval_acc=__kval_acc, kval_dec=__kval_dec, int_spd=__int_spd, st_slp=__st_slp, fn_slp_acc=__fn_slp_acc, fn_slp_dec=__fn_slp_dec,
                               k_therm=__k_therm, adc_out=__adc_out, ocd_out=__ocd_out, stall_th=__stall_th, fs_spd=__fs_spd, step_mode=__step_mode, alarm_en=__alarm_en,
                               port=cnc.port,rate=cnc.baud_rate
                               )

@app.route("/connect", methods=['POST'])
def serial_connection():
    if cnc.is_connect:
        cnc.fin()
        cnc.ser.close()
        cnc.is_connect = False
    else:
        cnc.port = request.form['port']
        cnc.baud_rate = int(request.form['baud_rate'])
        
        for k in request.form:
            val = int(request.form[k], 0)
            if k in cnc.l6470_setting:
                if cnc.l6470_setting[k] != val:
                    cnc.l6470_setting[k] = val        
                    
        cnc.init()
        
    if cnc.is_error:
        return '<type>error</type><code>' + cnc.error_code + '</code><message>'+ cnc.error_message + '</message>'
    else:
        if cnc.is_connect:
            return '<type>normal</type><message>COM' + cnc.port + 'にボーレイト' + str(cnc.baud_rate) + 'で接続しました</message>'
        else:
            return '<type>normal</type><message>COM' + cnc.port + 'を閉じました</message>'

@app.route("/move", methods=['POST'])
def cnc_move():
    if cnc.check_connection():
        pos = cnc.conv_to_rotation(numpy.array([float(request.form['x']), float(request.form['y']), float(request.form['z'])]))
        is_def = False if request.form['is_def'] == 'false' else True
                       
        cnc.moveto(pos, is_def)
        return '<type>normal</type><rot_x>' + str(cnc.rot_x) + '</rot_x><rot_y>' + str(cnc.rot_y) + '</rot_y><rot_z>' + str(cnc.rot_z) + '</rot_z>' + \
               '<pos_x>' + str(cnc.x) + '</pos_x><pos_y>' + str(cnc.y) + '</pos_y><pos_z>' + str(cnc.z) + '</pos_z>' + \
               '<message>移動： X->' + str(cnc.x) + ' Y->' + str(cnc.y) + ' Z->' + str(cnc.z) + '</message>'
    else:
        return '<type>error</type><code>' + cnc.error_code + '</code><message>'+ cnc.error_message + '</message>'

@app.route("/setpos")
def set_pos():
    cnc.init() 
    
    if cnc.is_error:
        return '<type>error</type><code>' + cnc.error_code + '</code><message>'+ cnc.error_message + '</message>'
    else:
        return '<type>normal</type><rot_x>' + str(cnc.rot_x) + '</rot_x><rot_y>' + str(cnc.rot_y) + '</rot_y><rot_z>' + str(cnc.rot_z) + '</rot_z>' + \
               '<pos_x>' + str(cnc.x) + '</pos_x><pos_y>' + str(cnc.y) + '</pos_y><pos_z>' + str(cnc.z) + '</pos_z>' + \
               '<message>基準座標を現在の座標に設定しました</message>'
               
@app.route("/setzero")
def set_zero():
    cnc.zero() 
    
    if cnc.is_error:
        return '<type>error</type><code>' + cnc.error_code + '</code><message>'+ cnc.error_message + '</message>'
    else:
        return '<type>normal</type><rot_x>' + str(cnc.rot_x) + '</rot_x><rot_y>' + str(cnc.rot_y) + '</rot_y><rot_z>' + str(cnc.rot_z) + '</rot_z>' + \
               '<pos_x>' + str(cnc.x) + '</pos_x><pos_y>' + str(cnc.y) + '</pos_y><pos_z>' + str(cnc.z) + '</pos_z>' + \
               '<message>基準座標を現在の座標に設定しました</message>'

@app.route("/input", methods=['POST'])
def read_input_file():
    input_file = request.form['input']
    input_type = request.form['type']
    
    svg_tag = cnc.code_parser.load(input_type, input_file)

    return '<type>normal</type><svg>' + svg_tag + '</svg><message>読み込み完了</message>'

@app.route("/exec", methods=['POST'])
def execute_code():
    if cnc.check_connection():
        ex_line = int(request.form['line'])
        
        if len(cnc.code_parser.path_list[0]) <= ex_line:
            cnc.fin()
            
            if cnc.is_error:
                return '<type>error</type><code>' + cnc.error_code + '</code><message>'+ cnc.error_message + '</message>'
            else:
                return '<type>error</type><code>w99</code><message>:完了しました</message>'
        else:
            pos = cnc.conv_to_rotation(numpy.array([cnc.code_parser.path_list[1][ex_line] , cnc.code_parser.path_list[2][ex_line] , cnc.code_parser.path_list[3][ex_line]]))
            
            if cnc.code_parser.path_list[0][ex_line] == 'M':
                cnc.top_z = cnc.conv_to_rotation(cnc.code_parser.path_list[4][ex_line])
                cnc.goto(pos, False)                
            else:
                cnc.moveto(pos, False)
                
            return '<type>normal</type><rot_x>' + str(cnc.rot_x) + '</rot_x><rot_y>' + str(cnc.rot_y) + '</rot_y><rot_z>' + str(cnc.rot_z) + '</rot_z>' + \
                   '<pos_x>' + str(cnc.x) + '</pos_x><pos_y>' + str(cnc.y) + '</pos_y><pos_z>' + str(cnc.z) + '</pos_z>' + \
                   '<message>移動： X->' + str(cnc.x) + ' Y->' + str(cnc.y) + ' Z->' + str(cnc.z) + '</message>'
    else:
        return '<type>error</type><code>' + cnc.error_code + '</code><message>'+ cnc.error_message + '</message>'

if __name__ == '__main__':
    app.run(host="192.168.1.10", port=5000)