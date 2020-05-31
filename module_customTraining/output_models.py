import os
from gensim.models.doc2vec import Doc2Vec

MODELS_PATH = "MODELS/"


def get_last_model_path(test_folder_name, new_model=False):
    next_output_name = 0
    while os.path.exists(MODELS_PATH + test_folder_name + "/model_%s.m" % next_output_name):
        next_output_name += 1
    return MODELS_PATH + test_folder_name + "/model_%s.m" % (next_output_name - (0 if new_model else 1))


def save_new_test(test_name, models_list):
    os.mkdir(MODELS_PATH + test_name)
    for model in models_list:
        new_model_path = get_last_model_path(test_name, new_model=True)
        model.save(new_model_path)


def save_model(test_name, model_id, model: Doc2Vec):
    model.save(MODELS_PATH + test_name + "/model_%s.m" % model_id)


def get_models(test_name):
    models_names = os.listdir(MODELS_PATH + test_name)
    return [Doc2Vec.load(MODELS_PATH + test_name + "/" + mn) for mn in models_names]


def get_model(test_name, model_id):
    return Doc2Vec.load(MODELS_PATH + test_name + "/model_%s.m" % model_id)
