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

from aux_build import hasFieldPT as _hasFieldPT, Print as _Print
from aux_build import CORPUS_FOLDER as _CORPUS_FOLDER, URLs_FOLDER as _URLs_FOLDER,  SCRAPPED_PAGES_FOLDER as _SCRAPPED_PAGES_FOLDER
from aux_build import getWikicatComponents as _getWikicatComponents
from aux_build import filterSimpleWikicats as _filterSimpleWikicats, filterSimpleSubjects as _filterSimpleSubjects
from aux_build import CORPUS_MIN_TXT_SIZE as _CORPUS_MIN_TXT_SIZE
from aux_build import UNRETRIEVED_PAGES_FILENAME as _UNRETRIEVED_PAGES_FILENAME, DISCARDED_PAGES_FILENAME as _DISCARDED_PAGES_FILENAME
	
from scrap import scrapFunctions as _scrapFunctions
from textSimilarities import textSimilarityFunctions as _textSimilarityFunctions

import sys
sys.path.append('../module_processCorpus')
from S1_AddSuffixToTexts import processS1List as _processS1List
from S2_BuildDbpediaInfoFromTexts import processS2Folder as _processS2Folder
from S3_UpdateTextsEntities import processS3Folder as _processS3Folder
from S4_tokenize import processS4Folder as _processS4Folder

sys.path.append('../module_train')
from D2V_BuildOwnModel_t import buildDoc2VecModel as _buildDoc2VecModel



# QUERY (/doPh1getWikicatsFromText) to attend the query to get wikicats from a text   
# receives: the text
# computes and saves files with wikicats (length.wk) and subjects (length.sb)
# returns:
# result["lenOriginalText"]: the length of the original text
# result["wikicats"]: list of wikicats (and saves them in the file $CORPUS_FOLDER/length.wk)
# result["subjects"]: list of subjects (and saves them in the file $CORPUS_FOLDER/length.sb)
# result[wk] = [component list] one for each wikicat, with the different components of each wikicat name
# result["formerSelectedWikicats"]: list of wikicats selected in the past, to be identified in the interface
def doPh1getWikicatsFromText():
	_Print("Requested Phase 1")
	
	originalText = request.values.get("originalText")
	
	result = doPh1(originalText)
	return jsonify(result);
	
def doPh1 (originalText):
	_Print("Executing Phase 1")
	lenOriginalText = len(originalText)  # length of the received text
			
	if not os.path.exists(_CORPUS_FOLDER):  # create KORPUS folder if not exists
		os.makedirs(_CORPUS_FOLDER)
		
	filename = _CORPUS_FOLDER+str(lenOriginalText)+".txt"   # save the received text with length.txt filename
	_saveFile(filename, originalText)
	
	filename_wk = _CORPUS_FOLDER+str(lenOriginalText)+".wk"   # filename for wikicats (length.wk)
	filename_sb = _CORPUS_FOLDER+str(lenOriginalText)+".sb"   # filename for subjects (length.sb)
			
	result = {}
	
	try:  # open wikicats file if exists
		with _Open(filename_wk) as fp:
			listWikicats = fp.read().splitlines()
			result["wikicats"] = listWikicats
	except:  # fetch wikicats if file does not exist yet
		result = _getCategoriesInText(originalText)  # function getCategoriesInText from px_DB_Manager.py
	
		if ("error" in result):   # return error if could not fetch wikicats 
			return result;
		
		listWikicats = list(filter(_filterSimpleWikicats, result["wikicats"])) # remove simple wikicats with function from aux_build.py
		result["wikicats"] = listWikicats  # update result wikicats to return
		
		_saveFile(filename_wk, '\n'.join(listWikicats))  # save file (length.wk) with wikicats, one per line
		
		listSubjects = list(filter(_filterSimpleWikicats, result["subjects"]))  # remove simple subjects with function from aux_build.py
		result["subjects"] = listSubjects # update result subjects to return
		
		_saveFile(filename_sb, '\n'.join(listSubjects)) # save file (length.sb) with subjects, one per line
		
	
	for w in listWikicats:    # compute components for every wikicat and add all of them to result
		wlc = _getWikicatComponents(w)   # function getWikicatComponets from aux_build.py
		result[w] = {"components":wlc}  # one entry per wikicat, with a dict with only one key "components"
	
	filename_selected = _CORPUS_FOLDER+str(lenOriginalText)+".selected.wk"   # previously selected wikicats file for this text
	
	try:  # try to open previously selected wikicats file if exists
		with _Open(filename_selected) as fp:
			wkSelectedList = fp.read().splitlines()
	except:
		wkSelectedList = []    # no previously selected wikicats
	
	result["selectedWikicats"] = wkSelectedList

	return result;







# QUERY (/doPh2getUrlsCandidateFiles)  to attend the query to find out URLs of candidate files
# receives:
# * the length of the original text
# * the list of selected wikicats
# returns: the results, mainly the number of files identified for each wikicat
def doPh2getUrlsCandidateFiles():
	_Print("Requested Phase 2")
		
	fromStart = json.loads(request.values.get("fromStart")) 
	originalText = request.values.get("originalText")
	lenOriginalText = len(originalText)
	
	if fromStart:
		resultPh1 = doPh1(originalText)
		selectedWikicats = resultPh1["wikicats"]	# todas las wikicats seleccionadas
	else: 
		selectedWikicats = json.loads(request.values.get("selectedWikicats"))   # get parameter with selected wikicats
		
	result = doPh2(lenOriginalText, selectedWikicats)
	
	# result[wikicat] = {"db": numURLs, "wk": numURLs}
	# add fields to update phase 1 interface
	
	if fromStart:  # add key "components" to each wikicat dict
		result["wikicats"] = selectedWikicats
		for w in selectedWikicats:	# all the wikicats, selected or not
			components = resultPh1[w]["components"]
			db = result[w]["db"]
			wk = result[w]["wk"]
			result[w] = {"components": components, "db": db, "wk": wk}
		
	return jsonify(result);  
	
	
