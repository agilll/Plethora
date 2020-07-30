import sys
import os
from datetime import datetime
import time
import json
import csv

from flask import request, jsonify
from smart_open import open as _Open
from requests_futures.sessions import FuturesSession

from px_DB_Manager import getCategoriesInText as _getCategoriesInText
from px_aux import saveFile as _saveFile, appendFile as _appendFile, URL_DB as _URL_DB, URL_WK as _URL_WK

from aux_build import hasFieldPT as _hasFieldPT, Print as _Print, SortTuplaList_byPosTupla as _SortTuplaList_byPosTupla
from aux_build import CORPUS_FOLDER as _CORPUS_FOLDER, URLs_FOLDER as _URLs_FOLDER,  SCRAPPED_PAGES_FOLDER as _SCRAPPED_PAGES_FOLDER
from aux_build import MODELS_FOLDER as _MODELS_FOLDER, LEE_D2V_MODEL as _LEE_D2V_MODEL
from aux_build import getWikicatComponents as _getWikicatComponents
from aux_build import filterSimpleWikicats as _filterSimpleWikicats, filterSimpleSubjects as _filterSimpleSubjects
from aux_build import CORPUS_MIN_TXT_SIZE as _CORPUS_MIN_TXT_SIZE
from aux_build import UNRETRIEVED_PAGES_FILENAME as _UNRETRIEVED_PAGES_FILENAME, DISCARDED_PAGES_FILENAME as _DISCARDED_PAGES_FILENAME

from scrap import scrapFunctions as _scrapFunctions
from textSimilarities import textSimilarityFunctions as _textSimilarityFunctions, Doc2VecSimilarity as _Doc2VecSimilarity

# to preprocess corpus files
sys.path.append('../module_processCorpus')
from S1_AddSuffixToTexts import processS1List as _processS1List
from S2_BuildDbpediaInfoFromTexts import processS2List as _processS2List
from S3_UpdateTextsEntities import processS3List as _processS3List
from S4_tokenize import processS4List as _processS4List   # requires Standord CoreNLP server started

# to train the D2V model
sys.path.append('../module_train')
from D2V_BuildOwnModel_t import buildDoc2VecModelFromList as _buildDoc2VecModelFromList



# QUERY (/doPh1getWikicatsFromText) to attend the query to get wikicats from a text
# receives:
# P0_originalText: the original text
# computes and saves files with wikicats (length.ph1.wk) and subjects (length.ph1.sb)
# returns:
# result["lenOriginalText"]: the length of the original text
# result["wikicats"]: list of wikicats (and saves them in the file $CORPUS_FOLDER/length/length.ph1.wk)
# result["subjects"]: list of subjects (and saves them in the file $CORPUS_FOLDER/length/length.ph1.sb)
# result[wk] = [component list] one for each wikicat, with the different components of each wikicat name
# result["formerSelectedWikicats"]: list of wikicats selected in the past, for them to be identified in the interface
def doPh1getWikicatsFromText():
	_Print("Requested Phase 1")

	P0_originalText = request.values.get("P0_originalText")

	result = doPh1(P0_originalText)
	return jsonify(result);


def doPh1 (P0_originalText):
	_Print("Executing Phase 1")

	lenOriginalText = len(P0_originalText)  # length of the received text

	if not os.path.exists(_CORPUS_FOLDER):  # create KORPUS folder if not exists
		os.makedirs(_CORPUS_FOLDER)

	if not os.path.exists(_MODELS_FOLDER):  # create MODELS folder if not exists
		os.makedirs(_MODELS_FOLDER)

	lengthFolder = _CORPUS_FOLDER+str(lenOriginalText)+"/"

	if not os.path.exists(lengthFolder):  # create KORPUS/length folder if not exists
		os.makedirs(lengthFolder)


	# to log messages
	logFilename = lengthFolder+str(lenOriginalText)+".log"
	_appendFile(logFilename, "\n\nExecuting Phase 1")


	filename = lengthFolder+str(lenOriginalText)+".ph0.txt"   # save the received text with length.ph0.txt filename
	_saveFile(filename, P0_originalText)

	filename_wk = lengthFolder+str(lenOriginalText)+".ph1.wk"   # filename for wikicats (length.ph1.wk)
	filename_sb = lengthFolder+str(lenOriginalText)+".ph1.sb"   # filename for subjects (length.ph1.sb)
	filename_en = lengthFolder+str(lenOriginalText)+".ph1.en"   # filename for entities (length.ph1.en)

	result = {}

	try:  # open wikicats file if exists
		with _Open(filename_wk) as fp:
			listWikicats = fp.read().splitlines()
	except:  # if wikicats file does not exist yet, compute wikicats-subjects-entities files
		data = _getCategoriesInText(P0_originalText)  # function getCategoriesInText from px_DB_Manager.py

		if ("error" in data):   # return error if could not fetch wikicats
			result["error"] = data["error"]
			return result;

		listWikicats = list(filter(_filterSimpleWikicats, data["wikicats"])) # remove simple wikicats with function from aux_build.py
		_saveFile(filename_wk, '\n'.join(listWikicats))  # save file (length.ph1.wk) with wikicats, one per line

		listSubjects = list(filter(_filterSimpleWikicats, data["subjects"]))  # remove simple subjects with function from aux_build.py
		_saveFile(filename_sb, '\n'.join(listSubjects)) # save file (length.ph1.sb) with subjects, one per line

		listURIs = data["URIs_persons_places_events"]
		_saveFile(filename_en, '\n'.join(listURIs)) # save file (length.ph1.en) with URIs of identified entities, one per line

	result["P1_wikicats"] = listWikicats  # add result wikicats to return

	for w in listWikicats:    # compute components for every wikicat and add all of them to result
		wlc = _getWikicatComponents(w)   # function getWikicatComponets from aux_build.py
		result[w] = {"components":wlc}  # one entry per wikicat, with a dict with only one key "components"

	filename_selected_wk = lengthFolder+str(lenOriginalText)+".ph2-1.selected.wk"   # previously selected wikicats file for this text

	try:  # try to open previously selected wikicats file if exists
		with _Open(filename_selected_wk) as fp:
			wkSelectedList = fp.read().splitlines()
	except:
		wkSelectedList = []    # no previously selected wikicats

	result["P1_selectedWikicats"] = wkSelectedList

	_appendFile(logFilename, "Returning wikicats: "+str(len(listWikicats)))
	return result;







# QUERY (/doPh2getUrlsCandidateFiles)  to attend the query to find out URLs of candidate files
# receives:
# * the original text
# * the list of selected wikicats
# returns: the results, mainly the number of files identified for each wikicat
def doPh2getUrlsCandidateFiles():
	_Print("Requested Phase 2")

	fromStart = json.loads(request.values.get("fromStart"))
	P0_originalText = request.values.get("P0_originalText")
	lenOriginalText = len(P0_originalText)

	# in case execution from start, Phase 1 must be executed first
	if fromStart:
		resultPh1 = doPh1(P0_originalText)
		P1_selectedWikicats = resultPh1["P1_wikicats"]	# user does not select wikicats, we asume all of them are selected
	else:
		P1_selectedWikicats = json.loads(request.values.get("P1_selectedWikicats"))   # get parameter with selected wikicats by user

	result = doPh2(lenOriginalText, P1_selectedWikicats)
	if "error" in result:
		return jsonify(result);

	result["P1_selectedWikicats"] = P1_selectedWikicats

	# in phases 1 and 2 different dicts are returned for result[wikicat]
	# in phase 1,  result[wikicat] = {"components": compList}
	# in phase 2,  result[wikicat] = {"db": numURLsDB, "wk": numURLsWK}

	# in case execution from start, fields needed to present data in previous phases must be added to the answer
	if fromStart:
		result["P1_wikicats"] = P1_selectedWikicats
		# both dicts for result[wikicat] must be combined
		for w in P1_selectedWikicats:	# all the wikicats, selected or not
			result[w]["components"] = resultPh1[w]["components"]  # the 'components' field of the first phase dict is added to the second phase dict

	return jsonify(result);


def doPh2 (lenOriginalText, P1_selectedWikicats):
	lengthFolder = _CORPUS_FOLDER+str(lenOriginalText)+"/"

	logFilename = lengthFolder+str(lenOriginalText)+".log"
	_Print("Executing Phase 2")
	_appendFile(logFilename, "\n\nExecuting Phase 2")



	result = {}  # object to store the results to be returned to the request

	print("\nNumber of selected wikicats:", len(P1_selectedWikicats))
	numUrlsDB = 0
	numUrlsWK = 0

	# store the selected wikicats in the file $CORPUS_FOLDER/length.ph2-1.selected.wk
	_saveFile(lengthFolder+str(lenOriginalText)+".ph2-1.selected.wk", '\n'.join(P1_selectedWikicats))

	# create the folder to store two files per wikicat, with the URLs linked to such wikicat coming from DB and WK
	# it must be done before calling the getUrlsLinked2Wikicats function, that it stores there files if fetched

	if not os.path.exists(_URLs_FOLDER):
		os.makedirs(_URLs_FOLDER)


	print("\n********** Starting DB and WK queries...", "\n")

	# now get the URLs associated to any of those wikicats (this function is below, at the end of this file)
	# it reads from local DB (URLs) if exist, otherwise it connects to Internet to fetch and store them in local DB

	urlsObjects = getUrlsLinked2Wikicats(P1_selectedWikicats, logFilename)

	# it has been received a dictionary entry for each wikicat   urlsObjects[wikicat] = {"db": urlsDB, "wk": urlsWK}
	# urlsDB and urlsWK are lists of URLs, possibly with duplicates

	fullList = [] # to aggregate the full list of URLs for all wikicats

	# process all results to return

	print("Number of URLs for every wikicat: ", end='')

	for wikicat in P1_selectedWikicats:

		# first, the results from DB

		dbUrls = urlsObjects[wikicat]["db"]   # get the set of DB URLs
		dbUrls = list(map(lambda x: x.replace("https://", "http://"), dbUrls))    # change 'https://' to 'http://' to avoid duplicates
		numUrlsDB += len(dbUrls)

		fullList.extend(dbUrls)  # add the DB URLs of current wikicat to the whole list

		# now, the results from WK

		wkUrls = urlsObjects[wikicat]["wk"]
		wkUrls = list(map(lambda x: x.replace("https://", "http://"), wkUrls))    # change 'https://' to 'http://' to avoid duplicates
		numUrlsWK += len(wkUrls)

		fullList.extend(wkUrls)  # add the WK URLs of current wikicat to the whole list

		longs1 = "(DB=" + str(len(dbUrls)) + ", WK=" + str(len(wkUrls)) + ")"
		print(wikicat, longs1, end=', ')
		result[wikicat] = {"db": len(dbUrls), "wk": len(wkUrls)}  # add results for this wikicat to result

	listWithoutDuplicates = list(set(fullList))  # remove duplicated URLs (case sensitive)
	print("")
	#listWithoutDuplicates = removeDup(listWithoutDuplicates)  # remove elements that are duplicated if case-insensitive check

	# store listWithoutDuplicates in local DB to be used in the next phases
	listWithoutDuplicatesFile =  lengthFolder+str(lenOriginalText)+".ph2-2.listWithoutDuplicates"   # name of the file with listWithoutDuplicates
	_saveFile(listWithoutDuplicatesFile, '\n'.join(listWithoutDuplicates))

	lenListWithoutDuplicates  = len(listWithoutDuplicates)  # length of full list to process
	print("\n\nSummary of URLs numbers: DB=", numUrlsDB, ", WK= ", numUrlsWK, ", total without duplicates=", lenListWithoutDuplicates)

	_appendFile(logFilename, "Number of unique discovered URLs: "+str(lenListWithoutDuplicates))

	# returns number of results, the result items are only the numbers of discovered URLs
	result["P2_totalDB"] = numUrlsDB
	result["P2_totalWK"] = numUrlsWK
	result["P2_totalUrls"] = lenListWithoutDuplicates

	_appendFile(logFilename, "Computed URLs: "+str(lenListWithoutDuplicates))
	return result


