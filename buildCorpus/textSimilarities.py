import time

from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import euclidean_distances
from sklearn.metrics.pairwise import cosine_similarity
import spacy

from smart_open import open as _Open

from aux import CORPUS_FOLDER as _CORPUS_FOLDER
from ourSimilarityListsFunctions import ourSimilarityListsFunctions as _ourSimilarityListsFunctions
from aux import myTokenizer as _myTokenizer, getWikicatComponents as _getWikicatComponents, NmaxElements as _NmaxElements, NmaxElements3T as _NmaxElements3T
from aux import filterSimpleWikicats as _filterSimpleWikicats

from px_DB_Manager import getCategoriesInText as _getCategoriesInText
from px_aux import saveFile as _saveFile
		
class textSimilarityFunctions():
	
	pause = 4   # to sleep after querying DBpedia, to avoid reject by too many queries
	delay = 10
	
	# Load the nlp large package for spacy metrics
	# It is better to load it once at the class initialization, to save loading time each time it is used
	nlp = spacy.load('en_core_web_lg')
	
	measures = _ourSimilarityListsFunctions()   # Create an object from the ourSimilarityListsFunctions class


	#############################################################################################################################################
	
	# spaCy similarity:    Takes two pieces of text and returns the text similarity based on spaCy
	
	def spacyTextSimilarity (self, original_text, candidate_text):
		
		# Tokenize original text based on the nlp package
		original_text_tokens = self.nlp(original_text)

		# Tokenize candidate text based on the nlp package
		candidate_text_tokens = self.nlp(candidate_text)

		# Measure both texts similarity based on spaCy
		spacy_similarity = original_text_tokens.similarity(candidate_text_tokens)

		return spacy_similarity

	#############################################################################################################################################

	# Doc2Vec similarity: Calculate text similarity based on the trained model
	
	def doc2VecTextSimilarity (self, original_text, candidate_text, trained_model):
		from gensim.models.doc2vec import Doc2Vec

		original_text_tokens = _myTokenizer(original_text)
		candidate_text_tokens = _myTokenizer(candidate_text)

		# Load the model
		model = Doc2Vec.load(trained_model)

		# infer_vector(): Generates a vector from a document
		# The document should be tokenized in the same way the model's training documents were tokenized
		# The function may accept some optional parameters (alpha, min_alpha, epochs, steps)

		# infer_vector(doc_words, alpha=None, min_alpha=None, epochs=None, steps=None)
		# doc_words (list of str) – A document for which the vector representation will be inferred.
		# alpha (float, optional) – The initial learning rate. If unspecified, value from model initialization will be reused.
		# min_alpha (float, optional) – Learning rate will linearly drop to min_alpha over all inference epochs. If unspecified, value from model initialization will be reused.
		# epochs (int, optional) – Number of times to train the new document. Larger values take more time, but may improve quality and run-to-run stability of inferred vectors. If unspecified, the epochs value from model initialization will be reused.
		# steps (int, optional, deprecated) – Previous name for epochs, still available for now for backward compatibility: if epochs is unspecified but steps is, the steps value will be used.

		# Generate a vector from the tokenized original text
		original_text_inferred_vector = model.infer_vector(original_text_tokens)

		# Generate a vector from the tokenized text
		candidate_text_inferred_vector = model.infer_vector(candidate_text_tokens)

		# The sklearn math functions returns an array with the results
		# We shall keep only one of them, either sklearn or ourSimilarityListsFunctions

		# Measure vectors similarity using cosine similarity
		# cos_similarity = cosine_similarity([original_text_inferred_vector], [text_inferred_vector])

		# Measure vectors similarity using euclidean distance
		# euc_distance = euclidean_distances([original_text_inferred_vector], [text_inferred_vector])

		# Used our basic math functions instead of sklearn's cosine similarity and euclidean distance
		self.measures = _ourSimilarityListsFunctions()   # Create an object from the ourSimilarityListsFunctions class

		# Measure vectors similarity using cosine similarity
		cos_similarity = self.measures.oCosineSimilarity(original_text_inferred_vector, candidate_text_inferred_vector)

		# Measure vectors similarity using euclidean distance
		euc_distance = self.measures.oEuclideanDistance(original_text_inferred_vector, candidate_text_inferred_vector)

		# Measure vectors similarity using manhattan distance
		man_distance = self.measures.oManhattanDistance(original_text_inferred_vector, candidate_text_inferred_vector)

		return (cos_similarity, euc_distance)

	#############################################################################################################################################

	# Jaccard similarity, using ourSimilarityListsFunctions
	
	def jaccardTextSimilarity (self, original_text, candidate_text):
		
		original_text_tokens = _myTokenizer(original_text)
		candidate_text_tokens = _myTokenizer(candidate_text)
		
		jaccard_similarity = self.measures.oJaccardSimilarity(original_text_tokens, candidate_text_tokens)
		
		return jaccard_similarity

	#############################################################################################################################################

	# Euclidean similarity, using SKLEARN
	
	def euclideanTextSimilarity (self, original_text, candidate_text):

		list_of_text = [original_text, candidate_text]   # Create a list of documents of the original text and the new candidate text

		vectorizer = CountVectorizer()   # Create a CountVectorizer Object

		# Transform arbitrary data into numerical features
		# Description: remove stopwords, tokenize the text, create a vocabulary from distinct words, map each document to vocabulary (tokens)
		features = vectorizer.fit_transform(list_of_text).todense()

		# Measure the euclidean distance, returns an array with the euclidean distance
		euclidean_distance = euclidean_distances(features[0], features[1])

		return euclidean_distance[0][0]

	#############################################################################################################################################

	# Full Wikicats and subjects similarity between two texts, using ourSimilarityListsFunctions
	# it measures complete matching between wikicats/subjects
	def fullWikicatsAndSubjectsSimilarity (self, original_text, candidate_text):
		original_text_categories = _getCategoriesInText(original_text)
		candidate_text_categories = _getCategoriesInText(candidate_text)
	
		try:
			original_text_wikicats = original_text_categories["wikicats"]
		except Exception as e:
			original_text_wikicats = []
	
		try:
			candidate_text_wikicats = candidate_text_categories["wikicats"]
		except Exception as e:
			# In case of long text, the function _getCategoriesInText returns an error  (length exceeds capacity limit)
			# In this case, the similarity will be equal to zero
			candidate_text_wikicats = []
	
	
		try:
			original_text_subjects = original_text_categories["subjects"]
		except Exception as e:
			original_text_subjects = []
	
		try:
			candidate_text_subjects = candidate_text_categories["subjects"]
		except Exception as e:
			# In case of long text, the function _getCategoriesInText returns an error.
			# In this case, the similarity will be equal to zero
			candidate_text_subjects = []
	
	
		if original_text_wikicats == []:
			wikicats_jaccard_similarity = 0
		else:
			wikicats_jaccard_similarity = self.measures.oJaccardSimilarity(original_text_wikicats, candidate_text_wikicats)
	
		if candidate_text_subjects == []:
			subjects_jaccard_similarity = 0
		else:
			subjects_jaccard_similarity = self.measures.oJaccardSimilarity(original_text_subjects, candidate_text_subjects)
	
		return wikicats_jaccard_similarity, subjects_jaccard_similarity


