from __future__ import print_function
import sklearn as sk
from sklearn.metrics import confusion_matrix
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import tensorflow as tf
import numpy as np
import sys
from tensorflow.contrib import rnn
from sklearn.model_selection import KFold, cross_val_score
import csv
from sklearn.utils import shuffle
import os

# Import WiFi Activity data
# csv_convert(window_size,threshold)
from cross_vali_input_data import csv_import, DataSet

window_size = 500
threshold = 60

# Parameters
learning_rate = 0.0001  #학습의 속도에 영향. 너무 크면 학습이 overshooting해서 학습에 실패하고, 너무 작으면 더디게 진행하다가 학습이 끝나 버린다.
training_iters = 2000 #학습반복횟수
batch_size = 200 #한번에 사용할 데이터의 양. (200개의 데이터가 하나의 batch로 취급된다)
display_step = 100

# Network Parameters
n_input = 90 # WiFi activity data input (img shape: 90*window_size) , RNN의 데이터 가로줄 사이즈
n_steps = window_size # RNN의 데이터 세로줄 사이즈
n_hidden = 200 # hidden layer num of features original 200 , 히든레이어 갯수
n_classes = 7 # WiFi activity total classes , One-hot encoding 방식의 7개의 클래스

# Output folder
OUTPUT_FOLDER_PATTERN = "LR{0}_BATCHSIZE{1}_NHIDDEN{2}/"
output_folder = OUTPUT_FOLDER_PATTERN.format(learning_rate, batch_size, n_hidden)
if not os.path.exists(output_folder):
    os.makedirs(output_folder)

# tf Graph input // 텐서플로우 그래프에 넣어질 입력값 x, y
x = tf.placeholder("float", [None, n_steps, n_input]) #500행(윈도우사이즈) 90열 정해지지 않은 층의 3차원 입력값
y = tf.placeholder("float", [None, n_classes]) #7열 정해지지 않은 행의 2차원 입력값

# Define weights
weights = {
    'out': tf.Variable(tf.random_normal([n_hidden, n_classes]))
}
biases = {
    'out': tf.Variable(tf.random_normal([n_classes]))
}

def RNN(x, weights, biases):

    # Prepare data shape to match `rnn` function requirements
    # Current data input shape: (batch_size, n_steps, n_input)
    # Required shape: 'n_steps' tensors list of shape (batch_size, n_input)

    # Permuting batch_size and n_steps
    x = tf.transpose(x, [1, 0, 2])
    # Reshaping to (n_steps*batch_size, n_input)
    x = tf.reshape(x, [-1, n_input])
    # Split to get a list of 'n_steps' tensors of shape (batch_size, n_input)
    x = tf.split(x, n_steps, 0)

    # Define a lstm cell with tensorflow
    lstm_cell = rnn.BasicLSTMCell(n_hidden, forget_bias=1.0) #RNN을 위한 셀을 만드는 텐서플로 메소드

    # Get lstm cell output
    outputs, states = rnn.static_rnn(lstm_cell, x, dtype=tf.float32) #셀을 이용해 RNN을 돌려 OUTPUT을 만드는 메소드.

    # Linear activation, using rnn inner loop last output
    return tf.matmul(outputs[-1], weights['out']) + biases['out']    # y = x * W + b

##### main #####
pred = RNN(x, weights, biases)

# Define loss and optimizer
cost = tf.reduce_mean(tf.nn.softmax_cross_entropy_with_logits(logits = pred, labels = y)) #cost는 학습의 오차율을 나타내는 것으로 보이며, 오차율을 감소시키기 위해 optimizer의 tf.train,AdamOptimizer을 사용하는것으로 보임
optimizer = tf.train.AdamOptimizer(learning_rate=learning_rate).minimize(cost) #레이블 역할을 하는 Y와 예측값을 비교해서 , 오차를 측정하고 오차율을 감소시킨다.
#tf,train.AdamOptimizer(Learning late = 학습속도).minimize(cost = 로스율)    minimize의 첫 번째 인자는 loss이며 cost가 들어간다.
#https://www.tensorflow.org/api_docs/python/tf/train/AdamOptimizer
#AdamOptimizer는 오차를 감소시키기 위한 텐서플로 함수의 일종
# Evaluate model
correct_pred = tf.equal(tf.argmax(pred,1), tf.argmax(y,1))
accuracy = tf.reduce_mean(tf.cast(correct_pred, tf.float32))

# Initializing the variables
init = tf.global_variables_initializer()
cvscores = []
confusion_sum = [[0 for i in range(7)] for j in range(7)]