def doPh2 (lenOriginalText, selectedWikicats):
	_Print("Executing Phase 2")
		
	logFilename = "corpus.log"
	logFile = _Open(logFilename, "a")
	logFile.write("\n\n")
	logFile.write(str(datetime.now())+"\n")
	logFile.close()
	
	result = {}  # object to store the results to be returned to the request
	
	print("\nNumber of selected wikicats:", len(selectedWikicats))
	numUrlsDB = 0
	numUrlsWK = 0

	# store the selected wikicats in the file $CORPUS_FOLDER/length.selected.wk
	_saveFile(_CORPUS_FOLDER+str(lenOriginalText)+".selected.wk", '\n'.join(selectedWikicats))
			
	
	# Now, we have wikicats in 'selectedWikicats' and subjects in 'sbOriginalText'
	
	# create the folder to store two files per wikicat, with the URLs linked to such wikicat coming from DB and WK
	# it must be done before calling the getUrlsLinked2Wikicats function, that it stores there files if fetched

	if not os.path.exists(_URLs_FOLDER):
		os.makedirs(_URLs_FOLDER)


	print("\n********** Starting DB and WK queries...", "\n")
	
	# now get the URLs associated to any of those wikicats (this function is below)
	# it reads from local DB (URLs) if exist, otherwise it connects to Internet to fetch them and store them in local DB

	urlsObjects = getUrlsLinked2Wikicats(selectedWikicats, logFilename)

	# it has been received a dictionary entry for each wikicat   urlsObjects[wikicat] = {"db": urlsDB, "wk": urlsWK}
	# urlsDB and urlsWK are lists of URLs

	fullList = [] # to aggregate the full list of URLs for all wikicats
		
	# process all results to return
	
	print("Number of URLs for every wikicat: ", end='')
	
	for wikicat in selectedWikicats:
		
		# first, the results from DB

		dbUrls = urlsObjects[wikicat]["db"]   # get the set of DB URLs
		dbUrls = list(map(lambda x: x.replace("https://", "http://"), dbUrls))    # change to http:// to avoid duplicates
		numUrlsDB += len(dbUrls)
		
		fullList.extend(dbUrls)  # add the DB URLs of current wikicat to the whole list
		
		# now, the results from WK

		wkUrls = urlsObjects[wikicat]["wk"]
		wkUrls = list(map(lambda x: x.replace("https://", "http://"), wkUrls))    # change to http:// to avoid duplicates
		numUrlsWK += len(wkUrls)
		
		fullList.extend(wkUrls)  # add the WK URLs of current wikicat to the whole list

		longs1 = "(DB=" + str(len(dbUrls)) + ", WK=" + str(len(wkUrls)) + ")"
		print(wikicat, longs1, end=', ')
		result[wikicat] = {"db": len(dbUrls), "wk": len(wkUrls)}  # add results for this wikicat to result

	listWithoutDuplicates = list(set(fullList))  # remove fully duplicated URLs (case sensitive)
	print("")
	#listWithoutDuplicates = removeDup(listWithoutDuplicates)  # remove elements that are duplicated if case-insensitive check


	
	lenListWithoutDuplicates  = len(listWithoutDuplicates)  # length of full list to process
	print("\n\nSummary of URLs numbers: DB=", numUrlsDB, ", WK= ", numUrlsWK, ", total without duplicates=", lenListWithoutDuplicates)
	
	_appendFile(logFilename, "Number of unique discovered URLs: "+str(lenListWithoutDuplicates))
	
	# returns number of results, the result items are only the numbers of discovered URLs
	result["selectedWikicats"] = selectedWikicats
	result["totalDB"] = numUrlsDB
	result["totalWK"] = numUrlsWK
	result["totalUrls"] = lenListWithoutDuplicates
	result["listWithoutDuplicates"] = listWithoutDuplicates
	
	return result  


# remove elements that are duplicated if case-insensitive check
def removeDup (lista):
	listaLower = list(map(lambda x: x.lower(), lista)) 

	dictDup = {}	# dict with keys urlLower and value urlOriginal
	for url in lista:
		num = listaLower.count(url.lower())
		if num > 1:
			if url.lower() in dictDup:
				print(url, num)
				continue
			else:
				dictDup[url.lower()] = url
	
	for url in dictDup:
		lista.remove(dictDup[url])
	
	return lista
			




		
		
		
		


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
# * the list of URLs
# returns: the number of downloaded and cleaned files with and without enough content	
		
def doPh3downloadCandidateTexts():
	_Print("Requested Phase 3")
		
	fromStart = json.loads(request.values.get("fromStart")) 
	originalText = request.values.get("originalText")
	lenOriginalText = len(originalText)
	
	if fromStart:
		resultPh1 = doPh1(originalText)
		selectedWikicats = resultPh1["wikicats"]
		resultPh2 = doPh2(lenOriginalText, selectedWikicats)
		listWithoutDuplicates = resultPh2["listWithoutDuplicates"]
	else:
		listWithoutDuplicates = json.loads(request.values.get("listWithoutDuplicates"))  # get parameter with the list of URLs
		selectedWikicats = json.loads(request.values.get("selectedWikicats"))  # get parameter with the list of wikicats
		
	result = doPh3(listWithoutDuplicates)
	result["selectedWikicats"] = selectedWikicats
	if fromStart:
		result["wikicats"] = selectedWikicats
		result["listWithoutDuplicates"] = listWithoutDuplicates
		for w in selectedWikicats:	# all the wikicats, selected or not
			components = resultPh1[w]["components"]
			db = resultPh2[w]["db"]
			wk = resultPh2[w]["wk"]
			result[w] = {"components": components, "db": db, "wk": wk}

	return jsonify(result);

	
	
