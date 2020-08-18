import os
import collections
import random
from smart_open import open as smart_open
import gensim
from gensim.models.doc2vec import Doc2Vec, TaggedDocument
from gensim.parsing.preprocessing import remove_stopwords
from gensim.utils import simple_preprocess

from aux_train import LEE_D2V_MODEL as _LEE_D2V_MODEL

LEE_TRAINING_CORPUS = 'lee_background.cor'
LEE_TESTING_CORPUS = 'lee.cor'

remove_stopWords = True	# use remove_stopWords to indicate if stopwords must be removed or not
suffix = "with_stopwords"
if (remove_stopWords == True):
	print("Removing stopwords")
	suffix = "without_stopwords"

model_filename = _LEE_D2V_MODEL+"."+suffix+".model"

# Read and Pre-process Text
def readCorpus(fileName, tokens_only=False):
	with smart_open(fileName, encoding="iso-8859-1") as fd:  	# Use the latin encoding
		for index, line in enumerate(fd):
			if (remove_stopWords):  # use rm_stop to indicate if stopwords must be removed or not
				line = remove_stopwords(line)

			# Use gensim.utils.simple_preprocess for processing:
			# tokenize text to individual words, remove punctuations, set to lowercase, and remove words less than 2 chars or more than 50 chars
			tokenList = simple_preprocess(line, max_len=50)

			# Use the tokens_only to process the training and testing data differently
			if tokens_only:  # tokens_only=true for testing data
				yield tokenList  # Return a generator with processed text
			else:   # tokens_only=false for training data
				yield TaggedDocument(tokenList, [index])   # Returns a generator with tagged training corpus


def buildDoc2VecModel():
	# Set file names for training and testing data
	test_data_dir = '{}'.format(os.sep).join([gensim.__path__[0], 'test', 'test_data'])

	# Use the Lee Background corpus dataset (set of documents) included in gensim library to train the model
	training_data = test_data_dir + os.sep + LEE_TRAINING_CORPUS

	# Use the Lee Corpus included gensim to test the model
	testing_data = test_data_dir + os.sep + LEE_TESTING_CORPUS

	# Convert generators to lists
	training_corpus = list(readCorpus(training_data, tokens_only=False))
	testing_corpus = list(readCorpus(testing_data, tokens_only=True))

	# Training the model: Instantiate a Doc2Vec Object
	# vector_size: vector dimensions
	# min_count: the minimum number of a word frequency to be included
	# epochs: Number of iterations over the training corpus
	model = Doc2Vec(vector_size=40, min_count=2, epochs=40)  # create empty model
	model.build_vocab(training_corpus)  # Build and set a vocabulary
	model.train(training_corpus, total_examples=model.corpus_count, epochs=model.epochs)  # train

	# Save model to disk
	model.save(model_filename)
	print("Doc2Vec Lee model "+suffix+" saved:", model_filename)


	# Model assessment with the training dataset

	ranks = []
	# second_ranks = []

	for doc_index in range(len(training_corpus)):  	# Go through each document of the training corpus
		inferred_vector = model.infer_vector(training_corpus[doc_index].words)  # Infer a new vector for training corpus documents
		self_similarity = model.docvecs.most_similar([inferred_vector], topn=len(model.docvecs)) # get the most similars to it
		rankList = [docindex for docindex, sim in self_similarity]
		rank = rankList.index(doc_index)   # get its rank, ideally should be 1
		ranks.append(rank)

		# second_ranks.append(self_similarity[1])

		# print('Document ({}): {}\n'.format(doc_index, ' '.join(training_corpus[doc_index].words)))
		# print('Documents similarity')
		# self_similarity_length = len(self_similarity)
		# for label, index in [('Most', 0), ('Second Most', 1), ('Median', self_similarity_length//2), ('Least', self_similarity_length-1)]:
		# 	print(u'%s %s: %s\n' % (label, self_similarity[index], ' '.join(training_corpus[self_similarity[index][0]].words)))

	# Count how many times each document ranks with respect to the training corpus
	documents_ranks = collections.Counter(ranks)
	print(documents_ranks)



	# Testing #

	# testing_corpus_length = len(testing_corpus)
	# # Generate a random id from the testing corpus
	# doc_index = random.randint(0, testing_corpus_length-1)
	#
	# # Infer a vector from the model
	# inferred_vector = model.infer_vector(testing_corpus[doc_index])
	#
	# self_similarity = model.docvecs.most_similar([inferred_vector], topn=len(model.docvecs))
	# print('Document ({}): {}\n'.format(doc_index, ' '.join(training_corpus[doc_index].words)))
	# self_similarity_length = len(self_similarity)
	#
	# for label, index in [('Most', 0), ('Second Most', 1), ('Median', self_similarity_length//2), ('Least', self_similarity_length-1)]:
	# 	print(u'%s %s: %s\n' % (label, self_similarity[index], ' '.join(training_corpus[self_similarity[index][0]].words)))


# Build a doc2vec model
buildDoc2VecModel()
