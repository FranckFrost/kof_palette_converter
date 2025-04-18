import numpy as np
from PIL import Image, ImageColor
from moviepy.editor import VideoFileClip
import os.path
#import argparse
import time
import sys
import glob
from gooey import Gooey, GooeyParser
	
def frames(file, start, out, fps): # if fps = 10 and video is 20 sec, you save 200 frames
	video = VideoFileClip(file)
	if len(out) == 0:
		out = file
	name, _ = os.path.splitext(out)
	start1 = time.perf_counter()
	
	if not os.path.isdir(name):
		os.mkdir(name)
	if fps == 0 or fps > video.fps: #can't save more frames than there are
		fps = video.fps
	step = 1/fps 
	
	f = len(glob.glob(f"{name}/*.png"))
	g = f
	for now in np.arange(start, video.duration, step):
		g+=1
		frame = os.path.join(name, f"frame#{g}.png")
		video.save_frame(frame, now)
		
	error = video.duration // step + 1 - (g - f)
	end1 = time.perf_counter()
	elapsed = end1 - start1
	print("\nSuccessfully extracted {} image file(s) from {} with {} error(s) in {:.3f}s\n\n".format(g-f, file, error, elapsed))
	return name

def remove_black(imageFileName):
  image = np.array(Image.open(imageFileName).convert("RGBA"))
  x = (image[...,:3] == np.array((0,0,0))).all(axis=-1)
  image[x,3] = 0
  result = Image.fromarray(image)
  return result

def processImageFile(inputFileName, outputFileName):
    start = time.perf_counter()
    transformedImage = remove_black(inputFileName)
    transformedImage.save(outputFileName)
    end = time.perf_counter()
    elapsed = end - start
    print("Wrote output image file \"{}\" (took {:.3f}s)".format(outputFileName, elapsed))
	
