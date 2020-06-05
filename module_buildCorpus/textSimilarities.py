import time
from datetime import datetime

from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import euclidean_distances
from sklearn.metrics.pairwise import cosine_similarity
import spacy

from smart_open import open as _Open

from aux_build import CORPUS_FOLDER as _CORPUS_FOLDER
from ourSimilarityListsFunctions import ourSimilarityListsFunctions as _ourSimilarityListsFunctions
from aux_build import myTokenizer as _myTokenizer, getWikicatComponents as _getWikicatComponents, NmaxElements as _NmaxElements, NmaxElements3T as _NmaxElements3T
from aux_build import getSubjectComponents as _getSubjectComponents, filterSimpleWikicats as _filterSimpleWikicats, Print as _Print

from px_DB_Manager import getCategoriesInText as _getCategoriesInText
from px_aux import saveFile as _saveFile,  appendFile as _appendFile

from gensim.models.doc2vec import Doc2Vec


class Doc2VecSimilarity():

	def __init__(self, modelName, original_text):
		self.model = Doc2Vec.load(modelName)
		self.original_text_tokens = _myTokenizer(original_text)
		# Generate a vector from the tokenized original text
		self.original_text_inferred_vector = self.model.infer_vector(self.original_text_tokens)

		# Use our basic math functions instead of sklearn's cosine similarity and euclidean distance
		self.ourMeasures = _ourSimilarityListsFunctions()
		return

	# Doc2Vec similarity: Calculate text similarity based on the trained model

	# text or file parameter must be received
	def doc2VecTextSimilarity (self, candidate_text=None, candidate_file=None):

		if not candidate_text:
			candidate_fileFD = _Open(candidate_file, "r")
			candidate_text = candidate_fileFD.read()

		# startTime1 = datetime.now()
		candidate_text_tokens = _myTokenizer(candidate_text)
		# endTime1 = datetime.now()
		# elapsedTime1 = endTime1 - startTime1
		# print("D2V: elapsed1 =", elapsedTime1.microseconds)

		# infer_vector(): Generates a vector from a document
		# The document should be tokenized in the same way the model's training documents were tokenized
		# The function may accept some optional parameters (alpha, min_alpha, epochs, steps)

		# infer_vector(doc_words, alpha=None, min_alpha=None, epochs=None, steps=None)
		# doc_words (list of str) – A document for which the vector representation will be inferred.
		# alpha (float, optional) – The initial learning rate. If unspecified, value from model initialization will be reused.
		# min_alpha (float, optional) – Learning rate will linearly drop to min_alpha over all inference epochs. If unspecified, value from model initialization will be reused.
		# epochs (int, optional) – Number of times to train the new document. Larger values take more time, but may improve quality and run-to-run stability of inferred vectors. If unspecified, the epochs value from model initialization will be reused.
		# steps (int, optional, deprecated) – Previous name for epochs, still available for now for backward compatibility: if epochs is unspecified but steps is, the steps value will be used.

		# Generate a vector from the tokenized candidate text

		# startTime2 = datetime.now()
		candidate_text_inferred_vector = self.model.infer_vector(candidate_text_tokens)
		# endTime2 = datetime.now()
		# elapsedTime2 = endTime2 - startTime2
		# print("D2V: elapsed2 =", elapsedTime2.microseconds)

		# The sklearn math functions returns an array with the results
		# We shall keep only one of them, either sklearn or ourSimilarityListsFunctions

		# Measure vectors similarity using cosine similarity
		# cos_similarity = cosine_similarity([original_text_inferred_vector], [text_inferred_vector])

		# Measure vectors similarity using euclidean distance
		# euc_distance = euclidean_distances([original_text_inferred_vector], [text_inferred_vector])

		# Measure vectors similarity using cosine similarity

		# startTime3 = datetime.now()
		cos_similarity = self.ourMeasures.oCosineSimilarity(self.original_text_inferred_vector, candidate_text_inferred_vector)
		# endTime3 = datetime.now()
		# elapsedTime3 = endTime3 - startTime3
		# print("D2V: elapsed3 =", elapsedTime3.microseconds)


		# Measure vectors similarity using euclidean distance
		# euc_distance = self.ourMeasures.oEuclideanDistance(self.original_text_inferred_vector, candidate_text_inferred_vector)

		# Measure vectors similarity using manhattan distance
		# man_distance = self.ourMeasures.oManhattanDistance(self.original_text_inferred_vector, candidate_text_inferred_vector)

		return cos_similarity





# other similarities