# remove elements that are duplicated if case-insensitive check
# not used because is a costly procedure
# def removeDup (lista):
# 	listaLower = list(map(lambda x: x.lower(), lista))
#
# 	dictDup = {}	# dict with keys urlLower and value urlOriginal
# 	for url in lista:
# 		num = listaLower.count(url.lower())
# 		if num > 1:
# 			if url.lower() in dictDup:
# 				print(url, num)
# 				continue
# 			else:
# 				dictDup[url.lower()] = url
#
# 	for url in dictDup:
# 		lista.remove(dictDup[url])
#
# 	return lista











# QUERY (/getWikicatUrls)  to attend the query to return URLs derived from a given wikicat
# receives: a  wikicat
# returns: results from DBpedia or Wikidata
def getWikicatUrls():
	wikicat = request.values.get("wikicat")
	DB = request.values.get("DB")  # to mark if DBpedia or Wikidata is requested

	results = []
	if DB == "true":
		filename = _URLs_FOLDER+"_Wikicat_"+wikicat+"_DB_Urls.txt"
	else:
		filename = _URLs_FOLDER+"_Wikicat_"+wikicat+"_WK_Urls.txt"

	print("Reading local file:"+filename)
	try:  # try to read wikicats of original text from local store
		with _Open(filename) as fp:
			results = fp.read().splitlines()
	except Exception as e:
		print("Exception in getWikicatUrls: "+str(e))

	result = {}
	result["urls"] = results
	return jsonify(result);









# QUERY (/doPh3downloadCandidateTexts)  to attend the query to download candidate texts
# receives:
# - the original text
# - the selected wikicats
# returns: the number of downloaded and cleaned files with and without enough content

def doPh3downloadCandidateTexts():
	_Print("Requested Phase 3")

	fromStart = json.loads(request.values.get("fromStart"))
	P0_originalText = request.values.get("P0_originalText")
	lenOriginalText = len(P0_originalText)

	# in case execution from start, Phases 1-2  must be executed first
	if fromStart:
		resultPh1 = doPh1(P0_originalText)
		P1_selectedWikicats = resultPh1["P1_wikicats"]
		resultPh2 = doPh2(lenOriginalText, P1_selectedWikicats)
	else:
		P1_selectedWikicats = json.loads(request.values.get("P1_selectedWikicats"))  # get parameter with the list of wikicats


	result = doPh3(lenOriginalText)
	if "error" in result:
		return jsonify(result);

	result["P1_selectedWikicats"] = P1_selectedWikicats

	# in case execution from start, fields needed to present data in previous phases must be added to the answer
	if fromStart:
		result["P1_wikicats"] = P1_selectedWikicats
		result["P2_totalDB"] = resultPh2["P2_totalDB"]
		result["P2_totalWK"] = resultPh2["P2_totalWK"]
		result["P2_totalUrls"] = resultPh2["P2_totalUrls"]
		for w in P1_selectedWikicats:	# all the wikicats, selected or not
			components = resultPh1[w]["components"]
			db = resultPh2[w]["db"]
			wk = resultPh2[w]["wk"]
			result[w] = {"components": components, "db": db, "wk": wk}

	return jsonify(result);



def doPh3(lenOriginalText):
	lengthFolder = _CORPUS_FOLDER+str(lenOriginalText)+"/"

	logFilename = lengthFolder+str(lenOriginalText)+".log"
	_Print("Executing Phase 3")
	_appendFile(logFilename, "\n\nExecuting Phase 3")

	result = {}  # object to store the results to be returned to the request

	listWithoutDuplicatesFile =  lengthFolder+str(lenOriginalText)+".ph2-2.listWithoutDuplicates"  # name of the file with listWithoutDuplicates saved in previous phase

	try:  # try to read listWithoutDuplicates file
		with _Open(listWithoutDuplicatesFile) as fp:
			listWithoutDuplicates = fp.read().splitlines()
	except:
		result["error"]  = "No file "+listWithoutDuplicatesFile    # no file listWithoutDuplicatesFile
		return result

	lenListWithoutDuplicates  = len(listWithoutDuplicates)  # length of full list to process

	#  We have the set of URLs available in listWithoutDuplicates
	#  Let's start the analysis of their contents

	print("\n", "********** Downloading and cleaning", lenListWithoutDuplicates, "candidate texts...", "\n")

	if not os.path.exists(_SCRAPPED_PAGES_FOLDER):  # create the folder to store scrapped pages and wikicat files for them
	 	os.makedirs(_SCRAPPED_PAGES_FOLDER)

	scrap = _scrapFunctions()   # Create a scrapFunctions object to clean pages
	unretrieved_pages_list = []  # a list for unsuccessful pages retrieval

	P3_numUrlsDownloaded = 0  # number of urls downloaded from Internet IN THIS ITERATION

	listEnoughContent = [] # list of pages with sufficient content to proceed  ( > _CORPUS_MIN_TXT_SIZE bytes -currently 300-, a constant from aux_build.py)
	listNotEnoughContent = [] # list of pages with insufficient content to proceed

	# download not locally stored pages, scrap them, and save them
	startTime = datetime.now()

	for idx, page in enumerate(listWithoutDuplicates, start=1):
		if (idx % 5000) == 0:
			print(".", end=' ', flush=True)

		_Print("("+str(idx)+" of "+str(lenListWithoutDuplicates)+") -- ", page)

		# scrapped pages will be stored classified by domain, in specific folders with such domain names
		# currently, only "en.wikipedia.org" domain is used

		pageWithoutHTTP = page[2+page.find("//"):]		# get the domain of this page
		domainFolder = pageWithoutHTTP[:pageWithoutHTTP.find("/")]

		if (not os.path.exists(_SCRAPPED_PAGES_FOLDER+domainFolder)):	# create this domain folder if not exists
			os.makedirs(_SCRAPPED_PAGES_FOLDER+domainFolder)

		# the pagename will be the name of the file, with the following change
		# dir1/dir2/page --> dir1..dir2..page.txt

		onlyPage = pageWithoutHTTP[1+pageWithoutHTTP.find("/"):]
		onlyPageChanged =  onlyPage.replace("/", "..")

		# Add file extension '.txt' to page name for saving it   !!!!!!!!!!
		# pageFinalName = page[1+page.rindex("/"):]
		rFileNameCandidate = domainFolder+"/"+onlyPageChanged+".txt"
		fileNameCandidate = _SCRAPPED_PAGES_FOLDER+rFileNameCandidate

		if (os.path.exists(fileNameCandidate)):  # may be exists but corresponds to another urlname
			_Print("File already available in local DB:", fileNameCandidate)
			fsize = os.path.getsize(fileNameCandidate)
			if fsize < _CORPUS_MIN_TXT_SIZE:
				listNotEnoughContent.append(rFileNameCandidate)
			else:
				listEnoughContent.append(rFileNameCandidate)
		else:  # fetch file if not exists
			try:  # Retrieves the URL, and get the page title and the scraped page content
				pageContent = scrap.scrapPage(page)  # scrap page

				P3_numUrlsDownloaded += 1
				_saveFile(fileNameCandidate, pageContent)  # Save to text file
				_Print("File "+str(P3_numUrlsDownloaded)+" downloaded and saved it:", fileNameCandidate)

				if (len(pageContent) < _CORPUS_MIN_TXT_SIZE):
					listNotEnoughContent.append(rFileNameCandidate)
				else:
					listEnoughContent.append(rFileNameCandidate)
			except Exception as e:
				_appendFile(logFilename, "Page "+page+" could not be retrieved: "+repr(e))
				unretrieved_pages_list.append(page)

	endTime = datetime.now()
	elapsedTimeF3 = endTime - startTime

	# Save the unretrieved_pages_list to a file
	print("\n",str(len(unretrieved_pages_list)), "unretrieved pages")
	unretrievedPagesFile = lengthFolder+str(lenOriginalText)+".ph3."+_UNRETRIEVED_PAGES_FILENAME
	_saveFile(unretrievedPagesFile, '\n'.join(unretrieved_pages_list))

	lenListEnoughContent = len(listEnoughContent)

	_appendFile(logFilename, "Number of available pages with enough content: "+str(lenListEnoughContent))

	print("ALL PAGES AVAILABLE AND CLEANED.")
	print("New pages downloaded in this iteration:", str(P3_numUrlsDownloaded))
	print("Number of texts with enough content:", str(lenListEnoughContent))
	print("Number of texts without enough content:", str(len(listNotEnoughContent)))
	print("Duration F3 (downloading and cleaning):", str(elapsedTimeF3.seconds))

	# store listEnoughContent in local DB
	listEnoughContentFile =  lengthFolder+str(lenOriginalText)+".ph3.listEnoughContent"  # name of the file to store listEnoughContent
	_saveFile(listEnoughContentFile, '\n'.join(listEnoughContent))

	result["P3_numUrlsDownloaded"] = P3_numUrlsDownloaded
	result["P3_lenListEnoughContent"] = lenListEnoughContent
	result["P3_lenListNotEnoughContent"] = len(listNotEnoughContent)
	result["P3_elapsedTimeF3"] = elapsedTimeF3.seconds

	_appendFile(logFilename, "Available pages with content: "+str(lenListEnoughContent))
	return result








