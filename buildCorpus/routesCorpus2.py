import os
import sys
from flask import request, jsonify
import shutil
import csv
from requests_futures.sessions import FuturesSession
import time
import json

from px_DB_Manager import getCategoriesInText as _getCategoriesInText
from px_aux import saveFile as _saveFile, URL_DB as _URL_DB, URL_WK as _URL_WK
from aux import hasFieldPT as _hasFieldPT  # function to check if object has  ["pt"]["value"] field
	
from aux import CORPUS_FOLDER as _CORPUS_FOLDER, SELECTED_WIKICAT_LIST_FILENAME as _SELECTED_WIKICAT_LIST_FILENAME
from aux import URLs_FOLDER as _URLs_FOLDER, DISCARDED_PAGES_FILENAME as _DISCARDED_PAGES_FILENAME,  SCRAPPED_TEXT_PAGES_FOLDER as _SCRAPPED_TEXT_PAGES_FOLDER
from aux import UNRETRIEVED_PAGES_FILENAME as _UNRETRIEVED_PAGES_FILENAME, SIMILARITIES_CSV_FILENAME as _SIMILARITIES_CSV_FILENAME
from aux import LEE_D2V_MODEL as _LEE_D2V_MODEL, OWN_D2V_MODEL as _OWN_D2V_MODEL
	
from scrap import scrapFunctions as _scrapFunctions
from textSimilarities import textSimilarityFunctions as _textSimilarityFunctions


#############################################################################################################################################

