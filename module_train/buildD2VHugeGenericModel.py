# training Doc2Vec models with .w files (preprocessed .txt files, but still text files)

import os
import sys
import collections
import glob
import csv
from smart_open import open as _Open
from datetime import datetime
from gensim.models.doc2vec import Doc2Vec, TaggedDocument
from gensim.parsing.preprocessing import remove_stopwords as Gensim_remove_stopwords
from gensim.utils import simple_preprocess
import codecs


if len(sys.argv) < 2:
	print("Use: "+sys.argv[0]+" corpus")
	exit(-1)

TRCORPUS = sys.argv[1]  # webbase wikipedia

MODEL_NAME = "/Users/agil/CloudStation/KORPUS/generic_"+TRCORPUS+".model"

GEN_FOLDER_BASE = "/Users/agil/Downloads/_corpus/"
GEN_FOLDER = GEN_FOLDER_BASE+TRCORPUS+"/"

numIter=0


# read the generic corpus docs
listGeneric = []
if not os.path.exists(GEN_FOLDER):
	print(GEN_FOLDER, "not found!")
	quit()
else:
	listGeneric = glob.glob(GEN_FOLDER+"*.txt")	# Get all .txt files in the generic training corpus



# build the tags
dictTags = {}
for idx1,doc in enumerate(listGeneric):
	dictTags[doc] = [idx1]



class MyCorpusGen():
	def __init__(self):
		print("MyCorpusGen init")
		return


	def __iter__(self):
		global numIter

		print("MyCorpusGen iteration", numIter)
		numIter = numIter + 1

		startTime = datetime.now()
		for i,file in enumerate(listGeneric):
			if (i % 100) == 0:
				print(i, end=' ', flush=True)

			with codecs.open(file, 'r', encoding='utf-8', errors='ignore') as fdata:
				text = fdata.read()
				# remove stopwords
				cText = Gensim_remove_stopwords(text)
				# preprocess the text (tokenize, lower, remove punctuation, remove <2 and >50 length words)
				wordsText = simple_preprocess(cText, max_len=50)
				# feed the caller
				yield TaggedDocument(words=wordsText, tags=dictTags[file])

		endTime = datetime.now()
		elapsedTime = endTime - startTime
		print(" Duración:", elapsedTime.seconds)




# D2V training hyperparameters
vector_size = 200	# vector_size (int, optional) – Dimensionality of the feature vectors
window = 5	# window (int, optional) – The maximum distance between the current and predicted word within a sentence
alpha = 0.025	# alpha (float, optional) – The initial learning rate
min_alpha = 0.00025	# min_alpha (float, optional) – Learning rate will linearly drop to min_alpha as training progresses
# seed = 1 # Seed for the random number generator. Initial vectors for each word are seeded with a hash of the concatenation of word + str(seed)
min_count = 5	# min_count (int, optional) – Ignores all words with total frequency lower than this
max_vocab_size = None	# max_vocab_size (int, optional) – Limits the RAM during vocabulary building
distributed_memory = 0	# Defines the training algorithm. If dm=1, ‘distributed memory’ (PV-DM). Otherwise, distributed bag of words (PV-DBOW)
epochs1 = 10	# epochs (int, optional) – Number of iterations (epochs) over the corpus
epochs2 = 500

print("Vamos a crear la fuente del corpus")
corpus_data_gen = MyCorpusGen()


print("\nVamos con la red")
model = Doc2Vec(vector_size=vector_size, window=window, alpha=alpha, min_alpha=min_alpha, min_count=min_count, dm=distributed_memory)
print("Vamos a construir el vocabulario")
#model.build_vocab(corpus_data_both)
model.build_vocab(corpus_data_gen)

numIter=0
print("Vamos a entrenar con epochs=", epochs1," y vector size=", vector_size)
model.train(corpus_data_gen, total_examples=model.corpus_count, start_alpha=alpha, end_alpha=min_alpha, epochs=epochs1)  # hay 408 docs txt en el corpus gen
#model.train(corpus_data_ah, total_examples=5035, start_alpha=alpha, end_alpha=min_alpha, epochs=epochs2)  # hay 5035 docs txt en el corpus ah
print("\nTodo bien, guardamos el modelo")
model.save(MODEL_NAME)
print("Terminado", MODEL_NAME, epochs1, "epochs, vector size=", vector_size, " dm=", distributed_memory)
