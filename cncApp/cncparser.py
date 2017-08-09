# -*- coding: utf-8 -*-

import numpy, re, math, time
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

class CncCodeParser:
    BASE_AXES_XY = 'xy'
    BASE_AXES_ZX = 'zx'
    BASE_AXES_YZ = 'yz'
    
    BASE_UNIT_MM = 'mm'
    BASE_UNIT_INCH = 'inch'
    
    BASE_POS_MODE_ABS = 'absolute'
    BASE_POS_MODE_REL = 'relative'
        
    def __init__(self, max_def, base_scale):
        self.max_def = max_def 
        self.base_scale = base_scale
        
        self.pos_mode = CncCodeParser.BASE_POS_MODE_ABS
        self.pos_mode_ijk = CncCodeParser.BASE_POS_MODE_REL
        
        self.unit_mm = CncCodeParser.BASE_UNIT_MM
        self.rotate_mode = CncCodeParser.BASE_AXES_XY
        
        self.pos = numpy.array([0.0, 0.0, 0.0])
    
    def load(self, parse_type, data):
        self.path_list = [[],[],[],[],[]]        
        self.parse_type = parse_type
        self.cur_top_z = 15
        
        if self.parse_type == 'G':
            self.__parse_g(data)
        elif self.parse_type == 'SVG':
            self.__parse_svg(data)
        
        '''
        fig = plt.figure()
        ax = Axes3D(fig)
        ax.plot([self.path_list[1][i] for i in range(len(self.path_list[0])) if self.path_list[0][i] == 'P'],
                [self.path_list[2][i] for i in range(len(self.path_list[0])) if self.path_list[0][i] == 'P'],
                [self.path_list[3][i] for i in range(len(self.path_list[0])) if self.path_list[0][i] == 'P'],
                )
        plt.show()        
        '''
            
        return self.__generate_svg()
    
    def __generate_svg(self):
        layer_list = sorted(list(set([self.path_list[3][i] for i in range(len(self.path_list[0])) if self.path_list[0][i] == 'P'])), reverse=True)
        
        svg_path_list = {}
        for k in layer_list:
            svg_path_list['z_' + str(k)] = []
        
        for i in range(len(self.path_list[0])):
            if self.path_list[0][i] == 'P':
                is_start = not(i > 0 and self.path_list[3][i] == self.path_list[3][i-1] and self.path_list[0][i-1] == 'P')  
                svg_path_list['z_' + str(self.path_list[3][i])].append([is_start, self.path_list[1][i], self.path_list[2][i]])
        
        svg_tag = ''
        for k in svg_path_list:
            svg_tag += '<g id="' + k.replace('.', '_') + '" fill="none" stroke="#ccc" stroke-opacity="0.3" stroke-width="0.5">'
            for i in range(len(svg_path_list[k])):
                if svg_path_list[k][i][0]:
                    svg_tag += '<path d="M '
                else:
                    svg_tag += ' L '
                    
                svg_tag += str(svg_path_list[k][i][1]) + ' ' + str(svg_path_list[k][i][2])
                 
                if i + 1 == len(svg_path_list[k]) or svg_path_list[k][i + 1][0]:
                    svg_tag += '" />'
                
            svg_tag += '</g>'
        
        '''
        f = open('text.txt', 'w')
        f.write(svg_tag)
        f.close()
        '''
            
        return svg_tag
    
    def __parse_g(self, data):
        lines = data.split('\n')
    
        try:
            for g in lines:
                codes = re.sub('\(.*\)','', g).strip().split(' ')
                if len(codes) == 1 and codes[0] == '':
                    continue
                
                if not (codes[0][0] == 'X' or codes[0][0] == 'Y' or codes[0][0] == 'Z'):
                    code = codes[0].upper()
                    del codes[0]
                
                if len(code) == 2:
                    code = code[0] + '0' + code[1]
                    
                while self.g_syntax_check(code, codes):
                    code = codes.pop(0)
                    if len(code) == 2:
                        code = code[0] + '0' + code[1]
                    
        except Exception as e:
            print(e)
    
    def write_path(self, pos_e):
        if len(pos_e) == 2:
            if self.rotate_mode == CncCodeParser.BASE_AXES_XY:
                self.pos[0] = pos_e[0]
                self.pos[1] = pos_e[1]
            elif self.rotate_mode == CncCodeParser.BASE_AXES_YZ:
                self.pos[1] = pos_e[0]
                self.pos[2] = pos_e[1]
            elif self.rotate_mode == CncCodeParser.BASE_AXES_ZX:
                self.pos[0] = pos_e[0]
                self.pos[2] = pos_e[1]
        else:
            self.pos[:] = pos_e            
        
        self.path_list[0].append('P')
        self.path_list[1].append(self.pos[0])
        self.path_list[2].append(self.pos[1])
        self.path_list[3].append(self.pos[2])
        self.path_list[4].append('')
    
    def write_move_path(self, pos_e):
        if len(pos_e) == 2:
            if self.rotate_mode == CncCodeParser.BASE_AXES_XY:
                self.pos[0] = pos_e[0]
                self.pos[1] = pos_e[1]
            elif self.rotate_mode == CncCodeParser.BASE_AXES_YZ:
                self.pos[1] = pos_e[0]
                self.pos[2] = pos_e[1]
            elif self.rotate_mode == CncCodeParser.BASE_AXES_ZX:
                self.pos[0] = pos_e[0]
                self.pos[2] = pos_e[1]
        else:
            self.pos[:] = pos_e            
            
        self.path_list[0].append('M')
        self.path_list[1].append(self.pos[0])
        self.path_list[2].append(self.pos[1])
        self.path_list[3].append(self.pos[2])
        self.path_list[4].append(self.cur_top_z)
    
    def g_syntax_check(self, code, params):
        def __get_pos(pos_s, pos_e, pos_mode=self.pos_mode):
            return pos_s * (pos_mode == CncCodeParser.BASE_POS_MODE_REL) + pos_e
        
        def __get_dis(pos, pos_c):
            return numpy.linalg.norm(pos - pos_c)
        
        try:
            code_addr = ''
            if code == 'G00' or code == 'G01':
                pos = numpy.array(self.pos)
                
                for param in params:
                    code_addr = param[0]
                    if code_addr == 'X':
                        pos[0] = __get_pos(pos[0], float(param[1:]))
                    elif code_addr == 'Y':
                        pos[1] = __get_pos(pos[1], float(param[1:]))
                    elif code_addr == 'Z':
                        pos[2] = __get_pos(pos[2], float(param[1:]))
                    elif code_addr == 'F':
                        pass
                    else:
                        print(code, params)
                        raise Exception
                
                if code == 'G00':   self.write_move_path(pos)
                else:               self.write_path(pos)
                
                return False
            
            elif code == 'G02' or code == 'G03':
                pos = numpy.array(self.pos)
                pos_ijk = numpy.array(self.pos)
                                    
                for param in params:
                    code_addr = param[0]
                    if code_addr == 'X':
                        pos[0] = __get_pos(pos[0], float(param[1:]))
                    elif code_addr == 'Y':
                        pos[1] = __get_pos(pos[1], float(param[1:]))
                    elif code_addr == 'Z':
                        pos[2] = __get_pos(pos[2], float(param[1:]))
                    elif code_addr == 'I':
                        pos_ijk[0] = __get_pos(pos_ijk[0], float(param[1:]), self.pos_mode_ijk)
                    elif code_addr == 'J':
                        pos_ijk[1] = __get_pos(pos_ijk[1], float(param[1:]), self.pos_mode_ijk)
                    elif code_addr == 'K':
                        pos_ijk[2] = __get_pos(pos_ijk[2], float(param[1:]), self.pos_mode_ijk)
                    elif code_addr == 'F':
                        pass
                    else:
                        print(code, params)
                        raise Exception
                
                if self.rotate_mode == CncCodeParser.BASE_AXES_XY:
                    pos_s = numpy.array([self.pos[0], self.pos[1]])
                    pos_e = numpy.array([pos[0], pos[1]])
                    pos_c = numpy.array([pos_ijk[0], pos_ijk[1]])
                    
                    if pos[2] != self.pos[2]:
                        self.write_path(numpy.array([self.pos[0], self.pos[1], pos[2]]))
                elif self.rotate_mode == CncCodeParser.BASE_AXES_YZ:
                    pos_s = numpy.array([self.pos[1], self.pos[2]])
                    pos_e = numpy.array([pos[1], pos[2]])
                    pos_c = numpy.array([pos_ijk[1], pos_ijk[2]])
                    
                    if pos[0] != self.pos[0]:
                        self.write_path(numpy.array([pos[0], self.pos[1], self.pos[2]]))
                elif self.rotate_mode == CncCodeParser.BASE_AXES_ZX:
                    pos_s = numpy.array([self.pos[0], self.pos[2]])
                    pos_e = numpy.array([pos[0], pos[2]])
                    pos_c = numpy.array([pos_ijk[0], pos_ijk[2]])
                    
                    if pos[1] != self.pos[1]:
                        self.write_path(numpy.array([self.pos[0], pos[1], self.pos[2]]))
                
                sign = -1.0 if code == 'G02' else 1.0                    
                base_d = __get_dis(pos_e, pos_c)
                    
                rad_s = math.atan2(pos_s[1] - pos_c[1], pos_s[0] - pos_c[0])
                if rad_s < 0: rad_s += 2.0 * math.pi
                
                rad_e = math.atan2(pos_e[1] - pos_c[1], pos_e[0] - pos_c[0])
                if rad_e < 0: rad_e += 2.0 * math.pi
                    
                def_rad = math.pi / 180.0
                    
                cur_rad = rad_s + sign * def_rad
                np = pos_c + base_d * numpy.array([math.cos(cur_rad), math.sin(cur_rad)])
                while __get_dis(pos_s, np) > self.max_def:
                    def_rad /= 2.0
                    cur_rad = rad_s + sign * def_rad
                    np = pos_c + base_d * numpy.array([math.cos(cur_rad), math.sin(cur_rad)])
                
                if sign == -1.0:
                    if rad_s < rad_e:
                        d_cnt = 2.0 * math.pi + rad_s - rad_e
                    else:
                        d_cnt = rad_s - rad_e
                else:
                    if rad_e < rad_s:
                        d_cnt = 2.0 * math.pi + rad_e - rad_s
                    else:
                        d_cnt = rad_e - rad_s
                                
                d_cnt = int(d_cnt / def_rad) - 1
                self.write_path(np)
                for _ in range(d_cnt):
                    np = pos_c + base_d * numpy.array([math.cos(cur_rad), math.sin(cur_rad)])
                    self.write_path(np)
                    
                    cur_rad += sign * def_rad
                                    
                self.write_path(pos)
                return False
            
            elif code == 'G17':
                self.rotate_mode = CncCodeParser.BASE_AXES_XY
                return len(params) > 0
            
            elif code == 'G18':
                self.rotate_mode = CncCodeParser.BASE_AXES_ZX
                return len(params) > 0
            
            elif code == 'G19':
                self.rotate_mode = CncCodeParser.BASE_AXES_YZ
                return len(params) > 0
            
            elif code == 'G20':
                self.unit_mm = CncCodeParser.BASE_UNIT_INCH
                return False
            
            elif code == 'G21':
                self.unit_mm = CncCodeParser.BASE_UNIT_MM
                return False
            
            elif code == 'G40':
                return False
            
            elif code == 'G41':
                return False
            
            elif code == 'G42':
                return False
            
            elif code == 'G43':
                pos = numpy.array(self.pos)
                
                for param in params:
                    code_addr = param[0]
                    if code_addr == 'Z':
                        pos[2] = __get_pos(pos[2], float(param[1:]))
                        self.cur_top_z = pos[2]
                    elif code_addr == 'H':
                        pass
                    else:
                        print(code, params)
                        raise Exception
                
                self.write_move_path(pos)
                
                return False
            
            elif code == 'G49':
                return False
            
            elif code == 'G54' or code == 'G55' or code == 'G56' or code == 'G57' or code == 'G58' or code == 'G59':
                return False
            
            elif code == 'G90':
                self.pos_mode = CncCodeParser.BASE_POS_MODE_ABS
                return len(params) > 0
            
            elif code == 'G90.1':
                self.pos_mode_ijk = CncCodeParser.BASE_POS_MODE_ABS
                return len(params) > 0
            
            elif code == 'G91':
                self.pos_mode = CncCodeParser.BASE_POS_MODE_REL
                return len(params) > 0
            
            elif code == 'G91.1':
                self.pos_mode_ijk = CncCodeParser.BASE_POS_MODE_REL
                return len(params) > 0
            
            elif code == 'G94':
                return len(params) > 0
            
            elif code == 'M03' or code == 'M05' or code == 'M06' or code == 'M08' or code == 'M09':
                return False
            
            elif code == 'M02' or code == 'M30':
                print('Code End')
                '''
                fig = plt.figure()
                ax = Axes3D(fig)
                ax.plot(self.array_x, self.array_y, self.array_z)
                ax.set_xlim(0,200)
                ax.set_ylim(0,200)
                ax.set_zlim(0,200)
                plt.show()
                '''
                return False
            
            elif code[0] == 'S':
                return len(params) > 0
            
            elif code[0] == 'T':
                return len(params) > 0
            
            else:
                print('Warning: 次のコードがスキップされました', code, len(code), params)
                return len(params) > 0
            
        except Exception:
            print('Error: 解読不能コードが含まれています', code, code_addr)
            raise
        
    def __parse_svg(self, data):
        pass