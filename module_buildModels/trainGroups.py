from doc2vec_group import D2VModelGroup as _D2VModelGroup
from word2vec_group import W2VModelGroup as _W2VModelGroup
from gensim.models.doc2vec import TaggedDocument, Doc2Vec
from gensim.models.word2vec import Word2Vec
from gensim.parsing.preprocessing import remove_stopwords
from gensim.utils import simple_preprocess


def trainD2VGroupFromTxtFilePaths(training_files_paths, models_folder, group_name, parameters_list, percentage_training_corpus=100, flag_remove_stopWords=False, LOG=None):
    tagged_training_lists = []

    # apply the percentage_training_corpus to the corpus files number
    training_files_paths = training_files_paths[:int(len(training_files_paths)*percentage_training_corpus/100)]

    if LOG:
        LOG.append("Training with %i files (%i%% of the Corpus)" % (len(training_files_paths), percentage_training_corpus))

    for i, training_file in enumerate(training_files_paths):

        try:
            # read and store the file text
            training_fd = open(training_file, 'r')
            text = training_fd.read()

            # remove stopwords, if specified, with Gensim remove_stopwords function
            if flag_remove_stopWords:
                text = remove_stopwords(text)

            # preprocess the text (tokenize, lower, remove punctuation, remove <2 and >50 length words)
            training_tokens_list = simple_preprocess(text, max_len=50)

            # tag the training list (add an increasing number as tag)
            tagged_training_list = TaggedDocument(words=training_tokens_list, tags=[i])

            tagged_training_lists.append(tagged_training_list)
            # this is the input for training.
            # tagged_training_lists is a list:
            #   [TaggedDocument(['word1','word2',...], ['0']), TaggedDocument(['word1','word2',...], ['1']), ...]

        except Exception as e:
            print(e)
            if LOG:
                LOG.append("Skipping file %i of the Training Corpus..." % i)

    # create an instance of D2VModelGroup
    group = _D2VModelGroup(group_name, models_folder, override=True)  # override: False to add models to a existing group, True to override

    # create the models with every hyperparameter in parameters_list
    new_models = [Doc2Vec(**hp) for hp in parameters_list]

    # train every new model
    for i, model in enumerate(new_models):
        # append a new log message when each model starts the train
        if LOG:
            LOG.append("Training model %i in group '%s'..." % (i, group_name))

        # build the vocabulary with all words in the training corpus
        model.build_vocab(tagged_training_lists, update=(model.corpus_total_words != 0))

        # train each model with all default hyperparameters (defined in the Doc2Vec instance build)
        model.train(
            documents=tagged_training_lists,
            total_examples=model.corpus_count,
            epochs=model.epochs
        )

        # add the model to the group and save it in group_folder
        group.add(model, True)

    # append a new log message after saving the group
    if LOG:
        LOG.append("New doc2vec group '%s' was saved!" % group_name)

    return group


def trainW2VGroupFromTxtFilePaths(training_files_paths, models_folder, group_name, parameters_list, percentage_training_corpus=100, flag_remove_stopWords=False, LOG=None):
    training_lists = []

    # apply the percentage_training_corpus to the corpus files number
    training_files_paths = training_files_paths[:int(len(training_files_paths)*percentage_training_corpus/100)]

    if LOG:
        LOG.append("Training with %i files (%i%% of the Corpus)" % (len(training_files_paths), percentage_training_corpus))

    for i, training_file in enumerate(training_files_paths):
        try:
            # read and store the text in the file
            training_fd = open(training_file, 'r')
            text = training_fd.read()

            # remove stopwords, if specified, with Gensim remove_stopwords function
            if flag_remove_stopWords:
                text = remove_stopwords(text)

            # preprocess the text (tokenize, lower, remove punctuation, remove <2 and >50 length words)
            training_tokens_list = simple_preprocess(text, max_len=50)

            training_lists.append(training_tokens_list)
            # this is the input for training.
            # training_lists is a list:
            #   [['word1','word2',...], ['word1','word2',...], ...]

        except Exception as e:
            print(e)
            if LOG:
                LOG.append("Skipping file %i of the Training Corpus..." % i)

    # create an instance of D2VModelGroup
    group = _W2VModelGroup(group_name, models_folder, override=True)  # override: False to add models to a existing group, True to override

    # create the models with every hyperparameter in parameters_list
    new_models = [Word2Vec(**hp) for hp in parameters_list]

    # train every new model
    for i, model in enumerate(new_models):
        # append a new log message when each model starts the train
        if LOG:
            LOG.append("Training model %i in group '%s'..." % (i, group_name))

        # build the vocabulary with all words in the training corpus
        model.build_vocab(training_lists, update=(model.corpus_total_words != 0))

        # train each model with all default hyperparameters (defined in the Word2Vec instance build)
        model.train(
            sentences=training_lists,
            total_examples=model.corpus_count,
            epochs=model.epochs
        )

        # add the model to the group and save it in group_folder
        group.add(model, True)

    # append a new log message after saving the group
    if LOG:
        LOG.append("New word2vec group '%s' was saved!" % group_name)

    return group