@Gooey(program_description="Changes true black into full transparency on every image provided.", default_size=(690, 600), optional_cols=1, tabbed_groups=True)
def main():
	cwd = os.path.abspath(os.getcwd())
	defaultOutputPath = "output"

	parser = GooeyParser()
	input_group = parser.add_argument_group(
		"Input",
		"Name each file if few. Otherwise, name folder(s) containing them.")
	input_group.add_argument("-fi","--inputFiles",
		nargs="*",
		help="Name(s)/path(s) of PNG image file(s) to process.",
		widget="MultiFileChooser")
	input_group.add_argument("-f", "--inputFolders",
		nargs="*",
		help="Name(s)/path(s) of the folder(s) containing the PNG image file(s) to process.",
		widget="DirChooser")
	input_group.add_argument("-v", "--video",
		action="store_true",
		help="The file(s) provided are video(s) from which to extract the images.")
	
	video_group = parser.add_argument_group(
		"Video Options",
		"Set the parameters for image extraction from the video(s).")
	video_group.add_argument("-s", "--start",
		type=float,
		default=0,
		help="Time in seconds at which to start extracting frames from the video(s). Defaults to 0.",
		widget="DecimalField",
		gooey_options={'max':1000})
	video_group.add_argument("-i", "--fps",
		type=float,
		default=0,
		help="Number of frames per second to save from the video. Defaults to every frame.",
		widget="DecimalField")
	video_group.add_argument("-vo", "--video_out",
		default="",
		help="Single name/path to store the frames extracted from the video(s).",
		widget="DirChooser")
		
	output_group = parser.add_argument_group(
		"Output",
		"Customize output options.")
	output_group.add_argument("-n", "--name",
		default="",
		help="Name string to attach to each output file.")
	output_group.add_argument("-o", "--out",
		dest="outputPath",
		default=os.path.join(cwd, defaultOutputPath),
		help="Path to store output images.",
		widget="DirChooser")
	output_group.add_argument("-e", "--extract_only",
		action="store_true",
		help="Only extract frames from video(s) and do nothing to them.")
	output_group.add_argument("-d", "--default",
		action="store_true",
		help="Set the current values as the new default configuration.")
	
	"""
	if len(sys.argv) < 2:
		parser.print_help()
	else:
	"""
	args = vars(parser.parse_args()) # convert parsed arguments into dict
	folders = args["inputFolders"]
	video = args["video"]
	video_out = args["video_out"]
	start = args["start"]
	fps = args["fps"]
	name = args["name"]
	imageFileNames = args["inputFiles"]
	outputPath = os.path.abspath(args["outputPath"])
	extract_only = args["extract_only"]
	default = args["default"]
	
	if not folders or not os.path.exists(os.path.abspath(folders[0])):
		folders=[]
		if not imageFileNames or any(".jpg" in name.lower() for name in imageFileNames):
			parser.print_help()
			sys.exit()

	start1 = time.perf_counter()
	if not os.path.exists(outputPath):
		os.makedirs(outputPath)
		print("Created output directory \"{}\"".format(outputPath))
	imagesProcessedCount, errorCount = 0, 0
	
	#if not any(".png" in name.lower() for name in imageFileNames): folder = True
	if imageFileNames and any(vid in name.lower() for vid in [".mp4",".avi",".mkv",".webm"] for name in imageFileNames): video = True
	
	if video:
		for vid in imageFileNames: # Takes a vid from input
			folder = frames(vid, start, video_out, fps)
			if not folder in folders:
				folders.append(folder) # Makes a folder out of each vid and keeps the paths
		if extract_only:
			sys.exit()

	if len(folders)!=0:
		imageFileNames = folders
		files=[]
		output=[]
		for f in imageFileNames:
			folder = os.path.abspath(f)
			files.append(glob.glob(os.path.join(folder, "*.png"))) #creates a list of all *.png filenames in folder and appends it to files
			out = os.path.abspath(os.path.join(outputPath, f))
			if out == f: #when given path outside code folder
				f = f.split("\\")[-1]
				out = os.path.abspath(os.path.join(outputPath, f)) #output path matching given folder
			if not os.path.exists(out):
				os.makedirs(out)
				print("Created output subdirectory \"{}\"".format(out))
			if not out in output:
				output.append(out) #only adds an output path if it's not already registered
		outputPath = output
		inputImagePaths = [map(os.path.abspath, i) for i in files]
		
		j = 0
		for inputFileList in inputImagePaths:
			for inputFileName in inputFileList:
				baseFileName = os.path.basename(inputFileName)
				outputFileName = os.path.abspath(os.path.join(outputPath[j], name+baseFileName)) #adds naming scheme to outputfiles
				print("")
				try:
					print("Processing image file \"{}\"...".format(inputFileName))
					processImageFile(inputFileName, outputFileName)
					imagesProcessedCount += 1
				except Exception as e:
					print("Error while processing image file \"{}\":".format(inputFileName))
					print(e)
					errorCount += 1
			j+=1
	else:
		inputImagePaths = map(os.path.abspath, imageFileNames)
		for inputFileName in inputImagePaths:
			baseFileName = os.path.basename(inputFileName)
			outputFileName = os.path.abspath(os.path.join(outputPath, name+baseFileName))
			print("")
			try:
				print("Processing image file \"{}\"...".format(inputFileName))
				processImageFile(inputFileName, outputFileName)
				imagesProcessedCount += 1
			except Exception as e:
				print("Error while processing image file \"{}\":".format(inputFileName))
				print(e)
				errorCount += 1

	end1 = time.perf_counter()
	elapsed = end1 - start1
	print("\nProcessed {} image file(s) with {} error(s) in {:.3f}s".format(imagesProcessedCount, errorCount, elapsed))

	if default == True:
		video_out = repr(video_out) #Convert quotes into double quotes so the address is written later with quotes + deal with escape characters
		name = repr(name)
		output = repr(args["outputPath"])
		data=[start, fps, video_out, name, output]
		j=0
		with open("Transparent.py","r") as e:
			new = e.read().splitlines(True) #Grab each line and keep the \n endline character
			e.close()
		for i in range(len(data)):
			while new[j].find("default=") == -1:
				j+=1
			l = new[j].split("default=")
			new_line = l[0] + "default=" + str(data[i]) + ',\n'
			if new[j-1].find('#') == -1 and new[j] != new_line:
				new[j] = '#' + new[j].replace("default=","default(base)=")
				j+=1
				new.insert(j, new_line)          
			else:
				new[j] = new_line
			j+=1
		with open("Transparent.py","w") as e:
			e.write(''.join(new))
			e.close()

if __name__ == "__main__":
    result = main()
    sys.exit(result)
