# training with .t files (preprocessed .txt files)
# a .t file contains a binary structure (pickle saved): a list of lists of words (already lemmas). That is, tokenization has already been done

import os
import glob
from gensim.models.doc2vec import Doc2Vec, TaggedDocument
import pickle


# A function to build a model based on Doc2Vec, trained by our own training .t documents
def buildDoc2VecModel(tfiles_folder, model_name, vector_size, window, alpha, min_alpha, min_count, distributed_memory, epochs):

	if not os.path.exists(tfiles_folder):
		print(tfiles_folder, "not found!")
		return -1
	
	print("Training with .t files in", tfiles_folder)
	
	training_files = glob.glob(tfiles_folder+"*.t")	# Get all .t files in the training documents folder

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
	
	return 0

