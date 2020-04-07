import os
import sys
from flask import request, jsonify
import shutil
import csv
from requests_futures.sessions import FuturesSession
import time
import json
from smart_open import open as _Open
from datetime import datetime

from px_DB_Manager import getCategoriesInText as _getCategoriesInText
from px_aux import saveFile as _saveFile, appendFile as _appendFile, URL_DB as _URL_DB, URL_WK as _URL_WK
from aux import hasFieldPT as _hasFieldPT  # function to check if object has  ["pt"]["value"] field
from aux import filterSimpleWikicats as _filterSimpleWikicats, filterSimpleSubjects as _filterSimpleSubjects, getWikicatComponents as _getWikicatComponents	
from aux import CORPUS_FOLDER as _CORPUS_FOLDER
from aux import URLs_FOLDER as _URLs_FOLDER, DISCARDED_PAGES_FILENAME as _DISCARDED_PAGES_FILENAME,  SCRAPPED_TEXT_PAGES_FOLDER as _SCRAPPED_TEXT_PAGES_FOLDER
from aux import UNRETRIEVED_PAGES_FILENAME as _UNRETRIEVED_PAGES_FILENAME, SIMILARITIES_CSV_FILENAME as _SIMILARITIES_CSV_FILENAME
from aux import LEE_D2V_MODEL as _LEE_D2V_MODEL, OWN_D2V_MODEL as _OWN_D2V_MODEL
from aux import CORPUS_MIN_TXT_SIZE as _CORPUS_MIN_TXT_SIZE
import aux
	
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

	logFilename = "corpus.log"
	logFile = _Open(logFilename, "w")
	logFile.write(str(datetime.now())+"\n")
	logFile.close()
	
	originalText = request.values.get("text")  # get parameter with original text
	lenOriginalText = len(originalText)                                   	
	
	selectedWikicats = json.loads(request.values.get("wikicats"))   # get parameter with selected wikicats
	print("Number of selected wikicats:", len(selectedWikicats))
	numUrlsDB = 0
	numUrlsWK = 0

	# store the selected wikicats in the file $CORPUS_FOLDER/length.selected.wk
	_saveFile(_CORPUS_FOLDER+"/"+str(lenOriginalText)+".selected.wk", '\n'.join(selectedWikicats))
	
	# read the original text subjects from local store
	filename_sb = _CORPUS_FOLDER+"/"+str(lenOriginalText)+".sb"   # filename for subjects (length.sb)
	try:  
		with _Open(filename_sb) as fp:
			sbOriginalText = fp.read().splitlines()
	except:
		sbOriginalText = []    # no subjects for original text
		_appendFile(logFilename, "Subjects file not available: "+filename_sb)
			
	
	# Now, we have wikicats in 'selectedWikicats' and subjects in 'sbOriginalText'

	overwriteCorpus = json.loads(request.values.get("overwriteCorpus"))  # read the flag parameter overwriteCorpus from request
	
	if overwriteCorpus:   # if overwriteCorpus, remove current corpus  (URLs, scrapped pages and wikicats files)
		print("Deleting current URLs lists...")
		shutil.rmtree(_URLs_FOLDER)  
		print("Deleting current scrapped texts...")
		shutil.rmtree(_SCRAPPED_TEXT_PAGES_FOLDER) 
	
	
	# create the folder to store two files per wikicat, with the URLs linked to such wikicat coming from DB and WK
	# it must be done before calling the getUrlsLinked2Wikicats function, that it stores there files if fetched

	if not os.path.exists(_URLs_FOLDER):
		os.makedirs(_URLs_FOLDER)
		
	if not os.path.exists(_SCRAPPED_TEXT_PAGES_FOLDER):  # create the folder to store scrapped pages and wikicat files
		os.makedirs(_SCRAPPED_TEXT_PAGES_FOLDER)


	# now get the URLs associated to any of those wikicats (this function is below)
	# it reads from local files if exist, otherwise it connects to Internet to fetch them and store them locally

	urlsObjects = getUrlsLinked2Wikicats(selectedWikicats, logFilename)

	# it has been received a dictionary entry for each wikicat   urlsObjects[wikicat] = {"db": urlsDB, "wk": urlsWK}
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
	lenOfListWithoutDuplicates  = len(listWithoutDuplicates)  # length of full list to process
	print("\n\nSummary of URLs numbers: DB=", numUrlsDB, ", WK= ", numUrlsWK, ", total without duplicates=", lenOfListWithoutDuplicates)
	
	_appendFile(logFilename, "Number of discovered URLs: "+str(lenOfListWithoutDuplicates))
	
	# returns number of results, the result items are only the numbers of discovered URLs
	result["totalDB"] = numUrlsDB
	result["totalWK"] = numUrlsWK
	result["totalUrls"] = len(listWithoutDuplicates)
	# return jsonify(result);  # uncomment to return to the interface without processing files
	
	if aux.PSTOP == True:
		input("Type ENTER to continue...")
		
		
		
	
	###  We've got the first set of relevant URLs, available in listWithoutDuplicates, and stored in the URLs folder
	###  Let's start the analysis of their contents 
	
	print("\n Downloading and cleaning candidate texts...")
		
	scrap = _scrapFunctions()   # Create a scrapFunctions object to clean pages
	unretrieved_pages_list = []  # a list for unsuccessful pages retrieval
		
	nowDownloaded = 0  # number of files downloaded from Internet in this iteration
	
	listEnoughContent = [] # list of pages with sufficient content to proceed  ( > _CORPUS_MIN_TXT_SIZE bytes, a constant from aux.py)
	listNotEnoughContent = [] # list of pages with insufficient content to proceed
		
	# download not locally stored pages, scrap them, and save them
	for idx, page in enumerate(listWithoutDuplicates, start=1):
		
		print("(", idx, "of", lenOfListWithoutDuplicates, ") -- ", page)

		# scrapped pages will be stored classified by domain, in specific folders
		# currently, only "en.wikipedia.org" domain is used
						
		pageWithoutHTTP = page[2+page.find("//"):]		# get the domain of this page
		domainFolder = pageWithoutHTTP[:pageWithoutHTTP.find("/")]

		if (not os.path.exists(_SCRAPPED_TEXT_PAGES_FOLDER+"/"+domainFolder)):	# create this domain folder if not exists 
			os.makedirs(_SCRAPPED_TEXT_PAGES_FOLDER+"/"+domainFolder)
		
		# the pagename will be the name of the file, with the following change
		# dir1/dir2/page --> dir1..dir2..page.txt

		onlyPage = pageWithoutHTTP[1+pageWithoutHTTP.find("/"):]
		onlyPageChanged =  onlyPage.replace("/", "..")
		
		# Add file extension '.txt' to page name for saving it   !!!!!!!!!!
		# pageFinalName = page[1+page.rindex("/"):]
		fileNameCandidate = _SCRAPPED_TEXT_PAGES_FOLDER+"/"+domainFolder+"/"+onlyPageChanged+".txt"
				
		if (os.path.exists(fileNameCandidate)):
			print("File already available in local DB:", fileNameCandidate)
			fsize = os.path.getsize(fileNameCandidate)
			if fsize < _CORPUS_MIN_TXT_SIZE:
				listNotEnoughContent.append(page)
			else:
				listEnoughContent.append(page)
		else:  # fetch file if not exists	
			try:  # Retrieves the URL, and get the page title and the scraped page content
				pageName, pageContent = scrap.scrapPage(page)  # pageName result is not used
				nowDownloaded += 1
				_saveFile(fileNameCandidate, pageContent)  # Save to text file
				print("File", str(nowDownloaded), "downloaded and saved it:", fileNameCandidate)
				
				if (len(pageContent) < _CORPUS_MIN_TXT_SIZE):
					listNotEnoughContent.append(page)
				else:
					listEnoughContent.append(page)
			except Exception as exc:
				_appendFile(logFilename, "Page "+page+" could not be retrieved: "+repr(exc))
				unretrieved_pages_list.append(page)
			
	# Save the unretrieved_pages_list to a file
	print("")
	print(str(len(unretrieved_pages_list)) + " unretrieved pages")
	_saveFile(_UNRETRIEVED_PAGES_FILENAME, '\n'.join(unretrieved_pages_list))
	
	lenListEnoughContent = len(listEnoughContent)
	
	_appendFile(logFilename, "Number of available pages with enough content: "+str(lenListEnoughContent))
	
	print("ALL PAGES AVAILABLE AND CLEANED.")
	print("New pages downloaded in this iteration:", str(nowDownloaded))
	print("Number of pages with enough content:", str(lenListEnoughContent))
	print("Number of pages without enough content:", str(len(listNotEnoughContent)))

	if aux.PSTOP == True:
		input("Type ENTER to continue...")
		
		

	# all the pages not already available have been now fetched and cleaned
	
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
	

	print("")
	print("Identifying wikicats and subjects for candidate texts with DBpedia SpotLight...")
	currentDownloaded = 0
	
	listWithWikicats = [] # list of pages with available wikicats
	listWithoutWikicats = [] # list of pages with no wikicats
	
	for idx, page in enumerate(listEnoughContent, start=1):
		print("\n(", idx, "of", lenListEnoughContent, ") -- ", page)
						
		# Build filenames for this page
		pageWithoutHTTP = page[2+page.find("//"):]
		domainFolder = pageWithoutHTTP[:pageWithoutHTTP.find("/")]
		onlyPage = pageWithoutHTTP[1+pageWithoutHTTP.find("/"):]
		onlyPageChanged =  onlyPage.replace("/", "..")
		fileNameCandidateBase = _SCRAPPED_TEXT_PAGES_FOLDER+"/"+domainFolder+"/"+onlyPageChanged
		fileNameCandidate = fileNameCandidateBase+".txt"
		fileNameCandidateWikicats = fileNameCandidateBase+".wk"    # wikicats file for this page
		fileNameCandidateSubjects = fileNameCandidateBase+".sb"    # subjects file for this page
				
		# if both files (wikicats and subjects) exists, use them from local store
		if os.path.exists(fileNameCandidateWikicats) and os.path.exists(fileNameCandidateSubjects):
			print("Files WK and SB already available in local DB for", fileNameCandidate)
			fwsize = os.path.getsize(fileNameCandidateWikicats)
			fssize = os.path.getsize(fileNameCandidateSubjects)
			# if one of these two files is empty (no wikicats or no subjects), this page will not be used
			if (fwsize == 0) or (fssize == 0):
				listWithoutWikicats.append(page)
			else:
				listWithWikicats.append(page)
		else: # if one file not exists, fetch from Internet candidate text wikicats and subjects		
			try:  # open and read text of candidate file
				candidateTextFile = _Open(fileNameCandidate, "r")
				candidate_text = candidateTextFile.read()
				print("Reading candidate text file:", fileNameCandidate)
			except:  # file that inexplicably could not be read from local store, it will not be used
				_appendFile(logFilename, "ERROR buildCorpus2(): Unavailable candidate file, not in the store, but it should be: "+fileNameCandidate)
				listWithoutWikicats.append(page)
				continue
			
			print("Computing wikicats and subjects for:", page)
			candidate_text_categories = _getCategoriesInText(candidate_text)  # function _getCategoriesInText from px_DB_Manager
			
			if ("error" in candidate_text_categories):  # error while fetching info, the page will not be used
				_appendFile(logFilename, "ERROR buildCorpus2(): Problem in _getCategoriesInText(candidate_text): "+candidate_text_categories["error"])
				listWithoutWikicats.append(page)
				continue
				
			print("Wikicats and subjects downloaded for", fileNameCandidate)
			candidate_text_wikicats = list(filter(_filterSimpleWikicats, candidate_text_categories["wikicats"])) # remove simple wikicats with function from aux.py
			candidate_text_subjects = list(filter(_filterSimpleSubjects, candidate_text_categories["subjects"])) # remove simple subjects with function from aux.py
			
			_saveFile(fileNameCandidateWikicats, '\n'.join(candidate_text_wikicats))  # save file with original text wikicats, one per line
			_saveFile(fileNameCandidateSubjects, '\n'.join(candidate_text_subjects))  # save file with original text subjects, one per line
			currentDownloaded += 1
			
			# if no wikicats or no subjects, teh page will not be used
			if (len(candidate_text_wikicats) == 0) or (len(candidate_text_subjects) == 0):
				listWithoutWikicats.append(page)
			else:
				listWithWikicats.append(page)

	
	lenListWithWikicats = len(listWithWikicats)
	
	_appendFile(logFilename, "Number of available pages with wikicats and subjects: "+str(lenListWithWikicats))
	
	print("")
	print("ALL WIKICATs AND SUBJECTs COMPUTED.")
	print("New items computed in this iteration:", str(currentDownloaded))
	print("Number of pages with wikicats:", str(len(listWithWikicats)))
	print("Number of pages without wikicats:", str(len(listWithoutWikicats)))
		
	if aux.PSTOP == True:
		input("Type ENTER to continue...")
		
		
		
	print("\n Computing similarities...")
	
	discarded_pages_list = []     # a list to save discarded pages' URLs
	similarity = _textSimilarityFunctions()    # Create a textSimilarityFunctions object to measure text similarities
	
	# variables to store results
	sims_wk_sb = []	# list of triplets (filenameCandidate, similarityByWikicats, similarityBySubjects)	
	distribution_wk = {"0":0, "1":0, "2":0, "3":0, "4":0, "5":0, "6":0, "7":0, "8":0, "9":0}
	distribution_sb = {"0":0, "1":0, "2":0, "3":0, "4":0, "5":0, "6":0, "7":0, "8":0, "9":0}
			
	# Measure text similarity, and discard pages (discarded_pages_list) without a minimum similarity
	for idx, page in enumerate(listWithWikicats, start=1):
		
		print("(", idx, "of", lenListWithWikicats, ") -- ", page)
						
		# Build filename for this page
		pageWithoutHTTP = page[2+page.find("//"):]
		domainFolder = pageWithoutHTTP[:pageWithoutHTTP.find("/")]
		onlyPage = pageWithoutHTTP[1+pageWithoutHTTP.find("/"):]
		onlyPageChanged =  onlyPage.replace("/", "..")
		fileNameCandidateBase = _SCRAPPED_TEXT_PAGES_FOLDER+"/"+domainFolder+"/"+onlyPageChanged
		fileNameCandidate = fileNameCandidateBase+".txt"
		fileNameCandidateWikicats = fileNameCandidateBase+".wk"
		fileNameCandidateSubjects = fileNameCandidateBase+".sb"
				
		# try:  # open and read local file if already exists
		# 	candidateTextFile = _Open(fileNameCandidate, "r")
		# 	pageContent = candidateTextFile.read()
		# 	print("Reading file:", fileNameCandidate)
		# except:  # file that could not be downloaded
		# 	print("ERROR buildCorpus2(): Unavailable file, not in the store, but it should be:", fileNameCandidate)
		# 	input("ENTER to continue...")
		# 	continue


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
		shared_wikicats_jaccard_similarity = similarity.sharedWikicatsSimilarity(selectedWikicats, fileNameCandidateWikicats, logFilename)
		print("Wikicats shared jaccard similarity = "+str(shared_wikicats_jaccard_similarity))
		
		shared_subjects_jaccard_similarity = similarity.sharedSubjectsSimilarity(sbOriginalText, fileNameCandidateSubjects, logFilename)
		print("Subjects shared jaccard similarity = "+str(shared_subjects_jaccard_similarity))
		
		sims_wk_sb.append((fileNameCandidate, shared_wikicats_jaccard_similarity, shared_subjects_jaccard_similarity))
		
		# to compute distributions 
		if shared_wikicats_jaccard_similarity == -1:
			_appendFile(logFilename, "ERROR computing sharedWikicatsJaccard: "+fileNameCandidateWikicats)
		else:
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
	
	
		if shared_subjects_jaccard_similarity == -1:
			_appendFile(logFilename, "ERROR computing sharedSubjectsJaccard: "+fileNameCandidateSubjects)
		else:
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
	
	
	
	
		
		# # Save similarity to a CSV file
		# with _Open(_SIMILARITIES_CSV_FILENAME, 'a') as writeFile:
		# 	writer = csv.writer(writeFile, delimiter=';')
		# 	writer.writerow([page, euclidean_distance, spacy_similarity, doc2vec_euclideanDistance,
		# 	doc2vec_cosineSimilarity, doc2vec_trained_euclideanDistance, doc2vec_trained_cosineSimilarity, shared_wikicats_jaccard_similarity])


		# Minimum similarity for a page to be accepted.
		# WE MUST DECIDE THE MOST RELEVANT CRITERIUM TO DECIDE ON IT
		# currently, we used shared_wikicats_jaccard_similarity

	
	
	min_similarity = 0.3  # review this threshold
		
	both_above_min = list(filter(lambda triple : ((triple[1] > min_similarity) and (triple[2] > min_similarity)), sims_wk_sb)) 

	_appendFile(logFilename, "Number of pages with both similarities above "+str(min_similarity)+" = "+str(len(both_above_min)))
	print("Number of pages with both similarities above", min_similarity, "=", len(both_above_min))
	
	
	sims_wk_sb_str = list(map(lambda triple : (triple[0]+" "+str(triple[1])+" "+str(triple[2])), sims_wk_sb)) 
	_saveFile(_CORPUS_FOLDER+"/"+str(lenOriginalText)+".sims", '\n'.join(sims_wk_sb_str))

	result["distribution_wk"] = distribution_wk
	result["distribution_sb"] = distribution_sb
		
	# Save the discarded_pages_list to a file
	_saveFile(_DISCARDED_PAGES_FILENAME, '\n'.join(discarded_pages_list))
	# print(str(len(discarded_pages_list)) + " discarded pages")
	
	
	# print distributions
	t0 = distribution_wk["0"]
	p0 = 100*t0/lenListWithWikicats
	
	t1 = distribution_wk["1"]
	p1 = 100*t1/lenListWithWikicats
	t1a = t0+t1
	p1a = 100*t1a/lenListWithWikicats
		
	t2 = distribution_wk["2"]
	p2 = 100*t2/lenListWithWikicats
	t2a = t1a+t2
	p2a = 100*t2a/lenListWithWikicats
		
	t3 = distribution_wk["3"]
	p3 = 100*t3/lenListWithWikicats
	t3a = t2a+t3
	p3a = 100*t3a/lenListWithWikicats
	
	t4 = distribution_wk["4"]
	p4 = 100*t4/lenListWithWikicats
	t4a = t3a+t4
	p4a = 100*t4a/lenListWithWikicats
	
	t5 = distribution_wk["5"]
	p5 = 100*t5/lenListWithWikicats
	t5a = t4a+t5
	p5a = 100*t5a/lenListWithWikicats
	
	t6 = distribution_wk["6"]
	p6 = 100*t6/lenListWithWikicats
	t6a = t5a+t6
	p6a = 100*t6a/lenListWithWikicats
	
	t7 = distribution_wk["7"]
	p7 = 100*t7/lenListWithWikicats
	t7a = t6a+t7
	p7a = 100*t7a/lenListWithWikicats
	
	t8 = distribution_wk["8"]
	p8 = 100*t8/lenListWithWikicats
	t8a = t7a+t8
	p8a = 100*t8a/lenListWithWikicats
	
	t9 = distribution_wk["9"]
	p9 = 100*t9/lenListWithWikicats
	t9a = t8a+t9
	p9a = 100*t9a/lenListWithWikicats
	
	print("TOTAL WIKICATS = ", lenListWithWikicats)
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
	p0 = 100*t0/lenListWithWikicats
	
	t1 = distribution_sb["1"]
	p1 = 100*t1/lenListWithWikicats
	t1a = t0+t1
	p1a = 100*t1a/lenListWithWikicats
		
	t2 = distribution_sb["2"]
	p2 = 100*t2/lenListWithWikicats
	t2a = t1a+t2
	p2a = 100*t2a/lenListWithWikicats
		
	t3 = distribution_sb["3"]
	p3 = 100*t3/lenListWithWikicats
	t3a = t2a+t3
	p3a = 100*t3a/lenListWithWikicats
	
	t4 = distribution_sb["4"]
	p4 = 100*t4/lenListWithWikicats
	t4a = t3a+t4
	p4a = 100*t4a/lenListWithWikicats
	
	t5 = distribution_sb["5"]
	p5 = 100*t5/lenListWithWikicats
	t5a = t4a+t5
	p5a = 100*t5a/lenListWithWikicats
	
	t6 = distribution_sb["6"]
	p6 = 100*t6/lenListWithWikicats
	t6a = t5a+t6
	p6a = 100*t6a/lenListWithWikicats
	
	t7 = distribution_sb["7"]
	p7 = 100*t7/lenListWithWikicats
	t7a = t6a+t7
	p7a = 100*t7a/lenListWithWikicats
	
	t8 = distribution_sb["8"]
	p8 = 100*t8/lenListWithWikicats
	t8a = t7a+t8
	p8a = 100*t8a/lenListWithWikicats
	
	t9 = distribution_sb["9"]
	p9 = 100*t9/lenListWithWikicats
	t9a = t8a+t9
	p9a = 100*t9a/lenListWithWikicats
	
	print("TOTAL SUBJECTS = ", lenListWithWikicats)
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
				

	return jsonify(result)



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
				print("*** ERROR getUrlsLinked2Wikicats(): Error starting DB query for", wikicat, ":", exc)
				_appendFile(logFilename, "ERROR getUrlsLinked2Wikicats(): Error starting DB query for "+wikicat+": "+repr(exc))
				requestDB = None
				
			requestObjects[wikicat] = {"db": requestDB}  # store the request DB object for this wikicat
			requestDone = 1
		

		# now, read or fetch Wikicat results for Wikidata
		
		filename_wk = _URLs_FOLDER+"/_Wikicat_"+wikicat+"_WK_Urls.txt"	

		# it uses update with the objects dictionary, as the wikicat key has been already created for DBpedia	
		
		wcs = _getWikicatComponents(wikicat)
		wcs_string = " ".join(wcs)
		
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
					bd:serviceParam mwapi:srsearch '"""+wcs_string+"""' .
					?title wikibase:apiOutput mwapi:title .
				}
			} 		
			"""
			# start the WK query
			try:
				print("Starting WK query for: ", wcs_string)
				requestWK = _session.post(_URL_WK, data={"query": queryWK}, headers={"accept": "application/json"})
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
						_saveFile(_URLs_FOLDER+"/_Wikicat_"+wikicat+"_DB_Urls.txt", '\n'.join(urlsDB))  # save all results from DB for this wikicat
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
						_saveFile(_URLs_FOLDER+"/_Wikicat_"+wikicat+"_WK_Urls.txt", '\n'.join(urlsWK)) # save all results from WK for this wikicat
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
