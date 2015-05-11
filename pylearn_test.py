__author__ = 'Michael May'


import theano
from pylearn2.models import mlp
from pylearn2.training_algorithms import sgd
from pylearn2.termination_criteria import EpochCounter
from pylearn2.datasets.dense_design_matrix import DenseDesignMatrix

from sklearn import cross_validation
import pandas as pd
from sklearn import preprocessing
from ml_metrics import *
# try scaling http://sebastianraschka.com/Articles/2014_about_feature_scaling.html


class Dataset(DenseDesignMatrix):
    def __init__(self, features, classes):
        self.class_names = set(classes)

        actual = np.zeros([features.shape[0], len(set(classes))])
        rows = actual.shape[0]
        actual[np.arange(rows), classes.astype(int)] = 1

        print actual.shape
        super(Dataset, self).__init__(X=features, y=actual)


def load_test_data(std_scale):
    raw_testing_data = pd.read_csv('test.csv')
    raw_testing_data = raw_testing_data.astype('float32')  # convert types to float32

    # Get the features and the classes
    test_features = raw_testing_data.iloc[:, 1:94].values  # get the feature vectors

    test_features = std_scale.transform(test_features)  # scale the features
    return test_features


def save_results(file, test_features, results):
    # create colums and headers
    index = range(1, len(test_features) + 1)
    columns = ['Class_1', 'Class_2', 'Class_3', 'Class_4', 'Class_5', 'Class_6', 'Class_7', 'Class_8', 'Class_9']

    # create data frame
    res = pd.DataFrame.from_records(results, index=index, columns=columns)
    res.index.name = 'id'

    #save results
    res.to_csv(file)


def class_to_int(class_string):
    return int(class_string[6]) - 1


def load_training_data():
    raw_training_data = pd.read_csv('train.csv')

    # convert types to ints
    raw_training_data['target'] = raw_training_data['target'].apply(class_to_int)
    raw_training_data = raw_training_data.astype('float32')
    raw_training_data['target'] = raw_training_data['target'].astype('int32')

    # Get the features and the classes
    features = raw_training_data.iloc[:, 1:94].values
    classes = raw_training_data['target'].values

    print np.unique(classes)

    #split train/validate
    feat_train, feat_test, class_train, class_test = cross_validation.train_test_split(features, classes, test_size=0.3,
                                                                                       random_state=0)

    #scale the features
    std_scale = preprocessing.StandardScaler().fit(feat_train)
    feat_train = std_scale.transform(feat_train)
    feat_test = std_scale.transform(feat_test)

    training_data = Dataset(feat_train, class_train)
    test_data = [feat_test, class_test]

    return training_data, test_data, std_scale


def main():
    training_data, test_data, std_scale = load_training_data()
    kaggle_test_features = load_test_data(std_scale)


    #pylearn2 ML
    hidden_layer = mlp.Sigmoid(layer_name='hidden', dim=93, irange=.1, init_bias=1.)
    # create Softmax output layer
    output_layer = mlp.Softmax(9, 'output', irange=.1)
    # create Stochastic Gradient Descent trainer that runs for 400 epochs
    trainer = sgd.SGD(learning_rate=.05, batch_size=10, termination_criterion=EpochCounter(400))
    layers = [hidden_layer, output_layer]
    # create neural net that takes two inputs
    ann = mlp.MLP(layers, nvis=93)
    trainer.setup(ann, training_data)
    # train neural net until the termination criterion is true
    count = 0
    while True:
        trainer.train(dataset=training_data)
        ann.monitor.report_epoch()
        ann.monitor()
        count += 1
        if not trainer.continue_learning(ann):
            break

    #get an prediction of the accuracy from the test_data
    test_results = ann.fprop(theano.shared(test_data[0], name='test_data')).eval()

    print test_results.shape
    loss = multiclass_log_loss(test_data[1], test_results)

    print 'Test multiclass log loss:', loss

    out_file = 'pylearn2_results/' + str(loss) + 'ann'
    #exp.save(out_file + '.pkl')


    #save the kaggle results

    results = ann.fprop(theano.shared(kaggle_test_features, name='kaggle_test_data')).eval()
    save_results(out_file + '.csv', kaggle_test_features, results)


if __name__ == "__main__":
    main()