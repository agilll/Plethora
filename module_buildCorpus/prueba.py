
import nltk
import re

nltk_stopwords = nltk.corpus.stopwords.words('english')

def isNotStopWord (word):
		if word not in nltk_stopwords:
			return True
		return False

	
def wikicatComponents (wikicat):
	lista =[]
	word=""
	
	long = len(wikicat)
	idx = 0
	
	while idx < long:
		l = wikicat[idx]
		idx += 1
		
		if len(word) == 0:
			word = word + str(l)
			continue
		
		if str(l).isdigit():
			if not str(wikicat[idx-2]).isdigit():
				lista.append(word)
				word = str(l)
			else:
				word = word + str(l)
			continue
				
		if l.isupper():
			if wikicat[idx-2] == '-':
				word = word + str(l)
			else:
				if word.isupper():
					if wikicat[idx].islower():
						lista.append(word)
						word = str(l)
					else:
						word = word + str(l)
				else:
					if (l == 'B') and (wikicat[idx] == 'C'):
						word = word + "BC"
						idx += 1
					else:
						if (l == 'A') and (wikicat[idx] == 'D'):
							word = word + "AD"
							idx += 1;
						else:
							lista.append(word)
							word = str(l)

		else:
			word = word + str(l)
	
		
	if len(word) > 0:
		lista.append(word)
	
	return lista

print(wikicatComponents("NavalBattlesOfAncientGreece"))
print(wikicatComponents("5th-centuryBCGreekPeople"))
print(wikicatComponents("PeopleOfTheGreco-PersianWars"))
print(wikicatComponents("Greco-PersianWars"))
print(wikicatComponents("MunicipalitiesOfPeloponnese(region)"))
print(wikicatComponents("1965ShortStoryCollections"))
print(wikicatComponents("StatesAndTerritoriesEstablishedIn508BC"))