from doc2vec_group import getAllD2VGroups as _getAllD2VGroups
from word2vec_group import getAllW2VGroups as _getAllW2VGroups
from trainGroups import trainD2VGroupFromTxtFilePaths as _trainD2VGroupFromTxtFilePaths
from trainGroups import trainW2VGroupFromTxtFilePaths as _trainW2VGroupFromTxtFilePaths
from itertools import zip_longest as zipl, product as prod
from flask import request, jsonify
import json
import os

# string array for the new logs
# Any function can add any log message to this array and the client will access them from /getLog
LOG = []

# Folder path of the training Corpus. This folder MUST exist.
# All new groups (folders with models) will be saved here by default.
korpus_dir = "/home/sergio/Projects/TFG/KORPUS/"

# Use flag_remove_stopWords to indicate if stopwords must be removed or not in the training files.
flag_remove_stopWords = True


# this function obtains all saved groups (folders with models) in a specific path. This path is passed by a query
# param called "models_folder"
def getAllSavedGroups():
    global LOG

    # folder path where new models groups were saved
    models_folder = request.args.get("models_folder")
    # this variable is the actual absolute path for the new models groups. If 'models_folder' doesn't start
    # with '/', means it is a relative path from the Corpus path
    if models_folder.startswith("/"):
        abs_models_folder = models_folder
    else:
        abs_models_folder = korpus_dir + ("/" if not korpus_dir.endswith("/") else "") + models_folder

    abs_models_folder += "/" if not abs_models_folder.endswith("/") else ""  # is folder, so add "/" if is necessary

    # append new server log message
    LOG.append("Get all saved groups in " + abs_models_folder)

    # get all saved D2V models groups in the 'models_folder' path
    d2v_groups = _getAllD2VGroups(abs_models_folder + "Doc2Vec")
    # get all saved W2V models groups in the 'models_folder' path
    w2v_groups = _getAllW2VGroups(abs_models_folder + "Word2Vec")

    # return a list of d2v and w2v groups. Each element is a dict with the group name and a list of models
    d2v_groups_list = []
    w2v_groups_list = []
    for d2vg in d2v_groups:
        d2v_groups_list.append({
            'group': d2vg.name,
            'models': [model for model in os.listdir(d2vg.group_folder) if model.endswith(".d2v.model")]
        })
    for w2vg in w2v_groups:
        w2v_groups_list.append({
            'group': w2vg.name,
            'models': [model for model in os.listdir(w2vg.group_folder) if model.endswith(".w2v.model")]
        })
    return jsonify({
        "word2vec": w2v_groups_list,
        "doc2vec": d2v_groups_list
    }), 200


