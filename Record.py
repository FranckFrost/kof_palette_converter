import os
import glob
import sys
import subprocess
from gooey import Gooey, GooeyParser

@Gooey(program_description="Records the upper left 640x448 portion of the screen where the game's window should be.", tabbed_groups=True)
def main():
	
	ProgramFiles = os.path.abspath(os.environ["ProgramW6432"])
	VLCpath = "VideoLAN\VLC\\vlc.exe"
	cwd = os.path.abspath(os.getcwd())
	defaultRecordPath = "Videos"
	
	parser = GooeyParser()
	app_group = parser.add_argument_group(
		"Application",
		"Pick the program. Only VLC is confirmed to work as of now.",
		gooey_options={'columns':1})
	app_group.add_argument("VLC",
		default=os.path.join(ProgramFiles, VLCpath),
		help="Path to VLC's exe file.",
		widget="FileChooser")
	app_group.add_argument("-i", "--inp",
		default=os.path.join(os.path.expanduser("~"), "Videos"),
		help="VLC's output folder. Hence your video folder if unchanged in VLC's settings.",
		widget="DirChooser")
		
	capture_group = parser.add_argument_group(
		"Capture",
		"Set the parameters for the screen capture.")
	capture_group.add_argument("-t", "--top",
		type=int,
		default=87,
		help="Number of pixels to crop from the top.",
		widget="IntegerField",
		gooey_options={'max':10000})
	capture_group.add_argument("-l", "--left",
		type=int,
		default=0,
		help="Number of pixels to crop from the left.",
		widget="IntegerField",
		gooey_options={'max':10000})
	capture_group.add_argument("-w", "--width",
		type=int,
		default=640,
		help="Width of the screen capture field.",
		widget="IntegerField",
		gooey_options={'max':10000})
	capture_group.add_argument("-he", "--height",
		type=int,
		default=355,
		help="Height of the screen capture field.",
		widget="IntegerField",
		gooey_options={'max':10000})
	capture_group.add_argument("-f", "--fps",
		type=float,
		default=60.0,
		help="Number of frames per second to capture. Should match the game's framerate.",
		widget="DecimalField")
		
	output_group = parser.add_argument_group(
		"Output",
		"Customize output options, including setting a default configuration.",
		gooey_options={'columns':1})
	output_group.add_argument("-o", "--out",
		default=os.path.join(cwd, defaultRecordPath),
		help="Folder name/path to save the recording.",
		widget="DirChooser")
	output_group.add_argument("-n", "--name",
		default='VLC',
		help="Name of the recording. Defaults to 'VLC'.")
	output_group.add_argument("-d", "--default",
		action="store_true",
		help="Set the current values as the new default configuration.")
		
	args = vars(parser.parse_args()) # convert parsed arguments into dict
	VLC = args["VLC"]
	top = str(args["top"])
	left = str(args["left"])
	width = str(args["width"])
	height = str(args["height"])
	fps = str(args["fps"])
	inp = os.path.abspath(args["inp"])
	out = os.path.abspath(args["out"])
	name = args["name"]
	default = args["default"]
	
	if not os.path.exists(out):
		os.makedirs(out)
		print("\nCreated record directory \"{}\"".format(out))

	path = os.path.join(inp, "*.avi")
	before = len(glob.glob(path))

	command = VLC+" screen:// :screen-fps="+fps+" :live-caching=300 :screen-top="+top+" :screen-left="+left+" :screen-width="+width+" :screen-height="+height
	subprocess.call(command)

	new = name + ".avi"
	output = os.path.join(out, new)
	j=2
    
	path = os.path.join(inp, "*.avi")
	files = sorted(glob.glob(path), key=os.path.getmtime, reverse=True) #Sorts avi files by latest modification
	after = len(files)
	number = after - before
	if number == 0:
		print("\nNo new recording found in directory \"{}\". Make sure to press the red button on the VLC window to start/end the recording.".format(inp))
	while number > 0:
		avi = files[number-1]
		number-=1
		while os.path.exists(output):
			new = name + f"#{j}.avi"
			output = os.path.join(out, new)
			j+=1
		os.rename(avi, output)
		print("\nSaved recording {} in directory \"{}\"".format(new, out))
    
	if default == True:
		VLC = repr(VLC) #Convert quotes into double quotes so the address is written later with quotes + deal with escape characters
		inp = repr(args["inp"])
		out = repr(args["out"])
		name = repr(name)
		data=[VLC, inp, top, left, width, height, fps, out, name]
		j=0
		with open("Record.py","r") as e:
			new = e.read().splitlines(True) #Grab each line and keep the \n endline character
			e.close()
		for i in range(len(data)):
			while new[j].find("default=") == -1:
				j+=1
			l = new[j].split("default=")
			new_line = l[0] + "default=" + data[i] + ',\n'
			if new[j-1].find('#') == -1 and new[j] != new_line:
				new[j] = '#' + new[j].replace("default=","default(base)=")
				j+=1
				new.insert(j, new_line)          
			else:
				new[j] = new_line
			j+=1
		with open("Record.py","w") as e:
			e.write(''.join(new))
			e.close()

if __name__ == "__main__":
    result = main()
    sys.exit(result)
