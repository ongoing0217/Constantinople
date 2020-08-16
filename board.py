import timer, time
import readsgf

class board():
    #play_hist input format:[xcord, ycord, 'STATE']
    #board_stat input format:[xcord, ycord, 'STATE']
    #pass is given as a str 'PASS', not a list
    def __init__(self, board_size, komi, handicap=0):
        self.total=0
        self.board_size=board_size
        self.komi=komi
        self.play_hist=[]
        self.board_stat=[]
        self.past_board_stat=[]
        self.local_gp_list=[]
        self.result=''
        self.force_overwrite_to_play=''
        self.handicapped = False if handicap == 0 else True
        if handicap==0: return
        else:
            if handicap==1:
                self.komi=0
                return
            self.play_hist=[]
            if handicap==2:
                self.board_stat.extend([[15, 3, 'B'], [3, 15, 'B']])
            elif handicap==3:
                self.board_stat.extend([[15, 3, 'B'], [3, 15, 'B'], [15, 15, 'B']])
            elif handicap==4:
                self.board_stat.extend([[15, 3, 'B'], [3, 15, 'B'], [15, 15, 'B'], [3, 3, 'B']])
            elif handicap==5:
                self.board_stat.extend([[15, 3, 'B'], [3, 15, 'B'], [15, 15, 'B'], [3, 3, 'B'], [9, 9, 'B']])
            elif handicap==6:
                self.board_stat.extend([[15, 3, 'B'], [3, 15, 'B'], [15, 15, 'B'], [3, 3, 'B'], [15, 9, 'B'], [3, 9, 'B']])
            elif handicap==7:
                self.board_stat.extend([[15, 3, 'B'], [3, 15, 'B'], [15, 15, 'B'], [3, 3, 'B'], [15, 9, 'B'], [3, 9, 'B'], [9, 9, 'B']])
            elif handicap==8:
                self.board_stat.extend([[15, 3, 'B'], [3, 15, 'B'], [15, 15, 'B'], [3, 3, 'B'], [15, 9, 'B'], [3, 9, 'B'], [9, 3, 'B'], [9, 15, 'B']])
            elif handicap==9:
                self.board_stat.extend([[15, 3, 'B'], [3, 15, 'B'], [15, 15, 'B'], [3, 3, 'B'], [15, 9, 'B'], [3, 9, 'B'], [9, 3, 'B'], [9, 15, 'B'], [9, 9, 'B']])


    def det_to_play(self):
        #returns a state as str
        if self.handicapped:
            if len(self.play_hist) % 2 == 0:
                return 'W'
            elif len(self.play_hist) % 2 == 1:
                return 'B'
        else:
            if len(self.play_hist) % 2 == 0:
                return 'B'
            elif len(self.play_hist) % 2 == 1:
                return 'W'

    def get_state(self, x, y):
        if [x, y, 'B'] in self.board_stat: #check for B stones
            return 'B'
        elif [x, y, 'W'] in self.board_stat: #check for W stones
            return 'W'
        #check if outside board
        elif x>=self.board_size or x<0 or y>=self.board_size or y<0:
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
        # basically do{}while loop
        while True:
        #one expansion

            for elm in self.local_gp_list:
                if elm not in searched: self.expand_search(elm, stt, mode=mode)
                searched.append(elm)

            if back_var - len(self.local_gp_list)==0: break
            back_var = len(self.local_gp_list)

    def remove_repeats(self,list_):
        for elm in list_:
            if list_.count(elm) > 1:
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

    def will_kill_gp(self, x, y, stt):
        # Intuitively, the name should be will_suffocate_gp
        # call premise: there are stones connected to
        # the vertex (x, y) with {stt} as color
        # determines if a move is played, the group
        # will have 0 liberties or not
        self.board_stat.append([x,y,stt])
        self.get_connected_gp_list(x, y, stt)
        if self.count_gp_libs() == 0:
            self.board_stat.remove([x,y,stt])
            return True
        else:
            self.board_stat.remove([x,y,stt])
            return False

    def can_be_taken(self, x, y, stt): #indicates whether stones can be taken when move is played
        self.get_connected_gp_list(x, y, stt)
        return True if self.count_gp_libs()==0 else False

    def is_alone(self, x, y, stt):
        return True if stt not in self.get_neighbor_stat(x, y) else False

    def is_legal(self, x, y):
        if x>18 or x<0 or y>18 or y<0:
            return False
        elif [x,y,'B'] in self.board_stat or [x,y,'W'] in self.board_stat:
            return False
        
        nb=self.get_neighbor_stat(x,y)
        if 'EMPTY' in nb:
            return True
        else:
            stt=self.det_to_play() if self.force_overwrite_to_play == '' else self.force_overwrite_to_play
            if stt in nb:
                return True
                #return False if self.will_kill_gp(x, y, stt) else True

            move = [x,y,stt]
            self.board_stat.append(move)
            ph1 = self.get_neighbor_vert([x, y])
            ph2 = []
            #conditions for 0 liberty play:
            #1. can take a group
            #2. can take 1 stone (the position of the stone is not in ko)
            #3. connected to a gp

            for i in range(4):
                ph2.append('T') if self.can_be_taken(ph1[i][0], ph1[i][1], ph1[i][2]) else ph2.append('F')

            if 'T' not in ph2:
                return False #play 0 libs and not taking anything
            else:
                # ko logic: the vertex which had a single stone taken last move is in ko
                # if the stone played is alone and move previously on the board and move isn't on the board now:
                self.board_stat.remove(move)
                if self.is_alone(x, y, stt) and move in self.past_board_stat[-2] and move not in self.board_stat:
                    return False
                return True

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
                row.append(self.stt_to_sym_handler(j, i))

            if i<9:
                board_state+=" %d " % (i+1)
                for k in range(self.board_size):
                    board_state += row[k] + ' '
                board_state += '\n'
            else:
                board_state+="%d " % (i+1)
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
        st=time.time()
        legal = self.is_legal(x, y)
        self.total+=time.time()-st
        if legal:
            self.board_stat.append([x, y, state])
            self.remove_near_captured_stones(x, y)
            self.play_hist.append([x, y, state])
            if [x, y, 'EMPTY'] in self.board_stat:
                self.board_stat.remove([x,y,'EMPTY'])

        else:
            print(f"{self.twoto1(x, y)} by {state} is an illegal move!")
            self.board_stat.remove([x, y, state])
            return # exit function in case of failure

    def play(self, x, y, state):
        if self.force_overwrite_to_play != '': # no need to check if overwritten state is things other than 'B' or 'W'
            self.play_check_routine(x, y, self.force_overwrite_to_play)

        elif state != self.det_to_play():
            print("invalid action")
            return

        else:
            self.play_check_routine(x, y, state)

        self.local_gp_list=[]
        self.past_board_stat.append(self.board_stat[:])

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
        stt=''
        for i in range(19):
            for j in range(19):
                stt=self.get_state(i, j)
                if stt == 'EMPTY':
                    self.board_stat.append([i, j, stt])
                else: pass

    @timer.timer
    def load_game(self, _dir, file_name, verbose=0):
        data=readsgf.get_sgf(_dir, file_name)
        data_=readsgf.converter(readsgf.cropper(data)[1], verbose=verbose)
        self.play_hist=[]
        self.board_stat=[]
        for datum in data_:
            self.play(datum[0], datum[1], self.det_to_play()) if datum is not 'PASS' else self.Pass()

    def score(self, mode='default'): #Japanese counting
        empty_list, area_label, processed = [], [], []
        Bscore, Wscore = 0,0
        self.fill_empty()

        for i in range(self.board_size):
            for j in range(self.board_size):
                if self.get_state(i, j) is 'B': Bscore+=1
                elif self.get_state(i, j) is 'W': Wscore+=1
                elif [i, j, 'EMPTY'] in processed: continue

                elif [i, j, 'EMPTY'] in self.board_stat: #non-processed empty vertices, should be included in scoring process
                    self.get_connected_gp_list(i, j, 'EMPTY', mode='c')
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
            # If directly invoking the remove method inside the first loop,
            # the index of removal will shift to another member in the list,
            # causing an unwanted effect
            return result

    #utility stuff
    def x_reflect_board_pos(self):
        """reflect the board with respect to the y-axis at centre of the board."""
        for pos in self.board_stat:
            #18, 0 == 0,0
            #17, 0 == 1,0
            pos[0] = self.board_size - pos[0] + 1

    def y_reflect_board_pos(self):
        """reflect the board with respect to the x-axis at centre of the board."""
        for pos in self.board_stat:
            #0, 18 == 0,0
            #0, 17 == 0,1
            pos[1] = self.board_size - pos[1] + 1

    def rotate_board_clockwise_90deg(self):
        for pos in self.board_stat:
            x, y = pos[0], pos[1]
            #0, 1 == 18, 0
            #2, 3 == 15, 3
            pos[0] = self.board_size - y + 1
            pos[1] = x

    def twoto1(self, x, y):
        alphb='abcdefghijklmnopqrs'
        return alphb[x] + alphb[y]

    def oneto2(self, str_):
        alphb='abcdefghijklmnopqrs'
        return alphb.index(str_[0]), alphb.index(str_[1])
    
    def locate_near_empty_points(self, gp):
        empty_list=[]
        for vert in gp:
            nb=self.get_neighbor_vert([vert[0], vert[1]])
            for elm in nb:
                if elm in gp: continue
                if elm[2] == 'EMPTY': empty_list.append(elm)
            if len(empty_list) >= 2: return
        return empty_list
    
    def inform_updated_legality(self, x, y, state, legality_side):
        """
        returns the new legal and illegal positions *for the side to play*
        after the move formed by the function parameters are played.
        depends on self.board.board_stat.

        the control flow of the function is designed so as 
        to maximize efficiency and it may not be intuitive
        to understand.
            
        """
        self.board_stat.append([x, y, state])
        new_legal_verts_index, new_illegal_verts_index = [], [x+19*y]

        for vert in self.get_neighbor_vert([x, y]): # point, member, elm and vert are the same things with different names: [x, y, state]
            
            nb_stt = vert[2]
            if nb_stt == 'EDGE': continue
            
            # reducing liberties may cause the remaining vertex(s) to be a suicide move

            # check if other groups' liberties are limited
            # only necessary if the move played is different
            # from the legality side

            # the move can limit liberties of the group directly; or
            # block a space such that when the group extends, it will
            # have 0 liberties remaining, while it originally can extend
            # and still have 1 liberty

            # this block is handling the second case.
            if state != legality_side and nb_stt == 'EMPTY':
                x_, y_ = vert[0], vert[1]
                move = [x_, y_, legality_side]
                if self.get_neighbor_stat(x_, y_).count('EMPTY') < 2:
                    self.board_stat.append(move)
                    self.get_connected_gp_list(x_, y_, legality_side)
                    if self.count_gp_libs() == 0:
                        new_illegal_verts_index.append(x_+19*y_)
                    self.board_stat.remove(move)

            elif nb_stt == 'B' or nb_stt == 'W':
                self.get_connected_gp_list(vert[0], vert[1], nb_stt)
                empty_pts = self.locate_near_empty_points(self.local_gp_list)
                if empty_pts == None: continue # >=2 liberties
                liberties = len(empty_pts) 
                if liberties == 0:
                    # legality effected for vertices adjacent to groups (of the same color) connected to the taken groups
                    # and the taken groups themselves, special case being ko

                    # assign all stones that will be taken as legal vertices again
                    # if in ko however, it won't be registered
                    verts_adj_to_gp=[]
                    stone_removed = True
                    for member in self.local_gp_list:
                        if len(self.local_gp_list) == 1:
                            # taking 1 stone may result in ko illegality
                            if member[2] != legality_side and not self.is_ko(member):
                                new_legal_verts_index.append(member[0] + 19*member[1]) # index
                            else: stone_removed = False
                        else:
                            new_legal_verts_index.append(member[0] + 19*member[1])

                        if stone_removed:
                            for point in self.get_neighbor_vert([member[0], member[1]]):
                                if point[2] != 'EMPTY' and point not in self.local_gp_list:
                                    verts_adj_to_gp.append(point)

                    if stone_removed:
                        original_gp = self.local_gp_list[:]
                        nearby_gps=[]
                        # trace all groups connected to the adjacent vertices
                        for member in verts_adj_to_gp:
                            self.get_connected_gp_list(member[0], member[1], member[2])
                            if self.local_gp_list not in nearby_gps and self.local_gp_list != original_gp:
                                nearby_gps.append(self.local_gp_list[:])

                        # if they have exactly 1 empty point next to them,
                        # assign the point to be legal again
                        for gp in nearby_gps:
                            pts = self.locate_near_empty_points(gp)
                            if pts != None and len(pts) == 1:
                                x_, y_ = pts[0][0], pts[0][1]
                                self.board_stat.append([x_, y_, legality_side])
                                self.get_connected_gp_list(x_, y_, legality_side)
                                if self.count_gp_libs() == 0:
                                    new_legal_verts_index.append(x_+19*y_)
                                self.board_stat.remove([x_, y_, legality_side])

                # else: pass / 1 liberty case handled below
                #              at >=2 liberties nothing happens

        # check if self liberties is limited
        # the first case of the aforementioned liberty limit   
        if state == legality_side:
            self.get_connected_gp_list(x, y, state)
            point = self.locate_near_empty_points(self.local_gp_list)
            if point != None and len(point) == 1:
                index = point[0][0] + 19*point[0][1]
                new_illegal_verts_index.append(index)
            #else: pass / gp still has higher than 1 liberty -- nothing related to the group happens

        self.board_stat.remove([x, y, state])
        return new_legal_verts_index, new_illegal_verts_index
    
if __name__ == '__main__':
    toast=board(19, 7.5)
    toast.load_game('C:\\Users\\admin\\Desktop\\Resonance\\still black and white\\test\\', 'ZENITH_', verbose=1)
    print(toast.total)
#toast.score()
    #print(toast.board_stat, toast.play_hist)
    """toast.print_board_state()"""
#print(transformer(toast, toast.board_stat))
#print("--- %s seconds ---" % (time.time() - start_time))