# QUERY (/doPh4identifyWikicats)  to attend the query to identify wikicats in candidate texts
# receives: the original text
# returns: the number of downloaded and cleaned files with and without enough content

def doPh4identifyWikicats():
	_Print("Requested Phase 4")

	fromStart = json.loads(request.values.get("fromStart"))
	P0_originalText = request.values.get("P0_originalText")
	lenOriginalText = len(P0_originalText)

	# in case execution from start, Phases 1-2-3  must be executed first
	if fromStart:
		resultPh1 = doPh1(P0_originalText)
		P1_selectedWikicats = resultPh1["P1_wikicats"]
		resultPh2 = doPh2(lenOriginalText, P1_selectedWikicats)
		resultPh3 = doPh3(lenOriginalText)
	else:
		P1_selectedWikicats = json.loads(request.values.get("P1_selectedWikicats"))  # get parameter with the list of wikicats

	result = doPh4(lenOriginalText)
	if "error" in result:
		return jsonify(result);

	result["P1_selectedWikicats"] = P1_selectedWikicats

	# in case execution from start, fields needed to present data in previous phases must be added to the answer
	if fromStart:
		result["P1_wikicats"] = P1_selectedWikicats
		for w in P1_selectedWikicats:	# all the wikicats, selected or not
			components = resultPh1[w]["components"]
			db = resultPh2[w]["db"]
			wk = resultPh2[w]["wk"]
			result[w] = {"components": components, "db": db, "wk": wk}
		result["P2_totalDB"] = resultPh2["P2_totalDB"]
		result["P2_totalWK"] = resultPh2["P2_totalWK"]
		result["P2_totalUrls"] = resultPh2["P2_totalUrls"]
		result["P3_numUrlsDownloaded"] = resultPh3["P3_numUrlsDownloaded"]
		result["P3_lenListEnoughContent"] = resultPh3["P3_lenListEnoughContent"]
		result["P3_lenListNotEnoughContent"] = resultPh3["P3_lenListNotEnoughContent"]
		result["P3_elapsedTimeF3"] = resultPh3["P3_elapsedTimeF3"]

	return jsonify(result);



def doPh4(lenOriginalText):

	lengthFolder = _CORPUS_FOLDER+str(lenOriginalText)+"/"

	logFilename = lengthFolder+str(lenOriginalText)+".log"
	_Print("Executing Phase 4")
	_appendFile(logFilename, "\n\nExecuting Phase 4")

	result = {}  # object to store the results to be returned to the request

	listEnoughContentFile =  lengthFolder+str(lenOriginalText)+".ph3.listEnoughContent"  # name of the file with listEnoughContent stored in previous phase

	try:  # try to read listEnoughContent file
		with _Open(listEnoughContentFile) as fp:
			listEnoughContent = fp.read().splitlines()
	except:
		result["error"]  = "No file "+listEnoughContentFile    # no file listEnoughContentFile
		return result

	lenListEnoughContent  = len(listEnoughContent)  # length of full list to process

	print("\n", "********** Identifying wikicats and subjects for", lenListEnoughContent, "candidate texts with DBpedia SpotLight...","\n")
	P4_numUrlsProcessed = 0

	listWithWKSB = [] # list of docs with wikicats or subjects
	listWithoutWKSB = [] # list of docs with no wikicats and no subjects
	startTime = datetime.now()

	for idx, rFileNameCandidate in enumerate(listEnoughContent, start=1):
		if (idx % 5000) == 0:
			print(".", end=' ', flush=True)
		_Print("\n("+str(idx)+" of "+str(lenListEnoughContent)+") -- ", rFileNameCandidate)

		# Build filenames for this doc
		fileNameCandidate = _SCRAPPED_PAGES_FOLDER+rFileNameCandidate
		fileNameCandidateBase = fileNameCandidate[:fileNameCandidate.rfind(".")]
		fileNameCandidateWikicats = fileNameCandidateBase+".wk"    # wikicats file for this doc
		fileNameCandidateSubjects = fileNameCandidateBase+".sb"    # subjects file for this doc

		# if both files (wikicats and subjects) exist, use them from local store
		if os.path.exists(fileNameCandidateWikicats) and os.path.exists(fileNameCandidateSubjects):
			_Print("Files WK and SB already available in local DB for", fileNameCandidate)
			fwsize = os.path.getsize(fileNameCandidateWikicats)
			fssize = os.path.getsize(fileNameCandidateSubjects)
			# if these two files are empty (no wikicats and no subjects), this doc will not be used
			if (fwsize == 0) and (fssize == 0):
				listWithWKSB.append(rFileNameCandidate)  # we will compute both similarities even though there is no info (no wikicats and no subjects)
			else:
				listWithWKSB.append(rFileNameCandidate)
		else: # if one file does not exists, fetch from Internet wikicats and subjects for the candidate text
			try:  # open and read text of candidate file
				candidateTextFile = _Open(fileNameCandidate, "r")
				candidate_text = candidateTextFile.read()
				_Print("Reading candidate text file:", fileNameCandidate)
			except:  # file that inexplicably could not be read from local store, it will not be used
				_appendFile(logFilename, "ERROR doPh4identifyWikicats(): Unavailable candidate file, not in the store, but it should be: "+fileNameCandidate)
				listWithoutWKSB.append(rFileNameCandidate)
				continue

			_Print("Computing wikicats and subjects for:", rFileNameCandidate)
			candidate_text_categories = _getCategoriesInText(candidate_text)  # function _getCategoriesInText from px_DB_Manager

			if ("error" in candidate_text_categories):  # error while fetching info, the page will not be used
				_appendFile(logFilename, "ERROR doPh4identifyWikicats(): Problem in _getCategoriesInText(candidate_text): "+candidate_text_categories["error"])
				listWithoutWKSB.append(rFileNameCandidate)
				continue

			_Print("Wikicats and subjects downloaded for", fileNameCandidate)
			candidate_text_wikicats = list(filter(_filterSimpleWikicats, candidate_text_categories["wikicats"])) # remove simple wikicats with function from aux_build.py
			candidate_text_subjects = list(filter(_filterSimpleSubjects, candidate_text_categories["subjects"])) # remove simple subjects with function from aux_build.py

			_saveFile(fileNameCandidateWikicats, '\n'.join(candidate_text_wikicats))  # save file with candidate text wikicats, one per line
			_saveFile(fileNameCandidateSubjects, '\n'.join(candidate_text_subjects))  # save file with candidate text subjects, one per line
			P4_numUrlsProcessed += 1

			# if no wikicats and no subjects, the page will not be used
			if (len(candidate_text_wikicats) == 0) and (len(candidate_text_subjects) == 0):
				listWithWKSB.append(rFileNameCandidate)  # we will compute both similarities even though there is no info (no wikicats and no subjects)
			else:
				listWithWKSB.append(rFileNameCandidate)

	endTime = datetime.now()
	elapsedTimeF4 = endTime - startTime

	lenListWithWKSB = len(listWithWKSB)

	_appendFile(logFilename, "Number of available pages with wikicats or subjects: "+str(lenListWithWKSB))

	print("\n","ALL WIKICATs AND SUBJECTs COMPUTED")
	print("New items processed in this iteration:", str(P4_numUrlsProcessed))
	print("Number of docs with wikicats or subjects:", str(lenListWithWKSB))
	print("Number of docs without wikicats nor subjects:", str(len(listWithoutWKSB)))
	print("Duration F4 (identifying wikicats):", str(elapsedTimeF4.seconds))

	# store listWithWKSB
	listWithWKSBFile =  lengthFolder+str(lenOriginalText)+".ph4.listWithWKSB"   # name of the file to store listWithWKSB
	_saveFile(listWithWKSBFile, '\n'.join(listWithWKSB))

	result["P4_numUrlsProcessed"] = P4_numUrlsProcessed
	result["P4_lenListWithWKSB"] = lenListWithWKSB
	result["P4_lenListWithoutWKSB"] = len(listWithoutWKSB)
	result["P4_elapsedTimeF4"] = elapsedTimeF4.seconds

	_appendFile(logFilename, "Available pages with wikicats: "+str(lenListWithWKSB))
	return result










# QUERY (/doPh5computeSimilarities)  to attend the query to compute similarities for candidate texts
# receives: the original text
# returns: the resulting data

def doPh5computeSimilarities():
	_Print("Requested Phase 5")

	fromStart = json.loads(request.values.get("fromStart"))
	P0_originalText = request.values.get("P0_originalText")
	lenOriginalText = len(P0_originalText)

	# in case execution from start, Phases 1-2-3-4  must be executed first
	if fromStart:
		resultPh1 = doPh1(P0_originalText)
		P1_selectedWikicats = resultPh1["P1_wikicats"]
		resultPh2 = doPh2(lenOriginalText, P1_selectedWikicats)
		resultPh3 = doPh3(lenOriginalText)
		resultPh4 = doPh4(lenOriginalText)
	else:
		P1_selectedWikicats = json.loads(request.values.get("P1_selectedWikicats"))   # get parameter with selected wikicats

	result = doPh5(P0_originalText, P1_selectedWikicats)
	if "error" in result:
		return jsonify(result);

	# in case execution from start, fields needed to present data in previous phases must be added to the answer
	if fromStart:
		result["P1_wikicats"] = P1_selectedWikicats
		result["P1_selectedWikicats"] = P1_selectedWikicats
		for w in P1_selectedWikicats:	# all the wikicats, selected or not
			components = resultPh1[w]["components"]
			db = resultPh2[w]["db"]
			wk = resultPh2[w]["wk"]
			result[w] = {"components": components, "db": db, "wk": wk}

		result["P2_totalDB"] = resultPh2["P2_totalDB"]
		result["P2_totalWK"] = resultPh2["P2_totalWK"]
		result["P2_totalUrls"] = resultPh2["P2_totalUrls"]

		result["P3_numUrlsDownloaded"] = resultPh3["P3_numUrlsDownloaded"]
		result["P3_lenListEnoughContent"] = resultPh3["P3_lenListEnoughContent"]
		result["P3_lenListNotEnoughContent"] = resultPh3["P3_lenListNotEnoughContent"]
		result["P3_elapsedTimeF3"] = resultPh3["P3_elapsedTimeF3"]

		result["P4_numUrlsProcessed"] = resultPh4["P4_numUrlsProcessed"]
		result["P4_lenListWithWKSB"] = resultPh4["P4_lenListWithWKSB"]
		result["P4_lenListWithoutWKSB"] = resultPh4["P4_lenListWithoutWKSB"]
		result["P4_elapsedTimeF4"] = resultPh4["P4_elapsedTimeF4"]

	return jsonify(result);




