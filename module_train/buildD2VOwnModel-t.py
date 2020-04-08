# training with 100 epochs, min_count=5, and .t files
# .t files are preprocessed .txt files
# a .t file contains a binary structure (pickle saved): a list of lists of words (already lemmas). That is, tokenization has already been done

import glob
import os
from gensim.models.doc2vec import Doc2Vec, TaggedDocument
import pickle

from aux import TRAINING_T_FOLDER as _TRAINING_T_FOLDER, OWN_D2V_MODEL as _OWN_D2V_MODEL

if not os.path.exists(_TRAINING_T_FOLDER):
	print(_TRAINING_T_FOLDER, "not found!")
	exit()


# variables init

model_filename = _OWN_D2V_MODEL + "-t.model"

vector_size = 20	# vector_size (int, optional) – Dimensionality of the feature vectors
window = 8	# window (int, optional) – The maximum distance between the current and predicted word within a sentence
alpha = 0.025	# alpha (float, optional) – The initial learning rate
min_alpha = 0.00025	# min_alpha (float, optional) – Learning rate will linearly drop to min_alpha as training progresses

# seed (int, optional) – Seed for the random number generator. Initial vectors for each word are seeded with a hash of the concatenation of word + str(seed)
# seed = 1

min_count = 5	# min_count (int, optional) – Ignores all words with total frequency lower than this
max_vocab_size = None	# max_vocab_size (int, optional) – Limits the RAM during vocabulary building
distributed_memory = 1	# dm ({1,0}, optional) – Defines the training algorithm. If dm=1, ‘distributed memory’ (PV-DM). Otherwise, distributed bag of words (PV-DBOW)
epochs = 100	# epochs (int, optional) – Number of iterations (epochs) over the corpus


# A function to build a model based on Doc2Vec, trained by our own training .t documents
def buildDoc2VecModel(model_name, vector_size, window, alpha, min_alpha, min_count, distributed_memory, epochs):

	training_files = glob.glob(_TRAINING_T_FOLDER+"*.t")	# Get all .t files in the training documents folder

	training_lists = []	# each member is a list of words representing a file contents 

	# Add the content of the training_files to the training_corpus
	for training_file in training_files:
		list_list_words = pickle.load(open(training_file, "rb" ))  # list_list_words is a list of lists (each list are the words of a sentence) 
		list_words  = [item for sublist in list_list_words for item in sublist] # flat list with all words of the document
		training_lists.append(list_words)

	# Tag the training lists (add an increasing number as tag)
	tagged_training_lists = [TaggedDocument(words=l, tags=[str(i)]) for i, l in enumerate(training_lists)]

	# this is the input for training
	# tagged_training_lists is a list [TaggedDocument(['token1','token2',...], ['0']), TaggedDocument(['token1','token2',...], ['1']), ...]
	
	# Create a Doc2Vec model with the selected parameters
	model = Doc2Vec(vector_size=vector_size,
					window=window,
					alpha=alpha,
					min_alpha=min_alpha,
					min_count=min_count,
					dm=distributed_memory)

	# Build vocabulary from the tagged training lists
	model.build_vocab(tagged_training_lists)

	# Train the model from the tagged training lists
	model.train(tagged_training_lists,
				total_examples=model.corpus_count,
				epochs=epochs,
				start_alpha=alpha,
				end_alpha=min_alpha)

	# Save the trained model to file
	model.save(model_name)
	print(model_name, "model saved!")


# Build a doc2vec model trained with files in textos originales folder
buildDoc2VecModel(model_filename, vector_size, window, alpha, min_alpha, min_count, distributed_memory, epochs)
