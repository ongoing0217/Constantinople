import tensorflow as tf
import board as _board
import numpy as np
import random
from tensorflow.keras import models
import timer, time

def structer(board_stat, mode='B'):
    pre=[]
    for i in range(19):
        ph=[]
        for j in range(19):
            if [j+1, i+1, mode] in board_stat:
                ph.append(1.)
            else:
                ph.append(0.)
        pre.append(ph)

    return pre

def dirichlet_noise(self, p, x=0.5):
    return x*p + (1-x)*np.random.dirichlet_noise(p)

def nhwc_to_nchw(tensor):
    return tf.transpose(tensor, [0, 2, 3, 1])
    
class MCtree():
    def __init__(self,
                 network,
                 komi=7.5,
                 board_size=19,
                 base_play_hist=['filler'],
                 base_board_stat=[],
                 use_num_threads=1,
                 use_num_gpus=0,
                 reset_network = True,
                 reset_num_threads = True,
                 reset_num_gpus = True):
        
# Total action value is not used.
# trunk name: a string enlisting the complete play history from base position following parent
# -> children from left to right without spacing, not including the move played itself.
# node: [trunk_name, played move, board_stat, edge probability(tensor), all legal moves, V, action vector(Q), visit vector(N)]
# nodes go through 2 stages of development cycle:
# 1. Unevaluated: contains most necessary data of a node except policy and value,
#    and if pass is allowed or not assuming dumbpass not enabled.
# 2. Complete: contains all intended data the node is supposed to have.
# node dict:{'branch': node...}
# branch = trunk_name + move_played
# Figuratively, a small tree sort of look like this:
#      ''  (base)
#      /\
# 'aa'/  \'ab'

        if reset_num_threads:
            tf.compat.v1.ConfigProto(inter_op_parallelism_threads = use_num_threads)
        if reset_num_gpus:
            self.use_num_gpus=use_num_gpus
        if reset_network:
            self.network=network

        self.board=_board.board(board_size, komi)
        self.base_play_hist, self.base_board_stat = base_play_hist, base_board_stat
        self.base_to_play = 'W' if len(self.base_play_hist) % 2 == 0 else 'B'
        # Base to play means which player to play at the base position
        self.batched_positions = []
        self.batch_cycle = 0
        # Variables to be used for batching
        self.dumbpass_enabled = False
        
        # initializing base node
        self.node_dict={'':[0, 0, self.base_board_stat]}
        # Put in a dummy just to enable current board stat to be accessed,
        # which is to be replaced later by a fully developed node.

        # generate the first evaulation matrix.
        
        array=[]
        empty=[[0. for i in range(19)] for i in range(19)]

        base_branch = self.generate_branch(self.base_play_hist)
        
        no_of_moves = int(len(base_branch)/2)
        if no_of_moves>=4:
            #This block can't be condensed into a function sadly
            for i in range(4):
                board_stat = self.reconstruct_board_stat(no_of_moves-i)
                array.append(structer(board_stat, mode='B'))
                array.append(structer(board_stat, mode='W'))

        else:
            for i in range(no_of_moves):
                board_stat = self.reconstruct_board_stat(no_of_moves-i)
                array.append(structer(board_stat, mode='B'))
                array.append(structer(board_stat, mode='W'))
            for i in range(4-no_of_moves):
                array.append(empty)
                array.append(empty)

        # Determining who to play next: if W then fill with 0s, if B then fill with 1s
        if self.base_to_play == 'B':
            if no_of_moves % 2 == 0: #even number of moves played -- back to b
                array.append([[1. for i in range(19)] for i in range(19)])
            else: 
                array.append(empty)
        else:
            if no_of_moves % 2 == 0: #vise versa
                array.append(empty)
            else:
                array.append([[1. for i in range(19)] for i in range(19)])
                
        with tf.device('/CPU:0'):
            P, V = self.network.predict(nhwc_to_nchw(tf.reshape(array, [1, 9, 19, 19])))
        P, V = P[0], V[0][0]

        self.base_all_legal_positions = []
        # "second" literally means that the object represents states
        # from 1 move before the base board
        self.second_board_stat = self.reconstruct_board_stat(
            len(self.base_play_hist)-1-1)
        # extra -1 is for the filler
        
        if self.base_board_stat == []: # Empty board
            
            self.second_all_legal_positions = [1 for i in range(361)]
            # They don't exist on an empty board -> None
            
            self.base_all_legal_positions = self.second_all_legal_positions[:]
            if self.base_to_play == 'B':
                
                if self.pass_enabled(V, 'B', 361):
                    self.base_all_legal_positions.append(1)
                else:
                    self.base_all_legal_positions.append(-32767)

            else:
                
                if self.pass_enabled(V, 'W', 361):
                    self.base_all_legal_positions.append(1)
                else:
                    self.base_all_legal_positions.append(-32767)

        else:
            
            # generate base legality positions for b or w depending
            # on who to play first, 1 for legal and 0 for illegal
            self.board.board_stat = self.base_board_stat
            self.second_all_legal_positions = []
            
            if self.base_to_play == 'B':
                self.board.force_overwrite_to_play = 'B'
                for i in range(19):
                    for j in range(19):
                        if self.board.is_legal(j+1, i+1):
                            self.base_all_legal_positions.append(1)
                        else:
                            self.base_all_legal_positions.append(-32767)

                b_no_legal_verts = 361-self.base_all_legal_positions.count(-32767)
                # counting the more common element is faster
                if self.pass_enabled(V, 'B', b_no_legal_verts):
                    self.base_all_legal_positions.append(1)
                else:
                    self.base_all_legal_positions.append(-32767)
                # next section
                self.board.board_stat = self.second_board_stat[:]
                self.board.force_overwrite_to_play = 'W'
                for i in range(19):
                    for j in range(19):
                        if self.board.is_legal(j+1, i+1): 
                            self.second_all_legal_positions.append(1)
                        else:
                            self.second_all_legal_positions.append(-32767)                

                    
            else:
                self.board.force_overwrite_to_play = 'W'
                for i in range(19):
                    for j in range(19):
                        if self.board.is_legal(j+1, i+1): 
                            self.base_all_legal_positions.append(1)
                        else:
                            self.base_all_legal_positions.append(-32767)
         
                w_no_legal_verts = 361-self.base_all_legal_positions.count(-32767)
                if self.pass_enabled(V, 'W', w_no_legal_verts):
                    self.base_all_legal_positions.append(1)
                else:
                    self.base_all_legal_positions.append(-32767)
                # next section
                self.board.board_stat = self.second_board_stat[:]
                self.board.force_overwrite_to_play = 'B'
                for i in range(19):
                    for j in range(19):
                        if self.board.is_legal(j+1, i+1, 'B'):
                            self.second_all_legal_positions.append(1)
                        else:
                            self.second_all_legal_positions.append(-32767)

        # Definitions:
        # Base node is the node located exactly on the position of the inputted untouched board
        # '' as trunk name indicates no move was played

        # Not using variables for the same values because they shouldn't refer to the same object
        self.empty = [0. for i in range(362)]
        self.base_node=['', '', self.base_board_stat, P, self.base_all_legal_positions, V,
                        np.array(self.empty), np.array(self.empty[:])]
        
        self.base_stats=[V, 0, 0, 0, 1, 0, 0, 1] # 0.NNeval, 1.AvgDepth, 2.MaxDepth, 3.AvgChildren, 4.Visits, 5.no.Nodes, 6.Playouts, 7.NumChildren
        
        self.node_dict[''] = self.base_node

        self.total = 0
        
