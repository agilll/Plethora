import os

from flask import request, jsonify
from smart_open import open as _Open

from px_DB_Manager import getCategoriesInText as _getCategoriesInText
from px_aux import saveFile as _saveFile

from aux import CORPUS_FOLDER as _CORPUS_FOLDER
from aux import getWikicatComponents as _getWikicatComponents, filterSimpleWikicats as _filterSimpleWikicats
	
	

# QUERY (/getWikicatsFromText) to attend the query to get wikicats from a text   
# receives: the text
# computes and saves files with wikicats (length.wk) and subjects (length.sb)
# returns:
# result["wikicats"]: list of wikicats (and saves them in the file $CORPUS_FOLDER/length.wk)
# result["subjects"]: list of subjects (and saves them in the file $CORPUS_FOLDER/length.sb)
# result[wk] = [component list] one for each wikicat, with the different components of each wikicat name
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
			result[w] = wlc  # one entry per wikicat
		
		filename_selected = _CORPUS_FOLDER+"/"+str(len_text)+".selected.wk"   # previously selected wikicats file for this text
		
		try:  # try to open previously selected wikicats file if exists
			with _Open(filename_selected) as fp:
				wkSelectedList = fp.read().splitlines()
		except:
			wkSelectedList = []    # no previously selected wikicats
		
		result["formerSelectedWikicats"] = wkSelectedList
		
		return jsonify(result);
	
