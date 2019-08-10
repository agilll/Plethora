from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import euclidean_distances
from sklearn.metrics.pairwise import cosine_similarity

# To install: pip install spacy
import spacy

from gensim.models.doc2vec import Doc2Vec

# Used basic math functions instead of sklearn's cosine similarity and euclidean distance
from pa_mathSimilarities import mathSimilarity as _mathSimilarity


class similarityFunctions():

	#############################################################################################################################################

	# spaCy similarity

	# Download NLP English pre-trained statistical models

	# To download the core small package:
	# Description: English multi-task CNN trained on OntoNotes. Assigns context-specific token vectors, POS tags, dependency parse and named entities
	# python -m spacy download en_core_web_sm

	# To download the core medium package:
	# Description: English multi-task CNN trained on OntoNotes, with GloVe vectors trained on Common Crawl. Assigns word vectors, context-specific token vectors, POS tags, dependency parse and named entities.
	# python -m spacy download en_core_web_md

	# To download the core large package:
	# python -m spacy download en_core_web_lg

	# To download the vectors large package:
	# python -m spacy download en_vectors_web_lg

	# To download the best-matching default model and create shortcut link
	# python -m spacy download en


	# Load the nlp large package
	# It is better to load it once, to save loading time each time
	nlp = spacy.load('en_core_web_lg')


	# Takes two pieces of text and returns the text similarity based on spaCy
	def spacySimilarity(self, original_text, corpus_text):

		# Tokenize original text based on the nlp package
		original_text_tokens = self.nlp(original_text)

		# Tokenize corpus text based on the nlp package
		corpus_text_tokens = self.nlp(corpus_text)

		# Measure the text similarity based on spaCy
		spacy_similarity = original_text_tokens.similarity(corpus_text_tokens)

		return spacy_similarity


	#############################################################################################################################################


	# Doc2Vec similarity

	# Calculate text similarity based on the trained model
	def doc2VecSimilarity(self, original_text_tokens, corpus_text_tokens, trained_model):
		# Load the model
		model = Doc2Vec.load(trained_model)

		# infer_vector(): Generates a vector from a document
		# The document should be tokinized in the same way the model's training documents was tokinized
		# The function may accept some optional parameters (alpha, min_alpha, epochs, steps)

		# infer_vector(doc_words, alpha=None, min_alpha=None, epochs=None, steps=None)
		# doc_words (list of str) – A document for which the vector representation will be inferred.
		# alpha (float, optional) – The initial learning rate. If unspecified, value from model initialization will be reused.
		# min_alpha (float, optional) – Learning rate will linearly drop to min_alpha over all inference epochs. If unspecified, value from model initialization will be reused.
		# epochs (int, optional) – Number of times to train the new document. Larger values take more time, but may improve quality and run-to-run stability of inferred vectors. If unspecified, the epochs value from model initialization will be reused.
		# steps (int, optional, deprecated) – Previous name for epochs, still available for now for backward compatibility: if epochs is unspecified but steps is, the steps value will be used.

		# Generate a vector given from the tokenized original text
		original_text_inferred_vector = model.infer_vector(original_text_tokens)

		# Generate a vector given from the tokenized corpus text
		corpus_text_inferred_vector = model.infer_vector(corpus_text_tokens)


		# The sklearn math functions returns an array with the results
		# We shall keep only one of them, either sklearn or pa_mathSimilarities

		# Measure vectors similarity using cosine similarity
		# cos_similarity = cosine_similarity([original_text_inferred_vector], [corpus_text_inferred_vector])

		# Measure vectors similarity using euclidean distance
		# euc_distance = euclidean_distances([original_text_inferred_vector], [corpus_text_inferred_vector])

		# Create an object from the mathSimilarity class
		measures = _mathSimilarity()

		# Measure vectors similarity using cosine similarity
		cos_similarity = measures.cosine_similarity(original_text_inferred_vector, corpus_text_inferred_vector)

		# Measure vectors similarity using euclidean distance
		euc_distance = measures.euclidean_distance(original_text_inferred_vector, corpus_text_inferred_vector)

		# Measure vectors similarity using manhattan distance
		man_distance = measures.manhattan_distance(original_text_inferred_vector, corpus_text_inferred_vector)


		return(cos_similarity, euc_distance)


	#############################################################################################################################################


	# Jaccard similarity
	def jaccardSimilarity(self, original_text_tokens, corpus_text_tokens):

		# Convert text lists to sets to remove dublicates
		original_text_tokens_set = set(original_text_tokens)
		corpus_text_tokens_set = set(corpus_text_tokens)

		# Calculate similarity
		jaccard_similarity = len(original_text_tokens_set.intersection(corpus_text_tokens_set)) / len(original_text_tokens_set.union(corpus_text_tokens_set))

		return jaccard_similarity


	#############################################################################################################################################


	# Euclidean distance
	def euclideanDistance(self, original_text, corpus_text):

		# Create a list of documents of the original text and corpus text
		list_of_text = [original_text, corpus_text]

		# Create a CountVectorizer Object
		vectorizer = CountVectorizer()

		# Transform arbitrary data into numerical features
		# Description: remove stopwords, tokenize the text, create a vocabulary from distinct words, map each document to vocabulary (tokens)
		features = vectorizer.fit_transform(list_of_text).todense()

		# Measure the euclidean distance, returns an array wih the euclidean distance
		euclidean_distance = euclidean_distances(features[0], features[1])

		return euclidean_distance[0][0]


	#############################################################################################################################################
