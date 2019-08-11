import os
from flask import request, jsonify
import shutil
import csv
import nltk
from nltk.tokenize import RegexpTokenizer

import sys
sys.path.append('../')

from px_DB_Manager import getCategoriesInText as _getCategoriesInText
from px_aux import saveFile as _saveFile
	
from aux import CORPUS_FOLDER as _CORPUS_FOLDER, SELECTED_WIKICAT_LIST_FILENAME as _SELECTED_WIKICAT_LIST_FILENAME, URLs_FOLDER as _URLs_FOLDER
from aux import DISCARDED_PAGES_FILENAME as _DISCARDED_PAGES_FILENAME, SCRAPPED_PAGES_FOLDER as _SCRAPPED_PAGES_FOLDER, SCRAPPED_TEXT_PAGES_FOLDER as _SCRAPPED_TEXT_PAGES_FOLDER
from aux import UNRETRIEVED_PAGES_FILENAME as _UNRETRIEVED_PAGES_FILENAME, SIMILARITIES_CSV_FILENAME as _SIMILARITIES_CSV_FILENAME
from aux import LEE_D2V_MODEL as _LEE_D2V_MODEL, OWN_D2V_MODEL as _OWN_D2V_MODEL
	
from pp_routesCorpus import getUrlsWithWikicats as _getUrlsWithWikicats
from pa_scrap import scrapFunctions as _scrapFunctions
from pa_similarities import similarityFunctions as _similarityFunctions


#############################################################################################################################################


# Tokenize text, and returns a list of words after removing the stopwords
def tokenizer(text):

	# Create a tokenizer
	tokenizer = RegexpTokenizer('\w+')

	# Tokinize text
	tokens = tokenizer.tokenize(text)

	# Initialize a list for text words
	text_words = []


	# Loop through list tokens, change words to lower case, and append to words list
	for word in tokens:
		text_words.append(word.lower())


	# Get English stopwords from the NLTK (Natural Language Toolkit)
	nltk_stopwords = nltk.corpus.stopwords.words('english')

	# Initialize a new words list, to store words after removing the stopwords
	words_filtered = []

	# Append to words_filtered list all words that are in text_words but not in nltk_stopwords
	for word in text_words:
		if word not in nltk_stopwords:
			words_filtered.append(word)


	return words_filtered


#############################################################################################################################################


# Measures wikicats and subjects similarity
def measureWikicatsAndSubjectsSimilarity(original_text, corpus_text):
	original_text_categories = _getCategoriesInText(original_text)
	corpus_text_categories = _getCategoriesInText(corpus_text)

	try:
		original_text_wikicats = original_text_categories["wikicats"]
	except Exception as e:
		original_text_wikicats = []

	try:
		corpus_text_wikicats = corpus_text_categories["wikicats"]
	except Exception as e:
		# In case of long text, the function _getCategoriesInText returns an error.
		# (length exceeds capacity limit)
		# In this case, the similarity will be equal to zero
		corpus_text_wikicats = []


	try:
		original_text_subjects = original_text_categories["subjects"]
	except Exception as e:
		original_text_subjects = []

	try:
		corpus_text_subjects = corpus_text_categories["subjects"]
	except Exception as e:
		# In case of long text, the function _getCategoriesInText returns an error.
		# In this case, the similarity will be equal to zero
		corpus_text_subjects = []


	# Create a similarity object
	similarity = _similarityFunctions()

	if original_text_wikicats == []:
		wikicats_jaccard_similarity = 0
	else:
		wikicats_jaccard_similarity = similarity.jaccardSimilarity(original_text_wikicats, corpus_text_wikicats)

	if corpus_text_subjects == []:
		subjects_jaccard_similarity = 0
	else:
		subjects_jaccard_similarity = similarity.jaccardSimilarity(original_text_subjects, corpus_text_subjects)

	return wikicats_jaccard_similarity, subjects_jaccard_similarity


#############################################################################################################################################


