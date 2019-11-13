import time
import readsgf
start_time = time.time()

class board():
    #play_hist input format:[xcord, ycord]
    #board_stat input format:[xcord, ycord, 'STATE']
    #pass is given as a str 'PASS', not a list
    def __init__(self, board_size, komi):
        self.board_size=board_size
        self.komi=komi
        self.play_hist=['filler']
        self.board_stat=[]
        self.local_gp_list=[]
    
    def det_to_play(self):
        #returns a state as str
        if self.play_hist[-1] == 'PASS':
            return self.play_hist[-2][2]
        elif len(self.play_hist) % 2 ==0:
            return 'W'
        elif len(self.play_hist) % 2 ==1:
            return 'B'
        
    def is_ko(self, x, y, move=[]):
        #determines if the vertex given is in invalid state due to ko
        move=[x, y, self.det_to_play()]
        if self.play_hist[len(self.play_hist)-1] == move:
            return True
        else:
            return False

    def get_state(self, x, y):
        #check if outside board
        if x>self.board_size or x<1 or y>self.board_size or y<1:
            return 'EDGE'
        
        #black or white output
        elif [x, y, 'B'] in self.board_stat:
            return 'B'
        elif [x, y, 'W'] in self.board_stat:
            return 'W'
        elif [x, y, 'EMPTY'] in self.board_stat:
            return 'EMPTY'
        #empty output
        elif [x, y, self.det_to_play()] not in self.board_stat:
            return 'EMPTY'
        
        else:
            print('something is wrong : parse_color')

    def get_neighbor_stat(self, x, y):
        #returns states of 4 neighboting vertices in a clockwise order
        return [self.get_state(x,y-1),
        self.get_state(x+1,y),
        self.get_state(x,y+1),
        self.get_state(x-1,y)
                ]
    
    def get_neighbor_vert(self, vertex):
        #returns 4 neighboting vertices in list form in a clockwise order
        x_, y_ = vertex[0], vertex[1]
        return [[x_,y_-1,self.get_state(x_,y_-1)],
        [x_+1,y_,self.get_state(x_+1,y_)],
        [x_,y_+1,self.get_state(x_,y_+1)],
        [x_-1,y_,self.get_state(x_-1,y_)]
                ]
    
    def list_transfer(self,list_,stt):
        n=[]
        for i in range(len(list_)):
            if list_[i] == 'EDGE':
                n.append(list_[i])
            elif list_[i] != stt:
                n.append('EMPTY')
            elif list_[i] in stt:
                n.append(stt)
            else:
                raise ValueError("something is wrong")

        return n

    def expand_search(self, coord, stt, mode='n'):
        """Takes a list as input!"""
        if mode == 'n':#n for normal, c for count
            if stt == 'EMPTY': return
            elif stt == 'EDGE': return
        elif mode == 'c':
            if stt == 'B' or stt == 'W': return
            elif stt == 'EDGE': return
        
        x,y = coord[0], coord[1]
        nb=self.list_transfer(self.get_neighbor_stat(x,y),stt)
        def nothing():
            pass

        self.local_gp_list.append([x,y-1,stt]) if nb[0] ==stt and [x,y-1,stt] not in self.local_gp_list and [x,y-1,stt] in self.board_stat else nothing()
        self.local_gp_list.append([x+1,y,stt]) if nb[1] ==stt and [x+1,y,stt] not in self.local_gp_list and [x+1,y,stt] in self.board_stat else nothing()
        self.local_gp_list.append([x,y+1,stt]) if nb[2] ==stt and [x,y+1,stt] not in self.local_gp_list and [x,y+1,stt] in self.board_stat else nothing()
        self.local_gp_list.append([x-1,y,stt]) if nb[3] ==stt and [x-1,y,stt] not in self.local_gp_list and [x-1,y,stt] in self.board_stat else nothing()
        
    def get_connected_gp_list(self, x, y, stt, mode='n'):
        self.local_gp_list=[]
        searched=[]
        if stt == 'EDGE': return
        self.local_gp_list.append([x,y,stt])
        if stt not in self.get_neighbor_stat(x,y): return #single, only 1 elm in gp
        
        back_var=0

        #if stt is not 'EMPTY': #special case, implement counting of empty spaces when writing counting rules
        while True:
        #one expansion
            
            for elm in self.local_gp_list:
                if elm not in searched: self.expand_search(elm, stt, mode=mode)
                searched.append(elm)
                        
            if back_var - len(self.local_gp_list)==0: break
            back_var = len(self.local_gp_list)
            
    def remove_repeats(self,list_):
        for elm in list_:
            if list_.count(elm) >1:
                list_.remove(elm)
            else: pass
    
    def count_gp_libs(self):
        #condition:local_gp_list isn't empty
        list_=[]
        for elm in self.local_gp_list:
            for i in range(4):
            #get all the vertices of the elements' neighbors
                list_.append(self.get_neighbor_vert(elm)[i])
            #process the vertices
            self.remove_repeats(list_)
        for j in range(len(list_)):
            list_.append(list_[0][2])
            list_.remove(list_[0])

        return list_.count('EMPTY')



    def will_kill_gp(self, x, y, stt):#is actually will_suicide_gp
        self.board_stat.append([x,y,stt])
        if stt in self.get_neighbor_stat(x,y):
            self.get_connected_gp_list(x, y, stt)
            if self.count_gp_libs() == 0: 
                self.board_stat.remove([x,y,stt])
                return True
            else:
                self.board_stat.remove([x,y,stt])
                return False
        else:
            #not connected to any group, how can it kill a group?
            self.board_stat.remove([x,y,stt])
            return False

    def can_be_taken(self, x, y, stt): #indicates whether stones can be taken when move is played
        self.get_connected_gp_list(x, y, stt)
        return True if self.count_gp_libs()==0 else False
    
    def is_alone(self, x, y, stt):
        return True if stt not in self.get_neighbor_stat(x, y) else False
        
    def is_legal(self, x, y):
        ph1, ph2 = [], []
        stt=self.det_to_play()
        if x>19 or x<1 or y>19 or y<1:
            return False
        elif not self.will_kill_gp(x, y, stt):
            return True
        elif [x,y,'B'] in self.board_stat or [x,y,'W'] in self.board_stat:
            return False

        else:
            if self.get_neighbor_stat(x,y).count('EMPTY') >=1 or stt in self.get_neighbor_stat(x,y): #second stmt is result of 2 days of debugging
                return True
            elif self.get_neighbor_stat(x,y).count('EMPTY') ==0:
                self.board_stat.append([x,y,stt])
                #conditions for 0 liberty play:
                #1. can take a group
                #2. can take 1 stone (the position of the stone is not in ko)
                #3. connected to a gp
                
                for i in range(4):
                    ph1.append(self.get_neighbor_vert([x,y])[i])
                    ph2.append('T') if self.can_be_taken(ph1[i][0], ph1[i][1], ph1[i][2]) else ph2.append('F')
            
                if 'T' not in ph2: return False #play 0 libs and not taking anything
                else:
                    for i in range(4):
                        if self.is_alone(ph1[i][0], ph1[i][1], ph[i][2]) and not self.is_ko(ph1[i][0], ph1[i][1]): return True 
                        else: continue
                        
    def stt_to_sym_handler(self, x, y, stt=''):
        stt=self.get_state(x,y)
        if stt == 'EMPTY':
            return '*'
        elif stt == 'W':
            return 'O'
        elif stt == 'B':
            return 'X'
        
    def print_board_state(self):
        #restrict to 19x19 for now
        print("   A B C D E F G H J K L M N O P Q R S T")
        for i in range(self.board_size):
            row=[]
            for j in range(self.board_size):
                row.append(self.stt_to_sym_handler(j+1, i+1))
            if i<9:
                print("",i+1, row[0],row[1],row[2],row[3],row[4],row[5],row[6],row[7],row[8],row[9],row[10],row[11],row[12],row[13],row[14],row[15],row[16],row[17],row[18])
            else:
                print(i+1, row[0],row[1],row[2],row[3],row[4],row[5],row[6],row[7],row[8],row[9],row[10],row[11],row[12],row[13],row[14],row[15],row[16],row[17],row[18])

    def play(self, x, y, state):
        nb=self.get_neighbor_vert([x,y])
        if state != self.det_to_play():
            print("invalid action")
            return
            
        elif state == self.det_to_play():
            #first need to check legality; if legal, find any stones that can be taken to be taken off the board
            if self.is_legal(x, y):
                self.board_stat.append([x, y, state])
                
                for i in range(4):
                    if nb[i][2] != 'EMPTY': #checking status of stones
                        self.get_connected_gp_list(nb[i][0], nb[i][1], nb[i][2])
                        if self.count_gp_libs()>0:
                            pass
                            #can't take, connected
                            #this line is the result of 2 hrs of debugging btw
                        
                        elif self.can_be_taken(nb[i][0], nb[i][1], nb[i][2]) and self.is_alone(nb[i][0], nb[i][1], nb[i][2]):
                            self.board_stat.remove(nb[i])
                            #take one stone

                        else: #gp libs=0&not alone, take whole gp
                            for elm in self.local_gp_list:
                                self.board_stat.remove(elm)
                            
                    else: pass #nothing to take 

                self.play_hist.append([x,y,self.det_to_play()])
                    
            else:
                print("illegal move!")
                return

        self.local_gp_list=[]
        
    def Pass(self):
        self.play_hist.append('PASS')
        return
    
    def undo(self):
        #reload the board stat by playing from play_hist
        migration=[]
        for i in range(len(self.play_hist)):
            if i is len(self.play_hist): break
            migration.append(self.play_hist[i-1])
            
        self.play_hist = []
        for i in range(len(migration)):
            self.play_hist.append(migration[i-1])
        
    
    def twoto1(self, x, y):
        alphb='abcdefghijklmnopqrs'
        return alphb[x-1] + alphb[y-1]

    def oneto2(self, str_):
        alphb='abcdefghijklmnopqrs'
        return alphb.index(str_[0])+1, alphb.index(str_[1])+1
                        
    def init_game(self, board_size, komi):
        self.__init__(board_size, komi)
        print("Komi:", self.komi, ",", "Board size:", self.board_size)

    def remove_stone(self, x, y):
        self.board_stat.remove()
        return

    def fill_empty(self):
        stt=''
        for i in range(19):
            for j in range(19):
                stt=self.get_state(i+1, j+1)
                if stt == 'EMPTY':
                    self.board_stat.append([i+1, j+1, stt])
                else: pass

    def load_game(self, _dir, file_name):
        data=readsgf.get_sgf(_dir, file_name)
        data_=readsgf.converter(readsgf.cropper(data)[1])
        self.play_hist=['filler']
        self.board_stat=[]
        i=0
        for datum in data_:
            i+=1
            self.play(datum[0], datum[1], datum[2]) if datum is not 'PASS' else self.Pass()

    def score(self):
        empty_list, area_label, processed = [], [], []
        Bscore, Wscore = 0,0
        self.fill_empty()
        
        for i in range(self.board_size):
            for j in range(self.board_size):
                if self.get_state(i+1, j+1) is 'B': Bscore+=1
                elif self.get_state(i+1, j+1) is 'W': Wscore+=1
                elif [i+1, j+1, 'EMPTY'] in processed: continue
                
                elif [i+1, j+1, 'EMPTY'] in self.board_stat: #non-processed empty vertices, should be included in scoring process
                    self.get_connected_gp_list(i+1, j+1, 'EMPTY', mode='c')
                    empty_list.append(self.local_gp_list)
                    for elm in self.local_gp_list:
                        processed.append(elm)

        for group in empty_list:
            near_list=[]
            for i in range(len(group)):
                ph_=self.get_neighbor_stat(group[i][0], group[i][1])
                for i in range(4): near_list.append(ph_[i])
                    
            if 'B' not in near_list: area_label.append('W')
            elif 'W' not in near_list: area_label.append('B')
            else: area_label.append(None)

        for i in range(len(empty_list)):
            if area_label[i] == 'B':
                Bscore += len(empty_list[i])
            elif area_label[i] == 'W':
                Wscore += len(empty_list[i])
            else: continue
        print('Black wins by {} points'.format(Bscore-Wscore-self.komi)) if Bscore > Wscore + self.komi else print('White wins by {} points'.format(Wscore+self.komi-Bscore))
# for testing
print("--- %s seconds ---" % (time.time() - start_time))