def doPh3(listWithoutDuplicates):
	_Print("Executing Phase 3")	
	result = {}  # object to store the results to be returned to the request
	
	logFilename = "corpus.log"
	logFile = _Open(logFilename, "a")
	logFile.write("\n\n")
	logFile.write(str(datetime.now())+"\n")
	logFile.close()
	
	lenListWithoutDuplicates  = len(listWithoutDuplicates)  # length of full list to process
		
	#  We have teh set of URLs available in listWithoutDuplicates
	#  Let's start the analysis of their contents 
	
	print("\n", "********** Downloading and cleaning", lenListWithoutDuplicates, "candidate texts...", "\n")
	
	if not os.path.exists(_SCRAPPED_PAGES_FOLDER):  # create the folder to store scrapped pages and wikicat files
	 	os.makedirs(_SCRAPPED_PAGES_FOLDER)
	
	scrap = _scrapFunctions()   # Create a scrapFunctions object to clean pages
	unretrieved_pages_list = []  # a list for unsuccessful pages retrieval
		
	nowDownloaded = 0  # number of files downloaded from Internet in this iteration
	
	listEnoughContent = [] # list of pages with sufficient content to proceed  ( > _CORPUS_MIN_TXT_SIZE bytes, a constant from aux_build.py)
	listNotEnoughContent = [] # list of pages with insufficient content to proceed
		
	# download not locally stored pages, scrap them, and save them
	startTime = datetime.now()
	
	for idx, page in enumerate(listWithoutDuplicates, start=1):
		if (idx % 5000) == 0:
			print(".", end=' ', flush=True)
			
		_Print("("+str(idx)+" of "+str(lenListWithoutDuplicates)+") -- ", page)

		# scrapped pages will be stored classified by domain, in specific folders
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
		fileNameCandidate = _SCRAPPED_PAGES_FOLDER+domainFolder+"/"+onlyPageChanged+".txt"
				
		if (os.path.exists(fileNameCandidate)):  # may be exists but corresponds to another urlname
			_Print("File already available in local DB:", fileNameCandidate)
			fsize = os.path.getsize(fileNameCandidate)
			if fsize < _CORPUS_MIN_TXT_SIZE:
				listNotEnoughContent.append(fileNameCandidate)
			else:
				listEnoughContent.append(fileNameCandidate)
		else:  # fetch file if not exists	
			try:  # Retrieves the URL, and get the page title and the scraped page content
				pageName, pageContent = scrap.scrapPage(page)  # pageName result is not used
				nowDownloaded += 1
				_saveFile(fileNameCandidate, pageContent)  # Save to text file
				_Print("File "+str(nowDownloaded)+" downloaded and saved it:", fileNameCandidate)
				
				if (len(pageContent) < _CORPUS_MIN_TXT_SIZE):
					listNotEnoughContent.append(fileNameCandidate)
				else:
					listEnoughContent.append(fileNameCandidate)
			except Exception as e:
				_appendFile(logFilename, "Page "+page+" could not be retrieved: "+repr(e))
				unretrieved_pages_list.append(page)
	
	endTime = datetime.now()
	elapsedTimeF3 = endTime - startTime

	# Save the unretrieved_pages_list to a file
	print("\n",str(len(unretrieved_pages_list)), "unretrieved pages")
	_saveFile(_UNRETRIEVED_PAGES_FILENAME, '\n'.join(unretrieved_pages_list))
	
	lenListEnoughContent = len(listEnoughContent)
	
	_appendFile(logFilename, "Number of available pages with enough content: "+str(lenListEnoughContent))
	
	print("ALL PAGES AVAILABLE AND CLEANED.")
	print("New pages downloaded in this iteration:", str(nowDownloaded))
	print("Number of texts with enough content:", str(lenListEnoughContent))
	print("Number of texts without enough content:", str(len(listNotEnoughContent)))
	print("Duration F3 (downloading and cleaning):", str(elapsedTimeF3.seconds))

	result["nowDownloaded"] = nowDownloaded
	result["listEnoughContent"] = listEnoughContent
	result["lenListEnoughContent"] = lenListEnoughContent
	result["lenListNotEnoughContent"] = len(listNotEnoughContent)
	result["elapsedTimeF3"] = elapsedTimeF3.seconds
	
	return result








# QUERY (/doPh4identifyWikicats)  to attend the query to identify wikicats in candidate texts
# receives:
# * the list of candidate texts with enough content (>300 bytes)
# returns: the number of downloaded and cleaned files with and without enough content	
		