def doPh5(P0_originalText, P1_selectedWikicats):
	lenOriginalText = len(P0_originalText)
	lengthFolder = _CORPUS_FOLDER+str(lenOriginalText)+"/"

	logFilename = lengthFolder+str(lenOriginalText)+".log"
	_Print("Executing Phase 5")
	_appendFile(logFilename, "\n\nExecuting Phase 5")

	result = {}  # object to store the results to be returned to the request

	listWithWKSBFile =  lengthFolder+str(lenOriginalText)+".ph4.listWithWKSB"  # name of the file with listWithWKSB stored in previous phase

	try:  # try to read listWithWKSB file
		with _Open(listWithWKSBFile) as fp:
			listWithWKSB = fp.read().splitlines()
	except:
		result["error"]  = "No file "+listWithWKSBFile    # no file listWithWKSBFile
		return result

	lenListWithWKSB  = len(listWithWKSB)  # length of full list of candidate files to process


	# read the original text entities (E0) from local store, to later measure the quality of similarities
	filename_en = lengthFolder+str(lenOriginalText)+".ph1.en"   # filename for entities E0 (length.ph1.en)
	try:
		with _Open(filename_en) as fp:	# format    http://dbpedia.org/resource/Title
			listEntitiesOriginalText = fp.read().splitlines()

		listEntityTitlesOriginalText  = list(map(lambda x: x[1+x.rfind("/"):], listEntitiesOriginalText))	# keep only Title
		# add prefix and sufix to get format    en.wikipedia.org/wiki..Title.txt   DANGER!!!! may be not this way in future
		listEntityFilesOriginalText  = list(map(lambda x: "en.wikipedia.org/wiki.."+x+".txt", listEntityTitlesOriginalText))
	except:
		listEntityFilesOriginalText = []    # no entities for original text
		_Print("Entities file not available: "+filename_en)
		_appendFile(logFilename, "Entities file not available: "+filename_en)
		result["error"] = "doPh5 ERROR: Entities file not available: "+filename_en
		return result

	numEntitiesOriginalText = len(listEntityFilesOriginalText)
	_Print("numEntitiesOriginalText=", str(numEntitiesOriginalText))


	# read the original text subjects from local store
	filename_sb = lengthFolder+str(lenOriginalText)+".ph1.sb"   # filename for subjects (length.ph1.sb)
	try:
		with _Open(filename_sb) as fp:
			listSubjectsOriginalText = fp.read().splitlines()
	except:
		listSubjectsOriginalText = []    # no subjects for original text
		_Print("Subjects file not available: "+filename_sb)
		_appendFile(logFilename, "Subjects file not available: "+filename_sb)




	print("\n", "********** Computing similarities for", lenListWithWKSB, "candidate texts...", "\n")

	# variables to store results
	filenameSims = lengthFolder+str(lenOriginalText)+".ph5-1.sims.csv"  # file to store all similarities

	# to store jaccard wikicats/subjects similarity distribution
	distribution_wk = {"0":0, "1":0, "2":0, "3":0, "4":0, "5":0, "6":0, "7":0, "8":0, "9":0}
	distribution_sb = {"0":0, "1":0, "2":0, "3":0, "4":0, "5":0, "6":0, "7":0, "8":0, "9":0}


	# dict_sims_db and dict_sims_new: dicts to store all the similarities of all candidates to To
	# key: partial filename of candidate. Format = en.wikipedia.org/wiki..Dolno_Dupeni.txt
	# value: 6-tuple with the 6 similarity_to_To values
	dict_sims_db = {} # dict to read sims stored in local DB, in length.ph5-1.sims.csv
	dict_sims_new = {}  # dict to aggregate local DB sims and newly computed sims, for later updating local DB file

	# try to read existing sims file
	try:
		with _Open(filenameSims, 'r') as csvFile:
			reader = csv.reader(csvFile, delimiter=' ')
			next(reader)  # to skip header
			for row in reader:
				# row[0]=rDocName, row[1]=shared wk sim, row[2]=shared sb sim, row[3]=spaCy sim, row[4]=d2v sim, row[5] = euclidean sim, row[6] = full wk sim, row[7] = full sb sim
				dict_sims_db[row[0]] = (float(row[1]), float(row[2]), float(row[3]), float(row[4]), float(row[5]), float(row[6]), float(row[7]))

			csvFile.close()
	except:
		print("No similarities file")




	# Create a textSimilarityFunctions object to measure text similarities. It requires the original text, its wikicats and subjects.
	similarities = _textSimilarityFunctions(P0_originalText, P1_selectedWikicats, listSubjectsOriginalText, logFilename)

	# create object to measure Doc2Vec similarity with LEE_D2V_MODEL
	d2vLeeSimilarity = _Doc2VecSimilarity(_LEE_D2V_MODEL, P0_originalText)

	startTime = datetime.now()

	for idx, rFileNameCandidate in enumerate(listWithWKSB, start=1):  # format rFileNameCandidate = en.wikipedia.org/wiki..Title.txt
		if (idx % 5000) == 0:
			print(".", end=' ', flush=True)
		_Print("\n("+str(idx)+" of "+str(lenListWithWKSB)+") -- ", rFileNameCandidate)

		# Build filenames for this page
		fileNameCandidate = _SCRAPPED_PAGES_FOLDER+rFileNameCandidate   # format $HOME/KORPUS/SCRAPPED_PAGES/en.wikipedia.org/wiki..Title.txt
		fileNameCandidateBase = fileNameCandidate[:fileNameCandidate.rfind(".")]   # $HOME/KORPUS/SCRAPPED_PAGES/en.wikipedia.org/wiki..Title
		fileNameCandidateWikicats = fileNameCandidateBase+".wk"    # wikicats file for this doc  $HOME/KORPUS/SCRAPPED_PAGES/en.wikipedia.org/wiki..Title.wk
		fileNameCandidateSubjects = fileNameCandidateBase+".sb"    # subjects file for this doc  $HOME/KORPUS/SCRAPPED_PAGES/en.wikipedia.org/wiki..Title.sb

		# Now compute similarities. First, check if already stored in length.ph5-1.sims.csv (already read in dict_sims_db)
		try:
			sims = dict_sims_db[rFileNameCandidate] # if exists, return tuple with (wk_sim, sb_sim, spacy_sim, doc2vec_sim, euclidean_sim, full_wk_sim)
			_Print("Found already computed similarities for", rFileNameCandidate)
			full_wikicats_jaccard_sim = sims[0]
			full_subjects_jaccard_sim = sims[1]
			shared_wikicats_jaccard_sim = sims[2]
			shared_subjects_jaccard_sim = sims[3]
			spacy_sim = sims[4]
			d2v_lee_sim = sims[5]
			euclidean_sim = sims[6]


		except Exception as e:   # no sims found in local DB file, they must be computed
			_Print(str(idx)+". Sims not in local DB:", str(e))
			_appendFile(logFilename, "Sims not in local DB:"+str(e))

			# Measure the full wikicats jaccard similarity
			_Print("Computing full wikicats jaccard similarity for", rFileNameCandidate)
			full_wikicats_jaccard_sim = similarities.fullWikicatsJaccardSimilarity(fileNameCandidateWikicats)

			# Measure the full subjects jaccard similarity
			_Print("Computing full subjects jaccard similarity for", rFileNameCandidate)
			full_subjects_jaccard_sim = similarities.fullSubjectsJaccardSimilarity(fileNameCandidateSubjects)

			# Measure shared wikicats jaccard similarity (requires shared matching). Code -1 is returned if some error
			_Print("Computing shared wikicats similarity for", rFileNameCandidate)
			shared_wikicats_jaccard_sim = similarities.sharedWikicatsJaccardSimilarity(fileNameCandidateWikicats)
			if shared_wikicats_jaccard_sim < 0:
				_Print("ERROR computing sharedWikicatsJaccard ("+str(shared_wikicats_jaccard_sim)+"):", fileNameCandidateWikicats)
				_appendFile(logFilename, "ERROR computing sharedWikicatsJaccard: "+fileNameCandidateWikicats)
				continue

			# Measure shared subjects jaccard similarity (requires shared matching). Code -1 is returned if some error
			_Print("Computing shared subjects similarity for", rFileNameCandidate)
			shared_subjects_jaccard_sim = similarities.sharedSubjectsJaccardSimilarity(fileNameCandidateSubjects)
			if shared_subjects_jaccard_sim < 0:
				_Print("ERROR computing sharedSubjectsJaccard ("+str(shared_subjects_jaccard_sim)+"):", fileNameCandidateSubjects)
				_appendFile(logFilename, "ERROR computing sharedSubjectsJaccard: "+fileNameCandidateSubjects)
				continue

			# Measure the spaCy distance
			_Print("Computing spaCy similarity for", rFileNameCandidate)
			spacy_sim = similarities.spacyTextSimilarity(candidate_file=fileNameCandidate)

			# Measure the Doc2Vec (Lee) distance
			_Print("Computing Doc2Vec Lee similarity for", rFileNameCandidate)
			d2v_lee_sim = d2vLeeSimilarity.doc2VecTextSimilarity(candidate_file=fileNameCandidate)

			# Measure the euclidean distance using SKLEARN
			_Print("Computing Euclidean similarity for", rFileNameCandidate)
			euclidean_sim = similarities.euclideanTextSimilarity(candidate_file=fileNameCandidate)



		# all sims for this doc have been read or newly computed

		# add them to the dict_sims_new dict
		dict_sims_new[rFileNameCandidate] = (full_wikicats_jaccard_sim, full_subjects_jaccard_sim, shared_wikicats_jaccard_sim, shared_subjects_jaccard_sim, spacy_sim, d2v_lee_sim, euclidean_sim)

		_Print("Wikicats full jaccard similarity =", str(full_wikicats_jaccard_sim))
		_Print("Subjects full jaccard similarity =", str(full_subjects_jaccard_sim))
		_Print("Wikicats shared jaccard similarity =", str(shared_wikicats_jaccard_sim))
		_Print("Subjects shared jaccard similarity =", str(shared_subjects_jaccard_sim))
		_Print("Spacy similarity =", str(spacy_sim))
		_Print("Doc2Vec similarity =", str(d2v_lee_sim))
		_Print("Euclidean similarity =", str(euclidean_sim))


		# add this page value to compute distributions for shared wikicats and subjects jaccard

		if shared_wikicats_jaccard_sim < 0.1:
			distribution_wk["0"] = distribution_wk["0"] + 1
		elif shared_wikicats_jaccard_sim < 0.2:
			distribution_wk["1"] = distribution_wk["1"] + 1
		elif shared_wikicats_jaccard_sim < 0.3:
			distribution_wk["2"] = distribution_wk["2"] + 1
		elif shared_wikicats_jaccard_sim < 0.4:
			distribution_wk["3"] = distribution_wk["3"] + 1
		elif shared_wikicats_jaccard_sim < 0.5:
			distribution_wk["4"] = distribution_wk["4"] + 1
		elif shared_wikicats_jaccard_sim < 0.6:
			distribution_wk["5"] = distribution_wk["5"] + 1
		elif shared_wikicats_jaccard_sim < 0.7:
			distribution_wk["6"] = distribution_wk["6"] + 1
		elif shared_wikicats_jaccard_sim < 0.8:
			distribution_wk["7"] = distribution_wk["7"] + 1
		elif shared_wikicats_jaccard_sim < 0.9:
			distribution_wk["8"] = distribution_wk["8"] + 1
		else:
			distribution_wk["9"] = distribution_wk["9"] + 1


		if shared_subjects_jaccard_sim < 0.1:
			distribution_sb["0"] = distribution_sb["0"] + 1
		elif shared_subjects_jaccard_sim < 0.2:
			distribution_sb["1"] = distribution_sb["1"] + 1
		elif shared_subjects_jaccard_sim < 0.3:
			distribution_sb["2"] = distribution_sb["2"] + 1
		elif shared_subjects_jaccard_sim < 0.4:
			distribution_sb["3"] = distribution_sb["3"] + 1
		elif shared_subjects_jaccard_sim < 0.5:
			distribution_sb["4"] = distribution_sb["4"] + 1
		elif shared_subjects_jaccard_sim < 0.6:
			distribution_sb["5"] = distribution_sb["5"] + 1
		elif shared_subjects_jaccard_sim < 0.7:
			distribution_sb["6"] = distribution_sb["6"] + 1
		elif shared_subjects_jaccard_sim < 0.8:
			distribution_sb["7"] = distribution_sb["7"] + 1
		elif shared_subjects_jaccard_sim < 0.9:
			distribution_sb["8"] = distribution_sb["8"] + 1
		else:
			distribution_sb["9"] = distribution_sb["9"] + 1

	# end of loop for docs similarity computing

	endTime = datetime.now()
	elapsedTimeF5 = endTime - startTime


	print("\n\n", "Duration F5 (computing similarities):", str(elapsedTimeF5.seconds))


	# Update the csv file with all similarities
	with _Open(filenameSims, 'w') as csvFile:
		fieldnames = ['Page', 'Fwikicats', 'Fsubjects', 'Swikicats', 'Ssubjects', 'Spacy', 'Doc2vec-Lee', 'Euclidean']	# Name columns
		writer = csv.DictWriter(csvFile, fieldnames=fieldnames, delimiter=" ") # Create csv headers
		writer.writeheader()	# Write the column headers

		writer = csv.writer(csvFile, delimiter=' ')
		for key in dict_sims_new:
			try:
				sims = dict_sims_new[key]
				writer.writerow([key, sims[0], sims[1], sims[2], sims[3], sims[4], sims[5], sims[6]])
			except Exception as e:
				print("Error writing csv with similarities ("+str(e)+"):", row)
				_appendFile(logFilename, "Error writing csv with similarities  ("+str(e)+"):"+str(row))

		csvFile.close()





	# compute ratings for similarities to eval their quality and select the one that we will use

	listRatings = []  # list of tuplas (sim name, sim rating) to be able to order sims by rating
	ratings = {}	# dict to store rating info for all sims
	# ratings[sim] is also a dict
	# ratings[sim]["orderedList"] --> list of 2-tuplas (name,sim) with all candidates ordered by sim
	# ratings[sim]["originalEntities"] --> list of 2-tuplas (entityName, pos) with all the E0 entities ordered by pos
	# ratings[sim]["average"]

	# convert dict_sims_new in list of tuplas (filenameCandidate, simFullWikicats, simFullSubjects, simSharedWikicats, simSharedSubjects, simSpacy, simD2V-Lee, simEuclidean) to be able to order them
	list_sims_tuplas = [ (k, dict_sims_new[k][0], dict_sims_new[k][1], dict_sims_new[k][2], dict_sims_new[k][3], dict_sims_new[k][4], dict_sims_new[k][5], dict_sims_new[k][6]) for k in dict_sims_new]


	# compute ratings for a general sim
	# fills the ratings dict for the received key

	def computeRating(indexSim, nameSim):
		listEntities = listEntityFilesOriginalText.copy() # make a copy of the list E0 (list of entities in the original text, with format en.wikipedia.org/wiki..Title.txt)
		# _SortTuplaList_byPosTupla: function to order a list of tuplas (0,1,2,3,4,5,6,7...) by the element in the position 'pos'=1,2...
		listOrdered = _SortTuplaList_byPosTupla(list_sims_tuplas, indexSim)  # order sims list by indexSim similarity
		listOrdered_Names_Sims  = list(map(lambda x: (x[0], x[indexSim]), listOrdered)) # keep only the names of the docs and its indexedSim similarity
		ratings[nameSim] = {}
		ratings[nameSim]["orderedList"] = listOrdered_Names_Sims
		ratings[nameSim]["originalEntities"] = []  # list of pairs (entity, position)
		listOrdered_OnlyNames = list(map(lambda x: x[0], listOrdered_Names_Sims))  # keep only the names of the docs

		for idx, name in enumerate(listOrdered_OnlyNames, start=1):
			if name in listEntities:  # one entity of the original text found in list
				ratings[nameSim]["originalEntities"].append((name, idx))
			if len(ratings[nameSim]["originalEntities"]) == len(listEntities):  # all entities of the original text have been found in the list
				break

		listPositions = [pos for name,pos in ratings[nameSim]["originalEntities"]]   # get a list with all the positions of the entities
		averagePosition = sum(listPositions) / len(listPositions)  # average position

		ratings[nameSim]["average"]  = averagePosition

		ratingSim = numEntitiesOriginalText / averagePosition
		listRatings.append((nameSim, ratingSim))  # add rating for sim1 to the list

		return

	computeRating(1, "Fwikicats")
	computeRating(2, "Fsubjects")
	computeRating(3, "Swikicats")
	computeRating(4, "Ssubjects")
	computeRating(5, "Spacy")
	computeRating(6, "Doc2vec-Lee")
	computeRating(7, "Euclidean")



	# name of the file to save the positions of E0 entities for all sims, used for measure rating quality
	fileE0entitiesPositions = lengthFolder+str(lenOriginalText)+".ph5-2.entities.positions.csv"

	E0entitiesPositions = {}  # dict with an entry for each entity, a 6-tupla with the positions for each sim

	# build dict E0entitiesPositions to store the 7-possitions for every entity E0
	# range over list of tuplas (name_E0entity, position_in_this sim)
	# it is only to process all names, idx is irrelevant
	# next(i for (n,i) in ratings["Fwikicats"]["originalEntities"] if n == name) --> i of first tupla where n == name
	for name, idx in ratings["Fwikicats"]["originalEntities"]:
		# dict with an entry for each entity, a 7-tupla with the positions for each sim
		E0entitiesPositions[name] = (next(i for (n,i) in ratings["Fwikicats"]["originalEntities"] if n == name), next(i for (n,i) in ratings["Fsubjects"]["originalEntities"] if n == name),\
									next(i for (n,i) in ratings["Swikicats"]["originalEntities"] if n == name), next(i for (n,i) in ratings["Ssubjects"]["originalEntities"] if n == name),\
									next(i for (n,i) in ratings["Spacy"]["originalEntities"] if n == name), next(i for (n,i) in ratings["Doc2vec-Lee"]["originalEntities"] if n == name), \
									next(i for (n,i) in ratings["Euclidean"]["originalEntities"] if n == name))


	# store all positions of E0 entities in a file
	with _Open(fileE0entitiesPositions, 'w') as csvFile:
		fieldnames = ['Entity', 'Fwikicats', 'Fsubjects', 'Swikicats', 'Ssubjects', 'Spacy', 'Doc2vec-Lee', 'Euclidean']	# Name columns
		writer = csv.DictWriter(csvFile, fieldnames=fieldnames, delimiter=" ") # Create csv headers
		writer.writeheader()	# Write the column headers

		writer = csv.writer(csvFile, delimiter=' ')
		for key in E0entitiesPositions:
			try:
				writer.writerow([key, E0entitiesPositions[key][0], E0entitiesPositions[key][1], E0entitiesPositions[key][2], E0entitiesPositions[key][3], E0entitiesPositions[key][4], E0entitiesPositions[key][5], E0entitiesPositions[key][6]])
			except:
				print("Error writing csv with entities E0 positions", row)
				_appendFile(logFilename, "Error writing csv with entities E0 positions"+str(row))

		csvFile.close()


	# print the position of all the entities for each sim (shown ordered, because they are appended in order), and the average
	for key in ratings:
		print("\n**", key)
		for (page,idx)  in ratings[key]["originalEntities"]:
			print(page, "=", idx)
		print("## Average=", ratings[key]["average"])


	# select the best similarity (higher rating)
	listRatingsOrdered = _SortTuplaList_byPosTupla(listRatings, 1)

	bestRating = listRatingsOrdered[0]
	nameBestRating = bestRating[0]

	result["P5_bestSim"] = nameBestRating+" ("+str(ratings[nameBestRating]["average"])+")"

	print("\nBest Sim = ", nameBestRating+" ("+str(ratings[nameBestRating]["average"])+")")

	result["P5_ratings"] = ""

	for key in ratings:
		result["P5_ratings"] = result["P5_ratings"] + key + "="+str(ratings[key]["average"])
		if key !=  list(ratings.keys())[-1]:
			result["P5_ratings"] = result["P5_ratings"] + ", "


	# list of sims for best Similarity
	listSimsBest = ratings[nameBestRating]["orderedList"]  # select the list of the best sim


	# file to store sims for best similarity
	filenameSimsBest = lengthFolder+str(lenOriginalText)+".ph5-3.simsBest.csv"  # file to store sims for best similarity

	with _Open(filenameSimsBest, 'w') as csvFile:
		fieldnames = ['Doc', nameBestRating]	# Name columns
		writer = csv.DictWriter(csvFile, fieldnames=fieldnames, delimiter=" ") # Create csv headers
		writer.writeheader()	# Write the column headers

		writer = csv.writer(csvFile, delimiter=' ')
		for row in listSimsBest:
			try:
				writer.writerow([row[0], row[1]])   # store (doc, sim)
			except:
				print("Error writing csv with sims for best similarity", row)
				_appendFile(logFilename, "Error writing csv with sims for best similarity"+str(row))

		csvFile.close()

	printSimsDistribution(lenListWithWKSB, distribution_wk, distribution_sb)

	result["P5_elapsedTimeF5"] = elapsedTimeF5.seconds

	_appendFile(logFilename, "Used sim: "+nameBestRating)
	return result







