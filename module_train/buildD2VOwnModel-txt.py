# train with 100 epochs and .txt files

import glob
import os
from gensim.models.doc2vec import Doc2Vec, TaggedDocument
from nltk.tokenize import word_tokenize

from aux import TRAINING_TXT_FOLDER as _TRAINING_TXT_FOLDER, OWN_D2V_MODEL as _OWN_D2V_MODEL
	
if not os.path.exists(_TRAINING_TXT_FOLDER):
	print(_TRAINING_TXT_FOLDER, "not found!")
	exit()

# variables init

model_filename = _OWN_D2V_MODEL + "-txt.model"

vector_size = 20	# vector_size (int, optional) – Dimensionality of the feature vectors
window = 8	# window (int, optional) – The maximum distance between the current and predicted word within a sentence
alpha = 0.025	# alpha (float, optional) – The initial learning rate
min_alpha = 0.00025	# min_alpha (float, optional) – Learning rate will linearly drop to min_alpha as training progresses

# seed (int, optional) – Seed for the random number generator. Initial vectors for each word are seeded with a hash of the concatenation of word + str(seed)
# seed = 1

min_count = 1	# min_count (int, optional) – Ignores all words with total frequency lower than this
max_vocab_size = None	# max_vocab_size (int, optional) – Limits the RAM during vocabulary building
distributed_memory = 1	# dm ({1,0}, optional) – Defines the training algorithm. If dm=1, ‘distributed memory’ (PV-DM). Otherwise, distributed bag of words (PV-DBOW)
epochs = 100	# epochs (int, optional) – Number of iterations (epochs) over the corpus
alpha_delta = 0.0002	# delta - To decrease the learning rate manually




# A function to build a model based on Doc2Vec, trained by our own training text documents
def buildDoc2VecModel(model_name, vector_size, window, alpha, min_alpha, min_count, distributed_memory, epochs, alpha_delta):

	training_files = glob.glob(_TRAINING_TXT_FOLDER+"*.txt")	# Get all .txt files in the training documents folder

	training_texts = []	# A corpus with a list of strings: each string is the text content of one training file

	# read the training_files and add their contents to the training_texts list
	for training_file in training_files:
		training_fd = open(training_file, "r")
		text = training_fd.read()
		training_texts.append(text)

	# Tokenize and tag (add an increasing number as tag) the training texts
	# word_tokenize(_text.lower()) changes text to lower and tokenizes it: creates a list with the different words of the text
	tagged_training_lists = [TaggedDocument(words=word_tokenize(_text.lower()), tags=[str(i)]) for i, _text in enumerate(training_texts)]

	# this is the input for training
	# tagged_training_lists is a list [TaggedDocument(['token1','token2',...], ['0']), TaggedDocument(['token1','token2',...], ['1']), ...]
	
	
	# Create an empty Doc2Vec model with the selected parameters
	model = Doc2Vec(vector_size=vector_size,
					window=window,
					alpha=alpha,
					min_alpha=min_alpha,
					min_count=min_count,
					dm=distributed_memory)

	# Build model vocabulary from the tagged training lists
	model.build_vocab(tagged_training_lists)

	# Train the model with the tagged list of lists
	model.train(tagged_training_lists,
				total_examples=model.corpus_count,
				epochs=epochs,
				start_alpha=alpha,
				end_alpha=min_alpha)

	# Save the trained model to file
	model.save(model_name)
	print(model_name, "model saved!")

# start execution

# Build a doc2vec model trained with files in textos originales folder
buildDoc2VecModel(model_filename, vector_size, window, alpha, min_alpha, min_count, distributed_memory, epochs, alpha_delta)
