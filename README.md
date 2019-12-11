# Constantinople
A (currently) solo project by Magister. Also my(his?) first ever project.
The end goal is to use Tensorflow as main API to achieve a high level go artifical intelligence through adding non-traditional training methods.

# What
Previous pioneering Go AI projects uses deep reinforcement learning to train their models. By directly training the model with human pro games or self-play games, these AIs were able to reach superhuman level of play. However, there are flaws in direct training with the data, such as human professional data being incompetent(relatively) and the self-play method is rather slow in terms of improving. To deal with both problems at once, a method was devised such that the model can improved more stably and quickly while learning from self-play.

1. learn from a position generated randomly

by assessing a move randomly added on a position and comparing it to the previous position, the model can learn which moves are bad at certain positions while having noise to reduce overfitting.

2. learn from a MCTS that was done by the model

the model always selects the moves it think is best in a MCTS, which can be reviewed again by the same model. Then by adding noise to the model's evaluation, the model will sometimes trust and sometimes distrust it's evaluation and change it's play, with bad plays being ruled out in the long run, leading to the improvement of it's current best play.

3. learn from 2 similar positions' difference

Sometimes in Go, an exchange of moves(a player plays a move that his opponent must respond to) can change the game significantly. By training on 2 positions with and without the exchange, the model will learn if a position is favourable to itself and play exchanges when necessary.
(edit: 3 can be omitted as 2 should include exchanges of moves.)

# Progress
2019/10/12 GitHub repository created, with a board file that can allow players to play go through python shell(without counting).

2019/10/16 Project halted due to academic issues.

2019/10/31 Previously halted project restarted. First part of readsgf.py done.

2019/11/13 Finished version of board.py pushed, many errors fixed and robustness improved.
