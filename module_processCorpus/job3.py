import sys
import os
import glob
import shutil
import requests
from smart_open import open as _Open

from S1_AddSuffixToTexts import  processS1File as _processS1File
from S2_BuildDbpediaInfoFromTexts import  processS2File as _processS2File
from S3_UpdateTextsEntities import  processS3File as _processS3File

sys.path.append('../')
import px_aux
px_aux.FMES = True


spw_FOLDER = "/Users/agil/CloudStation/KORPUS/1926/files_s_p_w/"
corpusFolder = "/Users/agil/CloudStation/KORPUS/SCRAPPED_PAGES/en.wikipedia.org/"

_4Files = "/Users/agil/CloudStation/KORPUS/1926/1926.ph4.listWithWKSB"
with open(_4Files, 'r') as fp:
    list_4Files = fp.read().splitlines()

list_4FilesTXT = [url[1+url.rfind("/"):] for url in list_4Files]
list_4FilesFullTXT = [corpusFolder+f for f in list_4FilesTXT]
list_4FilesFullWK = [f+".wk" for f in list_4FilesFullTXT]
list_4FilesFullSB = [f+".sb" for f in list_4FilesFullTXT]

print("Tamaño 4 Files TXT = ", len(list_4FilesFullTXT))
print(list_4FilesFullTXT[0])
print("Tamaño 4 Files WK = ", len(list_4FilesFullWK))
print(list_4FilesFullWK[0])
print("Tamaño 4 Files SB = ", len(list_4FilesFullSB))
print(list_4FilesFullSB[0])


for f in list_4FilesFullTXT:
    fs = spw_FOLDER+f[1+f.rfind("/"):]+".s"
    fp = fs+".p"
    fw = fs+".w"

    try:
        if not os.path.exists(fs):
            raise Exception("No .s")

        fsize = os.path.getsize(fs)
        if fsize == 0:
            raise Exception(".s está vacío")
    except Exception as e:

        input("no hay .s?")
        print("Processing S1...")
        _processS1File(f)  # creates .s file



    try:
        if not os.path.exists(fp):
            raise Exception("No .p")

        fsize = os.path.getsize(fp)
        if fsize == 0:
            raise Exception(".p está vacío")
    except Exception as e:

        input("no hay .p?")
        print("Processing S2...")
        _processS2File(fs)  # creates .p file



    try:
        if not os.path.exists(fw):
            print("No hay", fw)
            raise Exception("No .w")

        fsize = os.path.getsize(fw)
        if fsize == 0:
            print("Vacio", fw)
            raise Exception(".w está vacío")
    except Exception as e:

        print("Processing S3...")
        result = _processS3File(fs)  # creates .w file
        if result == -1:
            print("ERROR")











# for f in list_4Files:
# 	if not os.path.exists(f):
# 		print(f, "no existe")
# 	else:
# 		fsize = os.path.getsize(f)
# 		if fsize == 0:
# 			print(f, "tiene tamaño 0")
# 		else:
# 			shutil.move(f, copiaFolder)



#
# list_of_txt_files = glob.glob(origFolder+"*.txt")
#
# print("Tamaño txt Files = ", len(list_of_txt_files))
#
# dif = list(set(listInitFiles) - set(list_of_txt_files))
#
# print("Tamaño dif Files = ", len(dif))

# for f in dif:
# 	print(f)


# for f in list_of_txt_files:
# 	shutil.move(f, copiaFolder)
