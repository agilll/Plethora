from doc2vec_group import D2VModelGroup as _D2VModelGroup
from word2vec_group import W2VModelGroup as _W2VModelGroup
from gensim.models.doc2vec import TaggedDocument, Doc2Vec
from gensim.models.word2vec import Word2Vec
from gensim.parsing.preprocessing import remove_stopwords
from gensim.utils import simple_preprocess


def trainD2VGroupFromTxtFilePaths(training_files_paths, models_folder, group_name, parameters_list, flag_remove_stopWords=False, LOG=None):
    tagged_training_lists = []

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

    if LOG:
        LOG.append("Training with " + str(len(tagged_training_lists)) + " files")

    # create an instance of D2VModelGroup
    group = _D2VModelGroup(group_name, models_folder, autoload=False)  # autoload: True to add models to a existing group, False to override

    # create one model with parameters in each element of the parameters_list and adds them to the new group
    group.add([Doc2Vec(**hp) for hp in parameters_list])

    # train all models in the new group
    for i, model in enumerate(group):
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

    # save the group in models_folder path. Creates a folder with the group name and saved the models inside
    group.save()

    # append a new log message after saving the group
    if LOG:
        LOG.append("New doc2vec group '%s' was saved!" % group_name)

    return group


def trainW2VGroupFromTxtFilePaths(training_files_paths, models_folder, group_name, parameters_list, flag_remove_stopWords=False, LOG=None):

    training_lists = []

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

    if LOG:
        LOG.append("Training with " + str(len(training_lists)) + " files")

    # create an instance of D2VModelGroup
    group = _W2VModelGroup(group_name, models_folder, autoload=False)  # autoload: True to add models to a existing group, False to override

    # create one model with parameters in each element of the parameters_list and adds them to the new group
    group.add([Word2Vec(**hp) for hp in parameters_list])

    # train all models in the new group
    for i, model in enumerate(group):
        # append a new log message when each model starts the train
        if LOG:
            LOG.append("Training model %i in group '%s'..." % (i, group_name))

        # build the vocabulary with all words in the training corpus
        model.build_vocab(training_lists, update=(model.corpus_total_words != 0))

        # train each model with all default hyperparameters (defined in the Doc2Vec instance build)
        model.train(
            sentences=training_lists,
            total_examples=model.corpus_count,
            epochs=model.epochs
        )

    # save the group in models_folder path. Creates a folder with the group name and saved the models inside
    group.save()

    # append a new log message after saving the group
    if LOG:
        LOG.append("New word2vec group '%s' was saved!" % group_name)

    return group