def doPh4identifyWikicats():
	_Print("Requested Phase 4")
		
	fromStart = json.loads(request.values.get("fromStart")) 
	originalText = request.values.get("originalText")
	lenOriginalText = len(originalText)
	
	if fromStart:
		resultPh1 = doPh1(originalText)
		selectedWikicats = resultPh1["wikicats"]
		resultPh2 = doPh2(lenOriginalText, selectedWikicats)
		listWithoutDuplicates = resultPh2["listWithoutDuplicates"]
		resultPh3 = doPh3(listWithoutDuplicates)
		listEnoughContent = resultPh3["listEnoughContent"]
		
	else:
		listEnoughContent = json.loads(request.values.get("listEnoughContent"))  # get parameter with the list of candidate texts with enough content
		selectedWikicats = json.loads(request.values.get("selectedWikicats"))  # get parameter with the list of wikicats
		
	result = doPh4(listEnoughContent)
	result["selectedWikicats"] = selectedWikicats
	if fromStart:
		result["wikicats"] = selectedWikicats
		result["listWithoutDuplicates"] = listWithoutDuplicates
		for w in selectedWikicats:	# all the wikicats, selected or not
			components = resultPh1[w]["components"]
			db = resultPh2[w]["db"]
			wk = resultPh2[w]["wk"]
			result[w] = {"components": components, "db": db, "wk": wk}
		result["nowDownloaded"] = resultPh3["nowDownloaded"]
		result["lenListEnoughContent"] = resultPh3["lenListEnoughContent"]
		result["lenListNotEnoughContent"] = resultPh3["lenListNotEnoughContent"]
		result["elapsedTimeF3"] = resultPh3["elapsedTimeF3"]	
	return jsonify(result);


	
def doPh4(listEnoughContent):
	_Print("Executing Phase 4")	
	result = {}  # object to store the results to be returned to the request
	
	logFilename = "corpus.log"
	logFile = _Open(logFilename, "a")
	logFile.write("\n\n")
	logFile.write(str(datetime.now())+"\n")
	logFile.close()


	lenListEnoughContent  = len(listEnoughContent)  # length of full list to process
	
	print("\n", "********** Identifying wikicats and subjects for", lenListEnoughContent, "candidate texts with DBpedia SpotLight...","\n")
	nowProcessed = 0
	
	listWithWKSB = [] # list of docs with wikicats or subjects
	listWithoutWKSB = [] # list of docs with no wikicats and no subjects
	startTime = datetime.now()
	
	for idx, doc in enumerate(listEnoughContent, start=1):
		if (idx % 5000) == 0:
			print(".", end=' ', flush=True)
		_Print("\n("+str(idx)+" of "+str(lenListEnoughContent)+") -- ", doc)
						
		# Build filenames for this doc
		fileNameCandidate = doc
		fileNameCandidateBase = doc[:doc.rfind(".")]
		fileNameCandidateWikicats = fileNameCandidateBase+".wk"    # wikicats file for this doc
		fileNameCandidateSubjects = fileNameCandidateBase+".sb"    # subjects file for this doc
				
		# if both files (wikicats and subjects) exist, use them from local store
		if os.path.exists(fileNameCandidateWikicats) and os.path.exists(fileNameCandidateSubjects):
			_Print("Files WK and SB already available in local DB for", fileNameCandidate)
			fwsize = os.path.getsize(fileNameCandidateWikicats)
			fssize = os.path.getsize(fileNameCandidateSubjects)
			# if these two files are empty (no wikicats and no subjects), this doc will not be used
			if (fwsize == 0) and (fssize == 0):
				listWithoutWKSB.append(doc)
			else:
				listWithWKSB.append(doc)
		else: # if one file does not exists, fetch from Internet candidate text wikicats and subjects		
			try:  # open and read text of candidate file
				candidateTextFile = _Open(fileNameCandidate, "r")
				candidate_text = candidateTextFile.read()
				_Print("Reading candidate text file:", fileNameCandidate)
			except:  # file that inexplicably could not be read from local store, it will not be used
				_appendFile(logFilename, "ERROR doPh4identifyWikicats(): Unavailable candidate file, not in the store, but it should be: "+fileNameCandidate)
				listWithoutWKSB.append(doc)
				continue
			
			_Print("Computing wikicats and subjects for:", doc)
			candidate_text_categories = _getCategoriesInText(candidate_text)  # function _getCategoriesInText from px_DB_Manager
			
			if ("error" in candidate_text_categories):  # error while fetching info, the page will not be used
				_appendFile(logFilename, "ERROR doPh4identifyWikicats(): Problem in _getCategoriesInText(candidate_text): "+candidate_text_categories["error"])
				listWithoutWKSB.append(doc)
				continue
				
			_Print("Wikicats and subjects downloaded for", fileNameCandidate)
			candidate_text_wikicats = list(filter(_filterSimpleWikicats, candidate_text_categories["wikicats"])) # remove simple wikicats with function from aux_build.py
			candidate_text_subjects = list(filter(_filterSimpleSubjects, candidate_text_categories["subjects"])) # remove simple subjects with function from aux_build.py
			
			_saveFile(fileNameCandidateWikicats, '\n'.join(candidate_text_wikicats))  # save file with original text wikicats, one per line
			_saveFile(fileNameCandidateSubjects, '\n'.join(candidate_text_subjects))  # save file with original text subjects, one per line
			nowProcessed += 1
			
			# if no wikicats and no subjects, the page will not be used
			if (len(candidate_text_wikicats) == 0) and (len(candidate_text_subjects) == 0):
				listWithoutWKSB.append(doc)
			else:
				listWithWKSB.append(doc)

	endTime = datetime.now()
	elapsedTimeF4 = endTime - startTime

	lenListWithWKSB = len(listWithWKSB)
	
	_appendFile(logFilename, "Number of available pages with wikicats or subjects: "+str(lenListWithWKSB))
	
	print("\n","ALL WIKICATs AND SUBJECTs COMPUTED")
	print("New items processed in this iteration:", str(nowProcessed))
	print("Number of docs with wikicats or subjects:", str(lenListWithWKSB))
	print("Number of docs without wikicats nor subjects:", str(len(listWithoutWKSB)))
	print("Duration F4 (identifying wikicats):", str(elapsedTimeF4.seconds))
		
	result["nowProcessed"] = nowProcessed
	result["listWithWKSB"] = listWithWKSB
	result["lenListWithWKSB"] = lenListWithWKSB
	result["lenListWithoutWKSB"] = len(listWithoutWKSB)
	result["elapsedTimeF4"] = elapsedTimeF4.seconds

	return result










