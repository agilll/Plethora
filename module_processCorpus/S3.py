
# script to test function processS3File and processS3Folder in S3_UpdateTextsEntities.py
# This script changes in a .s file (or all .s files in a folder) every surface form detected (located in .s.p file) by the entity name 
# input: a .s file, or a folder 
#			if folder, folder/files_s_p_w must exist, and all '.s' files in folder/files_s_p_w will be processed  (for every .s file a .s.p file is supposed to exist with the entities)
# output: several files will be created in folder/files_s_p_w
#			a .s.w file with the changes, for every processed file
#			a .s.w.p file with the updated entities, as the surface forms and the offsets have changed

# process the file contents twice, and it is stored in memory (could be a problem for large texts)

import os, os.path
import sys

from S3_UpdateTextsEntities import processS3File as _processS3File, processS3Folder as _processS3Folder

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
	ok = _processS3File(source)
	if ok == -1:
		print(source, "could not be processed")
			
# source is a folder. It must be the base CORPUS folder
# it must exist a files_s_p_w folder inside
# process all '.s' files in source/files_s_p_w
elif os.path.isdir(source):
	ok = _processS3Folder(source)
	if ok == -1:
		print(source, "could not be processed")
	
else:
	print(source, "not found!")
	


	
