#!/Library/Frameworks/Python.framework/Versions/Current/bin/python3

# This script changes in a .s file (or all .s files in a folder) every surface form detected (located in .s.p file) by the entity name 
# input: a .s file, or a folder 
#			if folder, folder/files_s_p_w must exist, and all '.s' files in folder/files_s_p_w will be processed  (for every .s file a .s.p file is supposed to exist with the entities)
# output: several files will be created in folder/files_s_p_w
#			a .s.w file with the changes, for every processed file
#			a .s.w.p file with the updated entities, as the surface forms and the offsets have changed

# process the file contents twice, and it is stored in memory (could be a problem for large texts)

import re
import os, os.path
import pickle
import sys
sys.path.append('../')    # to search for imported files in the parent folder

from px_aux import getContentMarked as _getContentMarked, saveFile as _saveFile

from aux_process import  SPW_FOLDER as _SPW_FOLDER


# aux functions

# to see if last word of sf is the same of the first one of the entity name    
# def solapamiento (sf, en):
# 	sf_lw = sf.split()[-1]
# 	if en.startswith(sf_lw):
# 		return True
# 	else:
# 		return False
	
	
# to apply all processing to a .s file and return result to save it in a '.s.w' file  
# besides, as a colateral effect (not good), saves the new file '.s.w.p'
def getContentAfterChanges (sfilename, pfilename):
	
	finalContent = ""
	finalHTMLContent = ""
	
	sfile = open(sfilename, 'r')
	
	if not os.path.isfile(pfilename):
		print(pfilename+" not found!")
		return (finalContent, finalHTMLContent)
	
	pfile = open(pfilename, 'rb')
	
	content = sfile.read()
	dicsEntities = pickle.load(pfile)
	
	currentPosition = 0  # marks the position in the original file
		
	offsets = list(dicsEntities["byOffset"].keys())
	
	# new offset for every entity identified in the .w file, it is necessary to correct it wrt the .s as we change the text of the file
	nuevoOffset = 0  # marks the position in the result file   
	# new dict byOffset with the offset updates. NECESSARY?? may be it is possible to update directly in the old one
	newByOffset = {}
	
								
	# iteration follows the input order in dict, that it is the offset one from low to high 
	for i in  range(len(offsets)):
		o = offsets[i]
		entity = dicsEntities["byOffset"][o]
		
		if o != entity["@offset"]:
			print(o, "the offset index is different from the one included in the entity")
				
		sf = entity["@surfaceForm"]				
		nameEntity = entity["entityName"]
		
		text = content[currentPosition:int(o)]
		currentPosition += len(text)
		
		finalContent += text
		nuevoOffset += len(text)
		entity["@offset"] = nuevoOffset      # update offset
		# entity["@surfaceForm"] = nameEntity  # no actualizamos la surfaceForm, para conservarla. El ancla en el texto debe ser a partir de ahora entity["entityName"]
		newByOffset[nuevoOffset] = entity	 # and save it in the new dict 

		finalHTMLContent += text.replace("\n", "\n<br>")
		
		finalContent += nameEntity   # the entity name is copied in the output file 
		nuevoOffset += len(nameEntity)
		
		# in the HTML file,  write in blue if not modified, and in striked blue and after in green if modified  
		if sf == nameEntity:
			finalHTMLContent += "<span style='color: blue'><b>"+nameEntity+"</b></span>"
		else:
			finalHTMLContent += "<span style='color: blue; text-decoration:line-through'>"+sf+"</span> <span style='color: green'><b>"+nameEntity+"</b></span>"
		
		# Now see how much to advance in the original file    

		nameEntitySpaced = nameEntity.replace("_", " ") # divide the entity name in words 
		
		# if equal,  advance the length 
		if sf == nameEntitySpaced:
			currentPosition += len(sf)
		else:
			# if the sf last word is not a prefix of the entity name, continue processing .s file from the end of the sf 
			if not nameEntitySpaced.startswith(sf):
				currentPosition += len(sf)
			# if the sf last word is a prefix of the entity name, check if the following chars are in the entity name   
			else:		
				# nameEntitySpacedRemaining = nameEntitySpaced[len(sf):]   # el resto del nombre de la entidad tras la surface form
				# nextContent = content[currentPosition+len(sf):currentPosition+len(sf)+80]  # lo que viene a partir de la surface form en el fichero original
				
				# wordsSF = sf.split()
				# if len(wordsSF) > 1:
				# 	leadingSF = " ".join(wordsSF[0:-1])+" "
				# 	finalContent += leadingSF
				# 	currentPosition += len(leadingSF)
				
				nextContent = content[currentPosition:currentPosition+80]  
				if nextContent.startswith(nameEntitySpaced): # if the following chars include the name of the entity, we jump it 
					advanceTo = currentPosition + len(nameEntity)
					if i+1 < len(offsets):
						if advanceTo > int(offsets[i+1]):
							currentPosition += len(sf)
						else:
							currentPosition += len(nameEntity)
					else:
						currentPosition += len(sf)
				else:
					currentPosition += len(sf)
	
	dicsEntities["byOffset"] = newByOffset    # substitute the new byOffset
	
	# update byUri and byType from the byOffset
	(nu, nt) = rebuild(newByOffset)
	
	dicsEntities["byUri"] = nu
	dicsEntities["byType"] = nt
	pickle.dump(dicsEntities, open(sfilename+".w.p", "wb" ))
	
	return  (finalContent, finalHTMLContent)