# this function builds a new group of models and trains these models with a specific corpus. Then the new group is
# saved in the given path with this pattern name for each model:
#   <group_name>_id<model_id>_dm<param_dm>_ep<param_epochs>_vs<param_vectorsize>_wn<param_window>.d2v.model
#   <group_name>_id<model_id>_it<param_iter>_sz<param_size>_wn<param_window>.w2v.model
def buildAndTrainNewModelGroup():
    global LOG

    # identification name for the new group. All _ characters will be removed in the final name
    group_name = request.get_json().get('group_name').replace('_', '')
    # d2v or w2v
    models_type = request.get_json().get('models_type')  # TODO use
    # file with all training files for the new models. Each line of this file must be a training file path.
    # Absolute path (if starts with '/') or relative path from the Corpus folder
    training_docs_file = request.get_json().get('training_docs_file')
    # percentage_training_corpus. Default 100%
    percentage_training_corpus = request.get_json().get('percentage_training_corpus')
    # folder path where the new group will be saved after the training.
    # Absolute path (if starts with '/') or relative path from the Corpus folder
    models_folder = request.get_json().get('models_folder')
    # training hyperparameters lists to create all models. This input must be a dict with
    #   key = parameter name
    #   value = list of values for this parameter
    # the models will be created with all possible combinations of all values
    params = request.get_json().get('params')

    # actual absolute path of the 'models_folder'
    if models_folder.startswith("/"):
        abs_models_folder = models_folder
    else:
        abs_models_folder = korpus_dir + ("/" if not korpus_dir.endswith("/") else "") + models_folder

    abs_models_folder += "/" if not abs_models_folder.endswith("/") else ""  # is folder, so add "/" if is necessary

    # actual absolute path of the 'training_docs_file'
    if training_docs_file.startswith("/"):
        abs_training_docs_file = training_docs_file
    else:
        abs_training_docs_file = korpus_dir + ("/" if not korpus_dir.endswith("/") else "") + training_docs_file

    # check query arguments validity. The http error code is always 400
    # TODO do it with every argument
    if not os.path.isfile(abs_training_docs_file):
        LOG.append("ERROR: Invalid query argument 'training_docs_file' in /buildAndTrainNewModelGroup request")
        return jsonify({
            'reason': "invalid argument",
            'msg': "training_docs_file argument does not exist. ("+abs_training_docs_file+")"
        }), 400

    # set percentage_training_corpus in the range [0,100]
    if int(percentage_training_corpus) < 0:
        percentage_training_corpus = 0
    elif int(percentage_training_corpus) > 100:
        percentage_training_corpus = 100
    else:
        percentage_training_corpus = int(percentage_training_corpus)

    # append new server log message
    LOG.append("Build new '%s' models group '%s' in folder '%s', with files in '%s'" % (models_type, group_name, abs_models_folder, abs_training_docs_file))

    parameters_list = []

    # store all hyperparameters names
    nlist = [name for name in params.keys() if len(params[name]) > 0]
    # store all values lists
    vlist = [params[name] for name in nlist]

    # add the default value of all other parameters (not received in the request).
    # these values are extracted from the file params.json
    with open('params.json') as params_file:
        all_hparams_json = json.load(params_file)
        all_hparams_json = all_hparams_json["word2vec"] if models_type == "w2v" else all_hparams_json["doc2vec"]
        not_defined_hparams = [hp for hp in all_hparams_json if hp["name"] not in nlist]
        nlist.extend([ndhp["name"] for ndhp in not_defined_hparams])
        vlist.extend([[ndhp["default"]] for ndhp in not_defined_hparams])

    # compute the cartesian product of the values lists. The result is a list of lists with
    # all combinations of all values
    values_prod = prod(*vlist)

    # fill 'parameters_list' with a list of dicts with each combination of parameters:
    #   [{vector_size: 10, window: 10}, {vector_size: 10, window: 11}, {vector_size: 10, window: 12}, ...]
    for values in values_prod:
        new_json = dict()
        for name, value in zipl(nlist, values, fillvalue=None):
            new_json[name] = value
        parameters_list.append(new_json)

    # opens the file with all training files paths and stores them in 'abs_training_files' variable. Each line may be
    # a relative path or a absolute path (if it starts with '/')
    abs_training_files = []
    with open(abs_training_docs_file) as df:
        for file_path in df:
            if file_path.startswith("/"):
                abs_file_path = file_path.strip()
            else:
                abs_file_path = korpus_dir + ("/" if not korpus_dir.endswith("/") else "") + file_path.strip()  # add "/" if is necessary
            abs_training_files.append(abs_file_path)

    # call _trainD2VGroupFromTxtFilePaths to create the new group of d2v or w2v models and train
    # them with the received hyperparameters ('parameters_list'). This function also apply the percentage to the
    # training corpus ('percentage_training_corpus' to 'abs_training_files')
    if models_type == "d2v":
        abs_models_folder = abs_models_folder + ("/" if not abs_models_folder.endswith("/") else "") + "Doc2Vec/"
        new_group = _trainD2VGroupFromTxtFilePaths(
            training_files_paths=abs_training_files,
            models_folder=abs_models_folder,
            group_name=group_name,
            parameters_list=parameters_list,
            percentage_training_corpus=percentage_training_corpus,
            flag_remove_stopWords=flag_remove_stopWords,
            LOG=LOG
        )

    else:
        abs_models_folder = abs_models_folder + ("/" if not abs_models_folder.endswith("/") else "") + "Word2Vec/"
        new_group = _trainW2VGroupFromTxtFilePaths(
            training_files_paths=abs_training_files,
            models_folder=abs_models_folder,
            group_name=group_name,
            parameters_list=parameters_list,
            percentage_training_corpus=percentage_training_corpus,
            flag_remove_stopWords=flag_remove_stopWords,
            LOG=LOG
        )

    # return the new group in a dict with the name of the group and a list with all models in the group
    group_models = []
    for i, model in enumerate(new_group):
        group_models.append({
            'model': i,
            'total_training_time': model.total_train_time
        })
    return jsonify({
        'group': group_name,
        'models': group_models
    }), 200


# this function gets the runtime Log from a specific index (given in a query parameter 'idx')
def getLog():
    global LOG

    # index the Log messages are returned from
    idx = request.args.get('idx', default=0, type=int)

    # return a dict with the messages list of the runtime Log from the given index, and the last index number
    return jsonify({
        'msgs': LOG[idx:],
        'lastidx': len(LOG)-1
    }), 200


# this function simply returns the Corpus folder, defined directly in this script.
def getKorpusPath():
    return jsonify({
        'korpus': korpus_dir
    })
