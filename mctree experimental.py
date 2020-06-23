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
    def __init__(self, network, komi=7.5, board_size=19, base_play_hist=['filler'], base_board_stat=[], use_num_thread=1, use_num_gpus=0):
        #tf.compat.v1.ConfigProto(inter_op_parallelism_threads = use_num_threads)
        self.use_num_gpus=use_num_gpus
        self.board=_board.board(board_size, komi)

        self.network=network
        self.base_play_hist, self.base_board_stat = base_play_hist, base_board_stat
        self.base_to_play = 'W' if len(self.base_play_hist) % 2 == 0 else 'B' # Base to play means which player to play at the base position
        self.batched_positions = []
        self.batch_cycle = 0
        self.dumbpass_enabled = False
        # About that pass policy...

        # """
        # // Always try passes if we're not trying to be clever.
        # auto allow_pass = cfg_dumbpass;

        # // Less than 20 available intersections in a 19x19 game.
        # if (nodelist.size() <= std::max(5, BOARD_SIZE)) {
        #     allow_pass = true;
        # }

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
        # From Leela Zero UCTNode.cpp
        # Basically, when allow_pass = True, passes are always attempted.
        # If cfg_dumbpass enabled / less than 20 intersections on board / winning in relative score and nn eval above some margin:
        # Pass enabled as an option
        # Meaning? 1 extra edge created at each node where pass is enabled with the name of the move played being 'PASS'. 
        # Identifier of 'PASS' in the trunk name is 'xp'.

        # initializing base node
        self.node_dict={'':[0, 0, self.base_board_stat]}
        # Put in a dummy just to enable current board stat to be accessed,
        # which is to be replaced later by a fully developed node.
        array = self.gen_input_matrix('')
        with tf.device('/CPU:0'):
            P, V = self.network.predict(nhwc_to_nchw(tf.reshape(array, [1, 9, 19, 19])))
        P, V = P[0], V[0][0]

        self.base_all_legal_positions_b, self.base_all_legal_positions_w = [], []
        if self.base_board_stat == []: # Empty board
            self.base_all_legal_positions_b = [1 for i in range(361)]
            
            if self.pass_enabled(V, 0, 361):
                self.base_all_legal_positions_b.append(1)
            else:
                self.base_all_legal_positions_b.append(-32767)
            self.base_all_legal_positions_w = self.base_all_legal_positions_b

        else:
            # generate base legality positions for both b and w, 1 for legal and 0 for illegal
            self.board.board_stat = self.base_board_stat
            for i in range(19):
                for j in range(19):

                    if self.board.is_legal(j+1, i+1, 'B'):
                        self.base_all_legal_positions_b.append(1)
                    else:
                        self.base_all_legal_positions_b.append(-32767)

                    if self.board.is_legal(j+1, i+1, 'W'): 
                        self.base_all_legal_positions_w.append(1)
                    else:
                        self.base_all_legal_positions_b.append(-32767)

            b_no_legal_verts = 361-self.base_all_legal_positions_b.count(-32767)
            w_no_legal_verts = 361-self.base_all_legal_positions_w.count(-32767) #counting the more common element is faster
            if self.pass_enabled(V, 'B', b_no_legal_verts):
                self.base_all_legal_positions_b.append(1)
            else:
                self.base_all_legal_positions_b.append(-32767)
            if self.pass_enabled(V, 'W', w_no_legal_verts):
                self.base_all_legal_positions_w.append(1)
            else:
                self.base_all_legal_positions_w.append(-32767)

        empty = tf.constant([0. for i in range(362)])
        # Definitions:
        # Base node is the node located exactly on the position of the inputted untouched board
        # '' as trunk name indicates no move was played
        if self.base_to_play == 'B':
            self.base_node=['', '', self.base_board_stat, P, self.base_all_legal_positions_b, V, empty, empty]
        else: 
            self.base_node=['', '', self.base_board_stat, P, self.base_all_legal_positions_w, V, empty, empty]

        self.base_stat=[V, 0, 0, 0, 0, 1, 0, 0] # 0.NNeval, 1.AvgDepth, 2.MaxDepth, 3.no.NonLeafNodes, 4.AvgChildren, 5.Visits, 6.no.Nodes, 7.Playouts
        
        self.node_dict[''] = self.base_node

        self.initialize_children(self.base_node)

