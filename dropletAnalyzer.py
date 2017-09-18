import Tkinter as tk
import time
import numpy as np
import argparse
import cv2
import os
from matplotlib import pyplot as plt
import seaborn as sns

DATA_FOLDER = 'experiments/'
REFERENCE_FILE = 'reference.tif'
RFP_REF = 'reference_TxR.tif'
GFP_REF = 'reference_FITC.tif'

class Application(tk.Frame):
	def __init__(self, master=None):
		tk.Frame.__init__(self, master)
		self.grid()
		self.createWidgets()

	def createWidgets(self):
		self.statusText = tk.StringVar()
		self.statusText.set('Ready!')
		self.statusLabel = tk.Label(self, textvariable=self.statusText)
		self.statusLabel.grid(row=0, column=0, columnspan=2)

		self.fileLabel = tk.Label(self, text='experiments/')
		self.fileLabel.grid(row=1, column=0)
		self.fileEntry = tk.Entry(self)
		self.fileEntry.grid(row=1, column=1)

		self.sizeLabel = tk.Label(self, text='Droplet Diameter (px)')
		self.sizeLabel.grid(row=2, column=0)
		self.sizeSlider = tk.Scale(self, from_=5, to=100, orient=tk.HORIZONTAL, length = 150)
		self.sizeSlider.grid(row=2, column=1)

		self.treshLabel = tk.Label(self, text='Threshold')
		self.treshLabel.grid(row=3, column=0)
		self.treshSlider = tk.Scale(self, from_=1, to=100, orient=tk.HORIZONTAL, length = 150)
		self.treshSlider.grid(row=3, column=1)

		self.gfpLabel = tk.Label(self, text='GFP Signal')
		self.gfpLabel.grid(row=4, column=0)
		self.gfpSlider = tk.Scale(self, from_=1, to=10, orient=tk.HORIZONTAL, length = 150)
		self.gfpSlider.grid(row=4, column=1)

		self.rfpLabel = tk.Label(self, text='RFP Signal')
		self.rfpLabel.grid(row=5, column=0)
		self.rfpSlider = tk.Scale(self, from_=1, to=10, orient=tk.HORIZONTAL, length = 150)
		self.rfpSlider.grid(row=5, column=1)

		self.applyButton = tk.Button(self, text='Apply', command=self.apply)
		self.applyButton.grid(row=6, column=0)

		self.submitButton = tk.Button(self, text='Submit', command=self.submit)
		self.submitButton.grid(row=6, column=1)

	def submit(self):
		directory = DATA_FOLDER + self.fileEntry.get()

		for folder in os.walk(directory):
			print folder[0]
			if len(folder[1]) == 0:
				tifs = [os.path.join(folder[0], f) for f in folder[2] if f.split('.')[-1] == 'tif']
				fileHeaders = set(['_'.join(f.split('_')[:-1]) for f in tifs])
				
				accumulated_droplets = []

				print fileHeaders

				triples = []
				for header in fileHeaders:
					if header+'_FITC.tif' in tifs and header+'_BF.tif' in tifs and header+'_TxR.tif' in tifs:
						triples.append(header)

				for triple in triples:
					circles = self.getCircles(triple+'_BF.tif', triple+'_FITC.tif', triple+'_TxR.tif')
					lvs = self.quantifyFluor(circles, triple+'_FITC.tif', triple+'_TxR.tif')
					accumulated_droplets.extend(lvs)

				plt.scatter([p[0] for p in accumulated_droplets], [p[1] for p in accumulated_droplets], s=70, alpha= 0.1)
				plt.title(folder[0])
				plt.xlabel('GFP Signal')
				plt.ylabel('RFP Signal')
				plt.xlim([0,400])
				plt.ylim([0,400])
				plt.savefig(folder[0]+'.png')
				plt.clf()

	def quantifyFluor(self, circles, gfp_filepath, rfp_filepath):
		gfp = cv2.imread(gfp_filepath)
		height, width, channels = gfp.shape
		while height > 700 and width > 700:
			height = height/2
			width = width/2
		gfp = cv2.resize(gfp, dsize = (width, height))
		rfp = cv2.imread(rfp_filepath)
		rfp = cv2.resize(rfp, dsize = (width, height))
		# fluors = (self.gfpSlider.get()*gfp) + (self.rfpSlider.get()*rfp)

		#x's then y's

		gray_gfp = cv2.cvtColor(gfp, cv2.COLOR_BGR2GRAY)
		gray_rfp = cv2.cvtColor(rfp, cv2.COLOR_BGR2GRAY)

		#gfp, rfp
		levels = []
		if circles is not None:
			circles = np.round(circles).astype("int")
			for (x, y, r) in circles:
				R, G = [], []
				for xx in range(x-r, x+r):
					for yy in range(y-r, y+r):
						if xx>-1 and yy>-1 and xx<width and yy<height:
							if self.distance((xx,yy), (x,y)) < r:
								R.append(gray_rfp[yy][xx].astype(float) * gray_rfp[yy][xx])
								G.append(gray_gfp[yy][xx].astype(float) * gray_gfp[yy][xx])
				# levels.append((np.percentile(G, 90), np.percentile(R, 90)))
				levels.append([np.mean(G), np.mean(R)])
		return levels

	def distance(self, pt1, pt2):
		return np.sqrt((pt1[0]-pt2[0])^2 + (pt1[1]-pt2[1])^2)


	def getCircles(self, image_filepath, gfp_filepath, rfp_filepath):
		# load the image, clone it for output, and then convert it to grayscale
		image = cv2.imread(image_filepath)

		height, width, channels = image.shape
		while height > 600 and width > 600:
			height = height/2
			width = width/2
		image = cv2.resize(image, dsize = (width, height))
		output = image.copy()
		gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
		# detect circles in the image
		diameter_val = self.sizeSlider.get()
		treshold_val = self.treshSlider.get()
		self.statusText.set('Running...')
		circles = cv2.HoughCircles(gray, cv2.HOUGH_GRADIENT, dp=1.2, minDist=max(1,2*int(0.9*(diameter_val/2))), minRadius=int(0.9*(diameter_val/2)), maxRadius=int(1.1*(diameter_val/2)), param2=treshold_val)
		# ensure at least some circles were found
		if circles is not None:
			self.statusText.set(str(len(circles[0])) + ' droplets')
			# convert the (x, y) coordinates and radius of the circles to integers
			circles = np.round(circles[0, :]).astype("int")
			# loop over the (x, y) coordinates and radius of the circles
			for (x, y, r) in circles:
				cv2.circle(output, (x, y), r, (91, 244, 255), 1)
			cv2.line(output, (10,10), (10+diameter_val, 10), (83, 232, 108), 2)
			# show the output image

			rfp = cv2.imread(rfp_filepath)
			rfp = cv2.resize(rfp, dsize = (width, height))

			gfp = cv2.imread(gfp_filepath)
			gfp = cv2.resize(gfp, dsize = (width, height))

			fluors = (self.gfpSlider.get()*gfp) + (self.rfpSlider.get()*rfp)

			for (x, y, r) in circles:
				cv2.circle(fluors, (x, y), r, (91, 244, 255), 1)
			cv2.line(fluors, (10,10), (10+diameter_val, 10), (83, 232, 108), 2)

			cv2.imshow("Viewer", np.hstack([output, fluors]))
			cv2.waitKey(500)
			return circles
		else:
			self.statusText.set('0 droplets')




	def apply(self):
		root_directory = self.fileEntry.get()

		# load the image, clone it for output, and then convert it to grayscale
		image = cv2.imread(DATA_FOLDER+root_directory+'/'+REFERENCE_FILE)

		height, width, channels = image.shape
		while height > 600 and width > 600:
			height = height/2
			width = width/2
		image = cv2.resize(image, dsize = (width, height))
		output = image.copy()
		gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

		# detect circles in the image
		diameter_val = self.sizeSlider.get()
		treshold_val = self.treshSlider.get()
		self.statusText.set('Running...')
		circles = cv2.HoughCircles(gray, cv2.HOUGH_GRADIENT, dp=1.2, minDist=max(1,2*int(0.9*(diameter_val/2))), minRadius=int(0.9*(diameter_val/2)), maxRadius=int(1.1*(diameter_val/2)), param2=treshold_val)
		# ensure at least some circles were found
		if circles is not None:
			self.statusText.set(str(len(circles[0])) + ' droplets')
			# convert the (x, y) coordinates and radius of the circles to integers
			circles = np.round(circles[0, :]).astype("int")
			# loop over the (x, y) coordinates and radius of the circles
			for (x, y, r) in circles:
				cv2.circle(output, (x, y), r, (91, 244, 255), 1)
			cv2.line(output, (10,10), (10+diameter_val, 10), (83, 232, 108), 2)
			# show the output image

			rfp = cv2.imread(DATA_FOLDER+root_directory+'/'+RFP_REF)
			if len(rfp) < 1:
				print 'Invalid RFP reference'
			rfp = cv2.resize(rfp, dsize = (width, height))

			gfp = cv2.imread(DATA_FOLDER+root_directory+'/'+GFP_REF)
			if len(gfp) < 1:
				print 'Invalid GFP reference'
			gfp = cv2.resize(gfp, dsize = (width, height))

			fluors = (self.gfpSlider.get()*gfp) + (self.rfpSlider.get()*rfp)


			for (x, y, r) in circles:
				cv2.circle(fluors, (x, y), r, (91, 244, 255), 1)
			cv2.line(fluors, (10,10), (10+diameter_val, 10), (83, 232, 108), 2)

			cv2.imshow("Viewer", np.hstack([output, fluors]))
			cv2.waitKey(100)
		else:
			self.statusText.set('0 droplets')



app = Application()
app.master.title('Droplet Analyzer')
app.mainloop()