# QUERY (/doPh5computeSimilarities)  to attend the query to compute similarities for candidate texts
# receives:
# * the list of candidate texts with wikicats
# returns: the resulting data	
		
def doPh5computeSimilarities():
	_Print("Requested Phase 5")
	
	fromStart = json.loads(request.values.get("fromStart"))
	originalText = request.values.get("originalText")
	lenOriginalText = len(originalText)
	
	if fromStart:
		resultPh1 = doPh1(originalText)
		selectedWikicats = resultPh1["wikicats"]
		resultPh2 = doPh2(lenOriginalText, selectedWikicats)
		listWithoutDuplicates = resultPh2["listWithoutDuplicates"]
		resultPh3 = doPh3(listWithoutDuplicates)
		listEnoughContent = resultPh3["listEnoughContent"]
		resultPh4 = doPh4(listEnoughContent)
		listWithWKSB = resultPh4["listWithWKSB"]
		
	else:
		selectedWikicats = json.loads(request.values.get("selectedWikicats"))   # get parameter with selected wikicats
		listWithWKSB = json.loads(request.values.get("listWithWKSB"))  # get parameter with the list of candidate texts with wikicats or subjects
		
	result = doPh5(listWithWKSB, lenOriginalText, selectedWikicats)
	result["selectedWikicats"] = selectedWikicats	
	if fromStart:
		result["wikicats"] = selectedWikicats
		result["listWithoutDuplicates"] = listWithoutDuplicates
		for w in selectedWikicats:	# all the wikicats, selected or not
			components = resultPh1[w]["components"]
			db = resultPh2[w]["db"]
			wk = resultPh2[w]["wk"]
			result[w] = {"components": components, "db": db, "wk": wk}
			
		result["nowDownloaded"] = resultPh3["nowDownloaded"]
		result["lenListEnoughContent"] = resultPh3["lenListEnoughContent"]
		result["lenListNotEnoughContent"] = resultPh3["lenListNotEnoughContent"]
		result["elapsedTimeF3"] = resultPh3["elapsedTimeF3"]
		
		result["nowProcessed"] = resultPh4["nowProcessed"]
		result["lenListWithWKSB"] = resultPh4["lenListWithWKSB"]
		result["lenListWithoutWKSB"] = resultPh4["lenListWithoutWKSB"]
		result["elapsedTimeF4"] = resultPh4["elapsedTimeF4"]
		
	return jsonify(result);