# utility
    def twoto1(self, x, y):
        alphb='abcdefghjklmnopqrst'
        return alphb[x-1] + alphb[y-1]

    def oneto2(self, str_):
        alphb='abcdefghjklmnopqrst'
        return alphb.index(str_[0])+1, alphb.index(str_[1])+1

    def test_err(node):
        try:
            assert len(node)==5
        except AssertionError:
            raise ValueError('Node Error')

    def num_to_pos(self, num):
        alphb='abcdefghjklmnopqrst'
        return alphb[num%19] + alphb[int(num/19)]

    def hasher(list_of_pos):
        hash_=''
        for elm in list_of_pos:
            hash_+=elm
        return hash_

    def generate_play_hist(self, trunk_name):
        # generate a playing history from empty board up
        new_hist = [elm for elm in self.base_play_hist]
        original_to_play = self.base_play_hist[-1][2]
        alt_to_play = 'B' if original_to_play == 'W' else 'W'
        extended_play_hist=[]
        for i in range(int(len(trunk_name)/2)):
            x, y = self.oneto2(trunk_name[i:i+2])
            extended_play_hist.append([x, y, alt_to_play]) if i % 2 == 0 else [x, y, original_to_play]
        new_hist.extend(extended_play_hist)
        return new_hist

    def generate_branch(self, play_hist):
        branch=''
        for elm in play_hist[1:]:
            branch += self.twoto1(elm[0], elm[1])
        return branch

    def det_to_play_from_trunk(self, trunk_name):
        no_of_moves_played_from_base = len(trunk_name)/2

        if self.base_to_play == 'B':
            return 'B' if no_of_moves_played_from_base % 2 == 0 else 'W'
        else:
            return 'B' if no_of_moves_played_from_base % 2 == 1 else 'W'


    def reconstruct_board_stat(self, t):
        #reconstruct the board from EMPTY board, t indicating the time step which the move is played, t=0 is when the board is empty
        self.board.board_stat, self.board.play_hist = [], ['filler']
        for move in self.base_play_hist[1:t+1]:
            self.board.play(move[0], move[1], move[2])

        return self.board.board_stat

    def pass_enabled(self, nneval, scoring_for, legal_verts_count):
        # depends on the board stat at the time

        # About pass policy...

        # """
        # // Always try passes if we're not trying to be clever.
        # auto allow_pass = cfg_dumbpass;
        #        
        # // Less than 20 available intersections in a 19x19 game.
        # if (nodelist.size() <= std::max(5, BOARD_SIZE)) {
        #     allow_pass = true;
        # }
        #
        # // If we're clever, only try passing if we're winning on the
        # // net score and on the board count.
        # if (!allow_pass && stm_eval > 0.8f) {
        #     const auto relative_score =
        #         (to_move == FastBoard::BLACK ? 1 : -1) * state.final_score();
        #     if (relative_score >= 0) {
        #         allow_pass = true;
        #     }
        # }
        # """
        #
        # From Leela Zero UCTNode.cpp
        # Basically, when allow_pass = True, passes are always attempted.
        # If cfg_dumbpass enabled / less than 20 intersections on board
        # OR winning in relative score and nn eval above some margin:
        # Pass enabled as an option
        # Meaning? 1 extra edge created at each node where pass is enabled
        # with the name of the move played being 'PASS'. 
        # Identifier of 'PASS' in the trunk name is 'xp'.

        if self.dumbpass_enabled: return True

        if legal_verts_count < 20:
            return True

        if nneval > 0.8: # nested if to prevent scoring all the time
            if scoring_for == 'B':
                if self.board.score(mode=1) > 0.: # board.score +ve then B is winnning 
                    return True
            else:
                if self.board.score(mode=1) < 0.:
                    return True

        return False

