import glob
import pickle

from gensim.models.doc2vec import Doc2Vec, TaggedDocument
from gensim.utils import simple_preprocess
from flask import request, jsonify
from nltk import word_tokenize

from module_customTraining.utils import split_params_combinations_from_json
from module_customTraining import output_models as outm


def build_d2v_models(test_data=None):
    """
    Build and save models in MODELS folder, classified in test folders by each call.
    'test_data' will pick up from POST request by default, unless it will be received in the function param.

    :param test_data: json with hyperparams lists and test name for the folder. Models will be built with all combinations of the hyperparams lists. Format:
        {
            hyperparams:{
                window: [w1, w2, ...],
                alpha: [a1, a2, a3, ...],
                ...
            },
            test_name:"example_test"
        }

    :return: list of built models (info about them)
    """
    test_data = request.get_json() if test_data is None else test_data
    print(test_data)
    hyperparams_list = split_params_combinations_from_json(test_data["hyperparams"])
    models_list = [Doc2Vec(**hp) for hp in hyperparams_list]
    outm.save_new_test(test_data["test_name"], models_list)
    return jsonify({"models": [model.__str__() for model in models_list]})


def train_test_models(training_lists, test_name):

    tagged_training_lists = [TaggedDocument(words=_text, tags=[str(i)]) for i, _text in enumerate(training_lists)]
    models_to_train: list[Doc2Vec] = outm.get_models(test_name)
    for i, mtt in enumerate(models_to_train):
        mtt.build_vocab(tagged_training_lists, update=True)
        print(mtt.corpus_total_words)
        mtt.train(
            documents=tagged_training_lists,
            total_examples=mtt.corpus_count,
            epochs=mtt.epochs
        )
        outm.save_model(test_name, i, mtt)


if __name__ == '__main__':  # Test
    # name = "test_1"
    # parameters_test = {
    #     "hyperparameters": {
    #         "vector_size": [10, 20],
    #         "window": [2, 5]
    #     },
    #     "test_name": name
    # }
    # d2v_models = build_d2v_models(parameters_test)
    # for n in range(4):
    #     model = Doc2Vec.load("MODELS/test_1/model_%s.m" % n)
    #     print(model)
    training_files = glob.glob("./CORPUS/files_t/" + "*.t")
    training_lists = []
    for training_file in training_files:
        list_list_words = pickle.load(open(training_file, "rb"))
        list_words = [item for sublist in list_list_words for item in sublist]
        training_lists.append(list_words)

    train_test_models(training_lists, "test_1")
