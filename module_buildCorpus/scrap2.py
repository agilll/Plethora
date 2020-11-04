import requests
from requests.exceptions import Timeout
import re
from bs4 import BeautifulSoup
import glob
from smart_open import open as _Open

FOLDER ="/Users/agil/CloudStation/KORPUS/SCRAPPED_PAGES/en.wikipedia.org"



# to save some ASCII content in a file
def saveFile (f, content):
	out = _Open(f, 'w')
	out.write(content)
	out.close()
	return



# Download HTML pages
def downloadPage(self, page):
	# Make the request
	try:
		request = requests.get(page, timeout=10)
	except Timeout as e:
		print("*** Request Exception (Timeout): ", page)
		raise Exception("Timeout")
	except Exception as e:
		print("*** Request Exception ("+str(e)+"): " + page)
		raise Exception("Unknown")

	# Extract HTML from Response object and print
	try:
		html = request.text
	except Exception as e:
		print("*** HTML Exception ("+str(e)+"): " + page)
		raise Exception("Unknown")

	return html


# Scrap HTML pages
def extractTextFromHTML(self, page):

	try:
		html = self.downloadPage(page)
	except Exception as e:
		print("*** extractTextFromHTML Exception: "+str(e))
		raise Exception(str(e))

	cleanedText = ""

	# Create a BeautifulSoup object from the HTML
	try:
		soup = BeautifulSoup(html, "html5lib")
	except Exception as e:
		print("*** extractTextFromHTML Exception: "+str(e))
		raise Exception(str(e))


	# Scrap plain text from paragraphs
	try:
		# Extract all paragraphs
		for p in soup.find_all("p"):
			# Clean paragraphs
			plainParagraph = p.get_text()

			# Remove references from text
			plainParagraph = re.sub("([\[]).*?([\]])", "", plainParagraph)
			# print(plainParagraph)

			# Append cleaned paragraph to cleanedText
			# Separate paragraphs by break lines
			cleanedText += plainParagraph + "\n"

	except Exception as e:
		print("*** extractTextFromHTML (extracting p): "+str(e))
		raise Exception(str(e))

	return cleanedText





# Scrap HTML pages
def scrapPage(self, page):
	# Make the request
	try:
		request = requests.get(page, timeout=10)
	except Timeout as e:
		print("*** Timeout ***", page)
		raise Exception("Timeout")
	except:
		print("scrapPage: Connection broken: " + page)
		return ""


	# Extract HTML from Response object and print
	try:
		html = request.text
	except Exception as e:
		print("scrapPage (text): " + str(e))
		return ""

	# Create a BeautifulSoup object from the HTML
	try:
		soup = BeautifulSoup(html, "html5lib")
	except Exception as e:
		print("scrapPage (BeautifulSoup): " + str(e))
		return ""

	try:
		# Get the page title
		pageTitle = soup.title.string
		# Create a page name from the page title after removing special characters
		pageName = pageTitle.translate ({ord(c): "-" for c in "!@#$%^*()[]{};:,./<>?\|`=+"})
	except Exception as e:
		print("scrapPage (title.string): " + str(e))


	# remove the footer div
	try:
		soup.find('footer', id="footer").decompose()
	except Exception as e:
		print("scrapPage (footer): "+str(e))

	# remove the mw-navigation div
	try:
		soup.find('div', id="mw-navigation").decompose()
	except Exception as e:
		print("scrapPage (div mw-navigation): "+str(e))

	# remove navigation links
	try:
		for link in soup.find_all("a", {'class': 'mw-jump-link'}):
			link.decompose()
	except Exception as e:
		print("scrapPage (a): "+str(e))

	# remove navigation sections (Includes the head and the side panel)
	try:
		for link in soup.find_all("div", {'role': 'navigation'}):
			link.decompose()
	except Exception as e:
		print("scrapPage (no navigation sections found): "+str(e))

	# Other elements that can be removed:
	# Site notices: div with id = "siteNotice"
	# References


	# remove the css
	try:
		soup.style.decompose()
	except Exception as e:
		print("scrapPage (no style): "+str(e))


	# remove all the js tags
	try:
		for tag in soup.find_all("script"):
			tag.decompose()
	except Exception as e:
		print("scrapPage (no script): "+str(e))


	# Extract text from HTML
	try:
		text = soup.get_text()
	except Exception as e:
		print("scrapPage (get_text): "+str(e))
		return ""

	# Since we don't need the whole page components, it would be better to extract..
	# ..the text only from paragraphs. This works for wikipedia pages.
	# Scrapping the whole page now is not necessary, but I left it just in case needed later

	# To save all paragraphs
	cleanedText = ""


	# Scrap plain text from paragraphs
	try:
		# Extract all paragraphs
		for p in soup.find_all("p"):
			# Clean paragraphs
			plainParagraph = p.get_text()

			# Remove references from text
			plainParagraph = re.sub("([\[]).*?([\]])", "", plainParagraph)
			# print(plainParagraph)

			# Append cleaned paragraph to cleanedText
			# Separate paragraphs by break lines
			cleanedText += plainParagraph + "\n"

	except Exception as e:
		print("scrapPage (extracting p): "+str(e))

	return cleanedText




# Takes a folder path i.e.: htmlFolder/, and scraps all pages
def htmlFolderToText(self, folderPath):
	list_of_files = glob.glob(folderPath+"*.html")

	for html_file in list_of_files:
		file = _Open(html_file, "r")
		html = file.read()

		pageName, cleanedText = htmlToText(html)
