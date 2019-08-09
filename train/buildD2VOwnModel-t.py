# with 100 epochs, min_count=5, and .t

import glob
import os
from gensim.models.doc2vec import Doc2Vec, TaggedDocument
from nltk.tokenize import word_tokenize
import pickle


from aux import CORPUS_FOLDER as _CORPUS_FOLDER
if not os.path.exists(_CORPUS_FOLDER):
	print(_CORPUS_FOLDER, "not found!")
	exit()
	
from aux import TRAINING_T_FOLDER as _TRAINING_T_FOLDER
if not os.path.exists(_TRAINING_T_FOLDER):
	print(_TRAINING_T_FOLDER, "not found!")
	exit()

from aux import MODELS_FOLDER as _MODELS_FOLDER
if not os.path.exists(_MODELS_FOLDER):
	os.makedirs(_MODELS_FOLDER)


from aux import OWN_D2V_MODEL as _OWN_D2V_MODEL
model_full_filename = _MODELS_FOLDER + _OWN_D2V_MODEL + "-t.model"



# vector_size (int, optional) – Dimensionality of the feature vectors
vector_size = 20

# window (int, optional) – The maximum distance between the current and predicted word within a sentence
window = 8

# alpha (float, optional) – The initial learning rate
alpha = 0.025

# min_alpha (float, optional) – Learning rate will linearly drop to min_alpha as training progresses
min_alpha = 0.00025

# seed (int, optional) – Seed for the random number generator. Initial vectors for each word are seeded with a hash of the concatenation of word + str(seed)
# seed = 1

# min_count (int, optional) – Ignores all words with total frequency lower than this
min_count = 5

# max_vocab_size (int, optional) – Limits the RAM during vocabulary building
max_vocab_size = None

# dm ({1,0}, optional) – Defines the training algorithm. If dm=1, ‘distributed memory’ (PV-DM) is used. Otherwise, distributed bag of words (PV-DBOW) is employed
distributed_memory = 1

# epochs (int, optional) – Number of iterations (epochs) over the corpus
epochs = 100



# A function to build a model based on Doc2Vec, trained by our training documents
def buildDoc2VecModel(model_name, vector_size, window, alpha, min_alpha, min_count, distributed_memory, epochs):

	# Get all text files in the training documents folder
	training_documents = glob.glob(_TRAINING_T_FOLDER+"*.t")

	# A corpus with all the training documents
	training_corpus = []

	# Add the training_documents to the training_corpus
	for training_document in training_documents:
		list_list_words = pickle.load(open(training_document, "rb" ))  # list_list_words is a list of lists (each list are teh words of a sentence) 
		list_words  = [item for sublist in list_list_words for item in sublist] # flat list with all words of the document
		training_corpus.append(list_words)

	# Tag the training documents
	tagged_training_corpus = [TaggedDocument(words=l, tags=[str(i)]) for i, l in enumerate(training_corpus)]

	# Create a Doc2Vec model
	model = Doc2Vec(vector_size=vector_size,
					window=window,
					alpha=alpha,
					min_alpha=min_alpha,
					min_count=min_count,
					dm=distributed_memory)

	# Build vocabulary from the tagged training corpus
	model.build_vocab(tagged_training_corpus)

	# Train the model
	model.train(tagged_training_corpus,
				total_examples=model.corpus_count,
				epochs=epochs,
				start_alpha=alpha,
				end_alpha=min_alpha)


	# Save the trained model to file
	model.save(model_name)
	print("Doc2Vec model saved!")


# Build a doc2vec model trained with files in textos originales folder
buildDoc2VecModel(model_full_filename, vector_size, window, alpha, min_alpha, min_count, distributed_memory, epochs)