# Total action value is not used.
# trunk name: a string enlisting the complete play history from base position following parent -> children from left to right without spacing, not including the move played itself.
# node: [trunk_name, played move, board_stat, edge probability(tensor), all legal moves, V, action vector(Q), visit vector(N)]
# node dict:{'branch': node...}
# branch = trunk_name + move_played
# Figuratively, a small tree sort of look like this:
   #      ''  (base)
   #      /\
   # 'aa'/  \'ab'

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
        """ expecting num from 0 to 360. """
        size=self.board.board_size
        try:
            return self.twoto1(num%size+1, int(num/size)+1)
        except IndexError:
            return 'xp'

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
        for elm in play_hist:
            branch += self.twoto1(elm[0], elm[1])
        return branch

    def det_to_play_from_trunk(self, trunk_name):
        no_of_moves_played_from_base = len(trunk_name)/2

        if self.base_to_play == 'B':
            return 'B' if no_of_moves_played_from_base % 2 == 0 else 'W'
        else:
            return 'B' if no_of_moves_played_from_base % 2 == 1 else 'W'
            
    def assign_value_to_tensor(self, tensor, value, index): # tensor has to be 1 dimensional
        # method @ https://github.com/tensorflow/tensorflow/issues/14132#issuecomment-483002522
        mask = []
        tensor = tf.cast(tensor, 'float32')
        r = range(len(tensor))
        for i in r:
            if i == index: mask.append(0)
            else: mask.append(1)
        mask = tf.constant(mask, dtype='float32')

        other = []
        for i in r:
            if i == index: other.append(value)
            else: other.append(0)
        other = tf.constant(other, dtype='float32')
            
        return tensor * mask + other * (1 - mask)

    def reconstruct_board_stat(self, t):
        #reconstruct the board from EMPTY board, t indicating the time step which the move is played, t=0 is when the board is empty
        self.board.board_stat, self.board.play_hist = [], ['filler']
        for move in self.base_play_hist[1:t+1]:
            self.board.play(move[0], move[1], move[2])

        return self.board.board_stat

    def pass_enabled(self, nneval, scoring_for, legal_verts_count):
        # depends on the board stat at the time
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

    def initialize_children(self, node):
        # initialized all legal children nodes from their parent as their respective placeholders. 
        # (I've realized how stupid I am for trying to generate a new legal action list for each board position =.=)
        # This function only creates from a fully developed node.

        # If cfg_dumbpass enabled / less than 20 intersections on board / winning in relative score and nn eval above some margin:
        # Pass enabled as an option
        trunk_name, legal_moves = node[0] + node[1], node[4]
        for index, value in enumerate(legal_moves):
            if value == 1:
                connects_to = self.num_to_pos(index)
                branch = trunk_name + connects_to
                self.node_dict[branch] = [trunk_name, connects_to]


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
            parent = self.node_dict[branch[:-2]]
            P, V = Parray[i], Varray[i][0]
            self.board.board_stat, legal_moves = parent[2], parent[4]

            to_play = self.det_to_play_from_trunk(branch[:-2])
            if self.pass_enabled(V, to_play, 361-legal_moves.count(0)):
                legal_moves[361] = 1
            else:
                legal_moves[361] = -32767

            x, y = self.oneto2(branch[-2:])
            index = x + (y-1)*19 -1
            for j in range(int(len(branch)/2)):
                trunk_name = branch[:-2]
                parent_name = trunk_name if i==0 else trunk_name[:-(2*i)]
                node = self.node_dict[parent_name]
                action_vector = node[6]
                Q, N = float(action_vector[index]), float(node[7][index]) # N already updated
                Q = (Q*(N-1)+V) / N
                node[6] = self.assign_value_to_tensor(action_vector, Q, index)
                
            self.initialize_children(node)
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
    def create_new_node(self, trunk_name, move_played):
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

        parent = self.node_dict[trunk_name]
        branch = trunk_name + move_played

        to_play = self.det_to_play_from_trunk(trunk_name)
        one_move_from_base = False
        if len(branch) >= 4:
            grandparent = self.node_dict[trunk_name[:-2]]
            legal_moves = [pos for pos in grandparent[4]] # legal moves at t-2
            self.board.board_stat = [pos for pos in grandparent[2]]
        else:
            one_move_from_base = True # impossible to be handling base node, must be one move away from base
            self.board.board_stat = self.reconstruct_board_stat(len(self.base_play_hist)-1)
            legal_moves = []
            for i in range(19):
                for j in range(19):
                    if self.board.is_legal(j+1, i+1): legal_moves.append(1)
                    else: legal_moves.append(0)

        if not (self.base_board_stat == [] and len(branch) == 2):
            if not one_move_from_base:
                x, y = self.oneto2(parent[1]) # first block handling legality change when last move was played
            else:
                prev_move = self.base_play_hist[-2:]
                x, y = self.oneto2(prev_move)
                
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

        self.node_dict[branch] = [0, 0, [move for move in self.board.board_stat]]# Put in a dummy just to enable current board stat to be accessed, which is to be replaced later by a fully developed node.
                
        index = x + (y-1)*19 -1
        #pass enablement/updating parent Q/children initializing moved to batching section
        empty = tf.constant([0. for i in range(362)])
        new_node = [trunk_name, move_played, self.board.board_stat, 0, legal_moves, 0, empty, empty] 
        #P, V, legal positions not finished initializing
        self.node_dict[branch] = new_node # A new node is added.

        for i in range(int(len(branch)/2)): # access all ancestors, yes, ancestors XD
            parent_name = trunk_name if i==0 else trunk_name[:-(2*i)]
            
            node = self.node_dict[parent_name]
            N = float(node[7][index])
            node[7] = self.assign_value_to_tensor(node[7], N+1, index)
        if branch != '':
            self.base_stat[5] += 1

        self.batched_positions.append(branch)
        self.batch_cycle += 1
        # conditions for batching to stop:
        # 1. reached maximum batch size (8)
        # 2. the branch has really high action value
        if self.batch_cycle == 8 or parent[6][index] > 0.8: #0.8 just a placeholder for now
            self.eval_batch()