# rebuild byUri and byType from the new byOffset
def rebuild(byOffset):
		newByType = {}
		newByUri = {}
		checkDuplicates = []
			
		for o in byOffset:
			entity = byOffset[o]

			# the string URI/surfaceForm must be not duplicated to put this entity in 'byUri'
			if entity["@URI"]+"/"+entity["@surfaceForm"] not in checkDuplicates:
				# if not duplicated, the unique string is added to the checkDuplicates list 
				checkDuplicates.append(entity["@URI"]+"/"+entity["@surfaceForm"])
		
				# put the entity in byUri if not already included 
				if entity['@URI'] not in newByUri:
					newByUri[entity['@URI']] = []  # if the URI no exists, create the list
					
				newByUri[entity['@URI']].append(entity)  # if already exists, add the new one corresponding to another sf
		
		
			# entity runs through all the entities indexed in byOffset  
			combinedTypes = entity["combinedTypes"]
	
			# study all types in this entity  
			for t in combinedTypes:
				if t not in newByType:  # if this type does mot exist in byType dictionary, the new key is created
					newByType[t] = []
				
				newByType[t].append(entity)   # add this entity to the list of entities of such type 
		
		return(newByUri, newByType)

# end of aux functions




# start processing

# parameter checking

# ok if only one param  
if len(sys.argv) == 2:
	# if only one param, cannot start by '-'
	if sys.argv[1][0] == "-":
		print("Use: "+sys.argv[0]+" file|folder")
		exit(-1)
	else:
		source = sys.argv[1]   # this is the file|folder with the source data
# error if more than one param
else:
	print("Use: "+sys.argv[0]+" file|folder")
	exit(-1)


# start processing

# process a file
if os.path.isfile(source):
	if not source.endswith(".s"):
		print("The file "+source+" has not '.s' extension")
		exit(-1)
	print("Processing file "+source+"...\n")
	result = getContentAfterChanges(source, source+".p")
	# save result in files with the same name a new extensions  
	_saveFile(source+".w", result[0])   # the new text with extensióo '.w'
	_saveFile(source+".w.html", result[1])   # the report with the changes with extension '.w.html'
	
	highlightedContent = _getContentMarked(source+".w", "w")
	_saveFile(source+".w.p.html", highlightedContent)
			
# source is a folder. It must be the base CORPUS folder
# it must exist a files_s_p_w folder inside
# process all '.s' files in source/files_s_p_w
elif os.path.isdir(source):
	print("Processing folder "+source+"...")
	spw_folder = source + _SPW_FOLDER
	if not os.path.exists(spw_folder):
		print(spw_folder, "not found!")
		exit()
	for sfilename in sorted(os.listdir(spw_folder)):
		if not sfilename.endswith(".s"):
			continue
		else:
			sfullfilename = spw_folder+"/"+sfilename
			pfullfilename = sfullfilename+".p"
			print("**************** Processing file ", sfullfilename)
			result = getContentAfterChanges(sfullfilename, pfullfilename)
			# save result in files with the same name and extension '.w'
			_saveFile(sfullfilename+".w", result[0])
			_saveFile(sfullfilename+".w.html", result[1])
			
			highlightedContent = _getContentMarked(sfullfilename+".w", "w")
			_saveFile(sfullfilename+".w.p.html", highlightedContent)
	
else:
	print(source, "not found!")
	


	