def doPh5(listWithWKSB, lenOriginalText, selectedWikicats):
	_Print("Executing Phase 5")	
	result = {}  # object to store the results to be returned to the request
	
	logFilename = "corpus.log"
	logFile = _Open(logFilename, "a")
	logFile.write("\n\n")
	logFile.write(str(datetime.now())+"\n")
	logFile.close()
	
	lenListWithWKSB  = len(listWithWKSB)  # length of full list to process
	
	print("\n", "********** Computing similarities for", lenListWithWKSB, "candidate texts...", "\n")
	
	discarded_pages_list = []     # a list to save discarded pages' URLs
	
	# read the original text subjects from local store
	filename_sb = _CORPUS_FOLDER+str(lenOriginalText)+".sb"   # filename for subjects (length.sb)
	try:  
		with _Open(filename_sb) as fp:
			sbOriginalText = fp.read().splitlines()
	except:
		sbOriginalText = []    # no subjects for original text
		_appendFile(logFilename, "Subjects file not available: "+filename_sb)
		
	similarity = _textSimilarityFunctions(selectedWikicats, sbOriginalText)    # Create a textSimilarityFunctions object to measure text similarities
	
	# variables to store results
	filenameSims = _CORPUS_FOLDER+str(lenOriginalText)+".sims.csv"  # file to store all similarities
	filenameCorpus = _CORPUS_FOLDER+str(lenOriginalText)+".corpus.csv"  # file to store documents selected for initial corpus

	distribution_wk = {"0":0, "1":0, "2":0, "3":0, "4":0, "5":0, "6":0, "7":0, "8":0, "9":0}
	distribution_sb = {"0":0, "1":0, "2":0, "3":0, "4":0, "5":0, "6":0, "7":0, "8":0, "9":0}
	
	# try to read existing sims file
	dict_sims_wk_sb = {} # dict to read sims stored in local DB
	try:
		with _Open(filenameSims, 'r') as csvFile:
			reader = csv.reader(csvFile, delimiter=' ')
			next(reader)  # to skip header
			for row in reader:
				dict_sims_wk_sb[row[0]] = (float(row[1]), float(row[2]))
		
			csvFile.close()
	except:
		print("No similarities file")
	
	# Measure text similarity to discard pages (discarded_pages_list) without a minimum similarity
	startTime = datetime.now()
	timeMatch = 0
	
	dict_sims_wk_sb2 = {} # dict to store sims
	
	for idx, doc in enumerate(listWithWKSB, start=1):
		if (idx % 5000) == 0:
			print(".", end=' ', flush=True)
		_Print("("+str(idx)+" of "+str(lenListWithWKSB)+") -- ", doc)
						
		# Build filenames for this page
		fileNameCandidate = doc
		fileNameCandidateBase = doc[:doc.rfind(".")]
		fileNameCandidateWikicats = fileNameCandidateBase+".wk"    # wikicats file for this doc
		fileNameCandidateSubjects = fileNameCandidateBase+".sb"    # subjects file for this doc
		lastNameCandidate = fileNameCandidate.replace(_SCRAPPED_PAGES_FOLDER, "")

		# Compare original text with the text of this candidate (in pageContent)
		# several criteria are now computed. THEIR RELEVANCE SHOULD BE STUDIED AS SOON AS POSSIBLE 

		# Measure text similarity based on the Lee doc2vec model
		# doc2vec_cosineSimilarity, doc2vec_euclideanDistance = similarity.doc2VecTextSimilarity(originalText, pageContent, _LEE_D2V_MODEL)
		# 
		# # Measure text similarity based on the trained doc2vec model with our training corpus
		# doc2vec_trained_cosineSimilarity, doc2vec_trained_euclideanDistance = similarity.doc2VecTextSimilarity(originalText, pageContent, _OWN_D2V_MODEL)
		# 
		# # Measure the euclidean distance using SKLEARN
		# euclidean_distance = similarity.euclideanTextSimilarity(originalText, pageContent)
		# 
		# # Measure the spaCy distance
		# spacy_similarity = similarity.spacyTextSimilarity(originalText, pageContent)
		
		
		# Now compute similarities. First, check if already stored in length.sims.csv
		try:
			sims = dict_sims_wk_sb[lastNameCandidate]
			_Print("Found already computed similarities for", fileNameCandidate)
			shared_wikicats_jaccard_similarity = sims[0]
			shared_subjects_jaccard_similarity = sims[1]
		except:
			# Measure wikicats similarity (requires shared matching). Code -1 is returned if some error
			shared_wikicats_jaccard_similarity = similarity.sharedWikicatsSimilarity(fileNameCandidateWikicats, logFilename)
			if shared_wikicats_jaccard_similarity < 0:
				_Print("ERROR computing sharedWikicatsJaccard:", fileNameCandidateWikicats)
				_appendFile(logFilename, "ERROR computing sharedWikicatsJaccard: "+fileNameCandidateWikicats)
				continue
			
			shared_subjects_jaccard_similarity = similarity.sharedSubjectsSimilarity(fileNameCandidateSubjects, logFilename)
			if shared_subjects_jaccard_similarity < 0:
				_Print("ERROR computing sharedSubjectsJaccard:", fileNameCandidateSubjects)
				_appendFile(logFilename, "ERROR computing sharedSubjectsJaccard: "+fileNameCandidateSubjects)
				continue
		
		dict_sims_wk_sb2[lastNameCandidate] = (shared_wikicats_jaccard_similarity,shared_subjects_jaccard_similarity)
		
		_Print("Wikicats shared jaccard similarity =", str(shared_wikicats_jaccard_similarity))
		_Print("Subjects shared jaccard similarity =", str(shared_subjects_jaccard_similarity))
		
			
		# to compute distributions 
		if shared_wikicats_jaccard_similarity < 0.1:
			distribution_wk["0"] = distribution_wk["0"] + 1
		elif shared_wikicats_jaccard_similarity < 0.2:
			distribution_wk["1"] = distribution_wk["1"] + 1
		elif shared_wikicats_jaccard_similarity < 0.3:
			distribution_wk["2"] = distribution_wk["2"] + 1
		elif shared_wikicats_jaccard_similarity < 0.4:
			distribution_wk["3"] = distribution_wk["3"] + 1
		elif shared_wikicats_jaccard_similarity < 0.5:
			distribution_wk["4"] = distribution_wk["4"] + 1
		elif shared_wikicats_jaccard_similarity < 0.6:
			distribution_wk["5"] = distribution_wk["5"] + 1
		elif shared_wikicats_jaccard_similarity < 0.7:
			distribution_wk["6"] = distribution_wk["6"] + 1
		elif shared_wikicats_jaccard_similarity < 0.8:
			distribution_wk["7"] = distribution_wk["7"] + 1
		elif shared_wikicats_jaccard_similarity < 0.9:
			distribution_wk["8"] = distribution_wk["8"] + 1
		else:
			distribution_wk["9"] = distribution_wk["9"] + 1
	
	
		if shared_subjects_jaccard_similarity < 0.1:
			distribution_sb["0"] = distribution_sb["0"] + 1
		elif shared_subjects_jaccard_similarity < 0.2:
			distribution_sb["1"] = distribution_sb["1"] + 1
		elif shared_subjects_jaccard_similarity < 0.3:
			distribution_sb["2"] = distribution_sb["2"] + 1
		elif shared_subjects_jaccard_similarity < 0.4:
			distribution_sb["3"] = distribution_sb["3"] + 1
		elif shared_subjects_jaccard_similarity < 0.5:
			distribution_sb["4"] = distribution_sb["4"] + 1
		elif shared_subjects_jaccard_similarity < 0.6:
			distribution_sb["5"] = distribution_sb["5"] + 1
		elif shared_subjects_jaccard_similarity < 0.7:
			distribution_sb["6"] = distribution_sb["6"] + 1
		elif shared_subjects_jaccard_similarity < 0.8:
			distribution_sb["7"] = distribution_sb["7"] + 1
		elif shared_subjects_jaccard_similarity < 0.9:
			distribution_sb["8"] = distribution_sb["8"] + 1
		else:
			distribution_sb["9"] = distribution_sb["9"] + 1
	
	# end of loop for pages similarity computing
	endTime = datetime.now()
	elapsedTimeF5 = endTime - startTime
	elapsedTimeF5sec = elapsedTimeF5.seconds

	print("\n\n", "Duration F5 (computing similarities):", str(elapsedTimeF5sec))
	

	# Update the csv file with all similarities, if changes 
	
	with _Open(filenameSims, 'w') as csvFile:
		fieldnames = ['Text', 'Wikicats Similarity', 'Subject Similarity']	# Name columns
		writer = csv.DictWriter(csvFile, fieldnames=fieldnames, delimiter=" ") # Create csv headers
		writer.writeheader()	# Write the column headers
	
		writer = csv.writer(csvFile, delimiter=' ')
		for key in dict_sims_wk_sb2:
			try:
				sims = dict_sims_wk_sb2[key]
				writer.writerow([key, sims[0], sims[1]])
			except:
				print("Error writing csv with similarities", row)
				_appendFile(logFilename, "Error writing csv with similarities"+str(row))
	
		csvFile.close()

	# convert dict in list of triplets to order (filenameCandidate, similarityByWikicats, similarityBySubjects)
	list_sims_wk_sb = [ (k, dict_sims_wk_sb2[k][0], dict_sims_wk_sb2[k][1]) for k in dict_sims_wk_sb2]
	
	# function to order a list of triples by the second element
	def Sort(trili): 
		trili.sort(reverse=True, key = lambda x: x[1]) 
		return trili
	
	# compute docCorpus with the 5% docs with higher wikicat similarity
	docsCorpus = Sort(list_sims_wk_sb)  # order by wikicat similarity
	sizeCorpus = int(lenListWithWKSB / 20)   # size of 5%
	docsCorpus = docsCorpus[:sizeCorpus]   # keep only 5%
	
	# to add full namein corpus list
	listDocsCorpus = list(map(lambda x: (_SCRAPPED_PAGES_FOLDER+x[0],x[1],x[2]), docsCorpus))
	
	# save corpus filenames
	with _Open(filenameCorpus, 'w') as csvFile:
		fieldnames = ['Text', 'Wikicats Similarity', 'Subject Similarity']	# Name columns
		writer = csv.DictWriter(csvFile, fieldnames=fieldnames, delimiter=" ") # Create csv headers
		writer.writeheader()	# Write the column headers
	
		writer = csv.writer(csvFile, delimiter=' ')
		for row in listDocsCorpus:
			try:
				writer.writerow([row[0], row[1], row[2]])
			except:
				print("Error writing csv with corpus", row)
				_appendFile(logFilename, "Error writing csv with corpus"+str(row))
	
		csvFile.close()
	
	# Save the discarded_pages_list to a file
	_saveFile(_DISCARDED_PAGES_FILENAME, '\n'.join(discarded_pages_list))
	
	printSimsDistribution(lenListWithWKSB, distribution_wk, distribution_sb)
	
	result["elapsedTimeF5"] = elapsedTimeF5.seconds
	result["distribution_wk"] = distribution_wk
	result["distribution_sb"] = distribution_sb
	result["listDocsCorpus"] = listDocsCorpus
	result["lenListDocsCorpus"] = len(listDocsCorpus)
		
	return result