# main functions
    def gen_input_matrix(self, branch): #branch = trunk_name + move_played
        array=[] #final input matrix
        empty=[[0. for i in range(19)] for i in range(19)]
        
        #fetch values for parent nodes -> convert their positions -> add to array
        # cases:
        
        # i.  branch length >= 4*2
        #     All prev boards accessible, fetch from node dict like normal
        # ii. branch length < 4*2:
        #     2 more cases under this condition
        # 1. base board stat length + branch length >= 4*2:
        #    fetch from node dict + regenerate with base board stat
        # 2. base board stat length + branch length < 4*2:
        #    fetch from node dict + regenerate + fill with empty

        no_of_moves = int(len(branch)/2)
        if no_of_moves>=4:
            #This block can't be condensed into a function sadly
            for i in range(4):
                new_branch = branch if i==0 else branch[:-2*i]
                board_stat = self.node_dict[new_branch][2]
                array.append(structer(board_stat, mode='B'))
                array.append(structer(board_stat, mode='W'))

        else:
            n = len(self.base_play_hist)

            if n + no_of_moves >= 4:
                # n moves played prior to start of search, 1 move played after search:
                # want board stat at t=n-1, n-2, n-32767
                for i in range(no_of_moves):
                    new_branch = branch if i==0 else branch[:-2*i]
                    board_stat = self.node_dict[new_branch][2]
                    array.append(structer(board_stat, mode='B'))
                    array.append(structer(board_stat, mode='W'))
                for i in range(4-no_of_moves):
                    board_stat = self.reconstruct_board_stat(n-i)
                    array.append(structer(board_stat, mode='B'))
                    array.append(structer(board_stat, mode='W'))

            else:
                for i in range(no_of_moves):
                    new_branch = branch if i==0 else branch[:-2*i]
                    board_stat = self.node_dict[new_branch][2]
                    array.append(structer(board_stat, mode='B'))
                    array.append(structer(board_stat, mode='W'))
                for i in range(n):
                    board_stat = self.reconstruct_board_stat(n-i)
                    array.append(structer(board_stat, mode='B'))
                    array.append(structer(board_stat, mode='W'))
                for i in range(4-no_of_moves-n):
                    array.append(empty)
                    array.append(empty)

        #randomized dihedral reflection/rotations
        # y_reflect = random.choice([True, False])
        # degree_of_rotation = random.choice([0,1,2,3])
        # size = self.board.board_size
        # if y_reflect:
        #     for pos in array:
        #         for move in pos:
        #             move[1] = size - move[1] + 1
        #     for pos in array:
        #         for move in pos:
        #             move[1] = size - move[1] + 1

        # for i in range(degree_of_rotation):
        #     for pos in array:
        #         for move in pos:
        #             x, y = move[0], move[1]
        #             move[0] = size - y + 1
        #             move[1] = x
        #     for pos in array:
        #         for move in pos:
        #             x, y = move[0], move[1]
        #             move[0] = size - y + 1
        #             move[1] = x

        # Determining who to play next: if W then fill with 0s, if B then fill with 1s
        if self.base_to_play == 'B':
            if no_of_moves % 2 == 0: #even number of moves played -- back to b
                array.append([[1. for i in range(19)] for i in range(19)])
            else: 
                array.append(empty)
        else:
            if no_of_moves % 2 == 0: #vise versa
                array.append(empty)
            else:
                array.append([[1. for i in range(19)] for i in range(19)])

        return array

    #@timer.timer
    def gen_value(self, branch):
        # will become basically obsolete after eval_batch is implemented
        array = self.gen_input_matrix(branch)
        with tf.device('/CPU:0'):
            P, V = self.network.predict(tf.constant(array, shape=[1, 19, 19, 9]))
        return P, V

