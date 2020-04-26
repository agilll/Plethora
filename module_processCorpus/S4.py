
# This script tokenizes .w files to get .t files
# a .w file is a text file that has been preprocessed with previous scripts
# a .t file is a binary file, saved with pickle, containing a list of lists of words

# tokenize is to convert the text in a list of sentences, each sentence being a list of words

# input: a .w file or a folder (the CORPUS base)
#         if folder, folder/files_s_p_w must exist, and all '.w' files in folder/files_s_p_w will be processed 
# output: a .t file per .w file, where text has been changed by a list of lists of words (saved in binary with pickle)
#         in case a folder, folder/files_t will be created to store results

# Requires the Stanford Core NLP server to be started and listening in port 9000
# get into the Stanford Core NLP folder and execute
# java -mx4g -cp "*" edu.stanford.nlp.pipeline.StanfordCoreNLPServer -port 9000 -timeout 15000 &

import os
import sys

from S4_tokenize import processS4File as _processS4File, processS4Folder as _processS4Folder

# parameter checking

# at least, one param
if len(sys.argv) < 2:
	print("Use: "+sys.argv[0]+" file|folder")
	exit(-1)

# if only one param, cannot start by '-'
if len(sys.argv) == 2:
	if sys.argv[1][0] == "-":
		print("Use: "+sys.argv[0]+" file|folder")
		exit(-1)
	else:
		source = sys.argv[1]  # this is the file|folder with the source data

# error if more than one param
else:
	print("Use: "+sys.argv[0]+" file|folder")
	exit(-1)

	


# process a file
if os.path.isfile(source):
	print("Processing file "+source+"...\n")
	ok = _processS4File(source)
	if ok == -1:
		print(source, "could not be processed")

# process a folder
elif os.path.isdir(source):
	ok = _processS4Folder(source)
	if ok == -1:
		print(source, "could not be processed")
	
else:
	print(source, "not found!")