# QUERY (/buildCorpus2)  to attend the query to build the corpus
# receives:
# * the list of selected wikicats
# * the original text
# * the flag overwriteCorpus to overwrite or not the current corpus
# returns: the results, mainly the number of files identified for each wikicat
def buildCorpus2():

	selectedWikicats = json.loads(request.values.get("wikicats"))
	print("Number of wikicats:", len(selectedWikicats))
	numUrlsDB = 0
	numUrlsWK = 0


	# stores the selected wikicats in the file $CORPUS_FOLDER/$SELECTED_WIKICAT_LIST_FILENAME
	content = ""
	for w in selectedWikicats:
		content += w+"\n"
	_saveFile(_CORPUS_FOLDER+"/"+_SELECTED_WIKICAT_LIST_FILENAME, content)

	# get the URLs associated to any of those wikicats, with a function that is ahead 
	urlsObjects = getUrlsLinked2Wikicats(selectedWikicats)
	print("\n\nReceived results for all the queries\n")

	result = {}  # object to store the results
	fullList = [] # to aggregate the full list of URLs for all wikicats

	# create folder to store a file per wikicat, with the URLs linked to such wikicat
	if not os.path.exists(_URLs_FOLDER):
		os.makedirs(_URLs_FOLDER)
		
	# process all results to return
	
	print("Number of URLs for every wikicat (DB,WK): ", end='')
	
	for wikicat in selectedWikicats:
		
		# first, the results from DB
		content = ""
		dbUrls = urlsObjects[wikicat]["db"]   # get the set of DB URLs
		numUrlsDB += len(dbUrls)
		for url in dbUrls:
			content += url+"\n"
		_saveFile(_URLs_FOLDER+"/_Wikicat_"+wikicat+"_DB_Urls.txt", content)  # save all results from DB for this wikicat
		fullList.extend(dbUrls)  # add the DB URLs of current wikicat to the whole list
		
		# now, the results from WK
		content = ""
		wkUrls = urlsObjects[wikicat]["wk"]
		numUrlsWK += len(wkUrls)
		for url in wkUrls:
			content += url+"\n"
		_saveFile(_URLs_FOLDER+"/_Wikicat_"+wikicat+"_WK_Urls.txt", content) # save all results from WK for this wikicat
		fullList.extend(wkUrls)

		longs1 = "(" + str(len(dbUrls)) + "," + str(len(wkUrls)) + ")"
		print(wikicat, longs1, end=', ')
		result[wikicat] = {"db": len(dbUrls), "wk": len(wkUrls)}  # add results for this wikicat


	listWithoutDuplicates = list(set(fullList))  # remove duplicates URLs
	print("\nSummary of URLs numbers (DB,WK,total without duplicates):", numUrlsDB, numUrlsWK, len(listWithoutDuplicates))
	
	# returns number of results
	result["totalDB"] = numUrlsDB
	result["totalWK"] = numUrlsWK
	result["totalUrls"] = len(listWithoutDuplicates)
	#return jsonify(result);  # uncomment to modify interface without processing files
	
	# the result are only numbers of URLs
	
	
	
	###  We've got the first set of relevant URLs.
	###  Let's start the analysis of their contents 
	
	originalText = request.values.get("text")

	# Create a new csv file if not exists
	with open(_SIMILARITIES_CSV_FILENAME, 'w+') as writeFile:
		# Name columns
		fieldnames = ['Page Title', 'URL', 'Jaccard Similarity', 'Euclidean Distance', 'Spacy', 'Doc2Vec Euclidean Distance',
		'Doc2Vec Cosine Similarity', 'Trained Doc2Vec Euclidean Distance', 'Trained Doc2Vec Cosine Similarity',
		'Wikicats Jaccard Similarity', 'Subjects Jaccard Similarity']

		# Create csv headers
		writer = csv.DictWriter(writeFile, fieldnames=fieldnames, delimiter=";")

		# Write the column headers
		writer.writeheader()


	overwriteCorpus = json.loads(request.values.get("overwriteCorpus"))  # read the flag overwriteCorpus from request

	if overwriteCorpus:
		shutil.rmtree(_SCRAPPED_TEXT_PAGES_FOLDER)  # if overwriteCorpus, remove current corpus

	if not os.path.exists(_SCRAPPED_TEXT_PAGES_FOLDER):  # create new corpus folder if necessary
		os.makedirs(_SCRAPPED_TEXT_PAGES_FOLDER)


	unretrieved_pages = []  # a list for unsuccessful pages retrieval
	discarded_list = []     # a list to save discarded pages' URLs

	# Create a new file or overwrite it if another already exists
	discarded_list_page = open(_DISCARDED_PAGES_FILENAME, "w+")

	# Create a textSimilarityFunctions object
	similarity = _textSimilarityFunctions()

	# Scrap pages, Measure text similarity, and save pages with a minimum similarity
	for idx, page in enumerate(listWithoutDuplicates, start=1):
		scrap = _scrapFunctions()

		# Retrieves the page title and the scraped page content
		try:
			pageName, pageContent = scrap.scrapPage(page)
			print(pageName, " (", idx, "of", len(listWithoutDuplicates), ")")
		except Exception as e:
			print(e)
			unretrieved_pages.append(page)
			continue


		# Add file extension for saving pages
		fileName = pageName + ".txt"

		# Perform the similarity check on the text before saving it
		# Compare original text with pageContent

		# Send the initial text tokens and the scrapped page text tokens to measure the jaccard similarity
		jaccard_similarity = similarity.jaccardTextSimilarity(originalText, pageContent)
		print("Jaccard similarity = "+str(jaccard_similarity))

		# Measure text similarity based on a doc2vec model
		doc2vec_cosineSimilarity, doc2vec_euclideanDistance = similarity.doc2VecTextSimilarity(originalText, pageContent, _LEE_D2V_MODEL)
		print("Doc2Vec CS = "+str(doc2vec_cosineSimilarity))
		print("Doc2Vec ED = "+str(doc2vec_euclideanDistance))

		# Measure text similarity based on the trained doc2vec model with our training corpus
		doc2vec_trained_cosineSimilarity, doc2vec_trained_euclideanDistance = similarity.doc2VecTextSimilarity(originalText, pageContent, _OWN_D2V_MODEL)
		print("Trained Doc2Vec CS = "+str(doc2vec_trained_cosineSimilarity))
		print("Trained Doc2Vec ED = "+str(doc2vec_trained_euclideanDistance))

		# Measure the euclidean distance
		euclidean_distance = similarity.euclideanTextSimilarity(originalText, pageContent)
		print("Euclidean distance = "+str(euclidean_distance))

		# Measure the euclidean distance
		spacy_similarity = similarity.spacyTextSimilarity(originalText, pageContent)
		print("Spacy similarity = "+str(spacy_similarity))


		# Measure wikicats similarity
		wikicats_jaccard_similarity, subjects_jaccard_similarity = similarity.WikicatsAndSubjectsSimilarity(originalText, pageContent)
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



#############################################################################################################################################	