# QUERY (/doPh6trainD2V) to attend the query to train the Doc2Vec network
# receives:
# * the list of corpus docs 
# returns: 
		
def doPh6trainD2V():
	_Print("Requested Phase 6")
	
	fromStart = json.loads(request.values.get("fromStart"))
	originalText = request.values.get("originalText")
	lenOriginalText = len(originalText)
	
	if fromStart:
		resultPh1 = doPh1(originalText)
		selectedWikicats = resultPh1["wikicats"]
		resultPh2 = doPh2(lenOriginalText, selectedWikicats)
		listWithoutDuplicates = resultPh2["listWithoutDuplicates"]
		resultPh3 = doPh3(listWithoutDuplicates)
		listEnoughContent = resultPh3["listEnoughContent"]
		resultPh4 = doPh4(listEnoughContent)
		listWithWKSB = resultPh4["listWithWKSB"]
		resultPh5 = doPh5(listWithWKSB, lenOriginalText, selectedWikicats)
		listDocsCorpus = resultPh5["listDocsCorpus"]
	else:
		listDocsCorpus = json.loads(request.values.get("listDocsCorpus"))  # get parameter with the corpus docs
		
	result = doPh6(listDocsCorpus, lenOriginalText)
	
	result["selectedWikicats"] = selectedWikicats	
	if fromStart:
		result["wikicats"] = selectedWikicats
		result["listWithoutDuplicates"] = listWithoutDuplicates
		for w in selectedWikicats:	# all the wikicats, selected or not
			components = resultPh1[w]["components"]
			db = resultPh2[w]["db"]
			wk = resultPh2[w]["wk"]
			result[w] = {"components": components, "db": db, "wk": wk}
			
		result["nowDownloaded"] = resultPh3["nowDownloaded"]
		result["lenListEnoughContent"] = resultPh3["lenListEnoughContent"]
		result["lenListNotEnoughContent"] = resultPh3["lenListNotEnoughContent"]
		result["elapsedTimeF3"] = resultPh3["elapsedTimeF3"]
		
		result["nowProcessed"] = resultPh4["nowProcessed"]
		result["lenListWithWKSB"] = resultPh4["lenListWithWKSB"]
		result["lenListWithoutWKSB"] = resultPh4["lenListWithoutWKSB"]
		result["elapsedTimeF4"] = resultPh4["elapsedTimeF4"]
		
		result["lenListDocsCorpus"] = resultPh5["lenListDocsCorpus"]
		result["elapsedTimeF5"] = resultPh5["elapsedTimeF5"]	
		
	return jsonify(result);	
	
	
	
