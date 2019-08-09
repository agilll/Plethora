#!/Library/Frameworks/Python.framework/Versions/Current/bin/python3

# This script receives as parameter a file (.s) or a folder and, for each file, it generate other (.s.p) with the entities identified in DB-SL 
# input: a .s file or a folder
#			if folder, folder/files_s_p_w must exist, and all '.s' files in folder/files_s_p_w will be processed
# outputs: several files will be created in folder/files_s_p_w
#			a file with '.s.p' extension for each processed file
#			a .s.p.html file with the entities marked in green
 
# IMPORTANT: the identification of entities in DB-SL is done with parameters 'confidence=0.5' and 'support=1'

# select ?uri ?label (group_concat(?subject; separator=";") as ?subjects) (group_concat(?type; separator=";") as ?types)
# where {

# VALUES ?uri {<http://dbpedia.org/resource/Hera> <http://dbpedia.org/resource/Eurotas> <http://dbpedia.org/resource/Dodona> <http://dbpedia.org/resource/Determinism> <http://dbpedia.org/resource/Julius_Caesar>} .
# ?uri rdfs:label ?label; rdf:type ?type .
# ?uri dct:subject ?subject .
# FILTER(regex(?type,'http://dbpedia.org/ontology|http://dbpedia.org/class/yago')) . FILTER(lang(?label) = 'en')} group by ?label ?uri


import os
import pickle
import json
import requests
import sys
sys.path.append('../')


from px_aux import URL_DB_SL_annotate as _URL_DB_SL_annotate, getContentMarked as _getContentMarked, saveFile as _saveFile
from px_DB_Manager import DBManager as _DBManager

SPW_FOLDER = "/files_s_p_w/"

# to process a file and return dictionaries with the entities detected and filtered 
def findEntities (filename, confPar, supPar):
		
	content_file = open(filename, 'r')
	content = content_file.read()
	
	# DB-SL is queried for teh preferred entity for each candidate detected in the file
	# see section 6.4 of the document describing the architecture for the formats of request and answer 
	dbsl_response = requests.post(_URL_DB_SL_annotate, data={"text": content, "confidence": confPar, "support": supPar}, headers={"accept": "application/json", "content-type": "application/x-www-form-urlencoded"})
	
	# the previous one is a synchronous call, anly returns after receiving the answer, that will be passed now to JSON
	try:
		dbsl_json = dbsl_response.json()
		dbsl_json["Resources"] # if no entity is detected an exception is raised
	except:
		print("No entity detected in the file")
		return {'byUri': {}, 'byType': {}, 'byOffset': {}}

	print("Detected", len( dbsl_json["Resources"]), "entities")
	
	# create class  _DBManager to parse results
	dbpediaManager = _DBManager()
	dbpediaManager.scanEntities(dbsl_json)
	allDicts = dbpediaManager.getDictionaries()
	
	byUri = allDicts["byUri"]
	byType = allDicts["byType"]
	byOffset = allDicts["byOffset"]
	byuriplana = [item for sublist in byUri.values() for item in sublist]
	print(len(byUri.keys()), len(byuriplana), len(byType.keys()), len(byOffset.keys()))
	
	return allDicts








# at least a parameter  
if len(sys.argv) < 2:
	print("Use: "+sys.argv[0]+" file|folder")
	exit(-1)

confidence = 0.5   # default parameters for DB-SL
support = 1

# if one parameter it cannot start by '-'
if len(sys.argv) == 2:
	origin = sys.argv[1]

# to simplify,  '-c' and '-s' must go together, or both or none
elif len(sys.argv) == 6:
	if sys.argv[1] == "-c":
		confidence = sys.argv[2]
	elif sys.argv[1] == "-s":
		support = sys.argv[2]
	else:
		print("Use: "+sys.argv[0]+" file|folder")
		exit(-1)
		
	if sys.argv[3] == "-c":
		confidence = sys.argv[4]
	elif sys.argv[3] == "-s":
		support = sys.argv[4]
	else:
		print("Use: "+sys.argv[0]+" file|folder")
		exit(-1)
	
	origin = sys.argv[5]

else:
	print("Use: "+sys.argv[0]+" file|folder")
	exit(-1)
	
	
	
# start processing

print("Processing with Confidence=", confidence, " and Support=", support, "\n")

# process a file
if os.path.isfile(origin):
	if origin.endswith(".s"):
		print("Processing file "+origin+"...\n")
		entities = findEntities(origin, confidence, support)
		pickle.dump(entities, open(origin+".p", "wb" ))
			
		highlightedContent = _getContentMarked(origin, 's')
		_saveFile(origin+".p.html", highlightedContent)
	else:
		print("The file "+origin+" has not '.s' extension")
		exit(-1)
	
# process all '.s' files in a folder
elif os.path.isdir(origin):
	print("Processing folder "+origin+"...")
	numFiles = 0
	spw_folder = origin + SPW_FOLDER
	if not os.path.exists(spw_folder):
		print(spw_folder, "not found!")
		exit()
	
	for sfilename in sorted(os.listdir(spw_folder)):
		if sfilename.endswith(".s"):
			numFiles += 1
			sfullfilename = spw_folder+sfilename
			print("\n", numFiles, " **************** Processing file ", sfullfilename+"...\n")
			entities = findEntities(sfullfilename, confidence, support)
			pickle.dump(entities, open(sfullfilename+".p", "wb" ))
			
			highlightedContent = _getContentMarked(sfullfilename, "s")
			_saveFile(sfullfilename+".p.html", highlightedContent)
		else:
			continue
	
else:
	print(origin, "not found!")
	exit(-1)
	
	

	
	
	
	