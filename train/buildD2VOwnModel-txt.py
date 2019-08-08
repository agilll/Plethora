# with 100 epochs and .txt

import glob
from gensim.models.doc2vec import Doc2Vec, TaggedDocument
from nltk.tokenize import word_tokenize

from aux import TRAINING_TXT_FOLDER as _TRAINING_TXT_FOLDER, OWN_D2V_MODEL as _OWN_D2V_MODEL


# Name the model
model = _OWN_D2V_MODEL+"-txt.model"

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
min_count = 1

# max_vocab_size (int, optional) – Limits the RAM during vocabulary building
max_vocab_size = None

# dm ({1,0}, optional) – Defines the training algorithm. If dm=1, ‘distributed memory’ (PV-DM) is used. Otherwise, distributed bag of words (PV-DBOW) is employed
distributed_memory = 1

# epochs (int, optional) – Number of iterations (epochs) over the corpus
epochs = 100

# delta - To decrease the learning rate manually
alpha_delta = 0.0002


# A function to build a model based on Doc2Vec, trained by our training documents
def buildDoc2VecModel(model_name, vector_size, window, alpha, min_alpha, min_count, distributed_memory, epochs, alpha_delta):

	# Get all text files in the training documents folder
	training_documents = glob.glob(_TRAINING_TXT_FOLDER+"*.txt")

	# A corpus with all the training documents
	training_corpus = []

	# Add the training_documents to the training_corpus
	for training_document in training_documents:
		training_text = open(training_document, "r")
		training_corpus.append(training_text.read())

	# Tag the training documents
	tagged_training_corpus = [TaggedDocument(words=word_tokenize(_d.lower()), tags=[str(i)]) for i, _d in enumerate(training_corpus)]

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
buildDoc2VecModel(model, vector_size, window, alpha, min_alpha, min_count, distributed_memory, epochs, alpha_delta)