# aux function to get all the URLs associated to any wikicat from a set of wikicats
# It queries DB and WK and parses the results
def getUrlsLinked2Wikicats (selectedWikicats):
	requestObjects = {} # to store request objects 
	
	print("Starting queries for: ", end='')
	_session = FuturesSession()  # to manage asynchronous requests 
					
	for wikicat in selectedWikicats:
		print(wikicat, end=' ', flush=True)
		fullWikicat = "Wikicat"+wikicat
	
		# asynchronous query to dbpedia
		queryDB = """
		PREFIX yago: <http://dbpedia.org/class/yago/>
		SELECT ?url ?der ?pt WHERE {
			?url  rdf:type yago:"""+fullWikicat+""" .
			OPTIONAL {?url  prov:wasDerivedFrom ?der}
			OPTIONAL {?url  foaf:isPrimaryTopicOf ?pt}
		}
		"""
		
		# asynchronous query to Wikidata
		queryWK =  """
		PREFIX wikibase: <http://wikiba.se/ontology#>
		PREFIX bd: <http://www.bigdata.com/rdf#>
		PREFIX mwapi: <https://www.mediawiki.org/ontology#API/>
		SELECT * WHERE {
			SERVICE wikibase:mwapi {
				bd:serviceParam wikibase:api 'Search' .
				bd:serviceParam wikibase:endpoint 'en.wikipedia.org' .
				bd:serviceParam mwapi:language "en" .
				bd:serviceParam mwapi:srsearch '"""+wikicat+"""' .
				?title wikibase:apiOutput mwapi:title .
			}
		} 		
		"""
		# start the queries 
		try:
			requestDB = _session.post(_URL_DB, data={"query": queryDB}, headers={"accept": "application/json"})
		except Exception as exc:
			print("\n*** Error querying DB for", wikicat, ":", exc)
			requestDB = None
			
		try:
			requestWK = _session.post(_URL_WK, data={"query": queryWK}, headers={"accept": "application/json"})
		except Exception as exc:
			print("\n***Error querying WK for", wikicat, ":", exc)
			requestWK = None	
		
		requestObjects[wikicat] = {"db": requestDB, "wk": requestWK}  # store the request objects for this wikicat
		time.sleep(4)  # delay to avoid server reject for too many queries
		
	print("\n\nAll queries started\n")
	
	# We now have an object for every wikicat, requestObjects[wikicat] = {"db": requestDB, "wk": requestWK} 
	
	# let's build an object {"db": urlsDB, "wk": urlsWK} for each wikicat (each field is a URL list)
	urlsObjects = {}
	
	# now, read the results received from all queries
	print("Waiting queries' result for: ", end='')
	
	for wikicat in selectedWikicats:
		print(wikicat, end=' ', flush=True)
		requestDB = requestObjects[wikicat]["db"] # get the request objects for this wikicat
		requestWK = requestObjects[wikicat]["wk"]
		
		# first, study results for DB
		
		if requestDB == None:  # error starting query, return []
			print("\n***Error querying DB for", wikicat, ": the query could not be started")
			urlsDB = []
		else:
			try:
				try:
					responseDB = requestDB.result()  # waiting for query completion
				except:
					raise Exception("timeout")
				
				if responseDB.status_code != 200:  # check if query ended correctly
					raise Exception ("answer is not 200, is "+str(responseDB.status_code))
				else:
					try:
						responseDBJson = responseDB.json()
					except:
						raise Exception("error decoding JSON")
					
					try:
						bindingsDB = responseDBJson["results"]["bindings"]
					except:
						raise Exception("no [results][bindings] in the answer")
					
					bindingsDBwithPT = list(filter(_hasFieldPT, bindingsDB)) # remove bindings with no pt field (isPrimaryTopicOf)
					urlsDB = list(map(lambda x: x["pt"]["value"], bindingsDBwithPT))  # keep only the URL in x["pt"]["value"]
			except Exception as exc:
				print("\n***Error querying DB for", wikicat,":", exc)
				urlsDB = []

		# end for DB
		
		# second, study results for WK
		
		# WK results come without prefix "https://en.wikipedia.org/wiki/", this function add it
		def addWKPrefix (x):
			return "https://en.wikipedia.org/wiki/"+x["title"]["value"].replace(" ", "_")
		
		
		if requestWK == None:  # error starting query, return []
			print("\n***Error querying WK for", wikicat, ": the query could not be started")
			urlsWK = []
		else:
			try:
				try:
					responseWK = requestWK.result()  # waiting for query completion
				except:
					raise Exception("timeout")
				
				if responseWK.status_code != 200: # check if query ended correctly
					raise Exception ("answer is not 200, is " + str(responseWK.status_code))
				else:
					try:
						responseWKJson = responseWK.json()
					except:
						raise Exception("error decoding JSON")
					
					try:
						bindingsWK = responseWKJson["results"]["bindings"]
					except:
						raise Exception("no [results][bindings] in the answer")

					urlsWK = list(map(addWKPrefix, bindingsWK))   # add WK prefix to x["title"]["value"], changing space by '_'
	
			except Exception as exc:
				print("\n***Error querying WK for", wikicat,":", exc)
				urlsWK = []

				
		# store results for this wikicat		
		urlsObjects[wikicat] = {"db": urlsDB, "wk": urlsWK}
	
	return urlsObjects  # return results to buildCorpus function
