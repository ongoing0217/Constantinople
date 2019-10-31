"""
an sgf of the standard opening of Fine Art (June2019) being read by the following function:

>>> def handle_sgf(file_name):
        with open("C:\\test\\%s.sgf" % file_name, 'r') as file:
            data = file.read()
            return data

data =
'(;GM[1]FF[4]CA[UTF-8]AP[Sabaki:0.43.3]KM[7.5]SZ[19]DT[2019-10-12]PB[RicochetE]PW[RicochetA]RE[B+R];B[pd];W[dp];B[pp];W[dd];B[cc];W[cd];B[dc];W[fc];B[ec];W[ed];B[fb];W[fq];B[cj];W[gc];B[gb];W[hc];B[])'

game record: B 16/4, W 4/16, B 16/16, W 4/4, B 3/3, W 3/4, B 4/3, W 6/3, B 5/3, W 5/4, B 6/2, W 6/17, B 3/10, W 7/3, B 7/2, W 8/3

file creater is sabaki, komi is 7.5, board size is 19, game starts at second semicolon

note: pass has an empty bracket as indication
"""

def get_sgf(_dir, file_name):
    with open(_dir + file_name + '.sgf', 'r') as file:
        return file.read()

def cropper(data):
    data_ = data[data.index(';')+1:]
    #first portion is game info
    data1 = data_[:data_.index(';')]
    #second portion is game record
    data2 = data_[data_.index(';'):]
    return data1, data2

def oneto2(str_):
    alphb='abcdefghijklmnopqrs'
    return alphb.index(str_[0])+1, alphb.index(str_[1])+1

def converter(data):
    #first identify the type of data
    list_ = []
    ph = data
    ph = ph[1::]
    ph1 = ''
    ph2 = 0
    if data[1] == 'B' or data[1] == 'W':
        print("detected game record")
        while len(ph) != 0:
            #return moves in list form [x,y, '']
            #cut from first semicolon to next semicolon(the symbol itself not required)
            if ph[0] is ';' :
                ph = ph[1::]
            else:
                ph1 = ph[:ph.index(']')+1]
                if ph1.index(']') - ph1.index('[') == 1:
                    #pass
                    list_.append('PASS')
                    ph = ph[3::]
                else:
                    ph2 = oneto2(ph1[2 : ph1.index(']')])
                    list_.append([ph2[0], ph2[1], ph1[0]])
                    ph = ph[5::]
                    

                

            #break if exceptions occur
            """
            try:
                list_.append(['PASS']) if placeholder[3] == ']' else list_.append([oneto2(placeholder[3:5])[0], oneto2(placeholder[3:5])[1], '%s' % placeholder[1]])
            except IndexError:
                break
            
            placeholder = placeholder[placeholder.index(';')+1:]
            #cant detect pass
            """
            

        return list_

    else:
        print("detected game info")
        #detect the info given first
        
#print(cropper(get_sgf("C:\\test\\", 'test'))[1]

print(converter(';B[ac];W[]'))
