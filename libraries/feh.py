# -*- coding: utf-8 -*-

import pickle
import os

fileName = "./feh.data"

class User:

	def __init__(self, pseudo):
		self.pseudo = str(pseudo)
		self.names = []
		self.values = []

	def add(self, name, value):
		self.names.append(name)
		self.values.append(value)

	def remove(self, name):
		i = 0
		key = None
		for val in self.names:
			name = name.lower()
			val = val.lower()
			if val == name:
				key = i
		i += 1

		if key != None:
			del self.names[key]
			del self.values[key]
		else:
			raise KeyError("Entrée introuvable")

def dataUpdate(data, objet, id):
	dt = {str(id):objet}
	data.update(dt)

def dataRemove(data, id):
	try:
		del data[str(id)]
	except KeyError:
		raise KeyError("User data not found")

def getFromData(data, id):
	try:
		get = data[str(id)]
		return get
	except KeyError:
		raise KeyError("User data not found")

def dataSave(data):
	f = open(fileName, "wb")
	p = pickle.Pickler(f)
	p.dump(data)
	f.close()

def dataGet():
	if os.path.exists(fileName):
		f = open(fileName, "rb")
		d = pickle.Unpickler(f)
		data = d.load()
		f.close()
	else:
		data = {}

	return data