# QUERY (/doPh6trainD2V) to attend the query to train the Doc2Vec network
# receives:
# * the list of corpus docs
# returns:

def doPh6trainD2V():
	_Print("Requested Phase 6")

	fromStart = json.loads(request.values.get("fromStart"))
	P0_originalText = request.values.get("P0_originalText")
	P5_pctgeInitialCorpus = int(request.values.get("P5_pctgeInitialCorpus"))

	lenOriginalText = len(P0_originalText)
	lengthFolder = _CORPUS_FOLDER+str(lenOriginalText)+"/"

	# in case execution from start, Phases 1-2-3-4-5  must be executed first
	if fromStart:
		resultPh1 = doPh1(P0_originalText)
		P1_selectedWikicats = resultPh1["P1_wikicats"]
		resultPh2 = doPh2(lenOriginalText, P1_selectedWikicats)
		resultPh3 = doPh3(lenOriginalText)
		resultPh4 = doPh4(lenOriginalText)
		resultPh5 = doPh5(P0_originalText, P1_selectedWikicats)

	result = doPh6(lenOriginalText, P5_pctgeInitialCorpus)
	if "error" in result:
		return jsonify(result);

	# in case execution from start, fields needed to present data in previous phases must be added to the answer
	if fromStart:
		result["P1_wikicats"] = P1_selectedWikicats
		result["P1_selectedWikicats"] = P1_selectedWikicats
		for w in P1_selectedWikicats:	# all the wikicats, selected or not
			components = resultPh1[w]["components"]
			db = resultPh2[w]["db"]
			wk = resultPh2[w]["wk"]
			result[w] = {"components": components, "db": db, "wk": wk}

		result["P2_totalDB"] = resultPh2["P2_totalDB"]
		result["P2_totalWK"] = resultPh2["P2_totalWK"]
		result["P2_totalUrls"] = resultPh2["P2_totalUrls"]

		result["P3_numUrlsDownloaded"] = resultPh3["P3_numUrlsDownloaded"]
		result["P3_lenListEnoughContent"] = resultPh3["P3_lenListEnoughContent"]
		result["P3_lenListNotEnoughContent"] = resultPh3["P3_lenListNotEnoughContent"]
		result["P3_elapsedTimeF3"] = resultPh3["P3_elapsedTimeF3"]

		result["P4_numUrlsProcessed"] = resultPh4["P4_numUrlsProcessed"]
		result["P4_lenListWithWKSB"] = resultPh4["P4_lenListWithWKSB"]
		result["P4_lenListWithoutWKSB"] = resultPh4["P4_lenListWithoutWKSB"]
		result["P4_elapsedTimeF4"] = resultPh4["P4_elapsedTimeF4"]

		result["P5_bestSim"] = resultPh5["P5_bestSim"]
		result["P5_ratings"] = resultPh5["P5_ratings"]
		result["P5_elapsedTimeF5"] = resultPh5["P5_elapsedTimeF5"]

	return jsonify(result);