class textSimilarityFunctions():

	# Load the nlp large package for spacy metrics
	# It is better to load it once at the class initialization, to save loading time each time it is used
	nlp = spacy.load('en_core_web_lg')

	def __init__(self, original_text, original_text_wikicats, original_text_subjects, logFilename):
		self.logFilename = logFilename
		self.original_text = original_text
		self.original_text_wikicats = original_text_wikicats
		self.pairs_original_text_wikicats = list(map(lambda x: (x, _getWikicatComponents(x)), original_text_wikicats))
		self.original_text_subjects = original_text_subjects
		self.pairs_original_text_subjects = list(map(lambda x: (x, _getSubjectComponents(x)), original_text_subjects))

		self.measures = _ourSimilarityListsFunctions()   # Create an object from the ourSimilarityListsFunctions class
		return




	#############################################################################################################################################

	# spaCy similarity: Takes two pieces of text and returns the text similarity based on spaCy

	def spacyTextSimilarity (self, candidate_text=None, candidate_file=None):

		def remove_stopwords(text):
			doc = self.nlp(text.lower())
			words = [token.text for token in doc if (token.lemma_ != '-PRON-') and (token.text not in self.nlp.Defaults.stop_words) and (not token.is_punct)]
			return " ".join(words)

		if not candidate_text:
			candidate_fileFD = _Open(candidate_file, "r")
			candidate_text = candidate_fileFD.read()

		# Tokenize original text based on the nlp package
		original_text_tokens = self.nlp(remove_stopwords(self.original_text))  # this could be done only once, at the object creation stage

		# Tokenize candidate text based on the nlp package
		candidate_text_tokens = self.nlp(remove_stopwords(candidate_text))

		# Measure both texts similarity based on spaCy
		spacy_similarity = original_text_tokens.similarity(candidate_text_tokens)

		return spacy_similarity


	#############################################################################################################################################

	# Jaccard text similarity, using ourSimilarityListsFunctions
	# not used, seems not interesting

	def jaccardTextSimilarity (self, candidate_text):

		original_text_tokens = _myTokenizer(original_text)
		candidate_text_tokens = _myTokenizer(candidate_text)

		jaccard_similarity = self.measures.oJaccardSimilarity(original_text_tokens, candidate_text_tokens)

		return jaccard_similarity


	#############################################################################################################################################

	# Euclidean similarity, using SKLEARN

	def euclideanTextSimilarity (self, candidate_text=None, candidate_file=None):

		if not candidate_text:
			candidate_fileFD = _Open(candidate_file, "r")
			candidate_text = candidate_fileFD.read()

		list_of_text = [self.original_text, candidate_text]   # Create a list of documents of the original text and the new candidate text

		vectorizer = CountVectorizer()   # Create a CountVectorizer Object

		# Transform arbitrary data into numerical features
		# Description: remove stopwords, tokenize the text, create a vocabulary from distinct words, map each document to vocabulary (tokens)
		features = vectorizer.fit_transform(list_of_text).todense()

		# Measure the euclidean distance, returns an array with the euclidean distance
		euclideanDistances = euclidean_distances(features[0], features[1])

		euclidean_distance = euclideanDistances[0][0]   # between 0 and N, 0 is the best

		euclidean_similarity = 1 / abs(1 - euclidean_distance) # between 0 and 1, 1 is the best

		return euclidean_similarity


	#############################################################################################################################################

	# Full Wikicats jaccard similarity between the original text and a new one, using ourSimilarityListsFunctions
	# the original text wikicats were received in object creation phase
	# it measures complete matching between wikicats
	def fullWikicatsJaccardSimilarity (self, fileNameCandidateWikicats):

		try:  # try to read candidate text wikicats from local store
			with _Open(fileNameCandidateWikicats) as fp:
				candidate_text_wikicats = fp.read().splitlines()
		except Exception as e:  # fetch candidate text wikicats if not in local store
			_Print("Candidate wikicats file not found in local DB:", fileNameCandidateWikicats)
			_appendFile(self.logFilename, "ERROR fullWikicatsJaccardSimilarity(): Candidate wikicats file not found: "+fileNameCandidateWikicats+" "+str(e))
			return -1

		if len(self.original_text_wikicats) == 0 or len(candidate_text_wikicats) == 0:
			return 0

		wikicats_jaccard_similarity = self.measures.oJaccardSimilarity(self.original_text_wikicats, candidate_text_wikicats)

		return wikicats_jaccard_similarity


