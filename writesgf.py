"""
writes sgf files or absolute simplistic training data (ASTD).
.astd encoding in utf-8.
"""
import random
import board

def twoto1(x, y):
    alphb='abcdefghijklmnopqrs'
    return alphb[x-1] + alphb[y-1]

def write_file(play_hist, result, komi, directory, format_='astd'):
    hash_=''
    for i in range(32):
        hash_+=format(random.choice([j for j in range(16)]), 'x')# hash is a 128bit name
        
    return_str = ''
    if format_ != 'sgf':
        if format_ != 'astd': raise UserWarning('you are writing to an unknown format.')
        for move in play_hist[1:]:
            if move != 'PASS':
                return_str += ' ' + twoto1(move[0], move[1])
            else: return_str += ' PASS'

        with open(directory + '\\%s' % hash_ + '.astd' , 'w') as file:
            file.write(result + komi + return_str)

    else:
        for move in play_hist[1:]:
            return_str += ';' + move[2] + '[' + twoto1(move[0], move[1]) + ']' #;B[dd]

        with open(directory + '\\%s' % hash_ + '.sgf' , 'w') as file:
            file.write(
            '(' + ';' + 'RE' + '[' + result + ']' + 'KM' + '[' + str(komi) + ']' + ';' +
            return_str + ')'
                        )