def doPh6(lenOriginalText, P5_pctgeInitialCorpus):

	lengthFolder = _CORPUS_FOLDER+str(lenOriginalText)+"/"

	logFilename = lengthFolder+str(lenOriginalText)+".log"
	_Print("Executing Phase 6")
	_appendFile(logFilename, "\n\nExecuting Phase 6")

	result = {}  # object to store the results to be returned to the request

	listDocs = []
	listDocsSimsFile =  lengthFolder+str(lenOriginalText)+".ph5-3.simsBest.csv"

	# try to read existing sims file
	try:
		with _Open(listDocsSimsFile, 'r') as csvFile:
			reader = csv.reader(csvFile, delimiter=' ')
			next(reader)  # to skip header
			for row in reader:
				# row[0]=rDocName, row[1]=sim
				listDocs.append(row[0])

			csvFile.close()
	except:
		print("No sims file for best similarity")

	lenListDocs = len(listDocs)
	sizeCorpus = int(lenListDocs / (100 / P5_pctgeInitialCorpus))

	listDocsCorpus = listDocs[:sizeCorpus]
	listDocsCorpus = list(map(lambda x: _SCRAPPED_PAGES_FOLDER+x, listDocsCorpus))   # get the absolute names

	# store listDocsCorpus
	listDocsCorpusFile =  lengthFolder+str(lenOriginalText)+".ph6."+str(P5_pctgeInitialCorpus)+".listDocsCorpus"
	_saveFile(listDocsCorpusFile, '\n'.join(listDocsCorpus))


    # initial corpus ready, do preprocessing
	startTime = datetime.now()

	_Print("Training with ", str(sizeCorpus), "documents")

	try:
		_Print("Processing S1...")
		np1 = _processS1List(lengthFolder, listDocsCorpus)  # creates corspusFolder/length/files_s_p_w and saves .s files

		_Print("Processing S2...")
		listDocsS = list(map(lambda x: lengthFolder+"files_s_p_w/"+x[(1+x.rfind("/")):]+".s", listDocsCorpus))
		np2 = _processS2List(listDocsS)

		_Print("Processing S3...")
		np3 = _processS3List(listDocsS)

		_Print("Processing S4...")
		listDocsW = list(map(lambda x: x+".w", listDocsS))
		np4 = _processS4List(listDocsW, lengthFolder)  # WARNING!! requires Standord CoreNLP server launched

		np = np1+np2+np3+np4

		endTime = datetime.now()
		elapsedTimeF61 = endTime - startTime
		startTime = datetime.now()

		# let's train

		vector_size = 20	# vector_size (int, optional) – Dimensionality of the feature vectors
		window = 8	# window (int, optional) – The maximum distance between the current and predicted word within a sentence
		alpha = 0.025	# alpha (float, optional) – The initial learning rate
		min_alpha = 0.00025	# min_alpha (float, optional) – Learning rate will linearly drop to min_alpha as training progresses
		# seed = 1 # Seed for the random number generator. Initial vectors for each word are seeded with a hash of the concatenation of word + str(seed)
		min_count = 5	# min_count (int, optional) – Ignores all words with total frequency lower than this
		max_vocab_size = None	# max_vocab_size (int, optional) – Limits the RAM during vocabulary building
		distributed_memory = 1	# Defines the training algorithm. If dm=1, ‘distributed memory’ (PV-DM). Otherwise, distributed bag of words (PV-DBOW)
		epochs = 100	# epochs (int, optional) – Number of iterations (epochs) over the corpus


		modelFilename = str(lenOriginalText)+ "-t."+str(P5_pctgeInitialCorpus)+".model"
		globalModelFilename =  _MODELS_FOLDER+modelFilename

		if os.path.exists(globalModelFilename) and np == 0:
			print("No changes, training not necessary for "+modelFilename+"!!")
		else:
			listDocsT = list(map(lambda x: lengthFolder+"files_t/"+x[(1+x.rfind("/")):]+".t", listDocsW))
			# Build a doc2vec model trained with files in list
			r = _buildDoc2VecModelFromList(listDocsT, globalModelFilename, vector_size, window, alpha, min_alpha, min_count, distributed_memory, epochs)

			if (r == 0):
				print("Training success!!")
			else:
				print("Training failed!")


		result["P6_elapsedTimeF61"] = elapsedTimeF61.seconds
	except Exception as e:
		result["error"] = str(e)
		print("Exception in doPh6:", str(e))
		_appendFile(logFilename, "Exception in doPh6: "+str(e))
		return result

	endTime = datetime.now()
	elapsedTimeF62 = endTime - startTime

	result["P6_elapsedTimeF62"] = elapsedTimeF62.seconds
	result["P6_modelName"] = modelFilename

	_appendFile(logFilename, "Computed model: "+modelFilename)
	return result






# QUERY (/doPh7reviewCorpus) to attend the query to review the corpus with D2V similarity
# receives:
# *
# returns:

def doPh7reviewCorpus():
	_Print("Requested Phase 7")

	fromStart = json.loads(request.values.get("fromStart"))
	P0_originalText = request.values.get("P0_originalText")
	lenOriginalText = len(P0_originalText)

	# in case execution from start, Phases 1-2-3-4-5-6  must be executed first
	if fromStart:
		resultPh1 = doPh1(P0_originalText)
		P1_selectedWikicats = resultPh1["P1_wikicats"]
		resultPh2 = doPh2(lenOriginalText, P1_selectedWikicats)
		resultPh3 = doPh3(lenOriginalText)
		resultPh4 = doPh4(lenOriginalText)
		resultPh5 = doPh5(P0_originalText, P1_selectedWikicats)
		resultPh6 = doPh6(lenOriginalText)
		P6_modelName = resultPh6["P6_modelName"]
	else:
		P6_modelName = request.values.get("P6_modelName")

	result = doPh7(P0_originalText, P6_modelName)
	if "error" in result:
		return jsonify(result);

	# in case execution from start, fields needed to present data in previous phases must be added to the answer
	if fromStart:
		result["P1_wikicats"] = P1_selectedWikicats
		result["P1_selectedWikicats"] = P1_selectedWikicats
		for w in P1_selectedWikicats:	# all the wikicats, selected or not
			components = resultPh1[w]["components"]
			db = resultPh2[w]["db"]
			wk = resultPh2[w]["wk"]
			result[w] = {"components": components, "db": db, "wk": wk}

		result["P2_totalDB"] = resultPh2["P2_totalDB"]
		result["P2_totalWK"] = resultPh2["P2_totalWK"]
		result["P2_totalUrls"] = resultPh2["P2_totalUrls"]

		result["P3_numUrlsDownloaded"] = resultPh3["P3_numUrlsDownloaded"]
		result["P3_lenListEnoughContent"] = resultPh3["P3_lenListEnoughContent"]
		result["P3_lenListNotEnoughContent"] = resultPh3["P3_lenListNotEnoughContent"]
		result["P3_elapsedTimeF3"] = resultPh3["P3_elapsedTimeF3"]

		result["P4_numUrlsProcessed"] = resultPh4["P4_numUrlsProcessed"]
		result["P4_lenListWithWKSB"] = resultPh4["P4_lenListWithWKSB"]
		result["P4_lenListWithoutWKSB"] = resultPh4["P4_lenListWithoutWKSB"]
		result["P4_elapsedTimeF4"] = resultPh4["P4_elapsedTimeF4"]

		result["P5_bestSim"] = resultPh5["P5_bestSim"]
		result["P5_ratings"] = resultPh5["P5_ratings"]
		result["P5_elapsedTimeF5"] = resultPh5["P5_elapsedTimeF5"]

		result["P6_elapsedTimeF61"] = resultPh6["P6_elapsedTimeF61"]
		result["P6_elapsedTimeF62"] = resultPh6["P6_elapsedTimeF62"]
		result["P6_modelName"] = P6_modelName

	return jsonify(result);



