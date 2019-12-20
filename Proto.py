import tensorflow as tf
from tensorflow.python import keras
from tensorflow.keras.layers import Dense, Flatten, Conv2D, Input, Reshape, MaxPool2D
from tensorflow.keras.layers import BatchNormalization as BN
from tensorflow.keras import Model

block_num=40
filter_num=256

tf.debugging.set_log_device_placement(True)

inputs=Input(shape=(19, 19, 10,))
x=Conv2D(int(filter_num/2), (3, 3), padding='same')(inputs)
x=BN()(x)

for i in range(block_num-2):
    if i%2 == 0:
        x=Conv2D(filter_num, (3, 3), padding='same')(x)
        x=BN()(x)
        x=tf.nn.relu(x)
        y=x
    elif i%2 == 1:
        y=Conv2D(filter_num, (3, 3), padding='same')(y)
        y=BN()(y)
        x=tf.nn.relu(x+y)

p=Conv2D(2, (1, 1))(x)
p=BN()(p)
p=tf.nn.relu(p)
p=Reshape((722,))(p)
policy_output=Dense(362, activation='softmax')(p)

v=Conv2D(1, (1, 1))(x)
v=BN()(v)
v=tf.nn.relu(v)
v=Reshape((361,))(v)
v=Dense(256, activation='relu')(v)
value_output=Dense(1, activation='tanh')(v)