# node: [trunk_name, played move, board_stat, edge probability(tensor), list of every legal action, value, action vector(Q), visit vector(N)]

    #@timer.timer
    def eval_batch(self):
        """Evaluates a batch of positions and do all the necessary updates to the affected nodes.""" 
        # N=int((n*(1<<14)*SM)/(H*W*C)) is a good batch size, where n is an integer and
        # SM the number of multiprocessors of the GPU (80 for V100, 68 for RTX 2080 Ti). 
        # Remi Coulom @ https://twitter.com/Remi_Coulom/status/1259188988646129665?s=20
        dense_input = [self.gen_input_matrix(branch) for branch in self.batched_positions]
        if self.use_num_gpus == 0:
            with tf.device('/CPU:0'):
                outputs = self.network.predict(nhwc_to_nchw(dense_input))
        else: raise NotImplementedError

        Parray, Varray = outputs[0], outputs[1]
        for i in range(self.batch_cycle):
            branch = self.batched_positions[i]
            node = self.node_dict[branch]
            P, V = Parray[i], Varray[i][0]
            self.board.board_stat, legal_moves = node[2], node[4]

            to_play = self.det_to_play_from_trunk(branch[:-2])
            if self.pass_enabled(V, to_play, 361-legal_moves.count(0)):
                legal_moves.append(1)
            else:
                legal_moves.append(-32767)

            x, y = self.oneto2(branch[-2:])
            index = x + (y-1)*19 -1
            depth = int(len(branch)/2)
            for j in range(depth):
                trunk_name = branch[:-2]
                parent_name = trunk_name if i==0 else trunk_name[:-(2*i)]
                node = self.node_dict[parent_name]
                Q, N = float(node[6][index]), float(node[7][index]) # N already updated
                Q = (Q*(N-1)+V) / N
                node[6][index] += Q

            node = self.node_dict[branch]
            node[3], node[5] = P, V

            if depth > self.base_stats[2]: self.base_stats[2] = depth
        
        # 2.MaxDepth, 3.AvgChildren, 4.Visits, 5.no.Nodes, 6.Playouts, 7.NumChildren
        self.base_stats[4] += self.batch_cycle
        self.base_stats[6] += self.batch_cycle
        self.base_stats[7] += depth # each update 
        
        self.batch_cycle = 0
        self.batched_positions = []

    def locate_near_empty_point(self, gp):
        empty_list=[]
        for vert in gp:
            nb=self.board.get_neighbor_vert([vert[0], vert[1]])
            for elm in nb:
                if elm in gp: break
                if elm[2] == 'EMPTY': empty_list.append(elm)
            if len(empty_list) >=2: return # >=2 liberties means nothing happens
        return empty_list[0]

    def inform_updated_legality(self, x, y, state):
        """returns the new legal and illegal positions after the move formed by the function parameters are played.
        depends on self.board.board_stat."""

        # Am I taking algorithm class?????
        self.board.board_stat.append([x, y, state])
        new_legal_verts_index, new_illegal_verts_index, adj_verts = [], [x+(y-1)*19-1], self.board.get_neighbor_vert([x, y]) # -1 due to counting from 0
        for vert in adj_verts: # point, member, elm and vert are the same things with different names: [x, y, state]
            nb_stt = vert[2]
            if nb_stt == 'EMPTY' or nb_stt == 'EDGE': continue
            self.board.get_connected_gp_list(vert[0], vert[1], vert[2])

            if self.board.count_gp_libs() == 0: # a group will be taken after move is played
                # legality effected for vertices adjacent to groups (of the same color) connected to the taken groups
                # and the taken groups themselves
                verts_adj_to_gp=[]
                for member in self.board.local_gp_list:
                    index = member[0] + (member[1]-1)*19 -1 # x+(y-1)*19-1
                    new_legal_verts_index.append(index)

                    for point in self.board.get_neighbor_vert([member[0], member[1]]):
                        if point[2] != 'EMPTY' and point not in self.board.local_gp_list:
                            verts_adj_to_gp.append(point)

                nearby_gps=[]
                # trace all groups connected to the adjacent vertices
                for member in verts_adj_to_gp:
                    self.board.get_connected_gp_list(member[0], member[1], member[2])
                    if self.board.local_gp_list not in nearby_gps:
                        new_gp = []
                        for elm in self.board.local_gp_list:
                            new_gp.append(elm)
                        nearby_gps.append(new_gp)

                # if they have exactly 1 empty point next to them, assign the point to be legal again
                for gp in nearby_gps:
                    point = self.locate_near_empty_point(gp)[0]
                    if point != None and point not in new_legal_verts:
                        index = point[0] + (point[1]-1)*19 -1
                        new_legal_verts_index.append(index)

            else:
                # reducing liberties may cause the remaining vertex(s) to be a suicide move
                point = self.locate_near_empty_point(self.board.local_gp_list)
                if point != None: 
                    index = point[0] + (point[1]-1)*19 -1
                    new_illegal_verts_index.append(index)
                #else: pass / gp still has higher than 1 liberty -- nothing related to the group happens

        self.board.board_stat.remove([x, y, state])
        return new_legal_verts_index, new_illegal_verts_index

