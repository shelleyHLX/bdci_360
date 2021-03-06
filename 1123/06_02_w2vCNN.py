# -*- encoding: utf-8 -*-
from __future__ import print_function  
import sys
reload(sys)
sys.setdefaultencoding('utf-8')


from gensim import models
import logging


from keras.layers import Dense, Input, Flatten,Dropout
from keras.layers import Conv1D, MaxPooling1D, Embedding,Merge
from keras.models import Sequential
from keras.layers import Merge 
from keras.models import model_from_json


import numpy as np  
import pandas as pd


from sklearn.cross_validation import train_test_split

logging.basicConfig(format='%(asctime)s : %(levelname)s : %(message)s', level=logging.INFO)

def trainModel(data,modelFile,cnn_mdl):
    # 划分数据集
    X =data[:,:-1]
    y =data[:,-1]
    
    print("shape of X:",X.shape)
    print("shape of y:",y.shape)
    
    train_set,test_set,train_tag,test_tag = train_test_split(X,y,test_size = 0.3)
    
    # 把一维的标签做onehot，pd.get_dummies的结果是df,把df转为ndarray (as_matrix())
    train_label = pd.get_dummies(train_tag).as_matrix()
    test_label = pd.get_dummies(test_tag).as_matrix()
    
    print('shape of train set:',train_set.shape)
    print('shape of train label:',train_label.shape)
    print('shape of test set:',test_set.shape)
    print('shape of test label:',test_label.shape)
    
    # 读入模型   
    model = models.Word2Vec.load(modelFile)
    # 读入word2vec模型提供的嵌入层，权重需要训练
    model_embedding = model.wv.get_embedding_layer(train_embeddings=False)

    # 训练嵌入层权重
    kmodel = Sequential()
    kmodel.add(model_embedding)
    kmodel.compile('rmsprop', 'mse')
    
#     print(model_embedding.get_weights())
    
    # 定义嵌入层
    # trainable=True 通过训练来更新权重
    # trainable=Fasle 由于使用了word2vec提供的权重，这里不用再训练了
    embedding_layer = Embedding(input_dim = model_embedding.input_dim,
                                output_dim = 100,
                                input_length = 300,
                                weights = model_embedding.get_weights(),
                                trainable = False)
    
    model_left = Sequential() 
    
    # 使用word2vec训练好的嵌入层
    model_left.add(embedding_layer)
    
    model_left.add(Conv1D(64, 3, padding='same',activation='relu')) 
    model_left.add(MaxPooling1D(3))
    model_left.add(Flatten())

    model_right = Sequential() 
    
    # 使用word2vec训练好的嵌入层
    model_right.add(embedding_layer)
    
    model_right.add(Conv1D(64, 4, padding='same',activation='relu')) 
    model_right.add(MaxPooling1D(4)) 
    model_right.add(Conv1D(64, 4, padding='same',activation='relu')) 
    model_right.add(MaxPooling1D(4)) 
    model_right.add(Conv1D(64, 4, padding='same',activation='relu')) 
    model_right.add(MaxPooling1D(12))
    model_right.add(Flatten()) 
    
   
    model_cent = Sequential() 
    
    # 使用word2vec训练好的嵌入层
    model_cent.add(embedding_layer)
    
    model_cent.add(Conv1D(64, 5, padding='same',activation='relu')) 
    model_cent.add(MaxPooling1D(5)) 
    model_cent.add(Conv1D(64, 5, padding='same',activation='relu')) 
    model_cent.add(MaxPooling1D(5)) 
    model_cent.add(Conv1D(64, 5, padding='same',activation='relu')) 
    model_cent.add(MaxPooling1D(8))
    model_cent.add(Flatten()) 
    
    # merged = Merge([model_left, model_right,model_cent], mode='concat')
    
    # 最终                       
    model_merge = Sequential() 
                   
    model_merge.add(Merge([model_left, model_right,model_cent], mode='concat'))
    model_merge.add(Dense(128, activation='relu')) # 全连接层  
    model_merge.add(Dense(2, activation='softmax')) # softmax，输出文本属于20种类别中每个类别的概率  
    
   
    #
#     plot_model(model,to_file=cnn_mdl+'.png',show_shapes=True)
    # 优化器我这里用了adadelta，也可以使用其他方法  
    model_merge.compile(loss='categorical_crossentropy',  
                  optimizer='Adadelta',  
                  metrics=['accuracy'])  

    # =下面开始训练，nb_epoch是迭代次数，可以高一些，训练效果会更好，但是训练会变慢  
    model_merge.fit(train_set, train_label,epochs=5,batch_size = 100)

    score = model_merge.evaluate(test_set,test_label, verbose=0)  # 评估模型在测试集中的效果，准确率约为97%，迭代次数多了，会进一步提升
    print('Test score:', score[0])
    print('Test accuracy:', score[1])

    # 存储模型
    saveMdl(model_left,cnn_mdl+"_left")
    
    # 存储模型
    saveMdl(model_right,cnn_mdl+"_right")
    
    # 存储模型
    saveMdl(model_cent,cnn_mdl+"_cent")
    
    # 存储模型
    saveMdl(model_merge,cnn_mdl+"_merge")
    
    # score = model.evaluate(train_set, train_label, verbose=0) # 评估模型在训练集中的效果，准确率约99%
    # print('train score:', score[0])
    # print('train accuracy:', score[1])

