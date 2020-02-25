import os
import requests
import re
import time
import pickle
from flask import request, jsonify
from requests_futures.sessions import FuturesSession
import shutil
from smart_open import open as _Open

from px_DB_Manager import getCategoriesInText as _getCategoriesInText
from px_aux import saveFile as _saveFile, URL_DB as _URL_DB, URL_WK as _URL_WK

from aux import CORPUS_FOLDER as _CORPUS_FOLDER
from aux import hasFieldPT as _hasFieldPT  # function to check if object has  ["pt"]["value"] field
from aux import getWikicatComponents as _getWikicatComponents, filterSimpleWikicats as _filterSimpleWikicats
	
	

# QUERY (/getWikicatsFromText) to attend the query to get wikicats from a text   
# receives: the text
# computes and saves files with wikicats (length.wk) and subjects (length.sb)
# returns:
# result["wikicats"]: list of wikicats (and saves them in the file $CORPUS_FOLDER/length.wk)
# result["subjects"]: list of subjects (and saves them in the file $CORPUS_FOLDER/length.sb)
# result[wk] = [component list] one for each wikicat
# result["formerSelectedWikicats"]: list of wikicats selected in the past, to be identified in the interface
def getWikicatsFromText():
	if request.method == "POST":		
		originalText = request.values.get("text")
		len_text = len(originalText)  # length of the received text
				
		if not os.path.exists(_CORPUS_FOLDER):  # create KORPUS folder if not exists
			os.makedirs(_CORPUS_FOLDER)
			
		filename = _CORPUS_FOLDER+"/"+str(len_text)+".txt"   # save the received text with length.txt filename
		_saveFile(filename, originalText)
		
		filename_wk = _CORPUS_FOLDER+"/"+str(len_text)+".wk"   # filename for wikicats (length.wk)
		filename_sb = _CORPUS_FOLDER+"/"+str(len_text)+".sb"   # filename for subjects (length.sb)
				
		result = {}
		
		try:  # open wikicats file if exists
			with _Open(filename_wk) as fp:
				listWikicats = fp.read().splitlines()
				result["wikicats"] = listWikicats
		except:  # fetch wikicats if file does not exist yet
			result = _getCategoriesInText(originalText)  # function getCategoriesInText from px_DB_Manager.py
		
			if ("error" in result):   # return error if could not fetch wikicats 
				return jsonify(result);
			
			listWikicats = list(filter(_filterSimpleWikicats, result["wikicats"])) # remove simple wikicats with function from aux.py
			result["wikicats"] = listWikicats  # update result wikicats to return
			
			_saveFile(filename_wk, '\n'.join(listWikicats))  # save file (length.wk) with wikicats, one per line
			
			listSubjects = list(filter(_filterSimpleWikicats, result["subjects"]))  # remove simple subjects with function from aux.py
			result["subjects"] = listSubjects # update result subjects to return
			
			_saveFile(filename_sb, '\n'.join(listSubjects)) # save file (length.sb) with subjects, one per line
			
		
		for w in listWikicats:    # compute components for every wikicat and add all of them to result
			wlc = _getWikicatComponents(w)   # function getWikicatComponets from aux.py
			result[w] = wlc  # one entry by wikicat
		
		filename_selected = _CORPUS_FOLDER+"/"+str(len_text)+".selected.wk"   # previously selected wikicats file for this text
		
		try:  # try to open previously selected wikicats file if exists
			with _Open(filename_selected) as fp:
				wkSelectedList = fp.read().splitlines()
		except:
			wkSelectedList = []    # no previously selected wikicats
		
		result["formerSelectedWikicats"] = wkSelectedList
		
		return jsonify(result);
	










#############################################################################################################################################	

# Para que vale lo siguiente?


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




# aux function to get results for DB
def getUrlsWithWikicatFromDBpedia (wikicat):
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




# aux function to get results for WK
def getUrlsWithWikicatFromWikidata (wikicat):
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