# node: [trunk_name, played move, board_stat, edge probability(tensor), list of every legal action, value, action vector(Q), visit vector(N)]

    #@timer.timer
    def create_new_node(self, branch):
        # Handles most of the necessary procedures in creating a new node after search.
        # The remaining procedures are handled in self.eval_batch().
        
        # First batch the position for eval. Then update list of legal actions.
        # Next backup data by updating N in every node above.
        
        # Handling legality
        # not doing self.board.is_legal(i, j, '') on every vertex for obvious reasons
        # instead, by the knowledge that only groups adjacent to the move played and the groups
        # in alternate color adjacent to the aforementioned groups have legality changes, an 
        # algorithm is used to pinpoint the location where legality is changed.

        # Case 1: t>=2
        # access legal position from t-2 where the players are the same for both moves.
        # update once for the move at t-1 and for the move at t.
        # Case 2: t=1
        # access legal position from t=-1: 1 move before the board position.
        # if the board is empty at t=-1, only 1 update is needed.
        # otherwise, 2 updates are still needed.
        # Case 3: t=0, the base node, impossible since base node already initialized

        trunk_name, move_played = branch[:-2], branch[-2:]
        parent = self.node_dict[trunk_name]
        depth = len(branch)/2

        to_play = self.det_to_play_from_trunk(trunk_name)
        one_move_from_base = False
        if depth >= 2:
            grandparent = self.node_dict[trunk_name[:-2]]
            legal_moves = grandparent[4][:-1] # legal moves at t-2
            self.board.board_stat = grandparent[2]
        else:
            one_move_from_base = True # impossible to be handling base node, must be one move away from base
            self.board.board_stat = self.reconstruct_board_stat(len(self.base_play_hist)-1)
            legal_moves = self.second_all_legal_positions[:]

            
        # first block handling legality change when last move was played
        if not (self.base_board_stat == [] and one_move_from_base):
            self.board.play_hist = self.base_play_hist[:-1]
            self.board.board_stat = self.second_board_stat[:]
            if not one_move_from_base:
                x, y = self.oneto2(parent[1]) 
            else:
                prev_move = self.base_play_hist[-1]
                x, y = prev_move[0], prev_move[1]
                
            prev_to_play = 'B' if to_play == 'W' else 'B'
            self.board.force_overwrite_to_play = prev_to_play
            new_legal_verts_index, new_illegal_verts_index = self.inform_updated_legality(x, y, prev_to_play)
            for index in new_legal_verts_index:
                legal_moves[index] = 1
            for index in new_illegal_verts_index:
                legal_moves[index] = -32767
            self.board.play(x, y, prev_to_play)
            
        # else: pass / first block doesn't run if nothing was on the board at t=-1

        self.board.force_overwrite_to_play = to_play        
        x, y = self.oneto2(move_played) # second block handling legality change when the current move is played
        new_legal_verts_index, new_illegal_verts_index = self.inform_updated_legality(x, y, to_play)
        for index in new_legal_verts_index:
            legal_moves[index] = 1
        for index in new_illegal_verts_index:
            legal_moves[index] = -32767
        self.board.play(x, y, to_play)

        index = x + (y-1)*19 -1
        
        new_node = [trunk_name, move_played, self.board.board_stat[:], 0, legal_moves, 0,
                    np.array(self.empty), np.array(self.empty[:])]
        #P, V, legal positions not finished initializing
        self.node_dict[branch] = new_node # A new node is added.

        for i in range(int(depth)): # access all ancestors, yes, ancestors XD
            parent_name = trunk_name if i==0 else trunk_name[:-(2*i)]
            node = self.node_dict[parent_name]
            node[7][index] += 1
            
        if branch != '':
            self.base_stats[4] += 1

        self.batched_positions.append(branch)
        self.batch_cycle += 1
        # conditions for batching to stop:
        # 1. reached maximum batch size (8)
        # 2. the branch has really high action value
        if self.batch_cycle == 8 or parent[6][index] > 0.8: #0.8 just a placeholder for now
            st=time.time()
            self.eval_batch()
            self.total += (time.time()-st)

