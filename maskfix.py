import os
import cv2 as cv
import numpy as np
import xml.etree.ElementTree as ET
from sys import argv
from glob import glob
from math import sqrt
from time import sleep
from shutil import copyfile

thickness = 5
emptyedge = 0.1
zoom = 0
x_, y_ = 0, 0  # curent mouse coords
ux, uy = 0, 0  # current window pose
L , R  = 0, 0  # current button state
scale = 1
D , C = 0, 0
T = 0
I = 0
object_ = "ingredient" # 
old_path = '/home/moley/Desktop/chesnut_mushroom_risotto/'
width = 1920
heigh = 1080

name_list = ['container-empty',\
			 'container-busy',\
			 'pot_medium_ruffoni',\
			 'pot_medium_ruffoni_handle',\
			 'ingredient',\
			 'hand',\
			 'hand_2',\
			 'spatula']

def mouse(event, x, y, flags, param):
	# print(flags)
	global x_
	global y_
	global ux
	global uy
	global L
	global D, C
	global zoom
	if event == cv.EVENT_MOUSEMOVE:
		if zoom:
			x_, y_ = x, y
		else:
			x_, y_ = int(x*scale), int(y*scale)

		x_, y_ = x_+ux, y_+uy

	if flags == 17: # shift + LKM
		L = 1
	if flags != 17:
		L = 0
	if flags == 20: # shift + SKM
		D = 1
	if flags != 20:
		D = 0
	if flags == 12: # ctrl + SKM
		C = 1
	if flags != 12:
		C = 0
	# print(flags)

def choose(root):
	global x_, y_
	global L, T, I, object_
	obj_ind = -1
	if L != 0 or T != 0:
		for i in range(2,len(root)):
			if ((root[i][0].text != object_) - I) and \
				int(root[i][1][0].text) <= x_ and \
				int(root[i][1][1].text) >= x_ and \
				int(root[i][1][2].text) <= y_ and \
				int(root[i][1][3].text) >= y_:
				obj_ind = i-2
				print(root[i][0].text)
	key = cv.waitKey(1)
	return obj_ind, key



def update_xml(mask, root, object_index, sx=0, sy=0, ex=width, ey=heigh):
	xmin = 10000
	xmax = 0
	ymin = 10000
	ymax = 0
	h,w = mask.shape
	for j in range(sy, ey):
		for i in range(sx, ex):
			if mask[j][i] > 10: # threshold
				if i<xmin: xmin=i
				if i>xmax: xmax=i
				if j<ymin: ymin=j
				if j>ymax: ymax=j
	# print(xmin,xmax, ymin,ymax)
	root[object_index+2][1][0].text = str(xmin)
	root[object_index+2][1][1].text = str(xmax)
	root[object_index+2][1][2].text = str(ymin)
	root[object_index+2][1][3].text = str(ymax)

def update_xml_fast(root, object_index, xmin, xmax, ymin, ymax):
	root[object_index+2][1][0].text = str(xmin)
	root[object_index+2][1][1].text = str(xmax)
	root[object_index+2][1][2].text = str(ymin)
	root[object_index+2][1][3].text = str(ymax)

# TODO: research
# adding new object in the end of xml-file 
def add_object(root, object_name):
	obj = ET.Element('object')
	root.append(obj)
	tmp = ET.SubElement(obj, 'name')
	tmp.text = object_name
	tmp  = ET.SubElement(obj, 'bndbox')
	tmp2 = ET.SubElement(tmp, 'xmin')
	tmp2.text = '0'
	tmp2 = ET.SubElement(tmp, 'xmax')
	tmp2.text = '0'
	tmp2 = ET.SubElement(tmp, 'ymin')
	tmp2.text = '0'
	tmp2 = ET.SubElement(tmp, 'ymax')
	tmp2.text = '0'
	tmp  = ET.SubElement(obj, 'pose3D')
	tmp2 = ET.SubElement(tmp, 'x')
	tmp2.text = '0'
	tmp2 = ET.SubElement(tmp, 'y')
	tmp2.text = '0'
	tmp2 = ET.SubElement(tmp, 'z')
	tmp2.text = '0'
	tmp2 = ET.SubElement(tmp, 'r1')
	tmp2.text = '0'
	tmp2 = ET.SubElement(tmp, 'r2')
	tmp2.text = '0'
	tmp2 = ET.SubElement(tmp, 'r3')
	tmp2.text = '0'

