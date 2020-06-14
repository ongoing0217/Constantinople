import timer
import readsgf

class board():
    #play_hist input format:[xcord, ycord]
    #board_stat input format:[xcord, ycord, 'STATE']
    #pass is given as a str 'PASS', not a list
    def __init__(self, board_size, komi, handicap=0):
        self.board_size=board_size
        self.komi=komi
        self.play_hist=['filler']
        self.board_stat=[]
        self.past_board_stat=[]
        self.local_gp_list=[]
        self.result=''
        self.force_overwrite_to_play=''
        self.handicap=handicap
        if handicap==0: return
        else:
            if handicap==1:
                self.komi=0
                return
            self.play_hist=[]
            if handicap==2:
                self.board_stat.extend([[16, 4, 'B'], [4, 16, 'B']])
            elif handicap==3:
                self.board_stat.extend([[16, 4, 'B'], [4, 16, 'B'], [16, 16, 'B']])
            elif handicap==4:
                self.board_stat.extend([[16, 4, 'B'], [4, 16, 'B'], [16, 16, 'B'], [4, 4, 'B']])
            elif handicap==5:
                self.board_stat.extend([[16, 4, 'B'], [4, 16, 'B'], [16, 16, 'B'], [4, 4, 'B'], [10, 10, 'B']])
            elif handicap==6:
                self.board_stat.extend([[16, 4, 'B'], [4, 16, 'B'], [16, 16, 'B'], [4, 4, 'B'], [16, 10, 'B'], [4, 10, 'B']])
            elif handicap==7:
                self.board_stat.extend([[16, 4, 'B'], [4, 16, 'B'], [16, 16, 'B'], [4, 4, 'B'], [16, 10, 'B'], [4, 10, 'B'], [10, 10, 'B']])
            elif handicap==8:
                self.board_stat.extend([[16, 4, 'B'], [4, 16, 'B'], [16, 16, 'B'], [4, 4, 'B'], [16, 10, 'B'], [4, 10, 'B'], [10, 4, 'B'], [10, 16, 'B']])
            elif handicap==9:
                self.board_stat.extend([[16, 4, 'B'], [4, 16, 'B'], [16, 16, 'B'], [4, 4, 'B'], [16, 10, 'B'], [4, 10, 'B'], [10, 4, 'B'], [10, 16, 'B'], [10, 10, 'B']])


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
        if [x, y, 'B'] in self.board_stat: #check for B stones
            return 'B'
        elif [x, y, 'W'] in self.board_stat: #check for W stones
            return 'W'
        #check if outside board
        elif x>self.board_size or x<1 or y>self.board_size or y<1:
            return 'EDGE'
        else: return 'EMPTY'

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

    def list_sieve(self,list_,stt):
        #removes odd type elements from the list
        n=[]
        for elm in list_:
            if elm != stt:
                n.append('EMPTY')
            elif elm == 'EDGE':
                n.append(elm)
            else:
                n.append(stt)

        return n

    def expand_search(self, coord, stt, mode='n'):
        """coord is a list in format [x, y]"""
        if stt=='EDGE': return
        if mode == 'n' and stt == 'EMPTY': #n for normal, c for count
            return
        elif mode == 'c':
            if stt == 'B' or stt == 'W': return

        x,y = coord[0], coord[1]
        nb=self.list_sieve(self.get_neighbor_stat(x,y),stt)

        if nb[0] == stt: # switch stmt for python pls
            vertex = [x,y-1,stt]
            if vertex not in self.local_gp_list:
                if vertex in self.board_stat:
                    self.local_gp_list.append(vertex)

        if nb[1] == stt:
            vertex = [x+1,y,stt]
            if vertex not in self.local_gp_list:
                if vertex in self.board_stat:
                    self.local_gp_list.append(vertex)

        if nb[2] == stt:
            vertex = [x,y+1,stt]
            if vertex not in self.local_gp_list:
                if vertex in self.board_stat:
                    self.local_gp_list.append(vertex)

        if nb[3] == stt:
            vertex = [x-1,y,stt]
            if vertex not in self.local_gp_list:
                if vertex in self.board_stat:
                    self.local_gp_list.append(vertex)

    def get_connected_gp_list(self, x, y, stt, mode='n'):
        if stt == 'EDGE': return
        self.local_gp_list=[[x,y,stt]]
        searched=[]
        if stt not in self.get_neighbor_stat(x,y): return #single, only 1 elm in gp

        back_var=0

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
            nb=self.get_neighbor_stat(elm[0], elm[1])
            for i in range(4): #get all the vertices of the elements' neighbors
                if nb[i] == 'EMPTY': return 1

        return 0

    def will_kill_gp(self, x, y, stt):#is actually will_suicide_gp
        if stt in self.get_neighbor_stat(x,y):
            self.board_stat.append([x,y,stt])
            self.get_connected_gp_list(x, y, stt)
            if self.count_gp_libs() == 0:
                self.board_stat.remove([x,y,stt])
                return True
            else:
                self.board_stat.remove([x,y,stt])
                return False
        else:
            #not connected to any group, how can it kill a group?
            return False

    def can_be_taken(self, x, y, stt): #indicates whether stones can be taken when move is played
        self.get_connected_gp_list(x, y, stt)
        return True if self.count_gp_libs()==0 else False

    def is_alone(self, x, y, stt):
        return True if stt not in self.get_neighbor_stat(x, y) else False

    def is_legal(self, x, y):
        if x>19 or x<1 or y>19 or y<1:
           return False
        elif [x,y,'B'] in self.board_stat or [x,y,'W'] in self.board_stat:
            return False
        stt=self.det_to_play() if self.force_overwrite_to_play == '' else self.force_overwrite_to_play
        if not self.will_kill_gp(x, y, stt):
            return True

        else:
            nb=self.get_neighbor_stat(x,y)
            if 'EMPTY' in nb or stt in nb: #second stmt is result of 2 days of debugging
                return True
            elif self.get_neighbor_stat(x,y).count('EMPTY') ==0:
                self.board_stat.append([x,y,stt])
                ph1 = self.get_neightbor_vert([x, y])
                ph2 = []
                #conditions for 0 liberty play:
                #1. can take a group
                #2. can take 1 stone (the position of the stone is not in ko)
                #3. connected to a gp

                for i in range(4):
                    ph2.append('T') if self.can_be_taken(ph1[i][0], ph1[i][1], ph1[i][2]) else ph2.append('F')

                if 'T' not in ph2: return False #play 0 libs and not taking anything
                else:
                    for i in range(4):
                        if self.is_alone(ph1[i][0], ph1[i][1], ph1[i][2]) and not self.is_ko(ph1[i][0], ph1[i][1]): return True

    def stt_to_sym_handler(self, x, y):
        stt=self.get_state(x,y)
        if stt == 'EMPTY':
            return '*'
        elif stt == 'W':
            return 'O'
        else:
            return 'X'

    def print_board_state(self):
        alphabet = 'ABCDEFGHIJKLMNOPQRST' # max board size is 19x19
        board_state="  "
        for i in range(self.board_size):
            board_state += ' ' + alphabet[i]
        board_state += '\n'

        for i in range(self.board_size):
            row=[]
            for j in range(self.board_size):
                row.append(self.stt_to_sym_handler(j+1, i+1))

            if i<9:
                t=i+1
                board_state+=" %d " % t
                for k in range(self.board_size):
                    board_state += row[k] + ' '
                board_state += '\n'
            else:
                t=i+1
                board_state+="%d " % t
                for k in range(self.board_size):
                    board_state += row[k] + ' '
                board_state += '\n'

        print(board_state)

    def remove_near_captured_stones(self, x, y): # assuming move already played
        nb=self.get_neighbor_vert([x,y])
        for i in range(4):
            x_, y_, state=nb[i][0], nb[i][1], nb[i][2]
            if state != 'EMPTY': #checking status of stones
                self.get_connected_gp_list(x_, y_, state)
                if self.count_gp_libs()>0:
                    pass
                    #can't take, connected
                    #this line is the result of 2 hrs of debugging btw

                elif self.can_be_taken(x_, y_, state) and self.is_alone(x_, y_, state):
                    self.board_stat.remove(nb[i])
                    #take one stone

                elif state=='EDGE': continue

                else: #gp libs=0&not alone, take whole gp
                    for elm in self.local_gp_list:
                        self.board_stat.remove(elm)

            else: pass #nothing to take

    def play_check_routine(self, x, y, state):
        #first need to check legality; if legal, find any stones that can be taken to be taken off the board
        if self.is_legal(x, y):
            self.board_stat.append([x, y, state])
            self.remove_near_captured_stones(x, y)
            self.play_hist.append([x, y, state])
            if [x, y, 'EMPTY'] in self.board_stat:
                self.board_stat.remove([x,y,'EMPTY'])

        else:
            print("illegal move!")
            return

    def play(self, x, y, state):
        if self.force_overwrite_to_play != '': # no need to check if overwritten state is things other than 'B' or 'W'
            self.play_check_routine(x, y, self.force_overwrite_to_play)

        elif state != self.det_to_play():
            print("invalid action")
            return

        elif state == self.det_to_play():
            self.play_check_routine(x, y, state)

        self.local_gp_list=[]
        self.past_board_stat.append(self.board_stat)

    def play_assume_legal(self, x, y): # idea from lightvector, leela zero github
        state=self.det_to_play()
        self.board_stat.append([x, y, state])
        self.remove_near_captured_stones(x, y)
        self.play_hist.append([x,y,self.det_to_play()])

    def Pass(self):
        self.play_hist.append('PASS')
        return

    def undo(self):
        self.play_hist=self.play_hist[:-1]
        self.board_stat=self.past_board_stat[-1]
        self.past_board_stat=self.past_board_stat[:-1]

    def resign(self):
        self.Pass()
        self.result='W+Resign' if self.det_to_play() == 'W' else 'B+Resign'

    def fill_empty(self):
        if len(self.board_stat) == 361: return # board_stat is full, nothing to fill
        stt=''
        for i in range(19):
            for j in range(19):
                stt=self.get_state(i+1, j+1)
                if stt == 'EMPTY':
                    self.board_stat.append([i+1, j+1, stt])
                else: pass

    @timer.timer
    def load_game(self, _dir, file_name):
        data=readsgf.get_sgf(_dir, file_name)
        data_=readsgf.converter(readsgf.cropper(data)[1])
        self.play_hist=['filler']
        self.board_stat=[]
        for datum in data_:
            self.play(datum[0], datum[1], self.det_to_play()) if datum is not 'PASS' else self.Pass()

    def score(self, mode='default'): #Japanese counting
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

        result = round(Bscore - Wscore - self.komi, 1) #+ve if b wins, -ve if w wins
        if mode == 'default':
            self.result='B+' + str(result) if result > 0 else 'W+' + str(round(-result, 1)) #Draw counts as w win?
        else:
            remove_list = []
            for member in self.board_stat:
                if member[2] == 'EMPTY': 
                    remove_list.append(member)
            for member in remove_list: self.board_stat.remove(member)
            # If directly invoking the remove method inside the first loop, the index of removal will shift to another member in the list,
            # causing an unwanted effect
            return result

    #utility stuff
    def x_reflect_board_pos(self):
        """reflect the board with respect to the y-axis at centre of the board."""
        for pos in self.board_stat:
            #19, 1 == 1,1
            #18, 1 == 2,1
            pos[0] = self.board_size - pos[0] + 1

    def y_reflect_board_pos(self):
        """reflect the board with respect to the x-axis at centre of the board."""
        for pos in self.board_stat:
            #1, 19 == 1,1
            #1, 18 == 1,2
            pos[1] = self.board_size - pos[1] + 1

    def rotate_board_clockwise_90deg(self):
        for pos in self.board_stat:
            x, y = pos[0], pos[1]
            #1, 2 == 18, 1
            #3, 4 == 16, 3
            pos[0] = self.board_size - y + 1
            pos[1] = x

    def twoto1(self, x, y):
        alphb='abcdefghijklmnopqrs'
        return alphb[x-1] + alphb[y-1]

    def oneto2(self, str_):
        alphb='abcdefghijklmnopqrs'
        return alphb.index(str_[0])+1, alphb.index(str_[1])+1

if __name__ == '__main__':
    toast=board(19, 7.5)
    """toast.load_game('C:\\Users\\admin\\Desktop\\Resonance\\still black and white\\test\\', 'ZENITH_')
#toast.score()
    toast.print_board_state()"""
#print(transformer(toast, toast.board_stat))
#print("--- %s seconds ---" % (time.time() - start_time))
