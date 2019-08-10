import os
import requests
import re
import time
import pickle
from flask import request, jsonify
from os.path import isfile
from requests_futures.sessions import FuturesSession

import shutil


# to attend the query to get wikicats from a text   (/getWikicatsFromText)
# receives: the text
# returns: list of wikicats (and stores them in the file CORPUS_FOLDER/WIKICAT_LIST)
def getWikicatsFromText():
	if request.method == "POST":
		from px_aux import CORPUS_FOLDER as _CORPUS_FOLDER, WIKICAT_LIST_FILENAME as _WIKICAT_LIST_FILENAME, SELECTED_WIKICAT_LIST_FILENAME as _SELECTED_WIKICAT_LIST_FILENAME, saveFile as _saveFile
		from px_DB_Manager import getCategoriesInText as _getCategoriesInText
		
		texto = request.values.get("text")
		
		result = _getCategoriesInText(texto)
		
		if ("error" in result):
			return jsonify(result);
		
		content = ""
		for w in result["wikicats"]:
			content += w+"\n"
		
		_saveFile(_CORPUS_FOLDER+"/"+_WIKICAT_LIST_FILENAME, content)

		fileSelectedWikicats = _CORPUS_FOLDER+"/"+_SELECTED_WIKICAT_LIST_FILENAME
		
		try:
			with open(fileSelectedWikicats) as fp:
				wkList = fp.read().splitlines()
		except:
			wkList = []
		
		result["formerSelectedWikicats"] = wkList
		
		return jsonify(result);
	


#############################################################################################################################################	

# to attend the query to build the corpus (/buildCorpus)
# receives: the list of selected wikicats
# returns: the results, mainly the number of files identified for each wikicat
def buildCorpus():
	from px_aux import CORPUS_FOLDER as _CORPUS_FOLDER, SELECTED_WIKICAT_LIST_FILENAME as _SELECTED_WIKICAT_LIST_FILENAME, saveFile as _saveFile
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
	urlsObjects = getUrlsWithWikicats(selectedWikicats)
	print("\n\nReceived result for all the queries\n")
	
	result = {}
	fullList = [] # to agregate the full list of URLs
		
	# process all results to return
	for wikicat in selectedWikicats:
		# first, the results from DB
		content = ""
		dbUrls = urlsObjects[wikicat]["db"]
		fullList.extend(dbUrls)
		numUrlsDB += len(dbUrls)
		for url in dbUrls:
			content += url+"\n"
		_saveFile(_CORPUS_FOLDER+"/_Wikicat_"+wikicat+"_DB_Urls.txt", content)  # save all results from DB
				
		# now, the results from WK
		content = ""
		wkUrls = urlsObjects[wikicat]["wk"]
		fullList.extend(wkUrls)
		numUrlsWK += len(wkUrls)
		for url in wkUrls:
			content += url+"\n"
		_saveFile(_CORPUS_FOLDER+"/_Wikicat_"+wikicat+"_WK_Urls.txt", content) # save all results from WK
	
		longs1 = "(" + str(len(dbUrls)) + "," + str(len(wkUrls)) + ")"
		print(wikicat, longs1, end=', ')
		result[wikicat] = {"db": len(dbUrls), "wk": len(wkUrls)}  # add results for this wikicat
	
	listWithoutDuplicates = list(set(fullList))  # remove duplicates URLs
	print("\n", numUrlsDB, numUrlsWK, len(listWithoutDuplicates))
	# returns number of results
	result["totalDB"] = numUrlsDB
	result["totalWK"] = numUrlsWK
	result["totalUrls"] = len(listWithoutDuplicates)
	
	return jsonify(result);  


