import os
import sys
from flask import request, jsonify
import shutil
import csv
from requests_futures.sessions import FuturesSession
import time
import json
from smart_open import open as _Open

from px_DB_Manager import getCategoriesInText as _getCategoriesInText
from px_aux import saveFile as _saveFile, URL_DB as _URL_DB, URL_WK as _URL_WK
from aux import hasFieldPT as _hasFieldPT  # function to check if object has  ["pt"]["value"] field
from aux import filterSimpleWikicats as _filterSimpleWikicats	
from aux import CORPUS_FOLDER as _CORPUS_FOLDER
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

	originalText = request.values.get("text")  # get parameter with original text
	len_text = len(originalText)                                   	
	fileNameOriginalWikicats = _CORPUS_FOLDER+"/"+str(len_text)+".wk" # to send to compute wikicats shared jaccard
	
	selectedWikicats = json.loads(request.values.get("wikicats"))   # get parameter with selected wikicats
	print("Number of selected wikicats:", len(selectedWikicats))
	numUrlsDB = 0
	numUrlsWK = 0

	# store the selected wikicats in the file $CORPUS_FOLDER/length.selected.wk
	_saveFile(_CORPUS_FOLDER+"/"+str(len_text)+".selected.wk", '\n'.join(selectedWikicats))

	# create a folder to store a file per wikicat, with the URLs linked to such wikicat
	# it must be done before calling the getUrlsLinked2Wikicats function, that it stores there files if fetched

	if not os.path.exists(_URLs_FOLDER):
		os.makedirs(_URLs_FOLDER)


	# now get the URLs associated to any of those wikicats (this function is below)
	# it reads from local files if exist, otherwise it connects to Internet to fetch them and store them locally

	urlsObjects = getUrlsLinked2Wikicats(selectedWikicats)

	# it receives a dictionary entry for each wikicat   urlsObjects[wikicat] = {"db": urlsDB, "wk": urlsWK}
	# urlsDB and urlsWK are lists of URLs

	result = {}  # object to store the results to be returned to the request
	fullList = [] # to aggregate the full list of URLs for all wikicats
		
	# process all results to return
	
	print("Number of URLs for every wikicat: ", end='')
	
	for wikicat in selectedWikicats:
		
		# first, the results from DB

		dbUrls = urlsObjects[wikicat]["db"]   # get the set of DB URLs
		numUrlsDB += len(dbUrls)
		
		fullList.extend(dbUrls)  # add the DB URLs of current wikicat to the whole list
		
		# now, the results from WK

		wkUrls = urlsObjects[wikicat]["wk"]
		numUrlsWK += len(wkUrls)
		
		fullList.extend(wkUrls)

		longs1 = "(DB=" + str(len(dbUrls)) + ", WK=" + str(len(wkUrls)) + ")"
		print(wikicat, longs1, end=', ')
		result[wikicat] = {"db": len(dbUrls), "wk": len(wkUrls)}  # add results for this wikicat


	listWithoutDuplicates = list(set(fullList))  # remove duplicated URLs
	print("\n\nSummary of URLs numbers: DB=", numUrlsDB, ", WK= ", numUrlsWK, ", total without duplicates=", len(listWithoutDuplicates))
	
	# returns number of results
	result["totalDB"] = numUrlsDB
	result["totalWK"] = numUrlsWK
	result["totalUrls"] = len(listWithoutDuplicates)
	# return jsonify(result);  # uncomment to return to the interface without processing files
	
	# the result are only the numbers of discovered URLs
	
	
	
	
	###  We've got the first set of relevant URLs, available in listWithoutDuplicates, and stored in the URLs folder
	###  Let's start the analysis of their contents 

	overwriteCorpus = json.loads(request.values.get("overwriteCorpus"))  # read the flag parameter overwriteCorpus from request

	if overwriteCorpus:
		print("Deleting current scrapped texts...")
		shutil.rmtree(_SCRAPPED_TEXT_PAGES_FOLDER)  # if overwriteCorpus, remove current corpus  (and the URLs?????)

	if not os.path.exists(_SCRAPPED_TEXT_PAGES_FOLDER):  # create new corpus folder if necessary
		os.makedirs(_SCRAPPED_TEXT_PAGES_FOLDER)

	
	print("\n")
	
	scrap = _scrapFunctions()   # Create a scrapFunctions object to clean pages
	unretrieved_pages_list = []  # a list for unsuccessful pages retrieval
		
	downloaded = 0  # number of files downloaded from Internet in this session
	
	lenOfListWithoutDuplicates  = len(listWithoutDuplicates)  # length of full list to process

	print("Downloading and cleaning candidate texts...")
	
	# download not locally stored pages, scrap them, and save them
	for idx, page in enumerate(listWithoutDuplicates, start=1):
		
		print("(", idx, "of", lenOfListWithoutDuplicates, ") -- ", page)

		# scrapped pages will be stored classified by domain, in specific folders
						
		pageWithoutHTTP = page[2+page.find("//"):]		# get the domain of this page
		domFolder = pageWithoutHTTP[:pageWithoutHTTP.find("/")]

		if (not os.path.exists(_SCRAPPED_TEXT_PAGES_FOLDER+"/"+domFolder)):	# create this domain folder if not exists 
			os.makedirs(_SCRAPPED_TEXT_PAGES_FOLDER+"/"+domFolder)
		
		# the pagename will be the name of the file, with the following change
		# dir1/dir2/page --> dir1..dir2..page.txt

		onlyPage = pageWithoutHTTP[1+pageWithoutHTTP.find("/"):]
		onlyPageChanged =  onlyPage.replace("/", "..")
		
		# Add file extension '.txt' to page name for saving it   !!!!!!!!!!
		# pageFinalName = page[1+page.rindex("/"):]
		fileNameCandidate = _SCRAPPED_TEXT_PAGES_FOLDER+"/"+domFolder+"/"+onlyPageChanged+".txt"
				
		if (os.path.exists(fileNameCandidate)):
			print("File already available in local DB:", fileNameCandidate)
		else:  # fetch file if not exists	
			try:  # Retrieves the URL, and get the page title and the scraped page content
				pageName, pageContent = scrap.scrapPage(page)  # pageName result is not used
				downloaded += 1
				# Save to text file
				_saveFile(fileNameCandidate, pageContent)
				print("File", str(downloaded), "downloaded and saved it:", fileNameCandidate)
			except Exception as e:
				print(page, ":", e)
				unretrieved_pages_list.append(page)
			
	# Save the unretrieved_pages_list to a file
	print("")
	print(str(len(unretrieved_pages_list)) + " unretrieved pages")
	_saveFile(_UNRETRIEVED_PAGES_FILENAME, '\n'.join(unretrieved_pages_list))
	
	print("ALL PAGES AVAILABLE AND CLEANED.", str(downloaded), "new files downloaded!!)")

	# all the pages not already available have been now fetched and cleaned

	
	similarity = _textSimilarityFunctions()    # Create a textSimilarityFunctions object to measure text similarities
	
	# # Create a new csv file if not exists. QUE SIGNIFICA W+ ? Temporalmente desactivado hasta que este claro lo que guardar
	# with _Open(_SIMILARITIES_CSV_FILENAME, 'w+') as writeFile:
	# 	# Name columns
	# 	fieldnames = ['URL', 'Euclidean Distance', 'Spacy', 'Doc2Vec Euclidean Distance',
	# 	'Doc2Vec Cosine Similarity', 'Trained Doc2Vec Euclidean Distance', 'Trained Doc2Vec Cosine Similarity',
	# 	'Wikicats Jaccard Similarity']
	# 
	# 	# Create csv headers
	# 	writer = csv.DictWriter(writeFile, fieldnames=fieldnames, delimiter=";")
	# 
	# 	# Write the column headers
	# 	writer.writeheader()
	


	discarded_pages_list = []     # a list to save discarded pages' URLs		

	print("")
	print("Identifying wikicats for candidate texts with DBpedia SpotLight...")
	downloaded = 0
	
	for idx, page in enumerate(listWithoutDuplicates, start=1):
		print("\n(", idx, "of", lenOfListWithoutDuplicates, ") -- ", page)
						
		# Build filename for this page
		pageWithoutHTTP = page[2+page.find("//"):]
		domFolder = pageWithoutHTTP[:pageWithoutHTTP.find("/")]
		onlyPage = pageWithoutHTTP[1+pageWithoutHTTP.find("/"):]
		onlyPageChanged =  onlyPage.replace("/", "..")
		fileNameCandidateBase = _SCRAPPED_TEXT_PAGES_FOLDER+"/"+domFolder+"/"+onlyPageChanged
		fileNameCandidate = fileNameCandidateBase+".txt"
		fileNameCandidateWikicats = fileNameCandidateBase+".wk"
				
		try:  # try to read candidate text wikicats from local store
			with _Open(fileNameCandidateWikicats) as fp:
				print("File already available in local DB:", fileNameCandidateWikicats)
		except:  # fetch candidate text wikicats if not in local store
			
			try:  # open and read candidate file
				candidateTextFile = _Open(fileNameCandidate, "r")
				candidate_text = candidateTextFile.read()
				print("Reading file:", fileNameCandidate)
			except:  # file that could not be downloaded
				print("ERROR buildCorpus2(): Unavailable file, not in the store, but it should be:", fileNameCandidate)
				continue
			
			candidate_text_categories = _getCategoriesInText(candidate_text)  # function _getCategoriesInText from px_DB_Manager
			
			if ("error" in candidate_text_categories):
				print("\n ERROR buildCorpus2(): Problem in _getCategoriesInText(candidate_text):", candidate_text_categories["error"])
				continue
				
			print("Wikicats downloaded for", fileNameCandidateWikicats)
			candidate_text_wikicats = list(filter(_filterSimpleWikicats, candidate_text_categories["wikicats"])) # remove simple wikicats with function located above
			
			_saveFile(fileNameCandidateWikicats, '\n'.join(candidate_text_wikicats))  # save file with original text wikicats,one per line
			downloaded += 1

	print("")
	print("ALL WIKICATs COMPUTED.", str(downloaded), "new files created!!)")
		
		
	print("\n Computing similarities...")
		
	# Measure text similarity, and discard pages (discarded_pages_list) without a minimum similarity
	for idx, page in enumerate(listWithoutDuplicates, start=1):
		
		print("(", idx, "of", lenOfListWithoutDuplicates, ") -- ", page)
						
		# Build filename for this page
		pageWithoutHTTP = page[2+page.find("//"):]
		domFolder = pageWithoutHTTP[:pageWithoutHTTP.find("/")]
		onlyPage = pageWithoutHTTP[1+pageWithoutHTTP.find("/"):]
		onlyPageChanged =  onlyPage.replace("/", "..")
		fileNameCandidateBase = _SCRAPPED_TEXT_PAGES_FOLDER+"/"+domFolder+"/"+onlyPageChanged
		fileNameCandidate = fileNameCandidateBase+".txt"
		fileNameCandidateWikicats = fileNameCandidateBase+".wk"
				
		try:  # open and read local file if already exists
			candidateTextFile = _Open(fileNameCandidate, "r")
			pageContent = candidateTextFile.read()
			print("Reading file:", fileNameCandidate)
		except:  # file that could not be downloaded
			print("ERROR buildCorpus2(): Unavailable file, not in the store, but it should be:", fileNameCandidate)
			continue


		# Compare original text with the text of this candidate (in pageContent)
		# several criteria are now computed. THEIR RELEVANCE SHOULD BE STUDIED AS SOON AS POSSIBLE 

		# Measure text similarity based on the Lee doc2vec model
		
		# doc2vec_cosineSimilarity, doc2vec_euclideanDistance = similarity.doc2VecTextSimilarity(originalText, pageContent, _LEE_D2V_MODEL)
		# print("Lee Doc2Vec CS = "+str(doc2vec_cosineSimilarity))
		# print("Lee Doc2Vec ED = "+str(doc2vec_euclideanDistance))
		# 
		# # Measure text similarity based on the trained doc2vec model with our training corpus
		# doc2vec_trained_cosineSimilarity, doc2vec_trained_euclideanDistance = similarity.doc2VecTextSimilarity(originalText, pageContent, _OWN_D2V_MODEL)
		# print("Trained Doc2Vec CS = "+str(doc2vec_trained_cosineSimilarity))
		# print("Trained Doc2Vec ED = "+str(doc2vec_trained_euclideanDistance))
		# 
		# # Measure the euclidean distance using SKLEARN
		# euclidean_distance = similarity.euclideanTextSimilarity(originalText, pageContent)
		# print("Euclidean distance = "+str(euclidean_distance))
		# 
		# # Measure the spaCy distance
		# spacy_similarity = similarity.spacyTextSimilarity(originalText, pageContent)
		# print("Spacy similarity = "+str(spacy_similarity))

		# Measure wikicats similarity (requires complete matching)
		# wikicats_jaccard_similarity, subjects_jaccard_similarity = similarity.fullWikicatsAndSubjectsSimilarity(originalText, pageContent)
		# print("Wikicats full jaccard similarity = "+str(wikicats_jaccard_similarity))
		# print("Subjects full jaccard similarity = "+str(subjects_jaccard_similarity))
		
		
		# Measure wikicats similarity (requires shared matching)
		shared_wikicats_jaccard_similarity = similarity.sharedWikicatsSimilarity(selectedWikicats, pageContent, fileNameCandidateWikicats)
		print("Wikicats shared jaccard similarity = "+str(shared_wikicats_jaccard_similarity))


		# # Save similarity to a CSV file
		# with _Open(_SIMILARITIES_CSV_FILENAME, 'a') as writeFile:
		# 	writer = csv.writer(writeFile, delimiter=';')
		# 	writer.writerow([page, euclidean_distance, spacy_similarity, doc2vec_euclideanDistance,
		# 	doc2vec_cosineSimilarity, doc2vec_trained_euclideanDistance, doc2vec_trained_cosineSimilarity, shared_wikicats_jaccard_similarity])


		# Minimum similarity for a page to be accepted.
		# WE MUST DECIDE THE MOST RELEVANT CRITERIUM TO DECIDE ON IT
		# currently, we used shared_wikicats_jaccard_similarity

		min_similarity = 0.2  # review this threshold

		# Filter pages to keep only the ones with at least such similarity
		if(shared_wikicats_jaccard_similarity >= min_similarity):
			print("page accepted\n")
		else:
			print("page discarded\n")

			# Save URL to discarded list
			discarded_pages_list.append(page)

	# Save the discarded_pages_list to a file
	_saveFile(_DISCARDED_PAGES_FILENAME, '\n'.join(discarded_pages_list))
	print(str(len(discarded_pages_list)) + " discarded pages")

	return jsonify(result)



