# Delta M algorithm.
## Python Script for Fiji

Description
============
This python script measures the quantification of the formation of spots around a certain pixel size (by default 2.07 pixels), returns a value for each time frame of the image stack.

Installation
============

1) Download the deltaM folder. ("Download or Clone" the project) 
2) Copy the deltaM folder to the plugins folder inside Fiji. You may need to relaunch Fiji.

Usage
============
1) Open the image stack. 
Some sample image stacks are provided in [my SharePoint account ](https://unican-my.sharepoint.com/:f:/g/personal/gomezperezai_unican_es/EpFrxdHEw2JFskqrGkSkF9QBvpLVRH3uTBam1OHlpC7iTQ?e=gCIfke)
2) Locate the script  at the bottom of Plugins menu. 
3) The maximum intensity projection of the image will be displayed, the measures will pop up in a plot. Values may be exported selecting the option "Save".

NOTE: Running it in Windows, will display a warning : "console: Failed to install '': java.nio.charset.UnsupportedCharsetException: cp0."
Know issue for Jython, adding -Dpython.console.encoding=UTF-8 as a VM argument to the run configuration for my program. For example: 
imageJ-win64.exe -Dpython.console.encoding=UTF-8
 
 Acknowledgment
 ==============
 This plugin runs in a modified version of the LoG3D plugin, that can be found in
[website of Daniel Sage](http://bigwww.epfl.ch/sage/soft/LoG3D/)