# node: [trunk_name, played move, board_stat, edge probability(tensor), list of every legal action, value, action vector(Q), visit vector(N)]

    def select_child(self, node):
        Cpuct = 20 #*****subject to change*****
        # Use argmax(Q + U): collect Q and U from edges and parent node respectively, operate on their tensor form.
        # U = Cpuct * sqrt(parent edge visit) * edge probability / (1 + edge visit)
        # return value is the branch leading to the next node.
        # Forces the batch to be evaluated if encounters request on accessing nodes that hasn't been
        # evaluated yet.
        legal_positions = node[4]
        if len(legal_positions) == 361: #trying to access non evaled node
            self.eval_batch()
            node = self.node_dict[node[0]+node[1]] # old data passed as parameter is obsolete, has to fetch from the updated one
            move_played, P, legal_positions, action_vector, visit_vector = node[1], node[3], node[4], node[6], node[7]
        else:
            move_played, P, action_vector, visit_vector = node[1], node[3], node[6], node[7]
            
        try:
            x, y = self.oneto2(move_played)
            index = x + (y-1)*19 -1
            parent_visit = self.node_dict[node[0]][7][index] #indexing from parent's visit vector
        except IndexError: # node is base node
            parent_visit = self.base_stats[4]
        U = Cpuct * (parent_visit)**0.5 * P * (1/(1 + visit_vector))
        return_value = node[0] + node[1] + self.num_to_pos(np.argmax(legal_positions * (action_vector + U)))
        return return_value

    #@timer.timer
    def find_best_child(self):
        # hate recursion.
        # start at the base node and search until a leaf node is reached.
        child_branch = self.select_child(self.base_node)
        if child_branch not in self.node_dict: # if leaf node is selected:
            return child_branch

        else:
            #keep traversing down the tree
            while True:
                selected_node = self.node_dict[child_branch]
                child_branch = self.select_child(selected_node)
                if child_branch not in self.node_dict:
                    return child_branch

    #@timer.timer
    def single_search(self):
        branch = self.find_best_child()
        self.create_new_node(branch)
        
    def print_best_sequence(self):
        """Returns string in normal gtp moves format, i.e. A19, B12, etc."""
        raw_seq = self.find_best_child()
        rev_alphb = 'tsrqponmlkjhgfedcba'
        output = ''
        for i in range(int(len(raw_seq)/2)):
            move = raw_seq[:2]
            move = move[0].capitalize() + str(rev_alphb.index(move[1])+1) + ' ' #converting str to gtp format
            output += move
            raw_seq = raw_seq[2:]
        print(output)

    #@timer.timer
    def search(self, playouts):
        while self.base_stats[6] < playouts:
            self.single_search()
        # 0.NNeval, 1.AvgDepth, 2.MaxDepth, 3.no.NonLeafNodes, 4.AvgChildren, 5.Visits, 6.no.Nodes, 7.Playouts
        # recalculate AvgDepth and AvgChildren every 64 playouts and at the end of the search

    def output_search_results(self): pass

    # Playouts: 11532, Win: 48.93%, PV: R4 D16 Q16 D4 P4 R17 Q17 R16 R15 S15 S14 R14 Q15 S13 S16 T14 S17 F17 C3
    # Q3 ->   30772 (V: 51.61%) (N:  4.09%) PV: Q3 D4 D16 R5 C3 D3 C4 C5 B5 B6 C6 D5 B7 B4 A6 B3 P17 P4 P3 O4 N3 Q14 M17 C17 C16 D17

