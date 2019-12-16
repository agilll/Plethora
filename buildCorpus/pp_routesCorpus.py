import os
import requests
import re
import time
import pickle
from flask import request, jsonify
from os.path import isfile
from requests_futures.sessions import FuturesSession
import shutil

from px_DB_Manager import getCategoriesInText as _getCategoriesInText
from px_aux import saveFile as _saveFile, URL_DB as _URL_DB, URL_WK as _URL_WK

from aux import CORPUS_FOLDER as _CORPUS_FOLDER, WIKICAT_LIST_FILENAME as _WIKICAT_LIST_FILENAME, SELECTED_WIKICAT_LIST_FILENAME as _SELECTED_WIKICAT_LIST_FILENAME 
from aux import hasFieldPT as _hasFieldPT  # function to check if object has  ["pt"]["value"] field
	
	
# QUERY (/getWikicatsFromText) to attend the query to get wikicats from a text   
# receives: the text
# returns:
# result[wikicats]: list of wikicats (and stores them in the file $CORPUS_FOLDER/$WIKICAT_LIST_FILENAME)
# result[formerSelectedWikicats]: list of wikicats selected in the past, to be identified in the interface
def getWikicatsFromText():
	if request.method == "POST":		
		originalText = request.values.get("text")
		
		result = _getCategoriesInText(originalText)  # function _getCategoriesInText from px_DB_Manager
		
		if ("error" in result):
			return jsonify(result);
		
		content = ""
		for w in result["wikicats"]:
			content += w+"\n"
		
		if not os.path.exists(_CORPUS_FOLDER):
			os.makedirs(_CORPUS_FOLDER)
		
		_saveFile(_CORPUS_FOLDER+"/"+_WIKICAT_LIST_FILENAME, content)

		# this is the file with the  Wikicats selected in the past
		fileSelectedWikicats = _CORPUS_FOLDER+"/"+_SELECTED_WIKICAT_LIST_FILENAME
		
		try:
			with open(fileSelectedWikicats) as fp:
				wkList = fp.read().splitlines()
		except:
			wkList = []
		
		result["formerSelectedWikicats"] = wkList
		
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

