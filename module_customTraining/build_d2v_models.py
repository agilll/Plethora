from gensim.models.doc2vec import Doc2Vec
from flask import request, jsonify
from module_customTraining.utils import split_params_combinations_from_json


def build_d2v_models():
    req = request.get_json()
    hyperparams_list = split_params_combinations_from_json(req["hyperparams"])
    models_list = [Doc2Vec(**hp) for hp in hyperparams_list]
    return jsonify({"models": [model.__str__() for model in models_list]})


if __name__ == '__main__':  # Test
    name = "test_1"
    parameters_test = {
        "vector_size": [10, 20],
        "window": [2, 5]
    }
    d2v_models = build_d2v_models(name, parameters_test)
    print(d2v_models)