#############################################################################################################################################

	# Shared Wikicats similarity between two texts, using ourSimilarityListsFunctions
	# it measures shared matching between wikicats (similarity among components of two wikicat names)
	def sharedWikicatsJaccardSimilarity (self, fileNameCandidateWikicats):

		try:  # try to read candidate text wikicats from local store
			with _Open(fileNameCandidateWikicats) as fp:
				candidate_text_wikicats = fp.read().splitlines()
		except Exception as e:  # fetch candidate text wikicats if not in local store
			_Print("Candidate wikicats file not found in local DB:", fileNameCandidateWikicats)
			_appendFile(self.logFilename, "ERROR sharedWikicatsJaccardSimilarity(): Candidate ikicats file not found: "+fileNameCandidateWikicats+" "+str(e))
			return -1

		if len(candidate_text_wikicats) == 0:
			return 0

		# the wikicats lists for both texts are now available

		try:
			# change every candidate wikicat by the pair (wikicat, list of wikicat components)
			pairs_candidate_text_wikicats = list(map(lambda x: (x, _getWikicatComponents(x)), candidate_text_wikicats))

			num=0
			sum_sims = 0
			for (wko,wkocl) in self.pairs_original_text_wikicats:
				for (wkc,wkccl) in pairs_candidate_text_wikicats:
					intersection_cardinality = len(set.intersection(set(wkocl), set(wkccl)))
					if intersection_cardinality < 2:
						continue
					else:
						union_cardinality = len(set.union(set(wkocl), set(wkocl)))
						components_jaccard_similarity = intersection_cardinality/float(union_cardinality)
						#components_jaccard_similarity = self.measures.oJaccardSimilarity(wkocl, wkccl)
						sum_sims += components_jaccard_similarity
					# if components_jaccard_similarity > 0 and intersection_cardinality == 1:
					# 	num += 1
					# 	print(num, "->", wko, ",", wkc, components_jaccard_similarity)

			denominator = len(self.original_text_wikicats) * len(candidate_text_wikicats)

			if denominator == 0:  # possible?
				return -1
			else:
				wikicats_jaccard_similarity = sum_sims / denominator
		except Exception as e:
			_appendFile(self.logFilename, "ERROR sharedWikicatsJaccardSimilarity(): Exception while computing Jaccard wikicats similarity: "+str(e))
			return -1

		if wikicats_jaccard_similarity > 1:
			_Print("Candidate with wikicats similarity > 1:", fileNameCandidateWikicats, sum_sims, denominator, wikicats_jaccard_similarity)
			_appendFile(self.logFilename, "ERROR sharedWikicatsJaccardSimilarity(): similarity > 1")
			return -1

		return wikicats_jaccard_similarity




	# Shared subjects similarity between two texts, using ourSimilarityListsFunctions
	# it measures shared matching between subjects (similarity among components of subject names)
	def sharedSubjectsJaccardSimilarity (self, fileNameCandidateSubjects):

		try:  # try to read candidate text subjects from local store
			with _Open(fileNameCandidateSubjects) as fp:
				candidate_text_subjects = fp.read().splitlines()
		except Exception as e:  # fetch candidate text subjects if not in local store
			_Print("Candidate subjects file not found in local DB:", fileNameCandidateSubjects)
			_appendFile(self.logFilename, "ERROR sharedSubjectsJaccardSimilarity(): subjects file not available: "+fileNameCandidateSubjects+" "+str(e))
			return -1

		if len(candidate_text_subjects) == 0:
			return 0

		# the subjects lists for both texts are now available

		try:
			# change every candidate subject by the pair (subject, list of subject components)
			pairs_candidate_text_subjects = list(map(lambda x: (x, _getSubjectComponents(x)), candidate_text_subjects))

			sum_sims = 0
			for (wko,wkocl) in self.pairs_original_text_subjects:
				for (wkc,wkccl) in pairs_candidate_text_subjects:
					components_jaccard_similarity = self.measures.oJaccardSimilarity(wkocl, wkccl)
					sum_sims += components_jaccard_similarity

			denominator = len(self.original_text_subjects) * len(candidate_text_subjects)

			if denominator == 0:   # possible?
				return -1
			else:
				subjects_jaccard_similarity = sum_sims / denominator
		except Exception as e:
			_appendFile(self.logFilename, "ERROR sharedSubjectsJaccardSimilarity(): Exception while computing Jaccard subjects similarity: "+str(e))
			return -1

		if subjects_jaccard_similarity > 1:
			_Print("Candidate with subjects similarity > 1:", fileNameCandidateSubjects, sum_sims, denominator, subjects_jaccard_similarity)
			_appendFile(self.logFilename, "ERROR sharedSubjectsJaccardSimilarity(): similarity > 1")
			return -1

		return subjects_jaccard_similarity
