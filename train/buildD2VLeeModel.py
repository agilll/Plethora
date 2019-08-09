import os
import collections
import random

# To install: pip install smart_open
from smart_open import open as smart_open

# to install: pip3 install gensim
import gensim
from gensim.models.doc2vec import Doc2Vec

from aux import MODELS_FOLDER as _MODELS_FOLDER
if not os.path.exists(_MODELS_FOLDER):
	os.makedirs(_MODELS_FOLDER)
	
from aux import LEE_D2V_MODEL as _LEE_D2V_MODEL
model_full_filename = _MODELS_FOLDER + _LEE_D2V_MODEL + ".model"

	
LEE_TRAINING_CORPUS = 'lee_background.cor'
LEE_TESTING_CORPUS = 'lee.cor'

def buildDoc2VecModel():
	# Set file names for training and testing data
	test_data_dir = '{}'.format(os.sep).join([gensim.__path__[0], 'test', 'test_data'])

	# Use the Lee Background corpus dataset (set of documents) included in gensim library to train the model
	training_data = test_data_dir + os.sep + LEE_TRAINING_CORPUS

	# Use the Lee Corpus included gensim to test the model
	testing_data = test_data_dir + os.sep + LEE_TESTING_CORPUS


	# Read and Pre-process Text
	def readCorpus(fileName, tokens_only=False):
		# smart_open is used for streaming very large files
		# Use the latin encoding
		with smart_open(fileName, encoding="iso-8859-1") as file:
			for index, line in enumerate(file):
				# Use the tokens_only to process the training and testing data differently
				if tokens_only:
					# Use gensim.utils.simple_preprocess for processing:
					# tokenize text to individual words
					# remove punctuations
					# set to lowercase
					# remove words less than 2 characters or more than 15 characters

					# Return a generator with processed text
					yield gensim.utils.simple_preprocess(line)
				else:
					# tokens_only = true for training data

					# Returns a generator with tagged training corpus
					yield gensim.models.doc2vec.TaggedDocument(gensim.utils.simple_preprocess(line), [index])


	# Convert generators to lists
	training_corpus = list(readCorpus(training_data))
	testing_corpus = list(readCorpus(testing_data, tokens_only=True))


	# Training the model #

	# Instantiate a Doc2Vec Object
	# vector_size: vector dimensions
	# min_count: the minimum number of a word frequency to be included
	# epochs: Number of iterations over the training corpus
	model = gensim.models.doc2vec.Doc2Vec(vector_size=40, min_count=2, epochs=40)

	# Build a Vocabulary
	model.build_vocab(training_corpus)


	# Model assessment with the training dataset #

	ranks = []
	second_ranks = []

	# Go through each document of the training corpus
	for doc_index in range(len(training_corpus)):
		# Infer a new vector to training corpus documents
		inferred_vector = model.infer_vector(training_corpus[doc_index].words)

		self_similarity = model.docvecs.most_similar([inferred_vector], topn=len(model.docvecs))
		rank = [docindex for docindex, sim in self_similarity].index(doc_index)
		ranks.append(rank)
		second_ranks.append(self_similarity[1])


	# Save model to disk, so we won't need to do the training everytime
	model.save(model_full_filename)
	print("Doc2Vec model saved!")

	# Count how each document ranks with respect to the training corpus
	documents_ranks = collections.Counter(ranks)

	print('Document ({}): {}\n'.format(doc_index, ' '.join(training_corpus[doc_index].words)))

	print('Documents similarity')

	self_similarity_length = len(self_similarity)


	for label, index in [('Most', 0), ('Second Most', 1), ('Median', self_similarity_length//2), ('Least', self_similarity_length-1)]:
		print(u'%s %s: %s\n' % (label, self_similarity[index], ' '.join(training_corpus[self_similarity[index][0]].words)))

	# Testing #

	testing_corpus_length = len(testing_corpus)
	# Generate a random id from the testing corpus
	doc_index = random.randint(0, testing_corpus_length-1)

	# Infer a vector from the model
	inferred_vector = model.infer_vector(testing_corpus[doc_index])

	self_similarity = model.docvecs.most_similar([inferred_vector], topn=len(model.docvecs))
	print('Document ({}): {}\n'.format(doc_index, ' '.join(training_corpus[doc_index].words)))


	for label, index in [('Most', 0), ('Second Most', 1), ('Median', self_similarity_length//2), ('Least', self_similarity_length-1)]:
		print(u'%s %s: %s\n' % (label, self_similarity[index], ' '.join(training_corpus[self_similarity[index][0]].words)))


# Build a doc2vec model
buildDoc2VecModel()
