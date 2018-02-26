
from ij import ImagePlus,ImageStack,IJ
from ij.process import ImageStatistics as IS
from ij.process import FloatProcessor,ImageProcessor
import os, csv
import sys
import math
from array import zeros
from time import time
#from os import path,makedirs
from ij.gui import Roi, OvalRoi,Plot
import java.awt.Color as Color
from jarray import array
from ij.measure import ResultsTable,Measurements as M

from ij.plugin import ZProjector
from ij.plugin.frame import RoiManager
from ij.io import FileSaver  

from ij.plugin.filter import GaussianBlur,ThresholdToSelection
from operator import *
from sys import path as sys_path

#Default path to Fiji plugin directory,

LOG_folder=os.path.join(os.getcwd(),"plugins","deltamalgo","LOG3DCaso5")
IW_folder=os.path.join(LOG_folder,"imageware")

if LOG_folder not in sys_path:
	sys_path.append(LOG_folder)

import LOG3DCaso5
import imageware


endosomeCharacteristics=dict(
Gamma_media=2.1, #2.07
Gamma_stdv=0.4, #0.46
A_media=2.0 , #Amplitude 
A_stdv=0 #1.06 
)

SimulationCharacteristics=dict(
CentralZSlices=9
)

GaussianBlurParam=dict(
	accuracy=0.01,
	initialRadius=3
)


def frange(a,b,step):
  result = a
  for i in range(int((b-a)/step)+1):
      yield a+i*step


#Function that returns the mean, median, min, max, stdDev intensity of a given image.
def getStatistics(imp):  
  """ Return statistics for the given ImagePlus """  
  options = IS.MEAN | IS.MEDIAN | IS.MIN_MAX |IS.STD_DEV|IS.KURTOSIS|IS.SKEWNESS
  ip = imp.getProcessor()  
  stats = IS.getStatistics(ip, options, imp.getCalibration())  
  return stats.mean, stats.median, stats.min, stats.max, stats.stdDev,stats.kurtosis,stats.skewness

def SegmentMask(ip):
	'''
	Returns a Region of Interest (ROI) that contains a proposed segmentation for the input image processor imp 
	Binarization:	Find the GaussianBlur with minimum radius necessary to perform a Minimum Autothreshold
	'''
	minThresholdValue=-1
	radius=GaussianBlurParam['initialRadius'] #Initial Radius os the Gaussian Blur 
	contador=0
	while (minThresholdValue==-1 and contador<6):
		contador=contador+1
		#Make a copy of the image
		impThres = ImagePlus()
		ipThres = ip.duplicate()
		impThres.setProcessor("Copy for thresholding", ipThres)
		    
	
		GaussianBlur().blurGaussian( impThres.getProcessor(), radius, radius,GaussianBlurParam['accuracy'])
		#impThres.show()
		try:
			IJ.setAutoThreshold(impThres, "Minimum dark")
			minThresholdValue = impThres.getProcessor().getMinThreshold()
		except:
			print("No threshold found for segmentation")
	    	
	
		if minThresholdValue !=-1:
		
			#Check thresholded image contains at least 50% of the original
			stats = impThres.getStatistics()
			histogram = stats.histogram
			binSize=(stats.max-stats.min)/256
			ThresholdBin=int(round((minThresholdValue-stats.min)/binSize))
			CumulativeValues=0
			for i in range(ThresholdBin):
				CumulativeValues+=histogram[i]
			ImageAboveThreshold=1-float(CumulativeValues)/(ip.width*ip.height)
			#(ImageAboveThreshold)
			#ImageAboveThreshold must be above 50%
			if ImageAboveThreshold < 0.5:
				minThresholdValue=-1
				radius=radius+1
	
	impThres.getProcessor().setThreshold(minThresholdValue, stats.max, ImageProcessor.NO_LUT_UPDATE)
	boundRoi = ThresholdToSelection.run(impThres)
					
	return boundRoi

