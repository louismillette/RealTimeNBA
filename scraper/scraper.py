from bs4 import BeautifulSoup
from bs4 import NavigableString
import json
import requests
import re
import sys
import os
import pymongo


# Base class for all teams
class Scrape():
	# set up local sqlite3 DB for textbook data dump
	def setUpDBLocal(self):
		conn = sqlite3.connect("{}/books/{}_texts.db".format(self.localDBdirr, self.school))
		c = conn.cursor()
		try:
			c.execute(
				'CREATE TABLE t' + self.db_name + ' (class text, number text, notice text, books text, classPostsNA text, classPostsBuy text, classPostsSell text, classEnrolment text)')
		except:
			print(
				"term data already exists, running this will add aditional data to the table, possibly causeing repeats.")
		conn.commit()
		return conn

	# goes through search links, scrape texts, put them in the DB
	def storeBooks(self, getLinks, getBooks, updateDB):
		links = getLinks(self.pageOne)
		for link in links:
			page = self.session.get(link)
			books = getBooks(page.text)
			updateDB(books)

	# scrape books from first page, put them in the DB
	def storeFirstPage(self, getBooks, updateDB, pageOne):
		books = getBooks(pageOne)
		updateDB(books)


# scrape the play-by-play page for given URL; put it in mongo DB
class PlayByPlay():
	def __init__(self, term, db_name=None):
		# self.db_name = term if not db_name else db_name
		# self.url = "https://fortuna.uwaterloo.ca/cgi-bin/cgiwrap/rsic/book/index.html"
		# self.term = term
		# # self.localDBdirr = os.getcwd() + "/books/"
		# self.localDBdirr = os.path.dirname(os.path.realpath(__file__))
		# self.school = 'Waterloo'
		# self.session = requests.Session()
		# self.connection = self.setUpDBLocal()
		# # Page one is HTML text, not BS4'd yet
		# self.pageOne = self.getFirstPage() # inside getFirstPage we initiate self.session
		# self.getLinks(self.pageOne)
		# Scrape.storeFirstPage(self, getBooks= self.getBooks, updateDB=self.insert, pageOne=self.pageOne)
		# Scrape.storeBooks(self,getLinks=self.getLinks,getBooks=self.getBooks,updateDB=self.insert)
		pass

		# for the purpose of testing the module, loads in HTML page

	def load_test_html(self):
		dirr = os.path.dirname(os.path.abspath(__file__))
		with open(os.path.join(dirr, 'test.html'), 'r')as file:
			html = ''.join(file.readlines())
			return html

	# pull the rows we care about out of the web page
	def extract_rows(self,html):
		soup = BeautifulSoup(html, "html.parser")
		table = soup.find('table',attrs={'id':'pbp'})
		rows = table.find_all('tr')
		# split by quarter
		q2_s = [ele.text.replace('\n','') for ele in rows].index('2nd Q')
		q3_s = [ele.text.replace('\n','') for ele in rows].index('3rd Q')
		q4_s = [ele.text.replace('\n','') for ele in rows].index('4th Q')
		q1 = rows[2:q2_s]
		q2 = rows[q2_s+2:q3_s]
		q3 = rows[q3_s+2: q4_s]
		q4 = rows[q4_s+2:]
		## TODO fix for OT games (up to 6)
		print(q1[5])
		lens = []
		return q1,q2,q3,q4,None,None,None,None,None,None # 4 regulated, 6 potential OT

	# take individual row and return dictionary
	def parse_play(self, row, awayteam, hometeam, gameid, quarter):
		tds = row.find_all('td')
		if len(tds) == 2:
			timestamp = tds[0].text
			team = awayteam
			score = None
			d = self.parse_text(text=tds[1])
		else: # MUST equal 6
			timestamp = tds[0].text
			if tds[1].text != ' ':
				d = self.parse_text(text=tds[1], scored=tds[2])
				team = awayteam
			elif tds[5].text != ' ':
				d= self.parse_text(text=tds[5], scored=tds[4])
				team = hometeam
			else:
				raise Exception('Row has no play')
			score = tds[3].text
		d['team'] = team
		d['time'] = timestamp
		d['gameid'] = gameid
		d['quarter'] = quarter
		d['score'] = score
		return d

	# go through text (td element), determine what happened.  Return dict
	def parse_text(self,text,scored = None):
		if scored and (not scored.text == ' '): # short circuit if no scored provided
			pointchange = int(scored.text.replace('+', ''))
		else:
			pointchange = 0

		(twoPoint, threePoint, feet, assist, block, turnover, offRebound, defRebound, primaryPlayer,
		 secondaryPlayer, action, offoul, freeThrow, foul) = tuple([None] * 14)
		text = text.text.replace('\n', ' ')
		# print(text)
		if "2-pt shot" in text:
			action = 'twoPoint'
			if "misses" in text:
				twoPoint = False
				assist = False
				primaryPlayer = text.split('misses 2-pt shot from')[0].replace(' ','')
				if " ft " in text:
					feet = int(text.split('misses 2-pt shot from')[1].split('ft')[0].replace(' ',''))
				else:
					feet = 0 # this shot was at the rim
				if "block by" in text:
					block = True
					secondaryPlayer = text.split('block by ')[1].replace(' ','').replace(')', '')
				else:
					block = False
			elif "makes" in text:
				twoPoint = True
				block = False
				primaryPlayer = text.split('makes 2-pt shot from')[0].replace(' ','')
				if " ft " in text:
					feet = int(text.split('makes 2-pt shot from')[1].split('ft')[0].replace(' ',''))
				else:
					feet = 0 # this shot was at the rim
				if "assist by" in text:
					assist = True
					secondaryPlayer = text.split('assist by ')[1].replace(' ','').replace(')', '')
				else:
					assist = False
		elif "3-pt shot" in text:
			action = "threePoint"
			if "misses" in text:
				threePoint = False
				assist = False
				primaryPlayer = text.split('misses 3-pt shot from')[0].replace(' ','')
				if " ft " in text:
					feet = int(text.split('misses 3-pt shot from')[1].split('ft')[0].replace(' ',''))
				else:
					feet = 0 # this shot was at the rim
				if "block by" in text:
					block = True
					secondaryPlayer = text.split('block by ')[1].replace(' ','').replace(')', '')
				else:
					block = False
			elif "makes" in text:
				threePoint = True
				block = False
				primaryPlayer = text.split('makes 3-pt shot from')[0].replace(' ','')
				if " ft " in text:
					feet = int(text.split('makes 3-pt shot from')[1].split('ft')[0].replace(' ',''))
				else:
					feet = 0 # this shot was at the rim
				if "assist by" in text:
					assist = True
					secondaryPlayer = text.split('assist by ')[1].replace(' ','').replace(')', '')
				else:
					assist = False
		elif "free throw" in text:
			if "misses" in text:
				freeThrow = False
				primaryPlayer = text.split(' misses free throw')[0].replace(' ','')
			elif "makes" in text:
				freeThrow = True
				primaryPlayer = text.split(' misses free throw')[0].replace(' ','')
		elif "Defensive rebound by" in text:
			defRebound = True
			primaryPlayer = text.split('Defensive rebound by ')[1].replace(' ','')
			action = 'defRebound'
		elif "Offensive rebound by" in text:
			offRebound = True
			primaryPlayer = text.split('Offensive rebound by ')[1].replace(' ','')
			action = 'offRebound'
		elif "Turnover by" in text:
			action = turnover
			PrimaryPlayer = text.split('Turnover by')[1].split('(')[0].replace(' ', '')
			if "offensive foul" in text:
				offoul = True
			else:
				offoun = False
		elif "Personal foul" in text:
			action = "pfoul"
			primaryPlayer = text.split("Personal foul by ")[1].split('(')[0].replace(' ','')
			secondaryPlayer = text.split("Personal foul by ")[1].split('(drawn by')[1].replace(' ','').replace(')','')
		elif "foul" in text:
			action = "foul"
			foul = text.split('foul')[0] # which foul spacifically?
			primaryPlayer = text.split('by')[1].split('(')[0].replace(' ','')
			secondaryPlayer = text.split('drawn by ')[1].replace(')','').replace(' ','')
		elif "timeout" in text:
			action = "timeout"
		elif " enters the game for " in text:
			action = "swap"
			primaryPlayer,secondaryPlayer = tuple(text.split(' enters the game for '))
		elif 'Jump ball' in text:
			primaryPlayer = text.split('(')[1].split(' gains possession)')[0]
			action = 'jump'
		elif 'quarter' in text:
			action = 'quarter'
		else:
			print(text)
			raise Exception('Play unidentified')
		return dict(
			list(zip(
				('twoPoint', 'threePoint', 'feet', 'assist', 'block', 'turnover', 'offRebound', 'defRebound', 'primaryPlayer',
				 'secondaryPlayer', 'action', 'offoul', 'freeThrow', 'foul', 'pointchange'),
				(twoPoint, threePoint, feet, assist, block, turnover, offRebound, defRebound, primaryPlayer,
				 secondaryPlayer, action, offoul, freeThrow, foul, pointchange)
			))
		)




if (__name__ == '__main__'):
	P = PlayByPlay(term=None)
	html = P.load_test_html()
	q1,q2,q3,q4,ot1,ot2,ot3,ot4,ot5,ot6 = P.extract_rows(html)
	rows = [P.parse_play(ele,'Boston','Chicago','idblah',1) for ele in q1]
	print(rows)