def saveMdl(model,mdlFile):
    # serialize model to JSON
    model_json = model.to_json()
    with open(mdlFile+".json", "w") as json_file:
        json_file.write(model_json)
    # serialize weights to HDF5
    model.save_weights(mdlFile+".h5")
    print("Saved "+ mdlFile + " to disk")

def getTestSet(inFile):

    # 标签集
    docid_set = []
    # 读入训练数据
    f=open(inFile)
    lines=f.readlines()
    for line in lines:
        article = line.replace('\n','').split(' ')
        
        # 标签
        docid_set.append(article[0])

    f.close()
    return docid_set


def writeFile(outputfile,newline):
    
    fw = open(outputfile, 'ab')
    fw.write(newline.encode("utf-8"))
    fw.close()

def loadMdl(mdl):
    # load json and create model
    json_file = open(mdl+'.json', 'r')
    loaded_model_json = json_file.read()
    json_file.close()
    loaded_model = model_from_json(loaded_model_json)
    loaded_model.summary()

    # load weights into new model
    loaded_model.load_weights(mdl+".h5")
    print("Loaded " + mdl + " from disk")

    return loaded_model


def pred(model,text,npy,mdl):

    docid = getTestSet(text)  
    lable = model.predict(npy)
    output = text + "_submit.txt"
    
    for idx,lab in enumerate(lable):
        if lab[0]>lab[1]:
            tag = 'NEGATIVE'
        else:
            tag = 'POSITIVE'
        newline = docid[idx] + "," + tag + "\n"
        writeFile(output,newline)
        

def loadPred(text,npy,mdl):

    docid = getTestSet(text)
    
    model_left = loadMdl(mdl+'_left')
    model_right = loadMdl(mdl+'_right')
    model_cent = loadMdl(mdl+'_cent')
    model_merge = loadMdl(mdl+'_merge')
    
    model_merge.compile(loss='categorical_crossentropy',optimizer='Adadelta',metrics=['accuracy']) 
    
    lable = model_merge.predict(npy)
    output = text + "_submit.txt"
  
    for idx,lab in enumerate(lable):
        if lab[0]>lab[1]:
            tag = 'NEGATIVE'
        else:
            tag = 'POSITIVE'
        newline = docid + "," + tag + "\n"
        writeFile(output,newline)
    
def loadTest(npy,mdl):

    # 载入网络模型
    model_left = loadMdl(mdl + '_left')
    model_right = loadMdl(mdl + '_right')
    model_cent = loadMdl(mdl + '_cent')
    model_merge = loadMdl(mdl + '_merge')

    # 载入数据
    data = np.load(npy)

    # 划分数据集
    X = data[:, :-1]
    y = data[:, -1]

    print("shape of X:", X.shape)
    print("shape of y:", y.shape)

    # 把一维的标签做onehot，pd.get_dummies的结果是df,把df转为ndarray (as_matrix())
    train_label = pd.get_dummies(y).as_matrix()

    score = model_merge.evaluate(X,train_label, verbose=0)  # 评估模型在测试集中的效果，准确率约为97%，迭代次数多了，会进一步提升
    print('Test score:', score[0])
    print('Test accuracy:', score[1])

def main():
    
    # 定义文件路径
    dataPath = "/home/hadoop/DataSencise/bdci2017/BDCI2017-360-Semi/"
    mdlPath = "/home/hadoop/DataSencise/bdci2017/BDCI2017-360-Semi/model/"
    
    inFile = [dataPath + "train/train_p"+ str(x) + ".npy" for x in range(1,6)]
    
    testFile = [dataPath + "test/test_p"+ str(x) + ".npy" for x in range(1,6)]
    # textFile = [dataPath + "test/test_p"+ str(x) + ".txt" for x in range(1,6)]
    textFile_all = dataPath + "test/test_all.txt"
    modelFile = mdlPath + "w2v_v1.mdl"
    
    cnn_mdl = [mdlPath + "cnn_m"+ str(x) for x in range(1,6)]
    
#     for (tf,mfncf) in zip(inFile,modelFile,cnn_mdl):
#         data = np.load(tf)
#         # 训练模 
#         trainModel(data,mf,cf)  
    
    # data = np.load(inFile[0])
    # trainModel(data,modelFile,cnn_mdl[0])
    
    # 测试模型
    loadTest(inFile[0],cnn_mdl[0])

if __name__ == '__main__':
    main()