def GetSigmaWavelet(ip,RWavelet,boundRoi=None):
	'''Returns normalized sigma2,skew,kurtosis of a image after applying a wavelet of scale Rwavelet in a given roi'''

	#Create a copy of the image to filter
	fpInicial = ip.duplicate()
	impInitial = ImagePlus("ImagenInicial",fpInicial)
	
	#Filter image
	A=LOG3DCaso5(False)
	input = imageware.Builder.create(impInitial,3); #Float=3, Double=4
	Output=A.doLoG(input,RWavelet,RWavelet) 
	imp2=ImagePlus(" ", Output.buildImageStack())
	
	#invert the convolved image
	pixelsConv=imp2.getProcessor()
	pixelsConv=pixelsConv.getPixels()
		
	for i in xrange(len(pixelsConv)):
		pixelsConv[i]=(-1)*pixelsConv[i]

	#Measure the statistics
	fpConv=FloatProcessor(ip.width, ip.height, pixelsConv, None)
	imp3=ImagePlus("ImagenConvolucionada",fpConv)
	imp3.setRoi(boundRoi)
	measurements = M.MEAN|M.STD_DEV|M.KURTOSIS|M.SKEWNESS
	stats = imp3.getStatistics(measurements)
	NSkew=round(stats.skewness*stats.stdDev**3,7)
	return NSkew

	


def CheckMoment(image):
	
	#Perform a maximum projection on the stack	
	stack = image.getStack()
	NSlices=image.getNSlices()
	#Take a fixed number of central slices
	i=float(NSlices-SimulationCharacteristics['CentralZSlices']) 
	i1=math.floor(i/2)
	i2=math.ceil(i/2)	
	startSlice=int(1+i1)
	stopSlice=int(NSlices-i2)
	p=bool(1)
	proj = ZProjector()
	proj.setMethod(ZProjector.MAX_METHOD)
	proj.setImage(image)
	proj.setStartSlice(startSlice)
	proj.setStopSlice(stopSlice)
	proj.doHyperStackProjection(p)
	imageMax = proj.getProjection()
	imageMax.show()
	stack = imageMax.getStack()
	n_slices= stack.getSize()
	

	#Get a Segmentation Mask List for every frame in the stack
	RoiList=[]
	RoiRatioList=[]
	for index in range(1, n_slices+1):
		ip = stack.getProcessor(index).convertToFloat()
		boundRoi=SegmentMask(ip)
		mask=boundRoi.getMask()
		PixelsMask=mask.getPixels()
		r=(-1)*float(sum(PixelsMask))/(ip.height*ip.width)
		RoiList.append(boundRoi)
		RoiRatioList.append(r)
#	print(RoiRatioList)		

	#Optimize the Roi List. No 1.0 ratios 
	AllRois1=all(item == 1.0 for  item in RoiRatioList)
	NFrames=len(RoiRatioList)
	if not AllRois1:
		for i in range(NFrames):
			if RoiRatioList[i]==1.0 or RoiList[i]==None:
				#Find the next value that is not 1.0
				NearestNot1=-1 
				prevIndex=i-1
				nextIndex=i+1
				Token=True #To run through the list alternating positions
				while prevIndex>=0 or nextIndex<NFrames:
					if prevIndex>0 and Token:
						if RoiRatioList[prevIndex]<0.9999:
							NearestNot1=prevIndex
							break
						else: 
							prevIndex-=1
							if nextIndex<NFrames:Token=False
							continue
					if nextIndex<NFrames:
					  
						if RoiRatioList[nextIndex]<0.9999:
							NearestNot1=nextIndex
							break
						else:
							nextIndex+=1
							if prevIndex>0: Token=True
							continue
				
				if NearestNot1!=-1:
					#Change RoiList and RoiRationList for the NearestNot1 element
					RoiList[i]=RoiList[NearestNot1]
					RoiRatioList[i]=RoiRatioList[NearestNot1]
				else:
					AllRois1=True
					print("No avaliable segmentation")
	
	if not AllRois1:
		RoiListMin=ModifyRoiList(RoiRatioList,RoiList)
	else:
		RoiListMin=[ None for i in range(len(RoiList))]
	

	#Find Optimum Scale for the Wavelet
	Gamma=endosomeCharacteristics['Gamma_media']
	To=endosomeCharacteristics['A_media']
	index=1 #Image 1
	ipOrig = stack.getProcessor(index).convertToFloat()	
	boundRoi=RoiListMin[0]
	MaxAmp,Ropt=AmplificationCurveMax(ipOrig,To,Gamma,boundRoi)
	print("Choosen Scale",Ropt)
		
	Moment3Array=[]
	for index in range(1,n_slices+1):
		print("time:"+str(index))
		ip = stack.getProcessor(index).convertToFloat()
		boundRoi=RoiListMin[index-1]
		Skew=GetSigmaWavelet(ip,Ropt,boundRoi)
  		Moment3Array.append(Skew)
		

	return Moment3Array	