#data import
x_bed, x_fall, x_pickup, x_run, x_sitdown, x_standup, x_walk, \
y_bed, y_fall, y_pickup, y_run, y_sitdown, y_standup, y_walk = csv_import()

print(" bed =",len(x_bed), " fall=", len(x_fall), " pickup =", len(x_pickup), " run=", len(x_run), " sitdown=", len(x_sitdown), " standup=", len(x_standup), " walk=", len(x_walk))

#data shuffle
x_bed, y_bed = shuffle(x_bed, y_bed, random_state=0)
x_fall, y_fall = shuffle(x_fall, y_fall, random_state=0)
x_pickup, y_pickup = shuffle(x_pickup, y_pickup, random_state=0)
x_run, y_run = shuffle(x_run, y_run, random_state=0)
x_sitdown, y_sitdown = shuffle(x_sitdown, y_sitdown, random_state=0)
x_standup, y_standup = shuffle(x_standup, y_standup, random_state=0)
x_walk, y_walk = shuffle(x_walk, y_walk, random_state=0)


#k_fold
kk = 10

# Launch the graph
with tf.Session() as sess:
    for i in range(kk):

        #Initialization
        train_loss = []
        train_acc = []
        validation_loss = []
        validation_acc = []

        #Roll the data
        x_bed = np.roll(x_bed, int(len(x_bed) / kk), axis=0)
        y_bed = np.roll(y_bed, int(len(y_bed) / kk), axis=0)
        x_fall = np.roll(x_fall, int(len(x_fall) / kk), axis=0)
        y_fall = np.roll(y_fall, int(len(y_fall) / kk), axis=0)
        x_pickup = np.roll(x_pickup, int(len(x_pickup) / kk), axis=0)
        y_pickup = np.roll(y_pickup, int(len(y_pickup) / kk), axis=0)
        x_run = np.roll(x_run, int(len(x_run) / kk), axis=0)
        y_run = np.roll(y_run, int(len(y_run) / kk), axis=0)
        x_sitdown = np.roll(x_sitdown, int(len(x_sitdown) / kk), axis=0)
        y_sitdown = np.roll(y_sitdown, int(len(y_sitdown) / kk), axis=0)
        x_standup = np.roll(x_standup, int(len(x_standup) / kk), axis=0)
        y_standup = np.roll(y_standup, int(len(y_standup) / kk), axis=0)
        x_walk = np.roll(x_walk, int(len(x_walk) / kk), axis=0)
        y_walk = np.roll(y_walk, int(len(y_walk) / kk), axis=0)

        #data separation // np.r_은 concatenate와 동일하다고 생각됨.
        wifi_x_train = np.r_[x_bed[int(len(x_bed) / kk):], x_fall[int(len(x_fall) / kk):], x_pickup[int(len(x_pickup) / kk):], \
                        x_run[int(len(x_run) / kk):], x_sitdown[int(len(x_sitdown) / kk):], x_standup[int(len(x_standup) / kk):], x_walk[int(len(x_walk) / kk):]]

        wifi_y_train = np.r_[y_bed[int(len(y_bed) / kk):], y_fall[int(len(y_fall) / kk):], y_pickup[int(len(y_pickup) / kk):], \
                        y_run[int(len(y_run) / kk):], y_sitdown[int(len(y_sitdown) / kk):], y_standup[int(len(y_standup) / kk):], y_walk[int(len(y_walk) / kk):]]

        wifi_y_train = wifi_y_train[:,1:]

        wifi_x_validation = np.r_[x_bed[:int(len(x_bed) / kk)], x_fall[:int(len(x_fall) / kk)], x_pickup[:int(len(x_pickup) / kk)], \
                        x_run[:int(len(x_run) / kk)], x_sitdown[:int(len(x_sitdown) / kk)], x_standup[:int(len(x_standup) / kk)], x_walk[:int(len(x_walk) / kk)]]

        wifi_y_validation = np.r_[y_bed[:int(len(y_bed) / kk)], y_fall[:int(len(y_fall) / kk)], y_pickup[:int(len(y_pickup) / kk)], \
                        y_run[:int(len(y_run) / kk)], y_sitdown[:int(len(y_sitdown) / kk)], y_standup[:int(len(y_standup) / kk)], y_walk[:int(len(y_walk) / kk)]]

        wifi_y_validation = wifi_y_validation[:,1:]

        #data set
        wifi_train = DataSet(wifi_x_train, wifi_y_train)
        wifi_validation = DataSet(wifi_x_validation, wifi_y_validation)
        print(wifi_x_train.shape, wifi_y_train.shape, wifi_x_validation.shape, wifi_y_validation.shape)
        saver = tf.train.Saver()
        sess.run(init)
        step = 1

        # Keep training until reach max iterations
        while step < training_iters:
            batch_x, batch_y = wifi_train.next_batch(batch_size) #wifi_train에 저장된 x와 y를 배치 사이즈만큼 가져옴.
            x_vali = wifi_validation.images[:]
            y_vali = wifi_validation.labels[:]
            # Reshape data to get 28 seq of 28 elements
            batch_x = batch_x.reshape((batch_size, n_steps, n_input)) #batch_x를 500행 90열 batch_size층의 3차원으로 reshape
            x_vali = x_vali.reshape((-1, n_steps, n_input)) #x_vail은 500행, 90열로 만들고 남은걸 배열 층으로 쌓음
            # Run optimization op (backprop)
            sess.run(optimizer, feed_dict={x: batch_x, y: batch_y})

            # Calculate batch accuracy
            acc = sess.run(accuracy, feed_dict={x: batch_x, y: batch_y})
            #x에 batch_x, y에 batch_y를 입력하여 accuracy 실행하여 결과값을 acc에 저장
            acc_vali = sess.run(accuracy, feed_dict={x: x_vali, y: y_vali})
            # Calculate batch loss
            loss = sess.run(cost, feed_dict={x: batch_x, y: batch_y})
            loss_vali = sess.run(cost, feed_dict={x: x_vali, y: y_vali})

            # Store the accuracy and loss
            train_acc.append(acc)
            train_loss.append(loss)
            validation_acc.append(acc_vali)
            validation_loss.append(loss_vali)

            if step % display_step == 0:
                print("Iter " + str(step) + ", Minibatch Training  Loss= " + \
                    "{:.6f}".format(loss) + ", Training Accuracy= " + \
                    "{:.5f}".format(acc) + ", Minibatch Validation  Loss= " + \
                    "{:.6f}".format(loss_vali) + ", Validation Accuracy= " + \
                    "{:.5f}".format(acc_vali) )
            step += 1

        #Calculate the confusion_matrix
        cvscores.append(acc_vali * 100)
        y_p = tf.argmax(pred, 1)
        val_accuracy, y_pred = sess.run([accuracy, y_p], feed_dict={x: x_vali, y: y_vali})
        #y_pred: 예측값 y_true: 실제값으로 추정. 1행 wifi_xvalidation의 z축만큼의 열을 가진 배열
        y_true = np.argmax(y_vali,1)
        print(sk.metrics.confusion_matrix(y_true, y_pred))
        #텐서플로우를 이용한 prediction 결과를 평가하기 위해 confusion matrix 사용, 결과값은 7*7의 배열
        #열들은 예측해야하는 라벨를 나타내고, 행들은 예측한 결과의 갯수를 나타낸다.
        #batch_size가 너무 작을 시 에러 발생.
        confusion = sk.metrics.confusion_matrix(y_true, y_pred)
        confusion_sum = confusion_sum + confusion

        #Save the Accuracy curve
        fig = plt.figure(2 * i - 1)
        plt.plot(train_acc)
        plt.plot(validation_acc)
        plt.xlabel("n_epoch")
        plt.ylabel("Accuracy")
        plt.legend(["train_acc","validation_acc"],loc=4)
        plt.ylim([0,1])
        plt.savefig((output_folder + "Accuracy_" + str(i) + ".png"), dpi=150)

        #Save the Loss curve
        fig = plt.figure(2 * i)
        plt.plot(train_loss)
        plt.plot(validation_loss)
        plt.xlabel("n_epoch")
        plt.ylabel("Loss")
        plt.legend(["train_loss","validation_loss"],loc=1)
        plt.ylim([0,2])
        plt.savefig((output_folder + "Loss_" + str(i) + ".png"), dpi=150)

    print("Optimization Finished!")
    print("%.1f%% (+/- %.1f%%)" % (np.mean(cvscores), np.std(cvscores)))
    saver.save(sess, output_folder + "model.ckpt")

    #Save the confusion_matrix
    np.savetxt(output_folder + "confusion_matrix.txt", confusion_sum, delimiter=",", fmt='%d')
    np.savetxt(output_folder + "accuracy.txt", (np.mean(cvscores), np.std(cvscores)), delimiter=".", fmt='%.1f')