def doPh6(listDocsCorpus, lenOriginalText):
	_Print("Executing Phase 6")
		
	result = {}  # object to store the results to be returned to the request
	
	logFilename = "corpus.log"
	logFile = _Open(logFilename, "a")
	logFile.write("\n\n")
	logFile.write(str(datetime.now())+"\n")
	logFile.close()
	
	listDocsCorpus = json.loads(request.values.get("listDocsCorpus"))  # get parameter with the corpus docs
	
	startTime = datetime.now()
	
	listDocs = list(map(lambda x: x[0], listDocsCorpus))
	
	corpusFolder = _CORPUS_FOLDER+str(lenOriginalText)+"/"
	if not os.path.exists(corpusFolder):  # create CORPUS folder for output files if does not exist
		os.makedirs(corpusFolder)

	_Print("Training with ", str(len(listDocs)), "documents")
	
	try:
		_Print("Processing S1...")
		_processS1List(str(corpusFolder), listDocs)
		_Print("Processing S2...")
		_processS2Folder(str(corpusFolder))
		_Print("Processing S3...")
		_processS3Folder(str(corpusFolder))
		_Print("Processing S4...")
		_processS4Folder(str(corpusFolder))
		
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
		
		model_filename =  _CORPUS_FOLDER+str(lenOriginalText)+ "-t.model"
		files_folder = corpusFolder+"files_t/"
				
		# Build a doc2vec model trained with files in 
		r =_buildDoc2VecModel(files_folder, model_filename, vector_size, window, alpha, min_alpha, min_count, distributed_memory, epochs)
		
		if (r == 0):
			print("Training success!!")
		else:
			print("Training failed!")
			
	except Exception as e:
		result["error"] = str(e)
		print("Exception in getTrainD2V", str(e))
		_appendFile(logFilename, "Exception in doPh6trainD2V"+str(e))

	endTime = datetime.now()
	elapsedTimeF62 = endTime - startTime
	
	result["elapsedTimeF61"] = elapsedTimeF61.seconds
	result["elapsedTimeF62"] = elapsedTimeF62.seconds
	
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
	
	print("TOTAL WIKICATS = ", lenListWithWKSB)
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



# aux function to get all the URLs associated to any wikicat from the set of selected wikicats
# Receives:
# - selectedWikicats: set of selected wikicats
# - logFilename: file to save errors
# For each wikicat, if there is a file for such wikicat, it is read for returning contents
# Otherwise, it connects to Internet to query DB and WK and parse the results to return, after storing them locally
# it returns a dictionary entry for each wikicat   urlsObjects[wikicat] = {"db": urlsDB, "wk": urlsWK}
# urlsDB and urlsWK are lists of URLs

def getUrlsLinked2Wikicats (selectedWikicats, logFilename):
	requestObjects = {} # dictionary to store request objects 
	
	futureSession = FuturesSession()  # to manage asynchronous requests 

	# first phase, reading files or start requests for DBpedia and Wikidata foreach wikicat
					
	for wikicat in selectedWikicats:
		
		# first, read or fetch Wikicat results for DBpedia

		filename_db = _URLs_FOLDER+"_Wikicat_"+wikicat+"_DB_Urls.txt"
		requestDone = 0  # to control if some request has been done, and if so, set a delay to not overload servers
		
		try:  # try to read wikicats of original text from local store
			with _Open(filename_db) as fp:
				urls_from_DB = fp.read().splitlines()
				_Print("File already available:", filename_db)
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
				requestDB = futureSession.post(_URL_DB, data={"query": queryDB}, headers={"accept": "application/json"})
			except Exception as exc:
				print("*** ERROR getUrlsLinked2Wikicats(): Error starting DB query for", wikicat, ":", exc)
				_appendFile(logFilename, "ERROR getUrlsLinked2Wikicats(): Error starting DB query for "+wikicat+": "+repr(exc))
				requestDB = None
				
			requestObjects[wikicat] = {"db": requestDB}  # store the request DB object for this wikicat
			requestDone = 1
		

		# now, read or fetch Wikicat results for Wikidata
		
		filename_wk = _URLs_FOLDER+"_Wikicat_"+wikicat+"_WK_Urls.txt"	

		# it uses update with the objects dictionary, as the wikicat key has been already created for DBpedia	
		
		wcs = _getWikicatComponents(wikicat)
		wcs_string = " ".join(wcs)
		
		try:  # try to read wikicats and subjects of original text from local store
			with _Open(filename_wk) as fp:
				urls_from_WK = fp.read().splitlines()
				_Print("File already available:", filename_wk)
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
					bd:serviceParam mwapi:srsearch '"""+wcs_string+"""' .
					?title wikibase:apiOutput mwapi:title .
				}
			} 		
			"""
			# start the WK query
			try:
				print("Starting WK query for: ", wikicat)
				requestWK = futureSession.post(_URL_WK, data={"query": queryWK}, headers={"accept": "application/json"})
			except Exception as exc:
				print("\n*** ERROR getUrlsLinked2Wikicats(): Error starting WK query for", wcs_string, ":", exc)
				_appendFile(logFilename, "ERROR getUrlsLinked2Wikicats(): Error starting WK query for "+wcs_string+": "+repr(exc))
				requestWK = None	
			
			requestObjects[wikicat].update({"wk": requestWK})  # store the request WK object for this wikicat
			requestDone = 1
			
		if requestDone == 1:
			time.sleep(3)  # delay to avoid server rejects for too many queries
		
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

	
