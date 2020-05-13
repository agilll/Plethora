# script to test function processS3List in S3_UpdateTextsEntities.py

# input: a list of .s files (a .s.p file must also exist)
# output: several files will be created in the same folder
#			a .s.w file with the changes, for every processed file
#			a .s.w.p file with the updated entities, as the surface forms and the offsets have changed


import os
import sys

from S3_UpdateTextsEntities import processS3List as _processS3List

# parameter checking

# one parameter is required  
if len(sys.argv) > 1:
	print("Use: python3 "+sys.argv[0])
	exit(-1)
	
	
# start processing
	
print("Processing list...")
_processS3List(["/Users/agil/GitHub/Plethora/CORPUS/files_s_p_w/d01.txt.s", "/Users/agil/GitHub/Plethora/CORPUS/files_s_p_w/d02.txt.s"])



	


	
