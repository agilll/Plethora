from itertools import zip_longest as zipl, product as prod
from gensim.models.doc2vec import TaggedDocument, Doc2Vec
from model_groups import D2VModelGroup, get_all_d2v_groups
from flask import request, jsonify
from pickle import load
import os

LOG = []
korpus_dir = "../CORPUS/"


def getAllSavedD2VGroups():
    global LOG
    models_folder = request.args.get("models_folder")
    abs_models_folder = models_folder if models_folder.startswith("/") else korpus_dir + models_folder
    LOG.append("Get all saved D2V groups in DB")
    groups = get_all_d2v_groups(abs_models_folder)
    return jsonify([{
        'group': group.name,
        'models': os.listdir(group.group_folder)
    } for group in groups]), 200


def buildAndTrainNewModelGroup():
    global LOG
    group_name = request.get_json().get('group_name').replace('_', '')
    models_type = request.get_json().get('models_type')  # TODO use
    training_docs_file = request.get_json().get('training_docs_file')
    models_folder = request.get_json().get('models_folder')
    params = request.get_json().get('params')

    abs_models_folder = models_folder if models_folder.startswith("/") else korpus_dir + models_folder
    abs_training_docs_file = training_docs_file if training_docs_file.startswith("/") else korpus_dir + training_docs_file
    with open(abs_training_docs_file) as df:
        abs_training_files = [file.strip() if file.startswith("/") else korpus_dir + file.strip() for file in df]

    LOG.append("Build the new '%s' models group '%s' with files in '%s' in the folder '%s'" % (models_type, group_name, abs_training_docs_file, abs_models_folder))
    parameters_list = []
    nlist = [name for name in params.keys() if len(params[name]) > 0]
    vlist = [params[name] for name in nlist]
    values_prod = prod(*vlist)
    for values in values_prod:
        new_json = dict()
        for name, value in zipl(nlist, values, fillvalue=None):
            new_json[name] = value
        parameters_list.append(new_json)

    group = D2VModelGroup(group_name, abs_models_folder, autoload=True)  # autoload --> True to add models, False to override
    group.add([Doc2Vec(**hp) for hp in parameters_list])

    training_lists = []
    for training_file in abs_training_files:
        list_list_words = load(open(training_file, "rb"))
        list_words = [item for sublist in list_list_words for item in sublist]
        training_lists.append(list_words)
    tagged_training_lists = [TaggedDocument(words=_text, tags=[str(i)]) for i, _text in enumerate(training_lists)]

    for i, model in enumerate(group):
        LOG.append("Training the model %i in the group '%s'..." % (i, group_name))
        model.build_vocab(tagged_training_lists, update=(model.corpus_total_words != 0))
        model.train(
            documents=tagged_training_lists,
            total_examples=model.corpus_count,
            epochs=model.epochs
        )

    group.save()
    LOG.append("The new group '%s' was saved!" % group_name)

    return jsonify({
        'group': group_name,
        'models': [{
            'model': i,
            'total_training_time': model.total_train_time
        } for i, model in enumerate(group)]
    }), 200


def getLog():
    global LOG
    idx = request.args.get('idx', default=0, type=int)
    return jsonify({'msgs': LOG[idx:], 'lastidx': len(LOG)-1}), 200
