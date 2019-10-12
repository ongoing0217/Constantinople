import time
start_time = time.time()

class board():
    #_play_hist input format:[xcord, ycord]
    #may merge it into board_stat later
    #board_stat input format:[xcord, ycord, 'STATE']
    #pass is given as a str 'PASS', not a list
    def __init__(self, board_size, komi):
        self.board_size=board_size
        self.komi=komi
        self._play_hist=['filler']
        self.board_stat=[]
        self.local_gp_list=[]
        
    
    def det_to_play(self):
        #returns a state as str
        if self._play_hist[-1] == 'PASS':
            return self._play_hist[-2][2]
        elif len(self._play_hist) % 2 ==0:
            return 'W'
        elif len(self._play_hist) % 2 ==1:
            return 'B'
        else:
            print("something is wrong : det_to_play")
        
    def join_vertex(self, x, y, state=''):
        #returns a vertex with 2 int as list
        #usual return value is appended to board_stat
        vertex=[]
        vertex.append(x)
        vertex.append(y)
        
        if state is not '':
            #state is predetermined
            vertex.append(state)
            return vertex
        
        else:
            vertex.append(self.det_to_play())
            return vertex
        del vertex

    def stat_update(self,x,y,stt=''):
        #call board_stat first so that the move has the same stats
        if stt == '':
            #default
            self.board_stat.append(self.join_vertex(x,y))
            self._play_hist.append(self.join_vertex(x,y))

        else:
            self.board_stat.append(self.join_vertex(x,y,state=stt))
            self._play_hist.append(self.join_vertex(x,y,state=stt))
        
    def is_ko(self, x, y, move=[]):
        #determines if the vertex given is in invalid state due to ko
        #assumes nothing else happened to the stones nearby, may fail
        move.append(x)
        move.append(y)
        move.append(self.det_to_play())
        if self._play_hist[len(self._play_hist)-1] == move:
            return True
        else:
            return False

    def get_state(self, x, y):
        #check if outside board
        if x>self.board_size or x<1 or y>self.board_size or y<1:
            return 'EDGE'
        elif x>self.board_size and y>self.board_size:
            return 'CORNER'
        elif x>self.board_size and y<1:
            return 'CORNER'
        elif x<1 and y>self.board_size:
            return 'CORNER'
        elif x<1 and y<1:
            return 'CORNER'
        
        #black or white output
        elif self.join_vertex(x, y, state='B') in self.board_stat:
            return 'B'
        elif self.join_vertex(x, y, state='W') in self.board_stat:
            return 'W'
        #empty output
        elif self.join_vertex(x,y) not in self._play_hist:
            return 'EMPTY'
        
        else:
            print('something is wrong : parse_color')

    def get_neighbor_stat(self, x, y):
        #returns states of 4 neighboting vertices in a clockwise order
        #can't think of better methods =.=
        return [self.get_state(x,y-1),
        self.get_state(x+1,y),
        self.get_state(x,y+1),
        self.get_state(x-1,y)
                ]
    
    def get_neighbor_vert(self, vertex):
        #returns 4 neighboting vertices in list form in a clockwise order
        x_, y_ = vertex[0], vertex[1]
        return [self.join_vertex(x_,y_-1,state=self.get_state(x_,y_-1)),
        self.join_vertex(x_+1,y_,state=self.get_state(x_+1,y_)),
        self.join_vertex(x_,y_+1,state=self.get_state(x_,y_+1)),
        self.join_vertex(x_-1,y_,state=self.get_state(x_-1,y_))
                ]
    
    def repeat_check(self,elm,list_):
        #check if an element is repeated for a given list.
        if elm in list_:
            return True
        else: return False
        
    def list_transfer(self,list_,stt,n=[]):
        n=[]
        for i in range(len(list_)):
            if list_[i] != stt:
                n.append('EMPTY')
            elif list_[i] in stt:
                n.append(stt)
            else:
                print("something is wrong")

        return n

    def expand_search(self, coord, stt, x=0, y=0):
        """Takes a list as input!"""
        if stt == 'EMPTY':
            print("cannot expand on empty vertex")
            return
        x,y = coord[0], coord[1]
        nb=self.list_transfer(self.get_neighbor_stat(x,y),stt)
        k=[]
        def nothing():
            pass

        while True:           
            
            if len(k) == 4: break
                #sealing holes
            elif 0 not in k:
                if nb[0] == stt:
                    self.local_gp_list.append(self.join_vertex(x,y-1,state=stt)) if not self.repeat_check(self.join_vertex(x,y-1,state=stt), self.local_gp_list) else nothing()
                    k.append(0)
                else:
                    k.append(0)
            elif 1 not in k:
                if nb[1] == stt:
                    self.local_gp_list.append(self.join_vertex(x+1,y,state=stt)) if not self.repeat_check(self.join_vertex(x+1,y,state=stt), self.local_gp_list) else nothing()
                    k.append(1)
                else:
                    k.append(1)
            elif 2 not in k:
                if nb[2] == stt:
                    self.local_gp_list.append(self.join_vertex(x,y+1,state=stt)) if not self.repeat_check(self.join_vertex(x,y+1,state=stt), self.local_gp_list) else nothing()
                    k.append(2)
                else:
                    k.append(2)
            elif 3 not in k:
                if nb[3] == stt:
                    self.local_gp_list.append(self.join_vertex(x-1,y,state=stt)) if not self.repeat_check(self.join_vertex(x-1,y,state=stt), self.local_gp_list) else nothing()
                    k.append(3)
                else:
                    k.append(3)
        return k
    
    def get_connected_gp_list(self, x, y, stt):
        if self.get_state(x,y) not in self.get_neighbor_stat(x,y): return None
        back_var=0
        if stt is not 'EMPTY': 
            self.local_gp_list.append(self.join_vertex(x,y,state=stt))
            #special case, implement counting of empty spaces when writing counting rules
        #repeat expansions
        while True:
        #one expansion
            for elm in self.local_gp_list:
                self.expand_search(elm, stt)
                #search all the elements of the list
                #only want elements of the same state
                #if element is in list: don't append
                #if not: do append                
                for i in range(len(self.local_gp_list)):
                    if self.local_gp_list.count(elm)>1:
                        pass
                    elif self.local_gp_list.count(elm)==1:
                        self.expand_search([elm[0],elm[1]],stt)
                        
            if back_var - len(self.local_gp_list)==0:
                break
            back_var = len(self.local_gp_list)
            
    def remove_repeats(self,list_):
        for elm in list_:
            if list_.count(elm) >1:
                list_.remove(elm)
            else:
                pass
    
    def count_gp_libs(self,list_=[]):
        #condition:local_gp_list isn't empty
        list_=[]
        for k in range(len(self.local_gp_list)):
            for i in range(4):
            #get all the vertices of the elements' neighbors
                list_.append(self.get_neighbor_vert(self.local_gp_list[k])[i])
            #process the vertices
            self.remove_repeats(list_)
        for j in range(len(list_)):
            list_.append(list_[0][2])
            list_.remove(list_[0])
            
        return list_.count('EMPTY')

    def will_kill_gp(self, x, y, stt=''):
        stt=self.det_to_play()
        self.board_stat.append(self.join_vertex(x,y,state=stt))
        if stt in self.get_neighbor_stat(x,y):
            self.get_connected_gp_list(x,y,stt)
            if self.count_gp_libs() == 0:
                self.board_stat.remove(self.join_vertex(x,y,state=stt))
                return True
            else:
                self.board_stat.remove(self.join_vertex(x,y,state=stt))
                return False
        else:
            #not connected to any group, how can it kill a group?
            self.board_stat.remove(self.join_vertex(x,y,state=stt))
            return False
                
    def is_legal(self, x, y, list1_=[]):
        stt=self.det_to_play()
        if x>19 or x<1 or y>19 or y<1:
            return False
        elif self.join_vertex(x,y,state='B') in self.board_stat:
            return False
        elif self.join_vertex(x,y,state='W') in self.board_stat:
            return False
        elif not self.will_kill_gp(x,y):
            if self.get_neighbor_stat(x,y).count('EMPTY') >=1:
                return True
            elif self.get_neighbor_stat(x,y).count('EMPTY') ==0:
                for i in range(4):
                    #get the stats of nearby vertices
                    #if they are connected to a group: count the liberties of the group
                    #if placing can capture: return a special output for play function and return True
                    #if they are solo: count their liberties
                    #if placing can capture and is not ko: return a special output for play function and return True

                    list1_.append(self.get_neighbor_vert([x,y])[i])
                for j in range(4):
                    if self.get_connected_gp_list(list1_[j][0],list1_[j][1],stt) is None:
                        #alone
                        if not self.is_ko(x,y):
                            self.board_stat.append(self.join_vertex(x,y,state=stt))
                            if self.get_neighbor_stat(list1_[j][0],list1_[j][1]).count('EMPTY')==0:
                                self.board_stat.remove(self.join_vertex(x,y,state=stt))
                                return True
                            else:
                                self.board_stat.remove(self.join_vertex(x,y,state=stt))
                                return False
                        else: return False

                    elif len(self.get_connected_gp_list(list1_[j])) != 0:
                        return True
                    #no need to check since not killing the group is prerequisite

        else: return False

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
        #Adjusted
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
            if state == 'PASS':
                self.board_stat.append('PASS')
                print("%s pass" % self.det_to_play)
                return
            else:
                print("invalid action")
                return
            
        elif state == self.det_to_play():
            #first need to check legality; if legal, check for any stones that can be taken to be taken off the board
            if self.is_legal(x, y):
                self.board_stat.append(self.join_vertex(x,y,state=self.det_to_play()))
                if self.get_connected_gp_list(x, y, state) is None:
                    #alone
                    
                    for i in range(4):
                        
                        self.get_connected_gp_list(nb[i][0], nb[i][1], self.get_state(nb[i][0], nb[i][1]))
                        if self.count_gp_libs()==0: #returned false
                            #taking a group, no kos
                            for j in range(len(self.local_gp_list)):
                                self.board_stat.remove(self.local_gp_list[j-1])
                            self._play_hist.append(self.join_vertex(x,y,self.det_to_play()))
                            self.local_gp_list=[]
                            
                        elif self.get_neighbor_stat(nb[i][0], nb[i][1]).count('EMPTY')==0:
                            self.board_stat.remove(nb[i])
                            self._play_hist.append(self.join_vertex(x,y,self.det_to_play()))
                            self.local_gp_list=[]

                else:
                    self._play_hist.append(self.join_vertex(x,y,self.det_to_play()))

            else:
                print("illegal move!")

        else: print("something is wrong")

    def remove_vertex(self, x, y):
        self.board_stat.remove(self.join_vertex(x, y, state=self.get_state(x,y)))
        self._play_hist.remove(self.join_vertex(x, y, state=self.get_state(x,y)))
                        
    def init_game(self, board_size, komi):
        self.__init__(board_size, komi)
        print("Komi:", self.komi, ",", "Board size:", self.board_size)

toast=board(19,6.5)
toast.init_game(19,6.5)

#toast.board_stat.append([4,3,'W'])
#toast.board_stat.append([4,2,'B'])
#toast.board_stat.append([3,2,'B'])
#toast.board_stat.append([2,3,'B'])
#toast.board_stat.append([3,4,'B'])
#toast.board_stat.append([4,4,'W'])
#toast.board_stat.append([3,3,'W'])
#toast.board_stat.append([5,4,'B'])
#toast.board_stat.append([5,3,'B'])
toast.play(4,4,'B')
print("--- %s seconds ---" % (time.time() - start_time))