def doPh7(P0_originalText, P6_modelName):

	lenOriginalText = len(P0_originalText)
	lengthFolder = _CORPUS_FOLDER+str(lenOriginalText)+"/"

	logFilename = lengthFolder+str(lenOriginalText)+".log"
	_Print("Executing Phase 7")
	_appendFile(logFilename, "\n\nExecuting Phase 7")

	result = {}  # object to store the results to be returned to the request

	modelFilename = _MODELS_FOLDER+P6_modelName

	# try to read existing AdHocD2VSims file for such model
	filenameAdHocD2VSims = lengthFolder+str(lenOriginalText)+".ph7.AdHocD2V."+P6_modelName+".sims.csv"
	simsAdHocD2V = {} # dict to read AdHoc D2V sims stored in local DB (sims computed with the ad hoc trained model)

	# ONLY if model exists and it is previous to this file?
	try:
		with _Open(filenameAdHocD2VSims, 'r') as csvFile:
			reader = csv.reader(csvFile, delimiter=' ')
			next(reader)  # to skip header
			for row in reader:
				simsAdHocD2V[row[0]] = float(row[1])

			csvFile.close()
	except:
		print("No ad hoc D2V similarities file")


	d2vSimilarity = _Doc2VecSimilarity(modelFilename, P0_originalText)

	listWithWKSBFile =  lengthFolder+str(lenOriginalText)+".ph4.listWithWKSB"

	try:  # try to read listWithWKSB file
		with _Open(listWithWKSBFile) as fp:
			listWithWKSB = fp.read().splitlines()
	except:
		result["error"]  = "No file "+listWithWKSBFile    # no file listWithWKSBFile
		return result

	lenListWithWKSB = len(listWithWKSB)

	_Print("Reviewing corpus ("+str(lenListWithWKSB)+" files) with Doc2Vec similarity derived from model:", P6_modelName)
	startTime = datetime.now()

	for idx, rCandidateFile in enumerate(listWithWKSB, start=1):
		if (idx % 5000) == 0:
			print(".", end=' ', flush=True)
		_Print("("+str(idx)+" of "+str(lenListWithWKSB)+") -- ", rCandidateFile)

		if rCandidateFile in simsAdHocD2V:
			_Print("Ad hoc D2V similarity found for candidate in local DB:", rCandidateFile)
			doc2vec_trained_cosineSimilarity = simsAdHocD2V[rCandidateFile]
		else:
			_Print("Computing ad hoc D2V similarity for candidate:", rCandidateFile)
			candidateFile = _SCRAPPED_PAGES_FOLDER+rCandidateFile
			candidateTextFD = _Open(candidateFile, "r")
			candidateText = candidateTextFD.read()
			doc2vec_trained_cosineSimilarity = d2vSimilarity.doc2VecTextSimilarity(candidate_text=candidateText)
			simsAdHocD2V[rCandidateFile] = doc2vec_trained_cosineSimilarity

		print("Ad hoc D2V similarity =", doc2vec_trained_cosineSimilarity)

	endTime = datetime.now()
	elapsedTimeF7 = endTime - startTime

	# Update the csv file with all ad hoc D2V similarities

	with _Open(filenameAdHocD2VSims, 'w') as csvFile:
		fieldnames = ['Text', 'AdHocD2V']	# Name columns
		writer = csv.DictWriter(csvFile, fieldnames=fieldnames, delimiter=" ") # Create csv headers
		writer.writeheader()	# Write the column headers

		writer = csv.writer(csvFile, delimiter=' ')
		for key in simsAdHocD2V:
			try:
				writer.writerow([key, simsAdHocD2V[key]])
			except:
				print("Error writing csv with ad hoc D2V similarities", row)
				_appendFile(logFilename, "Error writing csv with ad hoc D2V similarities"+str(row))

		csvFile.close()

	_appendFile(logFilename, "List of sims with ad hoc D2V computed: "+filenameAdHocD2VSims)

	result["P7_elapsedTimeF7"] = elapsedTimeF7.seconds

	# read the original text entities (E0) from local store, to measure the quality of ad hoc D2V results
	filename_en = lengthFolder+str(lenOriginalText)+".ph1.en"   # filename for entities E0 (length.ph1.en)
	try:
		with _Open(filename_en) as fp:	# format    http://dbpedia.org/resource/Title
			listEntitiesOriginalText = fp.read().splitlines()

		listEntityTitlesOriginalText  = list(map(lambda x: x[1+x.rfind("/"):], listEntitiesOriginalText))	# keep only Title
		# add prefix and sufix to get format    en.wikipedia.org/wiki..Title.txt   DANGER!!!! may be not this way in future
		listEntityFilesOriginalText  = list(map(lambda x: "en.wikipedia.org/wiki.."+x+".txt", listEntityTitlesOriginalText))
	except:
		listEntityFilesOriginalText = []    # no entities for original text
		_Print("Entities file not available: "+filename_en)
		_appendFile(logFilename, "Entities file not available: "+filename_en)
		result["error"] = "doPh5 ERROR: E0 Entities file not available: "+filename_en
		return result

	numEntitiesOriginalText = len(listEntityFilesOriginalText)
	_Print("numEntitiesOriginalText=", str(numEntitiesOriginalText))




	# convert dict simsAdHocD2V in list of tuplas (filenameCandidate, simAdHocD2V) to be able to order it
	list_sim_tupla = [ (k, simsAdHocD2V[k]) for k in simsAdHocD2V]

	#listEntities = listEntityFilesOriginalText.copy() # make a copy of the list E0 (list of entities in the original text, with format en.wikipedia.org/wiki..Title.txt)
	# _SortTuplaList_byPosTupla: function to order a list of tuplas (0,1,2,3,4,5,6,7...) by the element in the position 'pos'=1,2...
	listOrdered = _SortTuplaList_byPosTupla(list_sim_tupla, 1)  # order sims list by ad hoc d2v similarity
	listOrdered_OnlyNames = list(map(lambda x: x[0], listOrdered))  # keep only the names of the docs

	positions = [] # list of pairs (entity, position)

	for idx, name in enumerate(listOrdered_OnlyNames, start=1):
		if name in listEntityFilesOriginalText:  # one entity of the original text found in list
			positions.append((name, idx))
		if len(positions) == len(listEntityFilesOriginalText):  # all entities of the original text have been found in the list
			break

	for name, pos in positions:
		print(name,"=",pos)

	listPositions = [pos for name,pos in positions]   # get a list with all the positions of the entities

	if len(listPositions) == 0:
		averagePosition = -1
	else:
		averagePosition = sum(listPositions) / len(listPositions)  # average position

	result["P7_adhocD2Vaverage"] = averagePosition

	_Print("Ad hoc D2V average for "+P6_modelName+" =", str(averagePosition))

	return result