# node: [trunk_name, played move, board_stat, edge probability(tensor), list of every legal action, value, action vector(Q), visit vector(N)]

    def select_child(self, node):
        Cpuct = 1.4142 #*****
        # Use argmax(Q + U): collect Q and U from edges and parent node respectively, operate on their tensor form.
        # U = Cpuct * sqrt(parent edge visit) * edge probability / (1 + edge visit)
        # return value is the branch leading to the next node.
        move_played, P, legal_positions, action_vector, visit_vector = node[1], node[3], node[4], node[6], node[7]
        try:
            x, y = self.oneto2(move_played)
            index = x + (y-1)*19 -1
            parent_visit = self.node_dict[node[0]][7][index] #indexing from parent's visit vector
        except IndexError: # node is base node
            parent_visit = self.base_stat[5]
        U = Cpuct * (parent_visit)**0.5 * P * (1/(1 + visit_vector))
        action_vector, U = tf.cast(action_vector, 'float32'), tf.cast(U, 'float32')
        return_value = node[0] + node[1] + self.num_to_pos(np.argmax(legal_positions * (action_vector + U)))
        return return_value

    #@timer.timer
    def find_best_child(self, selected_node = None):
        # hate recursion.
        # start at the base node and search until a leaf node is reached.
        child_branch = self.select_child(self.base_node)
        selected_node = self.node_dict[child_branch]
        if len(selected_node) == 2: # if leaf node is selected:
            return child_branch

        else:
            #keep traversing down the tree
            while True:
                next_child_branch = self.select_child(selected_node)
                selected_node = self.node_dict[next_child_branch]
                if len(selected_node) == 2:
                    return next_child_branch

    #@timer.timer
    def single_search(self):
        branch = self.find_best_child()
        self.create_new_node(branch[:-2], branch[-2:])

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

    def search(self, playouts):
        for i in range(playouts):
            self.single_search()
        if self.batch_cycle != 1: self.eval_batch()

    def output_search_results(self): pass


