import requests
import re
from bs4 import BeautifulSoup
import glob


class scrapFunctions():
	from aux import CORPUS_FOLDER as _CORPUS_FOLDER, URLs_FOLDER as _URLs_FOLDER, SCRAPPED_PAGES_FOLDER as _SCRAPPED_PAGES_FOLDER, SCRAPPED_TEXT_PAGES_FOLDER as _SCRAPPED_TEXT_PAGES_FOLDER, HTML_PAGES_FOLDER as _HTML_PAGES_FOLDER, saveFile as _saveFile

	# Scrap HTML pages
	def scrapPage(self, page):
		# Make the request
		try:
			request = requests.get(page)
		except:
			print("connection broken: " + page)
			return


		# Extract HTML from Response object and print
		html = request.text

		# Create a BeautifulSoup object from the HTML
		soup = BeautifulSoup(html, "html5lib")

		# Get the page title
		pageTitle = soup.title.string

		# Create a page name from the page title after removing special characters
		pageName = pageTitle.translate ({ord(c): "-" for c in "!@#$%^*()[]{};:,./<>?\|`=+"})

		# remove the footer div
		try:
			soup.find('div', id="footer").decompose()
		except Exception:
			print("not a wikipedia page")

		# remove the mw-navigation div
		try:
			soup.find('div', id="mw-navigation").decompose()
		except Exception:
			print("not a wikipedia page")

		# remove navigation links
		try:
			for link in soup.find_all("a", {'class': 'mw-jump-link'}):
				link.decompose()
		except Exception:
			print("not a wikipedia page")

		# remove navigation sections (Includes the head and the side panel)
		try:
			for link in soup.find_all("div", {'role': 'navigation'}):
				link.decompose()
		except Exception:
			print("no navigation sections found")

		# Other elements that can be removed:
		# Site notices: div with id = "siteNotice"
		# References


		# remove the css
		try:
			soup.style.decompose()
		except Exception:
			pass


		# remove all the js tags
		try:
			for tag in soup.find_all("script"):
				tag.decompose()
		except Exception:
			pass


		# Extract text from HTML
		text = soup.get_text()

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

		except Exception:
			pass

		return pageName, cleanedText


	# Takes a url and saves it to html file, and returns the html content
	def urlToHtml(self, url):
		# Make the request
		try:
			request = requests.get(url)
		except:
			print("connection broken: " + url)
			return


		# Extract HTML from Response object and print
		html = request.text

		# Create a BeautifulSoup object from the HTML
		soup = BeautifulSoup(html, "html5lib")

		# Get the page title
		pageTitle = soup.title.string

		# Create a page name from the page title after removing special characters
		pageName = pageTitle.translate ({ord(c): "-" for c in "!@#$%^*()[]{};:,./<>?\|`=+"})

		# Add file extension for saving pages
		fileName = pageName + ".html"

		# Save to html file
		_saveFile(_HTML_PAGES_FOLDER+"/"+fileName, html)

		return html


	# Takes a url and saves it to text file, and returns the page name and the cleaned text
	def urlToText(self, url):
		# Make the request
		try:
			request = requests.get(url)
		except:
			print("connection broken: " + url)
			return


		# Extract HTML from Response object and print
		html = request.text

		# Create a BeautifulSoup object from the HTML
		soup = BeautifulSoup(html, "html5lib")

		# Get the page title
		pageTitle = soup.title.string

		# Create a page name from the page title after removing special characters
		pageName = pageTitle.translate ({ord(c): "-" for c in "!@#$%^*()[]{};:,./<>?\|`=+"})

		# remove the footer div
		try:
			soup.find('div', id="footer").decompose()
		except Exception:
			print("not a wikipedia page")

		# remove the mw-navigation div
		try:
			soup.find('div', id="mw-navigation").decompose()
		except Exception:
			print("not a wikipedia page")

		# remove navigation links
		try:
			for link in soup.find_all("a", {'class': 'mw-jump-link'}):
				link.decompose()
		except Exception:
			print("not a wikipedia page")

		# remove navigation sections (Includes the head and the side panel)
		try:
			for link in soup.find_all("div", {'role': 'navigation'}):
				link.decompose()
		except Exception:
			print("no navigation sections found")

		# Other elements that can be removed:
		# Site notices: div with id = "siteNotice"
		# References


		# remove the css
		try:
			soup.style.decompose()
		except Exception:
			pass


		# remove all the js tags
		try:
			for tag in soup.find_all("script"):
				tag.decompose()
		except Exception:
			pass


		# Extract text from HTML
		text = soup.get_text()

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

		except Exception:
			pass


		# Add file extension for saving pages
		fileName = 	pageName + ".txt"

		# Save to html file
		_saveFile(_SCRAPPED_TEXT_PAGES_FOLDER+"/"+fileName, html)

		return pageName, cleanedText


	# Takes html and saves it to text file, and returns the page name and the cleaned text
	def htmlToText(self, html):
		# Create a BeautifulSoup object from the HTML
		soup = BeautifulSoup(html, "html5lib")

		# Get the page title
		pageTitle = soup.title.string

		# Create a page name from the page title after removing special characters
		pageName = pageTitle.translate ({ord(c): "-" for c in "!@#$%^*()[]{};:,./<>?\|`=+"})

		# remove the footer div
		try:
			soup.find('div', id="footer").decompose()
		except Exception:
			print("not a wikipedia page")

		# remove the mw-navigation div
		try:
			soup.find('div', id="mw-navigation").decompose()
		except Exception:
			print("not a wikipedia page")

		# remove navigation links
		try:
			for link in soup.find_all("a", {'class': 'mw-jump-link'}):
				link.decompose()
		except Exception:
			print("not a wikipedia page")

		# remove navigation sections (Includes the head and the side panel)
		try:
			for link in soup.find_all("div", {'role': 'navigation'}):
				link.decompose()
		except Exception:
			print("no navigation sections found")

		# Other elements that can be removed:
		# Site notices: div with id = "siteNotice"
		# References


		# remove the css
		try:
			soup.style.decompose()
		except Exception:
			pass


		# remove all the js tags
		try:
			for tag in soup.find_all("script"):
				tag.decompose()
		except Exception:
			pass


		# Extract text from HTML
		text = soup.get_text()

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

		except Exception:
			pass


		# Add file extension for saving pages
		fileName = 	pageName + ".txt"

		# Save to html file
		_saveFile(_SCRAPPED_TEXT_PAGES_FOLDER+"/"+fileName, html)

		return pageName, cleanedText


	# Takes a list of urls and saves them to html files
	def urlListToHtml(self, urlsList):
		for url in urlsList:

			# Retrieves the page title and the scraped page content
			try:
				pageName, pageContent = urlToHtml(url)

			except Exception as e:
				print("Error retrieving page: " + e)
				unretrieved_pages.append(page)
				continue


	# Takes a folder path i.e.: htmlFolder/, and scraps all pages
	def htmlFolderToText(self, folderPath):
		list_of_files = glob.glob(folderPath+"*.html")

		for html_file in list_of_files:
			file = open(html_file, "r")
			html = file.read()

			pageName, cleanedText = htmlToText(html)