#############################################################################################################################################	



# aux function to get all the URLs associated to any wikicat from a set of wikicats
# If there is a file for a wikicat, it is read for returning contents
# Otherwise, it connects to Internet to query DB and WK and parse the results to return, after storing them locally
# it returns a dictionary entry for each wikicat   urlsObjects[wikicat] = {"db": urlsDB, "wk": urlsWK}
# urlsDB and urlsWK are lists of URLs

def getUrlsLinked2Wikicats (selectedWikicats):
	requestObjects = {} # dictionary to store request objects 
	
	_session = FuturesSession()  # to manage asynchronous requests 

	# first phase, reading files or start requests for DBpedia and Wikidata foreach wikicat
					
	for wikicat in selectedWikicats:
		
		# first, read or fetch Wikicat results for DBpedia

		filename_db = _URLs_FOLDER+"/_Wikicat_"+wikicat+"_DB_Urls.txt"
		requestDone = 0  # to control if some request has been done, and if so, set a delay to not overload servers
		
		try:  # try to read wikicats of original text from local store
			with _Open(filename_db) as fp:
				urls_from_DB = fp.read().splitlines()
				print("File already available:", filename_db)
				requestObjects[wikicat] = {"dburls": urls_from_DB}  # store the local available DB URLs for this wikicat
		except:  # fetch data from DB
			fullWikicat = "Wikicat"+wikicat
		
			# asynchronous query to dbpedia
			# request only URLs being primaruy topic of some dbpedia entity
			queryDB = """
			PREFIX yago: <http://dbpedia.org/class/yago/>
			SELECT ?url ?der ?pt WHERE {
				?url  rdf:type yago:"""+fullWikicat+""" .
				OPTIONAL {?url  prov:wasDerivedFrom ?der}
				OPTIONAL {?url  foaf:isPrimaryTopicOf ?pt}
			}
			"""
		
			# start the DB query
			try:
				print("Starting DB query for: ", wikicat)
				requestDB = _session.post(_URL_DB, data={"query": queryDB}, headers={"accept": "application/json"})
			except Exception as exc:
				print("\n*** ERROR getUrlsLinked2Wikicats(): Error querying DB for", wikicat, ":", exc)
				requestDB = None
				
			requestObjects[wikicat] = {"db": requestDB}  # store the request DB object for this wikicat
			requestDone = 1
		

		# now, read or fetch Wikicat results for Wikidata
		
		filename_wk = _URLs_FOLDER+"/_Wikicat_"+wikicat+"_WK_Urls.txt"	

		# it uses update with the objects dictionary, as the wikicat key has been already created for DBpedia	
		
		try:  # try to read wikicats and subjects of original text from local store
			with _Open(filename_wk) as fp:
				urls_from_WK = fp.read().splitlines()
				print("File already available:", filename_wk)
				requestObjects[wikicat].update({"wkurls": urls_from_WK})  # store the local available WK URLs for this wikicat
		except:  # fetch data from WK
	
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
			# start the WK query
			try:
				print("Starting WK query for: ", wikicat)
				requestWK = _session.post(_URL_WK, data={"query": queryWK}, headers={"accept": "application/json"})
			except Exception as exc:
				print("\n*** ERROR getUrlsLinked2Wikicats(): Error querying WK for", wikicat, ":", exc)
				requestWK = None	
			
			requestObjects[wikicat].update({"wk": requestWK})  # store the request WK object for this wikicat
			requestDone = 1
			
		if requestDone == 1:
			time.sleep(4)  # delay to avoid server reject for too many queries
		
	print("\n** ALL PENDING QUERIES LAUNCHED\n")
	
	# End of the first phase. All queries launched. Now, for every wikicat, we have:
	# requestObjects[wikicat] = {"dburls": URLs} or  {"db": requestDB}
	#                       and {"wkurls": URLS} or  {"wk": requestWK} 
	



	# let's build an object {"db": urlsDB, "wk": urlsWK} for each wikicat (each field is a URL list)
	urlsObjects = {}
	
	# Second phase. Now, read the results received from all queries
	
	for wikicat in selectedWikicats:
		
		# first, study results for DB
		
		try:
			urlsDB = requestObjects[wikicat]["dburls"]   # try to recover local DB results
		except:
			requestDB = requestObjects[wikicat]["db"]   # no local DB results, get the request DB object for this wikicat

			if requestDB == None:  # error starting DB query, return []
				print("\n*** ERROR getUrlsLinked2Wikicats(): Error querying DB for", wikicat, ": the query could not be started")
				urlsDB = []
			else:
				try:
					try:
						print("Waiting DB query result for:", wikicat)
						responseDB = requestDB.result()  # waiting for DB query completion
					except:
						raise Exception("timeout")
					
					if responseDB.status_code != 200:  # check if DB query ended correctly
						raise Exception ("answer is not 200, is "+str(responseDB.status_code))

					try:
						responseDBJson = responseDB.json()
					except:
						raise Exception("error decoding JSON")
					
					try:
						bindingsDB = responseDBJson["results"]["bindings"]
					except:
						raise Exception("no [results][bindings] in the answer")
					
					# remove bindings with no pt field (isPrimaryTopicOf), because they don't correspond to DBpedia entities ???
					bindingsDBwithPT = list(filter(_hasFieldPT, bindingsDB)) 
					urlsDB = list(map(lambda x: x["pt"]["value"], bindingsDBwithPT))  # keep only the URL in x["pt"]["value"]
					
					if len(urlsDB) > 0:
						_saveFile(_URLs_FOLDER+"/_Wikicat_"+wikicat+"_DB_Urls.txt", '\n'.join(urlsDB))  # save all results from DB for this wikicat
		
				except Exception as exc:
					print("\n*** ERROR getUrlsLinked2Wikicats(): Error querying DB for", wikicat,":", exc)
					urlsDB = []
	
		# end for DB, we already have urlsDB
		
		# second, study results for WK
		
		try:
			urlsWK = requestObjects[wikicat]["wkurls"]   # try to recover local WK results
		except:
			requestWK = requestObjects[wikicat]["wk"]  # no local WK results, get the request WK object for this wikicat
			
			# WK results come without prefix "https://en.wikipedia.org/wiki/", this function adds it
			def addWKPrefix (x):
				return "https://en.wikipedia.org/wiki/"+x["title"]["value"].replace(" ", "_")
			
			
			if requestWK == None:  # error starting WK query, return []
				print("\n*** ERROR getUrlsLinked2Wikicats(): Error querying WK for", wikicat, ": the query could not be started")
				urlsWK = []
			else:
				try:
					try:
						print("Waiting WK query result for:", wikicat)
						responseWK = requestWK.result()  # waiting for WK query completion
					except:
						raise Exception("timeout")
					
					if responseWK.status_code != 200: # check if WK query ended correctly
						raise Exception ("answer is not 200, is " + str(responseWK.status_code))

					try:
						responseWKJson = responseWK.json()
					except:
						raise Exception("error decoding JSON")
					
					try:
						bindingsWK = responseWKJson["results"]["bindings"]
					except:
						raise Exception("no [results][bindings] in the answer")

					urlsWK = list(map(addWKPrefix, bindingsWK))   # add WK prefix to x["title"]["value"], changing space by '_'
	
					if len(urlsWK) > 0:
						_saveFile(_URLs_FOLDER+"/_Wikicat_"+wikicat+"_WK_Urls.txt", '\n'.join(urlsWK)) # save all results from WK for this wikicat
		
				except Exception as exc:
					print("\n*** ERROR getUrlsLinked2Wikicats(): Error querying WK for", wikicat,":", exc)
					urlsWK = []

		# end for WK, we already have urlsWK

		# store results for this wikicat		
		urlsObjects[wikicat] = {"db": urlsDB, "wk": urlsWK}
		
	print("\n** RECEIVED ALL RESULTS FOR PENDING QUERIES\n")
	
	return urlsObjects  # return results to buildCorpus function
