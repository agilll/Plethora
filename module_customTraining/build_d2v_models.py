from gensim.models.doc2vec import Doc2Vec
from flask import request, jsonify


def build_d2v_models():
    req = request.get_json()
    model = Doc2Vec(**req["hyperparams"])
    return jsonify({"models": model.__str__()})


if __name__ == '__main__':  # Test
    name = "test_1"
    parameters_test = {
        "vector_size": [10, 20],
        "window": [2, 5]
    }
    d2v_models = build_d2v_models(name, parameters_test)
    print(d2v_models)