# to print similarity results distributions
def printSimsDistribution (lenListWithWKSB, distribution_wk, distribution_sb):

	# print distributions
	t0 = distribution_wk["0"]
	p0 = 100*t0/lenListWithWKSB

	t1 = distribution_wk["1"]
	p1 = 100*t1/lenListWithWKSB
	t1a = t0+t1
	p1a = 100*t1a/lenListWithWKSB

	t2 = distribution_wk["2"]
	p2 = 100*t2/lenListWithWKSB
	t2a = t1a+t2
	p2a = 100*t2a/lenListWithWKSB

	t3 = distribution_wk["3"]
	p3 = 100*t3/lenListWithWKSB
	t3a = t2a+t3
	p3a = 100*t3a/lenListWithWKSB

	t4 = distribution_wk["4"]
	p4 = 100*t4/lenListWithWKSB
	t4a = t3a+t4
	p4a = 100*t4a/lenListWithWKSB

	t5 = distribution_wk["5"]
	p5 = 100*t5/lenListWithWKSB
	t5a = t4a+t5
	p5a = 100*t5a/lenListWithWKSB

	t6 = distribution_wk["6"]
	p6 = 100*t6/lenListWithWKSB
	t6a = t5a+t6
	p6a = 100*t6a/lenListWithWKSB

	t7 = distribution_wk["7"]
	p7 = 100*t7/lenListWithWKSB
	t7a = t6a+t7
	p7a = 100*t7a/lenListWithWKSB

	t8 = distribution_wk["8"]
	p8 = 100*t8/lenListWithWKSB
	t8a = t7a+t8
	p8a = 100*t8a/lenListWithWKSB

	t9 = distribution_wk["9"]
	p9 = 100*t9/lenListWithWKSB
	t9a = t8a+t9
	p9a = 100*t9a/lenListWithWKSB

	print("\nTOTAL WIKICATS = ", lenListWithWKSB)
	print("0: %6d - %8.2f - %8.2f" % (t0, p0, p0))
	print("1: %6d - %8.2f - %8.2f" % (t1, p1, p1a))
	print("2: %6d - %8.2f - %8.2f" % (t2, p2, p2a))
	print("3: %6d - %8.2f - %8.2f" % (t3, p3, p3a))
	print("4: %6d - %8.2f - %8.2f" % (t4, p4, p4a))
	print("5: %6d - %8.2f - %8.2f" % (t5, p5, p5a))
	print("6: %6d - %8.2f - %8.2f" % (t6, p6, p6a))
	print("7: %6d - %8.2f - %8.2f" % (t7, p7, p7a))
	print("8: %6d - %8.2f - %8.2f" % (t8, p8, p8a))
	print("9: %6d - %8.2f - %8.2f" % (t9, p9, p9a))



	t0 = distribution_sb["0"]
	p0 = 100*t0/lenListWithWKSB

	t1 = distribution_sb["1"]
	p1 = 100*t1/lenListWithWKSB
	t1a = t0+t1
	p1a = 100*t1a/lenListWithWKSB

	t2 = distribution_sb["2"]
	p2 = 100*t2/lenListWithWKSB
	t2a = t1a+t2
	p2a = 100*t2a/lenListWithWKSB

	t3 = distribution_sb["3"]
	p3 = 100*t3/lenListWithWKSB
	t3a = t2a+t3
	p3a = 100*t3a/lenListWithWKSB

	t4 = distribution_sb["4"]
	p4 = 100*t4/lenListWithWKSB
	t4a = t3a+t4
	p4a = 100*t4a/lenListWithWKSB

	t5 = distribution_sb["5"]
	p5 = 100*t5/lenListWithWKSB
	t5a = t4a+t5
	p5a = 100*t5a/lenListWithWKSB

	t6 = distribution_sb["6"]
	p6 = 100*t6/lenListWithWKSB
	t6a = t5a+t6
	p6a = 100*t6a/lenListWithWKSB

	t7 = distribution_sb["7"]
	p7 = 100*t7/lenListWithWKSB
	t7a = t6a+t7
	p7a = 100*t7a/lenListWithWKSB

	t8 = distribution_sb["8"]
	p8 = 100*t8/lenListWithWKSB
	t8a = t7a+t8
	p8a = 100*t8a/lenListWithWKSB

	t9 = distribution_sb["9"]
	p9 = 100*t9/lenListWithWKSB
	t9a = t8a+t9
	p9a = 100*t9a/lenListWithWKSB

	print("TOTAL SUBJECTS = ", lenListWithWKSB)
	print("0: %6d - %8.2f - %8.2f" % (t0, p0, p0))
	print("1: %6d - %8.2f - %8.2f" % (t1, p1, p1a))
	print("2: %6d - %8.2f - %8.2f" % (t2, p2, p2a))
	print("3: %6d - %8.2f - %8.2f" % (t3, p3, p3a))
	print("4: %6d - %8.2f - %8.2f" % (t4, p4, p4a))
	print("5: %6d - %8.2f - %8.2f" % (t5, p5, p5a))
	print("6: %6d - %8.2f - %8.2f" % (t6, p6, p6a))
	print("7: %6d - %8.2f - %8.2f" % (t7, p7, p7a))
	print("8: %6d - %8.2f - %8.2f" % (t8, p8, p8a))
	print("9: %6d - %8.2f - %8.2f" % (t9, p9, p9a))

	return










#############################################################################################################################################



# aux function to discover all the URLs associated to any wikicat from the set of selected wikicats
# Receives:
# - P1_selectedWikicats: set of selected wikicats
# - logFilename: filename to save errors
# For each wikicat, if there is a file for such wikicat, it is read for returning contents
# Otherwise, it connects to Internet to query DB and WK and parse the results to return, after storing them locally
# it returns a dictionary entry for each wikicat   urlsObjects[wikicat] = {"db": urlsDB, "wk": urlsWK}
# urlsDB and urlsWK are lists of URLs

def getUrlsLinked2Wikicats (P1_selectedWikicats, logFilename):

	futureSession = FuturesSession()  # to manage asynchronous requests

	# first phase, reading files or start requests for DBpedia and Wikidata foreach wikicat

	requestObjects = {} # dictionary to store request objects

	for wikicat in P1_selectedWikicats:

		# first, read (or start query to fetch) Wikicat results for DBpedia

		filename_db = _URLs_FOLDER+"_Wikicat_"+wikicat+"_DB_Urls.txt"
		requestDone = 0  # to control if some request has been done, and if so, set a delay to not overload servers

		try:  # try to read URLs for this wikicat from local store
			with _Open(filename_db) as fp:
				urls_from_DB = fp.read().splitlines()
				_Print("File already available:", filename_db)
				requestObjects[wikicat] = {"dburls": urls_from_DB}  # store the local available DB URLs for this wikicat
		except:  # fetch data from DB
			fullWikicat = "Wikicat"+wikicat # the real name of the wikicat always start by the prefix "Wikicat"

			# launch asynchronous query to dbpedia
			# search for entities with the triplet     ?url  rdf:type yago:Wikicatwikicat
			# request only URLs being primary topic of some dbpedia entity
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
				requestDB = futureSession.post(_URL_DB, data={"query": queryDB}, headers={"accept": "application/json"})
				requestDone = 1
			except Exception as exc:
				print("*** ERROR getUrlsLinked2Wikicats(): Error starting DB query for", wikicat, ":", exc)
				_appendFile(logFilename, "ERROR getUrlsLinked2Wikicats(): Error starting DB query for "+wikicat+": "+repr(exc))
				requestDB = None

			requestObjects[wikicat] = {"db": requestDB}  # store the request DB object for this wikicat, None if some error


		# second, read (or start query to fetch) Wikicat results for Wikidata

		filename_wk = _URLs_FOLDER+"_Wikicat_"+wikicat+"_WK_Urls.txt"

		# it uses update with the objects dictionary, as the wikicat key has been already created for DBpedia

		try:  # try to read URLs for this wikicat from local store
			with _Open(filename_wk) as fp:
				urls_from_WK = fp.read().splitlines()
				_Print("File already available:", filename_wk)
				requestObjects[wikicat].update({"wkurls": urls_from_WK})  # store the local available WK URLs for this wikicat
		except:  # fetch data from WK

			# search for the not stopwords components of each wikicat. E.g. MunicipalitiesOfPeloponnese(region) --> search for "Municipalities Peloponnese region""
			wcs = _getWikicatComponents(wikicat)
			wcs_string = " ".join(wcs)
			_Print("wcs_string=", wcs_string)

			# launch asynchronous query to Wikidata
			queryWK =  """
			PREFIX wikibase: <http://wikiba.se/ontology#>
			PREFIX bd: <http://www.bigdata.com/rdf#>
			PREFIX mwapi: <https://www.mediawiki.org/ontology#API/>
			SELECT * WHERE {
				SERVICE wikibase:mwapi {
					bd:serviceParam wikibase:api 'Search' .
					bd:serviceParam wikibase:endpoint 'en.wikipedia.org' .
					bd:serviceParam mwapi:language "en" .
					bd:serviceParam mwapi:srsearch '"""+wcs_string+"""' .
					?title wikibase:apiOutput mwapi:title .
				}
			}
			"""
			# start the WK query
			try:
				print("Starting WK query for: ", wikicat)
				requestWK = futureSession.post(_URL_WK, data={"query": queryWK}, headers={"accept": "application/json"})
				requestDone = 1
			except Exception as exc:
				print("\n*** ERROR getUrlsLinked2Wikicats(): Error starting WK query for", wcs_string, ":", exc)
				_appendFile(logFilename, "ERROR getUrlsLinked2Wikicats(): Error starting WK query for "+wcs_string+": "+repr(exc))
				requestWK = None

			requestObjects[wikicat].update({"wk": requestWK})  # store the request WK object for this wikicat

		if requestDone == 1:
			time.sleep(3)  # delay to avoid server rejects for too many queries

	print("\n** ALL PENDING QUERIES LAUNCHED\n")

	# End of the first phase. All queries launched. Now, for every wikicat, we have:
	# requestObjects[wikicat] = {"dburls": URLs} or  {"db": requestDB}
	#                       and {"wkurls": URLS} or  {"wk": requestWK}




	# let's build an object {"db": urlsDB, "wk": urlsWK} for each wikicat (each field is a URL list)
	urlsObjects = {}

	# Second phase. Now, read the results received from all queries lauched

	for wikicat in P1_selectedWikicats:

		# first, study results for DB

		try:
			urlsDB = requestObjects[wikicat]["dburls"]   # try to recover local DB results
		except:
			requestDB = requestObjects[wikicat]["db"]   # no local DB results, so get the request DB object for this wikicat

			if requestDB == None:  # error starting DB query, return []
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
						_saveFile(_URLs_FOLDER+"_Wikicat_"+wikicat+"_DB_Urls.txt", '\n'.join(urlsDB))  # save all results from DB for this wikicat
					else:
						print("*** getUrlsLinked2Wikicats(): ", wikicat," provided 0 DB URLs from "+str(len(bindingsDB))+" results")
						_appendFile(logFilename, "getUrlsLinked2Wikicats(): "+wikicat+" provided 0 DB URLs from "+str(len(bindingsDB))+" results")

				except Exception as exc:
					print("*** ERROR getUrlsLinked2Wikicats(): Error querying DB for", wikicat,":", exc)
					_appendFile(logFilename, "ERROR getUrlsLinked2Wikicats(): Error querying DB for "+wikicat+": "+repr(exc))
					urlsDB = []

		# end for DB, we already have urlsDB

		# second, study results for WK

		wcs = _getWikicatComponents(wikicat)
		wcs_string = " ".join(wcs)

		try:
			urlsWK = requestObjects[wikicat]["wkurls"]   # try to recover local WK results
		except:
			requestWK = requestObjects[wikicat]["wk"]  # no local WK results, get the request WK object for this wikicat

			# WK results come without prefix "https://en.wikipedia.org/wiki/", this function adds it
			def addWKPrefix (x):
				return "https://en.wikipedia.org/wiki/"+x["title"]["value"].replace(" ", "_")


			if requestWK == None:  # error starting WK query, return []
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
						_saveFile(_URLs_FOLDER+"_Wikicat_"+wikicat+"_WK_Urls.txt", '\n'.join(urlsWK)) # save all results from WK for this wikicat
					else:
						print("*** getUrlsLinked2Wikicats(): ", wikicat," provided 0 WK URLs")
						_appendFile(logFilename, "getUrlsLinked2Wikicats(): "+wikicat+" provided 0 WK URLs")

				except Exception as exc:
					print("*** ERROR getUrlsLinked2Wikicats(): Error querying WK for", wcs_string,":", exc)
					_appendFile(logFilename, "ERROR getUrlsLinked2Wikicats(): Error querying WK for "+wcs_string+": "+repr(exc))
					urlsWK = []

		# end for WK, we already have urlsWK

		# store results for this wikicat
		urlsObjects[wikicat] = {"db": urlsDB, "wk": urlsWK}

	print("\n** RECEIVED ALL RESULTS FOR PENDING QUERIES\n")

	return urlsObjects  # return results to buildCorpus function