#############################################################################################################################################

	# Shared Wikicats similarity between two texts, using ourSimilarityListsFunctions
	# it measures shared matching between wikicats (similarity among components of wikicat name)
	def sharedWikicatsSimilarity (self, original_text, fileNameOriginalWikicats, candidate_text, fileNameCandidateWikicats):
				
		try:  # try to read original text wikicats from local store
			with _Open(fileNameOriginalWikicats) as fp:
				original_text_wikicats = fp.read().splitlines()
				print("File already available:", fileNameOriginalWikicats)
		except:  # fetch original text wikicats if not in local store
			original_text_categories = _getCategoriesInText(original_text)  # function _getCategoriesInText from px_DB_Manager
			
			if ("error" in original_text_categories):
				print("\nError in _getCategoriesInText(original_text):", original_text_categories["error"])
				return 0
			
			print("Wikicats downloaded for", fileNameOriginalWikicats)
			original_text_wikicats = list(filter(_filterSimpleWikicats, original_text_categories["wikicats"])) # remove simple wikicats with function located above
			
			content = ""    # create one line per wikicat to save in wikicats file
			for w in original_text_wikicats:
				content += w+"\n"
			
			_saveFile(fileNameOriginalWikicats, content)  # save file with original text wikicats
		
		try:  # try to read candidate text wikicats from local store
			with _Open(fileNameCandidateWikicats) as fp:
				candidate_text_wikicats = fp.read().splitlines()
				print("File already available:", fileNameCandidateWikicats)
		except:  # fetch candidate text wikicats if not in local store
			candidate_text_categories = _getCategoriesInText(candidate_text)  # function _getCategoriesInText from px_DB_Manager
			
			if ("error" in candidate_text_categories):
				print("\nError in _getCategoriesInText(candidate_text):", candidate_text_categories["error"])
				self.pause += 1
				self.delay += 5
				time.sleep(self.delay)
				return 0
			
			if self.pause > 4:
				self.pause -= 1
			
			if self.delay > 10:
				self.delay -= 5
				
			print("Wikicats downloaded for", fileNameCandidateWikicats)
			candidate_text_wikicats = list(filter(_filterSimpleWikicats, candidate_text_categories["wikicats"])) # remove simple wikicats with function located above
			
			content = ""    # create one line per wikicat to save in wikicats file
			for w in candidate_text_wikicats:
				content += w+"\n"
			
			_saveFile(fileNameCandidateWikicats, content)  # save file with original text wikicats
			time.sleep(self.pause)
			
			
		
		try:
			# change every original wikicat by the pair (wikicat, list of wikicat components)    NONSENSE to compute this every time
			original_text_wikicats = list(map(lambda x: (x, _getWikicatComponents(x)), original_text_wikicats))
				
			# change every candidate wikicat by the pair (wikicat, list of wikicat components)
			candidate_text_wikicats = list(map(lambda x: (x, _getWikicatComponents(x)), candidate_text_wikicats))
						
			sims = []
			for (wko,wkocl) in original_text_wikicats:
				for (wkc,wkccl) in candidate_text_wikicats:		
					wkc_jaccard_similarity = self.measures.oJaccardSimilarity(wkocl, wkccl)
					sims.append((wko, wkc, wkc_jaccard_similarity))
			
			N=10
			greatests = _NmaxElements3T(sims, N)
			greatests_nums = list(map(lambda x: x[2], greatests))
			
			if len(greatests_nums) == 0:
				wikicats_jaccard_similarity =0
			else:
				wikicats_jaccard_similarity = sum(greatests_nums) / len(greatests_nums)
		except Exception as e:
			print("Exception while computing Jaccard wikicats similarity in sharedWikicatsSimilarity:", e)
			exit()
			wikicats_jaccard_similarity = 0
			
		return wikicats_jaccard_similarity
		
		
	# CURRENTLY NOT USED	
	# Shared subjects similarity between two texts, using ourSimilarityListsFunctions
	# it measures shared matching between subjects (similarity among components of subject name)
	def sharedSubjectsSimilarity (self, original_text, candidate_text):
		
		len_orig_text = len(original_text)
		filename_sb = _CORPUS_FOLDER+"/"+str(len_orig_text)+"_sb.txt"
		
		try:  # try to read original text subjects from local store
			with _Open(filename_sb) as fp:
				original_text_subjects = fp.read().splitlines()
		except:  # fetch subjects if not in local store
			original_text_categories = _getCategoriesInText(original_text)  # function _getCategoriesInText from px_DB_Manager
			
			if ("error" in original_text_categories):
				print("\nError in _getCategoriesInText(original_text):", original_text_categories["error"])
				return 0
			
			original_text_subjects = original_text_categories["subjects"]
			
		candidate_text_categories = _getCategoriesInText(candidate_text)    # STORE LOCAL
		if ("error" in candidate_text_categories):
			print("\nError in _getCategoriesInText(candidate_text):", candidate_text_categories["error"])
			return 0
		
		candidate_text_subjects = candidate_text_categories["subjects"]
		
		try:
			# change every original subject by the pair (subject, list of subject components)    NONSENSE to compute this every time
			original_text_subjects = list(map(lambda x: (x, _getWikicatComponents(x)), original_text_subjects))
				
			# change every candidate subject by the pair (subject, list of subject components)
			candidate_text_subjects = list(map(lambda x: (x, _getWikicatComponents(x)), candidate_text_subjects))
			
			sims = []
			for (sbo,sbocl) in original_text_subjects:
				for (sbc,sbccl) in candidate_text_subjects:		
					sbc_jaccard_similarity = self.measures.oJaccardSimilarity(sbocl, sbccl)
					sims.append((sbo, sbc, sbc_jaccard_similarity))
			
			N=10
			greatests = _NmaxElements3T(sims, N)
			greatests_nums = list(map(lambda x: x[2], greatests))
				
			subjects_jaccard_similarity = sum(greatests_nums) / len(greatests_nums)
		except Exception as e:
			print("Exception while computing Jaccard subjects similarity in sharedSubjectsSimilarity:", e)
			subjects_jaccard_similarity = 0
			
		
		return subjects_jaccard_similarity