def ModifyRoiList(RoiRatioList,RoiList):
	'''Input: RoiRatioList, List with ratios of the roi contained in Roilist
	Returns: RoiListMin, List with minimum ratios'''
	
	RoiRatSort=sorted(RoiRatioList)	
	RoiListMin = list(RoiList)
	tam_list=len(RoiRatSort)

	
	if RoiRatSort[-1]-RoiRatSort[0]>0.05: #The diference is over 5%	
		i=0
		while True:
			if RoiRatSort[i]-RoiRatSort[0]>0.05:
				break
			i=i+1
		IndexCloseToMin=i-1
		if IndexCloseToMin<0:
			IndexCloseToMin=0
		
		ThresMinIndex=RoiRatioList.index(RoiRatSort[IndexCloseToMin])

		for j in range(len(RoiRatioList)):
			if RoiRatioList[j]>RoiRatioList[ThresMinIndex]:
				RoiListMin[j]=RoiListMin[ThresMinIndex]
				RoiRatioList[j]=RoiRatioList[ThresMinIndex]
		
		#print(RoiRatioList)
		
	return RoiListMin
	
def AmplificationCurveMax(ip,To,Gamma,boundRoi=None):

	MaxAmplificacion=0
	ROptima=2.0
	ValuePrev=0
	RepCounter=0
	
	#Create a copy of the image to filter
	fpInicial = ip.duplicate()
	impInitial = ImagePlus("ImagenInicial",fpInicial)
	if boundRoi!=None:
		impInitial.setRoi(boundRoi)
		
	stats=impInitial.getStatistics()
	imageOriginalStdDev=stats.stdDev

	for LogFilterSigma in frange(1,9,0.05):
	#Run the mexican hat wavelet over the background
		A=LOG3DCaso5(False)
		input = imageware.Builder.create(impInitial,3); #Float=3, Double=4
		Output=A.doLoG(input,LogFilterSigma,LogFilterSigma)
		impConvolucionada=ImagePlus("ImagenConvolucionada", Output.buildImageStack())
		impConvolucionada.setRoi(boundRoi)
		roiConvolucionadaStats=impConvolucionada.getStatistics()
		imageConvolucionadaStdDev=roiConvolucionadaStats.stdDev
	
		# Theoretical Wn/Wo
		K=2/(pow(Gamma,2)*pow((1+pow((LogFilterSigma/Gamma),2)),2))

		amplificacion=K*imageOriginalStdDev/imageConvolucionadaStdDev

		#Store the maximum values
		#print(LogFilterSigma,amplificacion)
		if (amplificacion > MaxAmplificacion) :
			MaxAmplificacion=amplificacion
			ROptima=LogFilterSigma
		if amplificacion <=ValuePrev :
			RepCounter+=1	
		else:
			RepCounter=0
		ValuePrev=amplificacion
		#Break if the value decreases for 3 consecutive values
		if(RepCounter==3):
			break

	return MaxAmplificacion,ROptima


#Main Method


image = IJ.getImage()
Moment3=CheckMoment(image)
Mom3Norm=[i/Moment3[0]-1.0 for i in Moment3]

NFrames= image.getNFrames()
xArr = array(range(1,NFrames+1), 'd')
plot = Plot("Title", "Time", "Delta m ",xArr,Mom3Norm)
plot.setLimits(1, NFrames, min(Mom3Norm), max(Mom3Norm))
plot.setColor(Color.BLUE)
plot.addPoints(xArr,Mom3Norm,Plot.CROSS)
plot.show()

