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
# Must not end with '/'
korpus_dir = "/home/sergio/Projects/TFG/KORPUS"

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
    abs_models_folder = korpus_dir + "/" + models_folder if not models_folder.startswith("/") else models_folder
    # remove the last '/' if exists
    abs_models_folder = abs_models_folder[:-1] if abs_models_folder.endswith("/") else abs_models_folder

    # append new server log message
    LOG.append("Get all saved groups in " + abs_models_folder)

    # get all saved D2V models groups in the 'models_folder' path (summary json)
    d2v_groups = _getAllD2VGroups(abs_models_folder + "/Doc2Vec", summary=True)
    # get all saved W2V models groups in the 'models_folder' path (summary json)
    w2v_groups = _getAllW2VGroups(abs_models_folder + "/Word2Vec", summary=True)

    return jsonify({
        "word2vec": w2v_groups,
        "doc2vec": d2v_groups
    }), 200


# this function builds a new group of models and trains these models with a specific corpus. Then the new group is
# saved in the given path with this pattern name for each model:
#   <group_name>_id<model_id>_dm<param_dm>_ep<param_epochs>_vs<param_vectorsize>_wn<param_window>.d2v.model
#   <group_name>_id<model_id>_it<param_iter>_sz<param_size>_wn<param_window>.w2v.model
def buildAndTrainNewModelGroup():
    global LOG

    # GET PARAMETERS #

    # identification name for the new group. All _ characters will be removed in the final name
    group_name = request.get_json().get('group_name').replace('_', '')
    # d2v or w2v
    models_type = request.get_json().get('models_type')
    # path to training files. Allows:
    #       - Path to file with a list of training files. Each line of this file must be a training file path.
    #       - Path to folder with the training files.
    # Absolute path (if starts with '/') or relative path from the Corpus folder
    training_docs_path = request.get_json().get('training_docs_path')
    # percentage_training_corpus. Default 100%
    percentage_training_corpus = request.get_json().get('percentage_training_corpus')
    # folder path where the new group will be saved after the training.
    # Absolute path (if starts with '/') or relative path from the Corpus folder
    models_folder = request.get_json().get('models_folder')
    # training hyperparameters lists to create all models. This input must be a dict with
    #   key = parameter name
    #   value = list of values for this parameter
    # the models will be created with all possible combinations of every value
    params = request.get_json().get('params')

    # FIX PATHS #

    # actual absolute path of the 'models_folder'
    abs_models_folder = korpus_dir + "/" + models_folder if not models_folder.startswith("/") else models_folder
    # remove the last '/' if exists
    abs_models_folder = abs_models_folder[:-1] if abs_models_folder.endswith("/") else abs_models_folder

    # actual absolute path of the 'training_docs_path'
    abs_training_docs_path = korpus_dir + "/" + training_docs_path if not training_docs_path.startswith("/") else training_docs_path
    # remove the last '/' if exists
    abs_training_docs_path = abs_training_docs_path[:-1] if abs_training_docs_path.endswith("/") else abs_training_docs_path

    # set percentage_training_corpus in the range [0,100]
    if int(percentage_training_corpus) < 0:
        percentage_training_corpus = 0
    elif int(percentage_training_corpus) > 100:
        percentage_training_corpus = 100
    else:
        percentage_training_corpus = int(percentage_training_corpus)

    # append new server log message
    LOG.append("Build new '%s' models group '%s' in folder '%s', with files in '%s'" % (models_type, group_name, abs_models_folder, abs_training_docs_path))

    # GET TRAINING TEXT FILES #

    # opens the file/folder with all training files and stores them in 'abs_training_files' variable.
    abs_training_files = []

    # file with the path to a training file per line
    if os.path.isfile(abs_training_docs_path):
        with open(abs_training_docs_path) as df:
            for file_path in df:
                file_path = file_path.strip()
                # Each line may be a relative path or a absolute path (if it starts with '/').
                abs_file_path = korpus_dir + "/" + file_path if not file_path.startswith("/") else file_path
                abs_training_files.append(abs_file_path)

    # directory where all training files are located
    elif os.path.isdir(abs_training_docs_path):
        abs_training_files = [abs_training_docs_path + "/" + file for file in os.listdir(abs_training_docs_path)]

    else:
        LOG.append("ERROR: '%s' path does not exist. Invalid training_docs_path argument." % abs_training_docs_path)
        return jsonify({
            'reason': "invalid argument",
            'msg': "'%s' path does not exist. Invalid training_docs_path argument." % abs_training_docs_path
        }), 400

    # CALCULATE HYPERPARAMETERS LISTS #

    parameters_list = []

    # store all hyperparameters names
    nlist = [name for name in params.keys() if len(params[name]) > 0]
    # store all values lists
    vlist = [params[name] for name in nlist]

    # add the default value of all other parameters (not received in the request).
    # These values are extracted from the file params.json.
    with open('params.json') as params_file:
        all_hparams_json = json.load(params_file)
        all_hparams_json = all_hparams_json["word2vec"] if models_type == "w2v" else all_hparams_json["doc2vec"]
        not_defined_hparams = [hp for hp in all_hparams_json if hp["name"] not in nlist]
        nlist.extend([ndhp["name"] for ndhp in not_defined_hparams])
        vlist.extend([[ndhp["default"]] for ndhp in not_defined_hparams])

    # compute the cartesian product of the values lists.
    # The result is a list of lists with all combinations of all values.
    values_prod = prod(*vlist)

    # fill 'parameters_list' with a list of dicts with each combination of parameters:
    #   [{vector_size: 10, window: 10}, {vector_size: 10, window: 11}, {vector_size: 10, window: 12}, ...]
    for values in values_prod:
        new_json = dict()
        for name, value in zipl(nlist, values, fillvalue=None):
            new_json[name] = value
        parameters_list.append(new_json)

    # CREATE CORPUS AND TRAIN MODELS #

    # call _trainD2VGroupFromTxtFilePaths to create the new group of d2v or w2v models and train them with the
    # received hyperparameters ('parameters_list').
    # This function also apply the percentage to the training corpus ('percentage_training_corpus' to 'abs_training_files').
    if models_type == "d2v":
        abs_models_folder = abs_models_folder + "/Doc2Vec"
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
        abs_models_folder = abs_models_folder + "/Word2Vec"
        new_group = _trainW2VGroupFromTxtFilePaths(
            training_files_paths=abs_training_files,
            models_folder=abs_models_folder,
            group_name=group_name,
            parameters_list=parameters_list,
            percentage_training_corpus=percentage_training_corpus,
            flag_remove_stopWords=flag_remove_stopWords,
            LOG=LOG
        )

    # RETURN POST RESPONSE #

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


# this function returns the Corpus folder path, defined directly in this script.
def getKorpusPath():
    return jsonify({
        'korpus': korpus_dir + "/"
    })
