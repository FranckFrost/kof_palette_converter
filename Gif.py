import numpy as np
from PIL import Image
import os.path
#import argparse
import time
import sys
import glob
import re
from gooey import Gooey, GooeyParser

def number(x):
	return float(re.findall("(\d+)",x)[-1])

def gif(files, start, pause, restart, end, gap, crop, output):
	files = files[start-1:pause] + files[restart-1:end] #indexation
	frames = [Image.open(image) for image in files]
	
	if crop == True:
		crops = []
		bbox = None
		for frame in frames:
			frame_bbox = frame.getbbox()
			if bbox is None:
				bbox = frame_bbox
			else:
				bbox = (
					min(bbox[0], frame_bbox[0]),
					min(bbox[1], frame_bbox[1]),
					max(bbox[2], frame_bbox[2]),
					max(bbox[3], frame_bbox[3])
				)
		for frame in frames:
			crop = frame.crop(bbox)
			crops.append(crop)
		frames = crops
		
	frames[0].save(output, format="GIF", append_images=frames[1:],
               save_all=True, duration=gap, disposal=2, optimize=False, loop=0) #disposal 2 to avoid trail of frames

@Gooey(program_description="Makes a customized gif out of png files. Will reset on completion for rapid usage.", tabbed_groups=True)
def main():
	cwd = os.getcwd()
	defaultOutputPath = "output"
	
	parser = GooeyParser()
	input_group = parser.add_argument_group(
		"Input",
		"Name/path of the folder containing the numbered png files.")
	input_group.add_argument("-if", "--inputFolder",
		default=os.path.join(cwd, defaultOutputPath),
		help="Folder name/path to get the frames. Defaults to current.",
		widget="DirChooser")
		
	gif_group = parser.add_argument_group(
		"Options",
		"Set the parameters for the gif creation.")
	gif_group.add_argument("-s", "--start",
		type=int,
		default=1,
		help="Frame# to start the gif.",
		widget="IntegerField",
		gooey_options={'max':10000})
	gif_group.add_argument("-p", "--pause",
		type=int,
		default=1,
		help="Frame# to pause the gif. Equate restart to omit.",
		widget="IntegerField",
		gooey_options={'max':10000})
	gif_group.add_argument("-r", "--restart",
		type=int,
		default=1,
		help="Frame# to restart the gif. Equate pause to omit.",
		widget="IntegerField",
		gooey_options={'max':10000})
	gif_group.add_argument("-e", "--end",
		type=int,
		default=0,
		help="Frame# to end the gif. Put 0 for all frames.",
		widget="IntegerField",
		gooey_options={'max':10000})
	gif_group.add_argument("-g", "--gap",
		default="60 fps",
		help="Time in ms between frames. You can write in fps. 1000/50 or 20 or 50fps are equivalent.")
	gif_group.add_argument("-c", "--crop",
		action="store_true",
		help="Autocrops transparency before making the gif.")
		
	output_group = parser.add_argument_group(
		"Output",
		"Customize output options.",
		gooey_options={'columns':1})
	output_group.add_argument("-of", "--outputFolder",
		default=os.path.join(cwd, defaultOutputPath),
		help="Folder name/path to save the gif.",
		widget="DirChooser")
	output_group.add_argument("-n", "--name",
		default="GIF",
		help="Name for the output gif file. Defaults to 'GIF'.")
	output_group.add_argument("-d", "--default",
		action="store_true",
		help="Set the current values as the new default configuration.")
	

	args = vars(parser.parse_args()) # convert parsed arguments into dict
	folder = args["inputFolder"]
	start = args["start"]
	restart = args["restart"]
	pause = args["pause"]
	end = args["end"]
	gap = args["gap"]
	default=args["default"]
	
	if any("/" in x for x in gap) :
		gap = float(gap.split("/")[0]) / float(gap.split("/")[1])
	if "fps" in gap :
		gap = 1000.0 / float(gap.split("fps")[0])
	gap = float(gap)
	crop = args["crop"]
	name = args["name"]
	new = name + ".gif"
	out = os.path.abspath(args["outputFolder"])
	output = os.path.join(out, new)
	j=2
	while os.path.exists(output):
		new = name + f"#{j}.gif"
		output = os.path.join(out, new)
		j+=1
	
	files = sorted(glob.glob(f"{folder}/*.png"), key=number) #sorts the files by frame#number
	
	if len(files) == 0:
		print("\nNo png files found in ",folder,"\n")
		exit()
	
	if end < start :
		end = len(files)
	if pause == restart:
		pause = start
		restart = start + 1
		
	go = time.perf_counter()
			
	gif(files, start, pause, restart, end, gap, crop, output)
	
	count = (pause - start + 1) + (end - restart + 1)
	stop = time.perf_counter()
	elapsed = stop - go
	print("\nGathered {} image file(s) into {} in {:.3f}s".format(count, new, elapsed))
    
	if default == True:
		folder = repr(folder) #Convert quotes into double quotes so the address is written later with quotes + deal with escape characters
		gap = repr(args["gap"])
		name = repr(args["name"])
		output = repr(args["outputFolder"])
		data=[folder, start, pause, restart, end, gap, name, output]
		j=0
		with open("Gif.py","r") as e:
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
		with open("Gif.py","w") as e:
			e.write(''.join(new))
			e.close()
	
if __name__ == "__main__":
    result = main()
    sys.exit(result)
