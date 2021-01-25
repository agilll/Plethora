from model_groups import getAllD2VGroups as _getAllD2VGroups
from model_groups import D2VModelGroup as _D2VModelGroup
from itertools import zip_longest as zipl, product as prod
from gensim.models.doc2vec import TaggedDocument, Doc2Vec
from gensim.parsing.preprocessing import remove_stopwords
from gensim.utils import simple_preprocess
from flask import request, jsonify
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
def getAllSavedD2VGroups():
    global LOG

    # folder path where new models groups were saved
    models_folder = request.args.get("models_folder")
    # this variable is the actual absolute path for the new models groups. If 'models_folder' doesn't start
    # with '/', means it is a relative path from the Corpus path
    if models_folder.startswith("/"):
        abs_models_folder = models_folder
    else:
        abs_models_folder = korpus_dir + ("/" if not korpus_dir.endswith("/") else "") + models_folder  # add "/" if is necessary

    # append new server log message
    LOG.append("Get all saved D2V groups in DB")

    # get all saved models groups in the 'models_folder' path
    groups = _getAllD2VGroups(abs_models_folder)

    # return a list of groups. Each element is a dict with the group name and a list of models
    groups_list = []
    for group in groups:
        groups_list.append({
            'group': group.name,
            'models': [model for model in os.listdir(group.group_folder) if model.endswith(".d2v.model")]
        })
    return jsonify(groups_list), 200


# this function builds a new group of models and trains these models with a specific corpus. Then the new group is
# saved in the given path with this pattern name for each model:
#   <group_name>_id<model_id>_dm<param_dm>_ep<param_epochs>_vs<param_vectorsize>_wn<param_window>.d2v.model
def buildAndTrainNewModelGroup():
    global LOG

    # identification name for the new group. All _ characters will be removed in the final name
    group_name = request.get_json().get('group_name').replace('_', '')
    # d2v or w2v
    models_type = request.get_json().get('models_type')  # TODO use
    # file with all training files for the new models. Each line of this file must be a training file path.
    # Absolute path (if starts with '/') or relative path from the Corpus folder
    training_docs_file = request.get_json().get('training_docs_file')
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
        abs_models_folder = korpus_dir + ("/" if not korpus_dir.endswith("/") else "") + models_folder  # add "/" if is necessary

    # actual absolute path of the 'training_docs_file'
    if training_docs_file.startswith("/"):
        abs_training_docs_file = training_docs_file
    else:
        abs_training_docs_file = korpus_dir + ("/" if not korpus_dir.endswith("/") else "") + training_docs_file  # add "/" if is necessary

    # check query arguments validity. The http error code is always 400
    # TODO do it with every argument
    if not os.path.isfile(abs_training_docs_file):
        LOG.append("ERROR: Invalid query argument 'training_docs_file' in /buildAndTrainNewModelGroup request")
        return jsonify({
            'reason': "invalid argument",
            'msg': "training_docs_file argument does refer to no existing file"
        }), 400

    # append new server log message
    LOG.append("Build new '%s' models group '%s' in folder '%s', with files in '%s'" % (models_type, group_name, abs_models_folder, abs_training_docs_file))

    parameters_list = []
    # store all hyperparameters names
    nlist = [name for name in params.keys() if len(params[name]) > 0]
    # store all values lists
    vlist = [params[name] for name in nlist]
    # compute the cartesian product of the values lists. The result is a list of lists with all combinations
    # of all values
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

    tagged_training_lists = []

    for i, training_file in enumerate(abs_training_files):

        try:
            # read and store the text in the file
            training_fd = open(training_file, 'r')
            text = training_fd.read()

            # remove stopwords, if specified, with Gensim remove_stopwords function
            if flag_remove_stopWords:
                text = remove_stopwords(text)

            # preprocess the text (tokenize, lower, remove punctuation, remove <2 and >50 length words)
            training_list = simple_preprocess(text, max_len=50)

            # tag the training list (add an increasing number as tag)
            tagged_training_list = TaggedDocument(words=training_list, tags=[i])

            tagged_training_lists.append(tagged_training_list)
            # this is the input for training.
            # tagged_training_lists is a list:
            #   [TaggedDocument(['word1','word2',...], ['0']), TaggedDocument(['word1','word2',...], ['1']), ...]

        except Exception as e:
            print(e)
            LOG.append("Skipping file %i of the Training Corpus..." % i)

    LOG.append("Training with " + str(len(tagged_training_lists)) + " files")

    # create an instance of D2VModelGroup
    group = _D2VModelGroup(group_name, abs_models_folder, autoload=False)  # autoload: True to add models to a existing group, False to override

    # create one model with parameters in each element of the parameters_list and adds them to the new group
    group.add([Doc2Vec(**hp) for hp in parameters_list])

    # train all models in the new group
    for i, model in enumerate(group):

        # append a new log message when each model starts the train
        LOG.append("Training model %i in group '%s'..." % (i, group_name))

        # build the vocabulary with all words in the training corpus
        model.build_vocab(tagged_training_lists, update=(model.corpus_total_words != 0))

        # train each model with all default hyperparameters (defined in the Doc2Vec instance build)
        model.train(
            documents=tagged_training_lists,
            total_examples=model.corpus_count,
            epochs=model.epochs
        )

    # save the group in models_folder path. Creates a folder with the group name and saved the models inside
    group.save()

    # append a new log message after saving the group
    LOG.append("New group '%s' was saved!" % group_name)

    # return the new group in a dict with the name of the group and a list with all models in the group
    group_models = []
    for i, model in enumerate(group):
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
