# training Doc2Vec models with .w files (preprocessed .txt files, but still text files)

import os
import sys
import collections
import glob
import csv
from smart_open import open as _Open
from datetime import datetime
import codecs


GEN_FOLDER_BASE = "/Users/agil/Downloads/_corpus"
GEN_FOLDER_INPUT = GEN_FOLDER_BASE+"/webbase/"
GEN_FOLDER_OUTPUT = GEN_FOLDER_BASE+"/webbase2/"

# read the generic corpus docs
listGeneric = []
if not os.path.exists(GEN_FOLDER_INPUT):
	print(GEN_FOLDER_INPUT, "not found!")
	quit()
else:
	listGeneric = glob.glob(GEN_FOLDER_INPUT+"*.txt")	# Get all .txt files in the generic training corpus



startTime = datetime.now()
for i,file in enumerate(listGeneric):
	print(i, file)
	with codecs.open(file, 'r', encoding='utf-8', errors='ignore') as fdata:
		listaDocs = []
		suffix=0
		file_name = file[1+file.rindex("/"):]
		for uid, line in enumerate(fdata):
			sline = line.strip()
			if (len(sline)) > 0:
				listaDocs.append(line)
			if (len(listaDocs) == 10000):
				suffix += 1
				file_output = GEN_FOLDER_OUTPUT+file_name+"_"+str(suffix)+".txt"
				foutput = codecs.open(file_output, 'w', encoding='utf-8', errors='ignore')
				for doc in listaDocs:
					foutput.write(doc)
				listaDocs.clear()
		if (len(listaDocs) > 0):
			suffix += 1
			file_output = GEN_FOLDER_OUTPUT+file_name+"_"+str(suffix)+".txt"
			foutput = codecs.open(file_output, 'w', encoding='utf-8', errors='ignore')
			for doc in listaDocs:
				foutput.write(doc)

endTime = datetime.now()
elapsedTime = endTime - startTime
print("Duración:", elapsedTime.seconds)