# aux function to all the URLs associated to a wikicats set
# It queries DB and WK and parses the results
def getUrlsWithWikicats (selectedWikicats):
	from px_aux import hasFieldPT as _hasFieldPT  # function to check if object has  ["pt"]["value"] field
	requestObjects = {} # to store request objects 
	
	print("Starting queries for: ", end='')
	_session = FuturesSession()  # to manage asynchronous requests 
					
	for wikicat in selectedWikicats:
		from px_aux import URL_DB as _URL_DB, URL_WK as _URL_WK
		
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
		except:
			print("\n*** Error querying DB for", wikicat, ")")
			requestDB = None
			
		try:
			requestWK = _session.post(_URL_WK, data={"query": queryWK}, headers={"accept": "application/json"})
		except:
			print("\n***Error querying WK for", wikicat, ")")
			requestWK = None	
		
		requestObjects[wikicat] = {"db": requestDB, "wk": requestWK}  # store the request objects for this wikicat
		time.sleep(4)  # delay to avoid server reject for too many queries
		
	
	print("\n\nAll queries started\n")
	# an object {"db": urlsDB, "wk": urlsWK} for each wikicat (each field is a URL list)
	urlsObjects = {}
	
	# now, read the results from queries
	print("Waiting queries' result for: ", end='')
	
	for wikicat in selectedWikicats:
		print(wikicat, end=' ', flush=True)
		requestDB = requestObjects[wikicat]["db"] # get the request objects for this wikicat
		requestWK = requestObjects[wikicat]["wk"]
		
		# study results for DB
		if requestDB != None:  #error starting query, return []
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
					urlsDB = list(map(lambda x: x["pt"]["value"], bindingsDBwithPT))
			except Exception as exc:
				print("\n***Error querying DB for", wikicat,":", exc)
				urlsDB = []

		else:
			print("\n***Error querying DB for", wikicat, ": the query could not be started")
			urlsDB = []
		
		# end for DB
		
		# study results for WK
			
		def addPrefix (x):
			return "https://en.wikipedia.org/wiki/"+x["title"]["value"].replace(" ", "_")
		
		
		if requestWK != None:  #error starting query, return []
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
					
					urlsWK = list(map(addPrefix, bindingsWK))
	
			except Exception as exc:
				print("\n***Error querying WK for", wikicat,":", exc)
				urlsWK = []
		
		else:
			print("\n***Error querying WK for", wikicat, ": the query could not be started")
			urlsWK = []
				
		# store results for this wikicat		
		urlsObjects[wikicat] = {"db": urlsDB, "wk": urlsWK}
		
	return urlsObjects  # return results to buildCorpus function


#############################################################################################################################################	

# to attend the query to search and return results for a given wikicat  
# receives: a  wikicat
# returns: results from DBpedia or Wikidata
def getWikicatUrls():
	wikicat = request.values.get("wikicat")
	DB = request.values.get("DB")  # to mark if DBpedia or Wikidata is requested
	
	if DB == "true":
		results = getUrlsWithWikicatFromDBpedia(wikicat)  # results for DB are requested
	else:
		results = getUrlsWithWikicatFromWikidata(wikicat)  # results for WK are requested
		
	if results == None:
		return jsonify({"error": "Error in query"});
	
	result = {}
	result["urls"] = results
	return jsonify(result);


#aux function to get results for DB
def getUrlsWithWikicatFromDBpedia (wikicat):
	from px_aux import URL_DB as _URL_DB, hasFieldPT as _hasFieldPT
	
	_session = FuturesSession()  # to manage asynchronous requests 
		
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
	requestDB = _session.post(_URL_DB, data={"query": queryDB}, headers={"accept": "application/json"})
	responseDB = requestDB.result()  # wait for query completion

	if responseDB.status_code != 200:
		print("Error in wikicats query to DBpedia: ", responseDB.status_code)
		return None
		
	responseDBJson = responseDB.json()
	bindingsDB = responseDBJson["results"]["bindings"]
	bindingsDBwithPT = list(filter(_hasFieldPT, bindingsDB))
	urlsDB = list(map(lambda x: x["pt"]["value"], bindingsDBwithPT))
	
	return urlsDB


#aux function to get results for WK
def getUrlsWithWikicatFromWikidata (wikicat):
	from px_aux import URL_WK as _URL_WK
	
	_session = FuturesSession()  # to manage asynchronous requests 
	
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

	requestWK = _session.post(_URL_WK, data={"query": queryWK}, headers={"accept": "application/json"})
	responseWK = requestWK.result()  # wait for query completion

	if responseWK.status_code != 200:
		print("Error in wikicats query to Wikidata: ", responseWK.status_code)
		return None

	responseWKJson = responseWK.json()
	bindingsWK = responseWKJson["results"]["bindings"]
	urlsWK = list(map(lambda x: "https://en.wikipedia.org/wiki/"+x["title"]["value"], bindingsWK))	

	return urlsWK