# to attend the query to build the corpus (/buildCorpus)
# receives: the list of selected wikicats
# returns: the results, mainly the number of files identified for each wikicat
def buildCorpus2():
	import json

	selectedWikicats = json.loads(request.values.get("wikicats"))
	print(len(selectedWikicats), "wikicats")
	numUrlsDB = 0
	numUrlsWK = 0


	# stores the selected wikicats in the file CORPUS_FOLDER/SELECTED_WIKICAT_LIST_FILENAME
	content = ""
	for w in selectedWikicats:
		content += w+"\n"
	_saveFile(_CORPUS_FOLDER+"/"+_SELECTED_WIKICAT_LIST_FILENAME, content)

	# get the information about all the wikicats
	urlsObjects = _getUrlsWithWikicats(selectedWikicats)
	print("\n\nReceived result for all the queries\n")

	result = {}
	fullList = [] # to agregate the full list of URLs

	if not os.path.exists(_URLs_FOLDER):
		os.makedirs(_URLs_FOLDER)
		
	# process all results to return
	for wikicat in selectedWikicats:
		# first, the results from DB
		content = ""
		dbUrls = urlsObjects[wikicat]["db"]
		fullList.extend(dbUrls)
		numUrlsDB += len(dbUrls)
		for url in dbUrls:
			content += url+"\n"
		_saveFile(_URLs_FOLDER+"/_Wikicat_"+wikicat+"_DB_Urls.txt", content)  # save all results from DB

		# now, the results from WK
		content = ""
		wkUrls = urlsObjects[wikicat]["wk"]
		fullList.extend(wkUrls)
		numUrlsWK += len(wkUrls)
		for url in wkUrls:
			content += url+"\n"
		_saveFile(_URLs_FOLDER+"/_Wikicat_"+wikicat+"_WK_Urls.txt", content) # save all results from WK

		longs1 = "(" + str(len(dbUrls)) + "," + str(len(wkUrls)) + ")"
		print(wikicat, longs1, end=', ')
		result[wikicat] = {"db": len(dbUrls), "wk": len(wkUrls)}  # add results for this wikicat

	listWithoutDuplicates = list(set(fullList))  # remove duplicates URLs
	print("\n", numUrlsDB, numUrlsWK, len(listWithoutDuplicates))
	# returns number of results
	result["totalDB"] = numUrlsDB
	result["totalWK"] = numUrlsWK
	result["totalUrls"] = len(listWithoutDuplicates)

	texto = request.values.get("text")

	# A list of the original text tokens
	original_text_tokens = tokenizer(texto)

	# Create a new csv file if it does not exists
	with open(_SIMILARITIES_CSV_FILENAME, 'w+') as writeFile:
		# Name columns
		fieldnames = ['Page Title', 'URL', 'Jaccard Similarity', 'Euclidean Distance', 'Spacy', 'Doc2Vec Euclidean Distance',
		'Doc2Vec Cosine Similarity', 'Trained Doc2Vec Euclidean Distance', 'Trained Doc2Vec Cosine Similarity',
		'Wikicats Jaccard Similarity', 'Subjects Jaccard Similarity']

		# Create csv headers
		writer = csv.DictWriter(writeFile, fieldnames=fieldnames, delimiter=";")

		# Write the column headers
		writer.writeheader()


	overwriteCorpus = json.loads(request.values.get("overwriteCorpus"))

	if overwriteCorpus:
		shutil.rmtree(_SCRAPPED_TEXT_PAGES_FOLDER)

	if not os.path.exists(_SCRAPPED_TEXT_PAGES_FOLDER):
		os.makedirs(_SCRAPPED_TEXT_PAGES_FOLDER)


	# Initialize a list to save discarded pages' URLs
	discarded_list = []

	# Create a new file and overwrite if another already exists
	discarded_list_page = open(_DISCARDED_PAGES_FILENAME, "w+")

	# Create a list of unsuccessful pages retrieval
	unretrieved_pages = []


	# Create a similarity object
	similarity = _similarityFunctions()


	# Scrap pages, Measure text similarity, and save pages with a minimum similarity
	for page in listWithoutDuplicates:
		scrap = _scrapFunctions()

		# Retrieves the page title and the scraped page content
		try:
			pageName, pageContent = scrap.scrapPage(page)
			print(pageName)

		except Exception as e:
			print(e)
			unretrieved_pages.append(page)
			continue


		# Add file extension for saving pages
		fileName = pageName + ".txt"

		# Perform the similarity check on the text before saving it
		# Compare texto with pageContent

		# Tokenize corpus text
		corpus_text_tokens = tokenizer(pageContent)

		# Send the initial text tokens and the scrapped page text tokens to measure the jaccard similarity
		jaccard_similarity = similarity.jaccardSimilarity(original_text_tokens, corpus_text_tokens)
		print("Jaccard similarity = "+str(jaccard_similarity))

		# Measure text similarity based on a doc2vec model
		doc2vec_cosineSimilarity, doc2vec_euclideanDistance = similarity.doc2VecSimilarity(original_text_tokens, corpus_text_tokens, _LEE_D2V_MODEL)
		print("Doc2Vec CS = "+str(doc2vec_cosineSimilarity))
		print("Doc2Vec ED = "+str(doc2vec_euclideanDistance))

		# Measure text similarity based on the trained doc2vec model with our training corpus
		doc2vec_trained_cosineSimilarity, doc2vec_trained_euclideanDistance = similarity.doc2VecSimilarity(original_text_tokens, corpus_text_tokens, _OWN_D2V_MODEL)
		print("Trained Doc2Vec CS = "+str(doc2vec_trained_cosineSimilarity))
		print("Trained Doc2Vec ED = "+str(doc2vec_trained_euclideanDistance))

		# Measure the euclidean distance
		euclidean_distance = similarity.euclideanDistance(texto, pageContent)
		print("Euclidean distance = "+str(euclidean_distance))

		# Measure the euclidean distance
		spacy_similarity = similarity.spacySimilarity(texto, pageContent)
		print("Spacy similarity = "+str(spacy_similarity))


		# Measure wikicats similarity
		wikicats_jaccard_similarity, subjects_jaccard_similarity = measureWikicatsAndSubjectsSimilarity(texto, pageContent)
		print("Wikicats jaccard similarity = "+str(wikicats_jaccard_similarity))
		print("Subjects jaccard similarity = "+str(subjects_jaccard_similarity))


		# Save similarity to a CSV file
		with open(_SIMILARITIES_CSV_FILENAME, 'a') as writeFile:
			writer = csv.writer(writeFile, delimiter=';')
			writer.writerow([pageName, page, jaccard_similarity, euclidean_distance, spacy_similarity, doc2vec_euclideanDistance,
			doc2vec_cosineSimilarity, doc2vec_trained_euclideanDistance, doc2vec_trained_cosineSimilarity, wikicats_jaccard_similarity,
			subjects_jaccard_similarity])


		# Minimum similarity for a page to be accepted by a jaccard similarity
		min_jaccard_similarity = 0.04

		# Minimum doc2vec similarity or Maximum distance
		# I'm not sure yet about it

		# Filter pages with at least s similarity
		if(jaccard_similarity >= min_jaccard_similarity):
			print("page accepted\n")

			# Save to text file
			_saveFile(_SCRAPPED_TEXT_PAGES_FOLDER+"/"+fileName, pageContent)
		else:
			print("page discarded\n")

			# Save URL to discarded list
			discarded_list.append(page)

			discarded_list_page = open(_DISCARDED_PAGES_FILENAME, "a")
			discarded_list_page.write(page+"\n")


	discarded_list_page.close()
	print(str(len(discarded_list)) + " discarded pages")

	# Save the unretrieved_pages list to a file
	print(str(len(unretrieved_pages)) + " unretrieved pages")
	_saveFile(_UNRETRIEVED_PAGES_FILENAME, str(unretrieved_pages))


	return jsonify(result);