def drawbb(img, root):
	global I, object_
	draw = img.copy()
	for i in range(2,len(root)):
		if ((root[i][0].text != object_) - I):
			cv.line(draw, (int(root[i][1][0].text),int(root[i][1][2].text)), (int(root[i][1][1].text),int(root[i][1][2].text)), (0,255,0), 1)
			cv.line(draw, (int(root[i][1][1].text),int(root[i][1][2].text)), (int(root[i][1][1].text),int(root[i][1][3].text)), (0,255,0), 1)
			cv.line(draw, (int(root[i][1][1].text),int(root[i][1][3].text)), (int(root[i][1][0].text),int(root[i][1][3].text)), (0,255,0), 1)
			cv.line(draw, (int(root[i][1][0].text),int(root[i][1][3].text)), (int(root[i][1][0].text),int(root[i][1][2].text)), (0,255,0), 1)
			cv.putText(draw, '%s'%(root[i][0].text) , (int(root[i][1][0].text),int(root[i][1][2].text)), cv.FONT_HERSHEY_SIMPLEX, 1, (0,0,255), 1)
	return draw


def main():
	global x_, y_
	global ux, uy
	global L, T, D, C, I
	global zoom
	path = os.getcwd()
	imglist = sorted(glob(path+'/*[0-9][0-9][0-9].png'))

	object_name = 'object'
	name        = 'Main Form'
	start_index = 0
	action      = 0
	# 0 - edit 
	# 1 - delete
	# 2 - add (have additional argument "object_name")


	if len(argv) > 1:
		for i in range(1,len(argv)):
			if argv[i] == '-i' and len(argv)>i+1:
				start_index = (int)(argv[i+1])
			if argv[i] == '-n' and len(argv)>i+1:
				object_name      = argv[i+1]

	cv.namedWindow(name)


	# for image
	img_index = start_index
	while img_index < len(imglist) and img_index >= 0:
		L = 0
		png = cv.imread(imglist[img_index])
		tree = ET.parse(imglist[img_index][0:-3]+'xml')
		root = tree.getroot()
		bmp = drawbb(png, root)

		h, w, _ = png.shape

		cv.putText(bmp, '%.3d'%img_index , (30,30), cv.FONT_HERSHEY_SIMPLEX, 1, (0,0,255), 1)
		cv.putText(bmp, '%d %s'%(action,object_name)  , (30,60), cv.FONT_HERSHEY_SIMPLEX, 1, (0,0,255), 1)

		cv.namedWindow(name)
		cv.moveWindow(name, 30, 30)
		frame = cv.resize(bmp,(int(w/scale), int(h/scale)))
		cv.imshow(name,frame)
		cv.setMouseCallback(name, mouse)
		object_index = -1
		if   action == 0: # edit ---------------------------------------
			key = 0
			zoom = 0
			ux, uy = 0, 0
			while object_index < 0:
				# d == next
				# a == prev
				object_index, key = choose(root)
				
				if key == ord('a'):
					img_index -= 1
					break
				if key == ord('d'):
					img_index += 1
					break
				if key == ord('i'):
					I = 1 - I
					break
				if key == ord('`'):
					action = 0
					break
				if key == ord('1'):
					action = 1
					break
				if key == ord('2'):
					action = 2
					break
				if key == ord('3'):
					action = 3
					break
				if key == 27: #esc
					exit()
			zoom = 1
			sleep(0.4)

			if(object_index >= 0):
				print(object_index, root[object_index+2][0].text, "\t", imglist[img_index][0:-4]+'_%d.png'%object_index)
				mask = cv.imread(imglist[img_index][0:-4]+'_%d.png'%object_index)
				_, mask = cv.threshold(mask,127,255,cv.THRESH_BINARY)

				ux = int((int(root[object_index+2][1][0].text)+int(root[object_index+2][1][1].text))/2)
				uy = int((int(root[object_index+2][1][2].text)+int(root[object_index+2][1][3].text))/2)
				d  = max(int(root[object_index+2][1][1].text)-int(root[object_index+2][1][0].text), int(root[object_index+2][1][3].text)-int(root[object_index+2][1][2].text))
				d  = max(d, 400)
				ux = int(max(0, ux-d))
				uy = int(max(0, uy-d))
				lx = int(min(w, ux+d*2))
				ly = int(min(h, uy+d*2))
				draw_type = 1
				point_list = []
				while 1:
					frame = cv.addWeighted(png, 0.5, mask, 0.5, 0)  # alpha-channel
					frame = cv.circle(frame, (x_,y_), thickness, (0,0,255), 1)  # drawing cursor
					frame = cv.circle(frame, (x_,y_), 0, (0,0,255), -1)  # drawing cursor
					if draw_type == 1 and len(point_list) > 0:
						cv.line(frame, (point_list[-1][0],point_list[-1][1]), (x_,y_), (255,255,255), 1)
					# frame = cv.resize(frame,(w//2, h//2))
					view = cv.resize(frame,(w//2, h//2))
					view = frame[uy:ly,ux:lx ]
					cv.imshow(name,view)
					

					if L:
						# drawing container mask
						if draw_type == 1 and ux<=x_ and x_<=lx and uy<=y_ and y_<=ly:
							if len(point_list)%2 == 0:
								mask = cv.circle(mask, (x_,y_), thickness-2, (255,255,255),-1)
							else:
								mask = cv.line(mask, (point_list[-1][0],point_list[-1][1]), (x_,y_), (255,255,255), thickness)
							point_list.append([x_,y_])
							sleep(0.2)
						elif draw_type == 2:
							point_list.append([x_,y_])
							# mask = cv.circle(mask, (x_,y_), 1, (255,255,255), -1)
							mask[y_,x_] = (255,255,255)
							if len(point_list) == 4:
								ax = min([point_list[0][0],point_list[1][0],point_list[2][0],point_list[3][0]])
								ay = min([point_list[0][1],point_list[1][1],point_list[2][1],point_list[3][1]])
								bx = max([point_list[0][0],point_list[1][0],point_list[2][0],point_list[3][0]])
								by = max([point_list[0][1],point_list[1][1],point_list[2][1],point_list[3][1]])
								cx = (bx+ax)//2
								cy = (by+ay)//2
								dx = (bx-ax)//2
								dy = (by-ay)//2
								mask =  np.zeros((h,w,3), np.uint8)
								mask = cv.ellipse (mask, (cx,cy), (dx,dy), 0,0,360,(255,255,255), -1)
							sleep(0.2)
						elif draw_type == 3:
							point_list.append([x_,y_])
							mask = cv.circle(mask, (x_,y_), 1, (255,255,255), -1)
							if len(point_list) == 2:
								mask =  np.zeros((h,w,3), np.uint8)
								r = int(sqrt((point_list[0][0]-point_list[1][0])**2 + (point_list[0][1]-point_list[1][1])**2))
								mask = cv.circle(mask, (point_list[0][0],point_list[0][1]), r, (255,255,255), -1)
							sleep(0.2)
					# end if L:

					if D:
						mask = cv.circle(mask, (x_,y_), thickness, (255,255,255),-1)
					# end if R:

					if C:
						mask = cv.circle(mask, (x_,y_), thickness, (0,0,0),-1)
					# end if R:


					key = cv.waitKey(10)  # reading key
					
					if   key == ord('1'):
						draw_type = 1
						point_list = []
					elif key == ord('2'):
						draw_type = 2
						point_list = []
					elif key == ord('3'):
						draw_type = 3
						point_list = []
					elif key == ord('n'):  # create new mask
						point_list = []
						mask =  np.zeros((h,w,3), np.uint8)
					# elif key == ord('b'):  # create new mask
					# 	mask_ = np.zeros((h+2,w+2,3))
					# 	mask_[1:-1,1:-1] = mask
					# 	_1, _2, mask, _4	=	cv.floodFill(mask, mask_, (x_,y_), 255)

					elif key == ord('s'):  # save mask 
						mask = cv.cvtColor(mask, cv.COLOR_BGR2GRAY)
						cv.imwrite(imglist[img_index][0:-4]+'_%d.png' % object_index, mask)
						# update_xml(mask, root, object_index)
						update_xml(mask, root, object_index, ux, uy, lx, ly)
						tree.write(imglist[img_index][0:-3]+'xml')
						break
					elif key == ord('m'):  # save mask 
						print(imglist[img_index][0:-4]+'_%d.png' % object_index)
						gray = cv.cvtColor(mask, cv.COLOR_BGR2GRAY)
						cv.imwrite(imglist[img_index][0:-4]+'_%d.png' % object_index, gray)
						mask_saved = 1
					# elif key == ord('f'):
					# 	T = 1
					# 	old_tree = ET.parse(old_path+os.path.basename(imglist[img_index])[0:-3]+'xml')
					# 	old_root = old_tree.getroot()
					# 	old_index, _ = choose(old_root)
					# 	if old_index > -1:
					# 		mask = cv.imread(old_path+os.path.basename(imglist[img_index])[0:-4]+'_%d.png' % old_index)
					# 		_, mask = cv.threshold(mask,1,255,cv.THRESH_BINARY)
					# 		# mask = cv.imread(imglist[img_index][0:-4]+'_%d.png'%object_index)
					# 	T = 0
					elif key == ord('c'):
						T = 1
						old_tree = ET.parse(imglist[img_index-1][0:-3]+'xml')
						old_root = old_tree.getroot()
						old_index, _ = choose(old_root)
						if old_index > -1:
							mask = cv.imread(imglist[img_index-1][0:-4]+'_%d.png' % old_index)
						T = 0
					elif key == ord('e'):
						break
					elif key == 27: # esc
						exit()

		elif action == 1: # delete -----------------------------------------
			key = 0
			zoom = 0
			object_index = -1
			while object_index < 0:
				# d == next
				# a == prev
				object_index, key = choose(root)
				if key == ord('a'):
					img_index -= 1
					break
				if key == ord('d'):
					img_index += 1
					break
				if key == ord('`'):
					action = 0
					break
				if key == ord('1'):
					action = 1
					break
				if key == ord('2'):
					action = 2
					break
				if key == ord('3'):
					action = 3
					break
				if key == ord('i'):
					I = 1 - I
					break
				if key == 27: #esc
					exit()
			sleep(0.2)
			if object_index >= 0:
				for i in range(object_index, len(root)-3):
					copyfile(imglist[img_index][0:-4]+'_%d.png'%(i+1), imglist[img_index][0:-4]+'_%d.png'%i)
				os.remove(imglist[img_index][0:-4]+'_%d.png'%(len(root)-3))

				root.remove(root[object_index+2])
				tree.write(imglist[img_index][0:-3]+'xml')
				sleep(0.3)

		elif action == 2: # add -----------------------------------------
			ux, uy = 0, 0
			lx, ly = w, h
			zoom = 0
			skip = 1
			while 1:
				# object_index, key = choose(root)
				key = cv. waitKey(10)

				if L:
					ux = max(0, x_-w//2)
					uy = max(0, y_-h//2)
					lx = min(w, x_+w//2)
					ly = min(h, y_+h//2)
					skip = 0
					break;
				# d == next
				# a == prev
				
				if key == ord('a'):
					img_index -= 1
					break
				if key == ord('d'):
					img_index += 1
					break
				if key == ord('`'):
					action = 0
					break
				if key == ord('1'):
					action = 1
					break
				if key == ord('2'):
					action = 2
					break
				if key == ord('3'):
					action = 3
					break
				if key == ord('i'):
					I = 1 - I
					break
				if key == ord('n'):
					menu = frame.copy()
					for i in range(len(name_list)):
						cv.putText(menu, '%d %s'%(i, name_list[i]) , (30,90 + 30*i), cv.FONT_HERSHEY_SIMPLEX, 1, (0,255,0), 1)
					cv.imshow(name, menu)
					key_ = 0
					while key_!=ord('e'):
						key_ = cv.waitKey(0)
						if (key_>=ord('0') and key_<=ord('9')):
							object_name = name_list[int(chr(key_))]
							break
					break

				if key == 27: #esc
					exit()
			zoom = 1

			if skip==0:
				sleep(0.2)
				mask =  np.zeros((h,w,3), np.uint8)
				
				draw_type = 1
				point_list = [] # for containers
				saved = 0
				mask_saved = 0
				xmin, xmax, ymin, ymax = 0, 0, 0, 0

				while 1:
					frame = cv.addWeighted(png, 0.5, mask, 0.5, 0)  # alpha-channel
					frame = cv.circle(frame, (x_,y_), thickness, (0,0,255), 1)  # drawing cursor
					frame = cv.circle(frame, (x_,y_), 1, (0,0,255), 1)  # drawing cursor
					if draw_type == 1 and len(point_list) > 1:
						cv.line(frame, (point_list[-1][0],point_list[-1][1]), (x_,y_), (255,255,255), 1)
						# frame = cv.resize(frame,(w//2, h//2))
					view = cv.resize(frame,(w//2, h//2))
					view = frame[uy:ly,ux:lx ]
					cv.imshow(name,view)
					
					if L:
						# drawing container mask
						if draw_type == 1 and ux<=x_ and x_<=lx and uy<=y_ and y_<=ly:
							if len(point_list)%2 == 0:
								mask = cv.circle(mask, (x_,y_), thickness-2, (255,255,255),-1)
							else:
								# ax = x_*emptyedge+point_list[-1][0]*(1-emptyedge)
								# ay = y_*emptyedge+point_list[-1][1]*(1-emptyedge)
								# bx = x_*(1-emptyedge)+point_list[-1][0]*emptyedge
								# by = y_*(1-emptyedge)+point_list[-1][1]*emptyedge
								# mask = cv.line(mask, (int(ax),int(ay)), (int(bx),int(by)), (255,255,255), thickness)
								mask = cv.line(mask, (point_list[-1][0],point_list[-1][1]), (x_,y_), (255,255,255), thickness)
							point_list.append([x_,y_])
							# if len(point_list) == 4:
							# 	ax = point_list[0][0]*emptyedge+point_list[-1][0]*(1-emptyedge)
							# 	ay = point_list[0][1]*emptyedge+point_list[-1][1]*(1-emptyedge)
							# 	bx = point_list[0][0]*(1-emptyedge)+point_list[-1][0]*emptyedge
							# 	by = point_list[0][1]*(1-emptyedge)+point_list[-1][1]*emptyedge
							# 	mask = cv.line(mask, (int(ax),int(ay)), (int(bx),int(by)), (255,255,255), thickness)
							sleep(0.2)
						elif draw_type == 2:
							point_list.append([x_,y_])
							# mask = cv.circle(mask, (x_,y_), 1, (255,255,255), -1)
							mask[y_,x_] = (255,255,255)
							if len(point_list) == 4:
								ax = min([point_list[0][0],point_list[1][0],point_list[2][0],point_list[3][0]])
								ay = min([point_list[0][1],point_list[1][1],point_list[2][1],point_list[3][1]])
								bx = max([point_list[0][0],point_list[1][0],point_list[2][0],point_list[3][0]])
								by = max([point_list[0][1],point_list[1][1],point_list[2][1],point_list[3][1]])
								cx = (bx+ax)//2
								cy = (by+ay)//2
								dx = (bx-ax)//2
								dy = (by-ay)//2
								mask =  np.zeros((h,w,3), np.uint8)
								mask = cv.ellipse (mask, (cx,cy), (dx,dy), 0,0,360,(255,255,255), -1)
							sleep(0.2)
						elif draw_type == 3:
							point_list.append([x_,y_])
							mask = cv.circle(mask, (x_,y_), 1, (255,255,255), -1)
							if len(point_list) == 2:
								mask =  np.zeros((h,w,3), np.uint8)
								r = int(sqrt((point_list[0][0]-point_list[1][0])**2 + (point_list[0][1]-point_list[1][1])**2))
								mask = cv.circle(mask, (point_list[0][0],point_list[0][1]), r, (255,255,255), -1)

							sleep(0.2)
					# end if L:

					key = cv.waitKey(10)  # reading key
					if   key == ord('1'):
						draw_type = 1
						point_list = []
					elif key == ord('2'):
						draw_type = 2
						point_list = []
					elif key == ord('3'):
						draw_type = 3
						point_list = []
					elif key == ord('n'):  # create new mask
						point_list = []
						saved = 0
						mask =  np.zeros((h,w,3), np.uint8)
					elif key == ord('s'):  # save xml 
						mask = cv.cvtColor(mask, cv.COLOR_BGR2GRAY)
						if mask_saved == 0:
							cv.imwrite(imglist[img_index][0:-4]+'_%d.png' % (len(root)-2), mask)
						add_object(root, object_name)
						if saved:
							update_xml_fast(root, len(root)-3, xmin, xmax, ymin, ymax)
						else:
							update_xml(mask, root, len(root)-3, ux,uy, lx, ly)
						tree.write(imglist[img_index][0:-3]+'xml')
						break
					elif key == ord('m'):  # save mask 
						print(imglist[img_index][0:-4]+'_%d.png' % (len(root)-2))
						gray = cv.cvtColor(mask, cv.COLOR_BGR2GRAY)
						cv.imwrite(imglist[img_index][0:-4]+'_%d.png' % (len(root)-2), gray)
						mask_saved = 1
					elif key == ord('c'):
						T = 1
						old_tree = ET.parse(imglist[img_index-1][0:-3]+'xml')
						old_root = old_tree.getroot()
						old_index, _ = choose(old_root)
						print(old_index, imglist[img_index-1][0:-3]+'xml')
						if old_index > -1:
							mask = cv.imread(imglist[img_index-1][0:-4]+'_%d.png'%old_index)
							print(imglist[img_index-1][0:-4]+'_%d.png'%old_index)
							xmin = old_root[old_index+2][1][0].text
							xmax = old_root[old_index+2][1][1].text
							ymin = old_root[old_index+2][1][2].text
							ymax = old_root[old_index+2][1][3].text
							saved = 1
						T = 0
					elif key == ord('e'):
						break
					elif key == 27: # esc
						exit()

		elif action == 3: # change_name -----------------------------------------
			key = 0
			zoom = 0
			object_index = -1
			while object_index < 0:
				# d == next
				# a == prev
				object_index, key = choose(root)
				
				if key == ord('a'):
					img_index -= 1
					break
				if key == ord('d'):
					img_index += 1
					break
				if key == ord('`'):
					action = 0
					break
				if key == ord('1'):
					action = 1
					break
				if key == ord('2'):
					action = 2
					break
				if key == ord('3'):
					action = 3
					break
				if key == ord('i'):
					I = 1 - I
					break
				if key == ord('n'):
					menu = frame.copy()
					for i in range(len(name_list)):
						cv.putText(menu, '%d %s'%(i, name_list[i]) , (30,30*i), cv.FONT_HERSHEY_SIMPLEX, 1, (0,255,0), 1)
					cv.imshow(name, menu)
					key_ = 0
					while key_!=ord('e'):
						key_ = cv.waitKey(0)
						if (key_>=ord('0') and key_<=ord('9')):
							object_name = name_list[int(chr(key_))]
							break
					break
				if key == 27: #esc
					exit()
			sleep(0.2)
			if object_index >= 0:
				root[object_index+2][0].text = object_name
				tree.write(imglist[img_index][0:-3]+'xml')
				sleep(0.3)

		# cv.destroyWindow(name)

	cv.destroyAllWindows()

if __name__ == '__main__':
	main()

